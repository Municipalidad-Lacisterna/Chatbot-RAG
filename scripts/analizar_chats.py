"""
Análisis de chats de WhatsApp para descubrir preguntas frecuentes municipales.

OBJETIVO
--------
Convertir los exports de WhatsApp de la línea de atención municipal en un
ranking de temas/preguntas que los vecinos repiten más. Con ese ranking
sabemos QUÉ documentos reales crear/priorizar para el chatbot RAG.

ENFOQUE (decisión de producto)
------------------------------
- SOLO usamos los chats para DESCUBRIR preguntas frecuentes (Opción A).
- NO indexamos los chats crudos en ChromaDB (evita bajar la veracidad del
  bot con respuestas humanas informales/erróneas). Ver docs/decision_tono... .

FORMATO DE ENTRADA (export de WhatsApp)
---------------------------------------
[12/08/2026, 09:45:12] Juan Pérez: ¿cuáles son los requisitos de la beca?
[12/08/2026, 09:46:01] Atención Vecino: Hola Juan, los requisitos son...

El script:
  1. Parsea cada línea (fecha, hora, autor, mensaje).
  2. Detecta los mensajes del AGENTE (lista configurable de nombres/números)
     y los EXCLUYE: nos interesan solo las preguntas de los vecinos.
  3. Limpia (minúsculas, sin emojis, sin puntuación rara, sin URLs).
  4. Marca (heurísticamente) qué mensajes parecen PREGUNTAS ("?", palabras
     interrogativas...).
  5. Asigna cada pregunta a un TEMA por palabras clave de vocabulario
     municipal (beca, permiso, certificado, impuesto, etc.).
  6. Genera un reporte de frecuencia: docs/FAQs_muestra.md y un CSV.

USO
---
  venv/bin/python scripts/analizar_chats.py [--dir data/chats]
"""
import argparse
import os
import re
import zipfile
import csv
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

# Directorio donde se ubican los exports de chats (configurable)
DEFAULT_CHATS_DIR = "data/chats"

# Autores que corresponden AL AGENTE (los que responden). Ajustar según
# los nombres reales del chat. Todo lo demás se trata como "vecino".
AGENTE_AUTORES = {
    "atención vecino", "atencion vecino", "municipalidad",
    "alcaldía", "alcaldia", "mesa de ayuda", "la cisterna",
    "registro civil", "soporte", "asistente", "agente",
}
# Números de teléfono internos del agente (si el .txt los trae en lugar del nombre)
AGENTE_PATRON = re.compile(r"^[\d\s\-+]{8,}$")

# Palabras que delatan una PREGUNTA (heurística simple)
PALABRAS_PREGUNTA = {
    "¿cuál", "cual", "¿cuáles", "cuales", "¿cómo", "como",
    "¿qué", "que", "¿cuándo", "cuando", "¿dónde", "donde",
    "¿quién", "quien", "requisito", "requisitos", "necesito",
    "quiero", "puedo", "cómo puedo", "calcular", "cuánto",
    "cuanto", "cuántos", "cuantos", "horario", "plazo",
}

# Vocabulario municipal → tema. Las claves pueden ser palabras o frases;
# el orden importa: se recorre en este orden para la primera coincidencia.
VOCABULARIO_TEMAS = [
    ("beca", "Becas / Ayudas de estudio"),
    ("permiso de circulación", "Permiso de circulación"),
    ("permiso", "Permisos municipales"),
    ("patente", "Patentes"),
    ("certificado", "Certificados"),
    ("impuesto territorial", "Impuesto territorial / contribuciones"),
    ("impuesto", "Impuestos"),
    ("subsidio", "Subsidios"),
    ("registro social", "Registro Social de Hogares"),
    ("registro civil", "Registro Civil"),
    ("parte", "Partes de tránsito / multas"),
    ("multa", "Multas / partes"),
    ("licencia de conducir", "Licencia de conducir"),
    ("licencia", "Licencias"),
    ("empadronamiento", "Empadronamiento municipal"),
    ("pago", "Pagos municipales"),
    ("vencimiento", "Vencimientos / plazos"),
    ("requisito", "Requisitos generales"),
    ("documento", "Documentación requerida"),
    ("horario", "Horarios de atención"),
    ("domicilio", "Atención a domicilio"),
    ("terreno", "Terrenos / uso de suelo"),
    ("arriendo", "Arriendos / subsidio de arriendo"),
    ("agua", "Agua / servicios básicos"),
    ("luz", "Alumbrado público"),
    ("aseo", "Aseo / recolección"),
    ("incivilidad", "Incivilidades / convivencia"),
    ("denunc", "Denuncias"),
    ("ruido", "Ruidos / convivencia"),
    ("molest", "Ruidos / convivencia"),
    ("contacto", "Contacto del municipio"),
]


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin emojis, sin URLs, sin puntuación rara."""
    # quitar URLs
    texto = re.sub(r"https?://\S+|www\.\S+", " ", texto)
    # quitar emojis (rango Unicode amplio)
    texto = re.sub(
        r"[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U00002000-\U0000206F]",
        " ",
        texto,
    )
    # quitar signos y normalizar espacios
    texto = re.sub(r"[^\w\s¿?¡!áéíóúüñ]", " ", texto)
    # minúsculas y quitar tildes
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    return re.sub(r"\s+", " ", texto).strip()


def _es_agente(autor: str) -> bool:
    """
    Detecta si el autor del mensaje es el agente (respuestas).

    Soporta sufijos entre paréntesis que suelen añadir los nombres
    (p. ej. "Atencion Vecino (Oficina Central)") extrayendo la primera parte.
    """
    autor = (autor or "").strip()
    # quitar posibles sufijos entre paréntesis o corchetes
    base = re.split(r"[\(\[<]", autor)[0].strip()
    a = _normalizar(base)
    if a in _normalizar_multi(AGENTE_AUTORES):
        return True
    # si el autor COMIENZA con el nombre del agente, también lo tratamos así
    for ag in AGENTE_AUTORES:
        if _normalizar(base).startswith(_normalizar(ag)):
            return True
    if AGENTE_PATRON.match(autor):
        return True
    return False


def _normalizar_multi(conjunto):
    return {_normalizar(x) for x in conjunto}


def _es_pregunta(mensaje: str) -> bool:
    """Heurística: ¿el mensaje parece una pregunta del vecino?"""
    m = _normalizar(mensaje)
    if not m:
        return False
    if m.endswith("?"):
        return True
    for p in PALABRAS_PREGUNTA:
        if p in m:
            return True
    return False


def _asignar_tema(mensaje: str) -> str:
    """Devuelve el tema (o 'Otros') según el vocabulario municipal."""
    m = _normalizar(mensaje)
    for palabra, tema in VOCABULARIO_TEMAS:
        if palabra in m:
            return tema
    return "Otros / no clasificado"


def _parsear_linea(linea: str):
    """
    Parsea una línea de export de WhatsApp.

    Retorna (autor, mensaje) o None si es una línea del sistema
    (p. ej. "Ha cambiado el estado", "Mensajes cifrados de extremo a extremo").
    Formato: [fecha, hora] Autor: mensaje
    """
    linea = linea.strip()
    m = re.match(r"^\[\s*[^\]]*\]\s*(.+?):\s*(.*)$", linea)
    if not m:
        return None
    autor, mensaje = m.group(1), m.group(2)
    if not autor or not mensaje:
        return None
    # descartar líneas del sistema
    if "cifrados" in mensaje or "cambió" in mensaje or "cambio" in mensaje:
        return None
    if "ha salido" in autor or "se unió" in autor:
        return None
    # descartar mensajes puramente multimedia (no son preguntas analizables)
    if re.search(r"<[^>]*omitid[^>]*>", mensaje):
        return None
    return autor.strip(), mensaje.strip()


def _leer_archivos(chats_dir: Path):
    """Lee todos los .txt y .zip (con .txt dentro) de la carpeta."""
    lineas = []
    if not chats_dir.exists():
        print(f"[chats] AVISO: no existe {chats_dir}. Crea la carpeta y pon ahí los exports.")
        return lineas
    for archivo in sorted(chats_dir.iterdir()):
        if archivo.suffix.lower() == ".zip":
            with zipfile.ZipFile(archivo) as z:
                for nombre in z.namelist():
                    if nombre.lower().endswith(".txt"):
                        lineas.extend(
                            z.read(nombre).decode("utf-8", errors="ignore").splitlines()
                        )
        elif archivo.suffix.lower() == ".txt":
            lineas.extend(archivo.read_text(encoding="utf-8", errors="ignore").splitlines())
    return lineas


def main():
    parser = argparse.ArgumentParser(description="Analiza chats de WhatsApp municipales")
    parser.add_argument("--dir", default=DEFAULT_CHATS_DIR, help="Carpeta con los exports")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    chats_dir = base / args.dir

    lineas = _leer_archivos(chats_dir)
    if not lineas:
        print("[chats] No se encontraron líneas de chat. Terminando sin análisis.")
        return

    total_mensajes = 0
    mensajes_vecino = 0
    preguntas = []
    temas = Counter()
    autores = defaultdict(int)

    for linea in lineas:
        parsed = _parsear_linea(linea)
        if not parsed:
            continue
        autor, mensaje = parsed
        total_mensajes += 1
        if _es_agente(autor):
            continue
        mensajes_vecino += 1
        autores[_normalizar(autor)] += 1
        if _es_pregunta(mensaje):
            tema = _asignar_tema(mensaje)
            preguntas.append((tema, mensaje))
            temas[tema] += 1

    # ---- Reporte Markdown (docs/FAQs_muestra.md) ----
    out_docs = base / "docs" / "FAQs_muestra.md"
    out_csv = base / "docs" / "frecuencia_temas.csv"

    with open(out_docs, "w", encoding="utf-8") as f:
        f.write("# Preguntas frecuentes detectadas en la muestra de chats\n\n")
        f.write(
            f"**Muestra analizada:** {total_mensajes} mensajes totales, "
            f"{mensajes_vecino} de vecinos.\n\n"
        )
        f.write("> Este análisis es una **muestra** (Opción A: descubrir FAQs).\n")
        f.write("> NO se indexan los chats en la base del bot. Ver docs/decision_tono_y_presupuesto.md\n\n")

        if not preguntas:
            f.write("No se detectaron preguntas en la muestra. Revisar ajustes del script.\n")
        else:
            f.write("## Ranking de temas por frecuencia\n\n")
            f.write("| # | Tema | Preguntas |\n|---|------|-----------|\n")
            for i, (tema, n) in enumerate(temas.most_common(), 1):
                f.write(f"| {i} | {tema} | {n} |\n")

            f.write("\n## Ejemplos de preguntas reales (muestra)\n\n")
            f.write("| Tema | Pregunta (ejemplo) |\n|------|--------------------|\n")
            for tema, mensaje in preguntas[:30]:
                corto = mensaje[:90] + ("..." if len(mensaje) > 90 else "")
                f.write(f"| {tema} | {corto} |\n")

    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tema", "frecuencia"])
        for tema, n in temas.most_common():
            w.writerow([tema, n])

    # ---- Consola ----
    print("=" * 60)
    print("ANÁLISIS DE CHATS DE WHATSAPP (muestra)")
    print("=" * 60)
    print(f"Mensajes totales : {total_mensajes}")
    print(f"Mensajes vecinos : {mensajes_vecino}")
    print(f"Preguntas detect : {len(preguntas)}")
    print("-" * 60)
    print("RANKING DE TEMAS:")
    for tema, n in temas.most_common():
        print(f"  {n:>4}  {tema}")
    print("-" * 60)
    print(f"Reporte: {out_docs.relative_to(base)}")
    print(f"CSV    : {out_csv.relative_to(base)}")


if __name__ == "__main__":
    main()