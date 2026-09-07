"""
Ingesta de documentos PDF a la base vectorial.

Flujo: PDF → Markdown (pymupdf4llm) → chunking en fragmentos con overlap →
almacenamiento en ChromaDB con metadatos (fuente + número de chunk).

El chunking es clave para el RAG: permite recuperar solo los fragmentos
relevantes de un documento (y no el PDF completo), lo que mejora la
precisión y ahorra tokens en el prompt.
"""
import os
import uuid
import re
import pymupdf4llm
from app import settings
from app.database import get_collection


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Divide el texto en fragmentos (chunks) de tamaño aproximado con overlap,
    RESPETANDO los límites de los encabezados Markdown (###, ##, #).

    Algoritmo (autocontenido, sin dependencias externas):
    1. Separa el texto en "secciones" usando los encabezados Markdown como
       límites DUROS: un encabezado abre una nueva sección y NUNCA se corta a
       mitad de una sección (así no se parten los bloques conceptuales de un
       trámite, p. ej. los "requisitos" a la mitad).
    2. Las secciones se agrupan (respetando su orden) hasta alcanzar
       `chunk_size` caracteres; cuando se pasa, se cierra el chunk.
    3. Mantiene un solapamiento de `overlap` caracteres entre chunks para no
       perder contexto en los bordes.

    Retorna lista de strings (fragmentos).
    """
    # Separar por encabezados Markdown. El regex captura el encabezado junto
    # con su cuerpo hasta el siguiente encabezado. Lanza división por línea.
    lines = text.splitlines()
    secciones: list[str] = []
    actual: list[str] = []

    def flush():
        nonlocal actual
        if actual:
            secciones.append("\n".join(actual).strip())
            actual = []

    for line in lines:
        if re.match(r"^\s{0,3}#{1,6}\s+", line):
            # Encabezado Markdown: cierra la sección anterior y abre una nueva.
            flush()
            actual.append(line)
        else:
            # Párrafo normal: acumular.
            actual.append(line)
    flush()

    # Si no hay encabezados, tratar todo el texto como una sola sección.
    if not secciones:
        secciones = [text]

    chunk_regex = re.compile(r"^\s{0,3}#{1,6}\s+")
    chunks: list[str] = []
    buffer: list[str] = []

    def buffer_len() -> int:
        return sum(len(s) + 2 for s in buffer) + len(buffer)  # +2 por doble \n

    for sec in secciones:
        if not sec:
            continue
        # Si una sección individual supera chunk_size, partirla por palabras
        # (caso raro: sección sin encabezado pero muy larga). Se conserva el
        # prefijo de encabezado en cada fragmento si la sección lo tenía.
        if len(sec) > chunk_size:
            flash = True
            # Extraer posible encabezado como prefijo a repetir
            prefijo = ""
            m = chunk_regex.match(sec)
            if m:
                prefijo = sec.splitlines()[0] + "\n"
            cuerpo = "\n".join(sec.splitlines()[1:]) if m else sec
            restante = cuerpo
            while len(restante) > chunk_size:
                cut = restante.rfind(" ", 0, chunk_size)
                if cut == -1:
                    cut = chunk_size
                chunks.append((prefijo + restante[:cut]).strip())
                restante = restante[cut:].strip()
            # La parte restante vuelve a la cola de agrupación
            if restante:
                buffer = [prefijo + restante]
            else:
                buffer = []
            flash = False
            # buffer_len recalcula
            continue

        # Agrupar secciones hasta llenar el chunk
        if not buffer:
            buffer = [sec]
        elif buffer_len() + len(sec) + 2 <= chunk_size:
            buffer.append(sec)
        else:
            chunks.append("\n\n".join(buffer).strip())
            # Overlap: repetir el final del chunk anterior pegándolo como
            # contexto antes de la nueva sección.
            tail = buffer[-1][-overlap:] if overlap else ""
            buffer = ([tail] if tail else []) + [sec]

    if buffer:
        chunks.append("\n\n".join(buffer).strip())

    return [c for c in chunks if c.strip()]


def ingest_pdf(pdf_filename: str):
    """
    Indexa un PDF del directorio `data/` en la base vectorial.

    Si el archivo ya existe, lo reemplaza (rebuild de sus chunks).
    """
    pdf_path = os.path.join(settings.DATA_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"[ingesta] Archivo no encontrado: {pdf_path}")
        return 0

    print(f"[ingesta] Procesando {pdf_filename}...")

    # 1. Convertir PDF a Markdown
    md_text = pymupdf4llm.to_markdown(pdf_path)

    return _indexar_texto(md_text, pdf_filename)


def ingest_markdown(md_filename: str):
    """
    Indexa un archivo Markdown (`.md`) del directorio `data/`.

    Los Markdown (p. ej. trámites extraídos de páginas web) ya están en
    texto limpio, así que no requieren conversión con pymupdf4llm.

    Si el archivo ya existe, lo reemplaza (rebuild de sus chunks).
    """
    md_path = os.path.join(settings.DATA_DIR, md_filename)
    if not os.path.exists(md_path):
        print(f"[ingesta] Archivo no encontrado: {md_path}")
        return 0

    print(f"[ingesta] Procesando {md_filename}...")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    return _indexar_texto(md_text, md_filename)


def _indexar_texto(md_text: str, fuente: str) -> int:
    """Chunking + persistencia en ChromaDB. Fuente = nombre del archivo."""
    # 2. Chunking
    chunks = _split_text(md_text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        print(f"[ingesta] No se extrajo texto de {fuente}")
        return 0

    # 3. Eliminar chunks previos del mismo documento (rebuild)
    collection = get_collection()
    existing = collection.get(where={"source": fuente})
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])
        print(f"[ingesta]   - eliminados {len(existing['ids'])} chunks previos")

    # 4. Insertar con IDs únicos y metadatos por trozo
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {"source": fuente, "chunk_index": i} for i in range(len(chunks))
    ]
    collection.add(documents=chunks, metadatas=metadatas, ids=ids)

    print(f"[ingesta] ✓ {fuente}: {len(chunks)} chunks indexados")
    return len(chunks)


def delete_original_file(pdf_filename: str):
    """
    Elimina el archivo físico (PDF/MD) de data/ CONSERVANDO sus chunks en
    ChromaDB.

    Es el flujo usado tras digitalizar: el texto ya quedó parseado en el
    vector store, así que el original solo ocupa espacio. Se borra el archivo
    pero se mantiene la información indexada para que el bot siga respondiendo.

    Uso típico:
        n = ingest_pdf("beca.pdf")        # indexa
        delete_original_file("beca.pdf")   # borra el PDF, conserva chunks

    La memoria conversacional (chat_history.db) no se toca.
    """
    path = os.path.join(settings.DATA_DIR, pdf_filename)
    if os.path.exists(path):
        os.remove(path)
        print(
            f"[ingesta] ✓ archivo original eliminado (chunks conservados): "
            f"{pdf_filename}"
        )
    else:
        print(f"[ingesta] AVISO: no se encontró {path} para eliminar.")


def delete_pdf(pdf_filename: str):
    """
    Elimina un PDF del sistema Y sus chunks de la base vectorial.

    Es una eliminación SINCRONIZADA: evita dejar chunks huérfanos en
    ChromaDB que provocarían que el bot responda con información de un
    documento que ya no existe.

    - Borra el archivo de data/.
    - Borra de ChromaDB todos los fragmentos con metadata.source == archivo.
    - La memoria conversacional (chat_history.db) NO se toca: borrar un
      documento no debe borrar las conversaciones ya ocurridas.
    """
    pdf_path = os.path.join(settings.DATA_DIR, pdf_filename)

    # 1. Validar que el archivo exista para avisar (aunque igual limpiamos DB)
    if not os.path.exists(pdf_path):
        print(
            f"[ingesta] AVISO: no se encontró el archivo {pdf_path}. "
            "Se limpiarán los chunks de la base por si acaso."
        )

    # 2. Borrar chunks del documento desde ChromaDB (fuente = nombre del PDF)
    collection = get_collection()
    existing = collection.get(where={"source": pdf_filename})
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])
        print(
            f"[ingesta] ✓ eliminados {len(existing['ids'])} chunks de "
            f"'{pdf_filename}' de la base vectorial."
        )
    else:
        print(f"[ingesta] No había chunks indexados para '{pdf_filename}'.")

    # 3. Borrar el archivo físico
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        print(f"[ingesta] ✓ archivo eliminado: {pdf_path}")

    # Nota: la memoria conversacional (chat_history.db) se conserva intacta.


def ingest_all():
    """
    Indexa TODOS los documentos del directorio `data/`, recorriendo las
    subcarpetas (categoría) recursivamente.

    - Extensiones aceptadas: `.pdf`, `.md` y `.csv`.
    - Cada archivo se etiqueta en ChromaDB con `source = "categoria/nombre"`,
      de modo que el bot distingue el origen (p. ej. `tramites/x.pdf` o
      `marco_normativo/y.md`). Si el archivo está en la raíz de `data/`
      (sin subcarpeta), `source` es solo el nombre.
    - Las carpetas `chats/` e `inbox/` se ignoran expresamente (no son
      documentos a indexar).

    Se usa tanto en arranque manual como vía `script rclone_sync.sh` /
    `ingest_programado.py`.
    """
    _EXCL = {"chats", "inbox"}  # carpetas que no son documentación a indexar
    if not os.path.isdir(settings.DATA_DIR):
        print(f"[ingesta] No existe el directorio {settings.DATA_DIR}")
        return 0

    total = 0
    # Recorrer recursivamente: (raiz, subdirs, archivos)
    for raiz, subdirs, archivos in os.walk(settings.DATA_DIR):
        # Limpiar carpetas ignoradas para no entrar en ellas
        subdirs[:] = [s for s in subdirs if s.lower() not in _EXCL]
        for f in sorted(archivos):
            ext = f.lower().rsplit(".", 1)[-1]
            if ext not in ("pdf", "md", "csv"):
                # No es documento: dejar pasar (no indexar)
                continue
            ruta = os.path.join(raiz, f)
            # Categoría = subcarpeta relativa a data/ ("" si está en la raíz)
            rel = os.path.relpath(raiz, settings.DATA_DIR)
            categoria = "" if rel == "." else rel
            fuente = f"{categoria}/{f}" if categoria else f

            # Idempotencia: si ya hay chunks de este MISMO source en la base,
            # los borramos primero para no duplicar en corridas repetidas
            # (p. ej. el flujo diario de gdown_sync.sh re-descarga los archivos
            # y vuelve a llamar a ingest_all). Así cada archivo queda indexado
            # EXACTAMENTE una vez.
            try:
                col = get_collection()
                previos = col.get(where={"source": fuente})
                if previos and previos.get("ids"):
                    col.delete(ids=previos["ids"])
                    print(f"[ingesta] ↻ reindexando '{fuente}' (limpiados {len(previos['ids'])} chunks viejos)")
            except Exception as e:
                print(f"[ingesta] AVISO: no se pudo limpiar chunks previos de '{fuente}': {e}")

            try:
                if ext == "pdf":
                    n = _indexar_archivo(ruta, fuente, "pdf")
                elif ext == "md":
                    n = _indexar_archivo(ruta, fuente, "md")
                else:
                    n = _indexar_archivo(ruta, fuente, "csv")
                total += n
                # Una vez indexado, borrar el archivo físico: el conocimiento
                # queda en ChromaDB y `data/` se mantiene como área temporal de
                # descarga (cada corrida de gdown_sync.sh re-descarga de Drive).
                # El chunk ya quedó etiquetado con su source, no se pierde nada.
                if os.path.exists(ruta) and os.path.isfile(ruta):
                    os.remove(ruta)
                    print(f"[ingesta] ✓ archivo indexado y eliminado: {fuente}")
            except Exception as e:
                print(f"[ingesta] ✗ ERROR en {fuente}: {e}")

    print(f"[ingesta] Listo. {total} chunks totales indexados.")
    return total


def _indexar_archivo(ruta_absoluta: str, fuente: str, tipo: str) -> int:
    """
    Extrae/transforma el contenido y lo indexa con la fuente dada.
    tipo ∈ {'pdf','md','csv'}.
    """
    if tipo == "csv":
        texto = _csv_a_texto(ruta_absoluta)
        if not texto or not texto.strip():
            print(f"[ingesta] No se extrajo texto de {fuente}")
            return 0
        # Los CSV representan trámites/servicios: cada bloque "### <Nombre>"
        # ({_csv_a_texto los genera así}) es un TRÁMITE atómico que NO debe
        # partirse a la mitad (el _split_text genérico cortaría los "requisitos"
        # de un trámite al dividir por caracteres). Por eso indexamos cada
        # trámite como un chunk propio e íntegro.
        return _indexar_chunks_atomicos(texto, fuente)
    elif tipo == "md":
        with open(ruta_absoluta, "r", encoding="utf-8") as fh:
            texto = fh.read()
    else:  # pdf
        texto = pymupdf4llm.to_markdown(ruta_absoluta)

    if not texto or not texto.strip():
        print(f"[ingesta] No se extrajo texto de {fuente}")
        return 0
    return _indexar_texto(texto, fuente)


def _indexar_chunks_atomicos(texto: str, fuente: str) -> int:
    """
    Indexa un texto ya estructurado por encabezados "###" (típico de los CSV
    de trámites) como bloques ATÓMICOS: cada bloque "### ..." (hasta el
    siguiente "###") se guarda como UN chunk, sin partirse. Así un trámite o
    servicio completo queda íntegro y fácil de recuperar (requirements, valor,
    lugar, etc. juntos).
    """
    import re as _re

    # Dividir por encabezados de nivel 3 (###) — el format que genera
    # _csv_a_texto. Si no hubiera ninguno, caemos al split genérico.
    parts = _re.split(r"(?m)^(?=###\s)", texto)
    bloques = [p.strip() for p in parts if p and p.strip()]
    if len(bloques) <= 1:
        # Sin encabezados ###: usar el chunking genérico
        return _indexar_texto(texto, fuente)

    # Rebuild: borrar chunks previos de este source
    collection = get_collection()
    existing = collection.get(where={"source": fuente})
    if existing and existing.get("ids"):
        collection.delete(ids=existing["ids"])
        print(f"[ingesta]   - eliminados {len(existing['ids'])} chunks previos")

    ids = [str(uuid.uuid4()) for _ in bloques]
    metadatas = [{"source": fuente, "chunk_index": i} for i in range(len(bloques))]
    collection.add(documents=bloques, metadatas=metadatas, ids=ids)

    print(f"[ingesta] ✓ {fuente}: {len(bloques)} trámites (chunks atómicos) indexados")
    return len(bloques)


def _csv_a_texto(ruta_csv: str) -> str:
    """
    Convierte un CSV a texto legible para el RAG.

    Un CSV es una tabla (encabezado + filas). Para que el bot pueda responder
    consultas sobre sus datos, lo convertimos a líneas de texto donde cada
    fila queda como "columna1: valor1 | columna2: valor2 | ...". El encabezado
    se repite al inicio para dar contexto sobre qué significa cada columna.

    Los CSV de "transparencia activa" del municipio traen bastante datos
    sueltos (nombre del trámite, descripción, requisitos, valor, lugar...).
    Esa información se conserva tal cual.

    Robustez: estos CSV vienen en encoding Latin-1/CP1252 (NO UTF-8) y usan
    ";" como delimitador (NO coma). Si asumimos UTF-8+coma, los acentos se
    rompen y las columnas colapsan. Aquí detectamos ambos automáticamente y
    además limpiemos el HTML (p. ej. "<a href='...'>Enlace</a>") dejando el
    texto visible.
    """
    import csv as _csv
    import re

    # ---- 1. Leer bytes y detectar encoding (Latin-1/CP1252 vs UTF-8) ----
    with open(ruta_csv, "rb") as fb:
        raw = fb.read()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Intentar CP1252 (Windows) primero, luego Latin-1 como fallback.
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")

    # ---- 2. Detectar el delimitador (; , tab) por la cabecera ----
    primera_linea = text.splitlines()[0] if text.splitlines() else ""
    # Contar cuál separador aparece más veces en la cabecera
    delimitador = ","
    mejor = 0
    for cand in (";", ",", "\t"):
        n = primera_linea.count(cand)
        if n > mejor:
            mejor = n
            delimitador = cand

    filas = []
    try:
        lector = _csv.reader(text.splitlines(), delimiter=delimitador)
        for fila in lector:
            filas.append(fila)
    except Exception:
        # Fallback: texto plano separado por el delimitador detectado
        for linea in text.splitlines():
            filas.append([campo.strip() for campo in linea.split(delimitador)])

    if not filas:
        return ""

    encabezado = filas[0]
    cuerpo = filas[1:]
    if not encabezado:
        return ""

    # ---- 3. Limpiar HTML dentro de las celdas (<a href='x'>Texto</a> → Texto) ----
    def _limpiar(valor):
        s = str(valor)
        # Quitar etiquetas HTML pero conservar el texto visible
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    encabezado_limpio = [_limpiar(c) for c in encabezado]

    # ---- 4. Construir la salida como MARKDOWN con encabezados por entrada ----
    # Cada "fila" del CSV (un trámite/servicio o una norma) es un bloque
    # ATÓMICO. Para que el chunker (_split_text) NO lo parta a la mitad,
    # generamos un encabezado Markdown "### <Nombre>" seguido de los demás
    # campos como lista. Así cada entrada queda como un bloque que _split_text
    # respeta íntegro, y el retrieval lo recupera completo.

    # Titulo global según el tipo de contenido (trámites/servicios o normas)
    # Detectamos por las columnas: si hay "denominación"/"norma" → marco
    # normativo; si no → trámites y servicios.
    _h_low = [str(h).lower() for h in encabezado_limpio]
    es_norma = any("denominaci" in h or "norma" in h or "publicaci" in h for h in _h_low)

    # Indices de columnas candidatas a "nombre" de cada entrada
    idx_nombre = None
    for pat in ("denominaci", "nombre", "trámite", "tramite", "descripci"):
        for i, h in enumerate(_h_low):
            if pat in h:
                idx_nombre = i
                break
        if idx_nombre is not None:
            break

    lineas: list[str] = []
    lineas.append("# Marco normativo municipal" if es_norma else "# Trámites y servicios municipales")

    for fila in cuerpo:
        valores = [_limpiar(v) for v in fila]
        if not any(valores):
            continue  # fila vacía

        # Nombre de la entrada: usar la columna detectada; si queda vacío,
        # concatenar primeras columnas no vacías como fallback.
        nombre = ""
        if idx_nombre is not None and idx_nombre < len(valores):
            nombre = valores[idx_nombre]
        if (not nombre) or nombre in ("-", "", "—"):
            # Fallback: primera celda no vacía que no sea "-"
            nombre = next((v for v in valores if v and v not in ("-", "")), "")
        if not nombre:
            continue

        lineas.append(f"### {nombre}")
        # Resto de columnas como "Campo: valor", saltando la del nombre y vacías
        for i, h in enumerate(encabezado_limpio):
            if not h or (i < len(valores) and valores[i] in ("", "-")):
                continue
            # Evitar repetir el nombre como campo si es la misma columna
            if idx_nombre is not None and i == idx_nombre:
                continue
            if i < len(valores) and valores[i]:
                lineas.append(f"- {h}: {valores[i]}")

    return "\n".join(lineas)


if __name__ == "__main__":
    ingest_all()