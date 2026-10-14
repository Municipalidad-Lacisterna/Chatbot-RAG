"""
Procesador semántico de planillas Excel (.xlsx, .xls) para RAG.

Convierte planillas municipales (preguntas frecuentes, guías de atención,
directorios telefónicos, juntas de vecinos) en documentos Markdown
estructurados con encabezados (###), lo que garantiza que el chunker de
ChromaDB mantenga íntegro el contexto de cada registro o trámite.
"""
import re
from pathlib import Path
import openpyxl


def _clean_val(val) -> str:
    """Limpia valores de celdas de Excel (floats .0, espacios repetidos)."""
    if val is None:
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    s = str(val).strip()
    # Limpiar formato 951215523.0 -> 951215523
    if re.match(r"^\d+\.0$", s):
        s = s[:-2]
    # Normalizar saltos de línea internos excesivos
    s = re.sub(r"\r\n|\r", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _detect_header_row(rows: list[tuple]) -> int:
    """Detecta el índice (0-based) de la fila que contiene los encabezados reales."""
    keywords = {
        "unidad", "pregunta", "nombre", "telefono", "teléfono", "correo",
        "direccion", "dirección", "horario", "anexo", "contacto", "partido",
        "celular", "encargado", "responsable", "categoria", "categoría", "tramite", "trámite"
    }
    best_idx = 0
    best_score = -1

    for idx, r in enumerate(rows[:6]):
        cells = [_clean_val(c).lower() for c in r if _clean_val(c)]
        score = sum(1 for c in cells if any(k in c for k in keywords))
        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


def _parse_faq_sheet(sheet_name: str, headers: list[str], rows: list[tuple], h_idx: int) -> list[str]:
    """Procesa hojas tipo FAQ (Pregunta / Respuesta)."""
    # Identificar columnas
    col_unidad = -1
    col_preg = -1
    col_resp = -1
    col_kw = -1

    for i, h in enumerate(headers):
        hl = h.lower()
        if "unidad" in hl or "depto" in hl or "departamento" in hl:
            col_unidad = i
        elif "pregunta" in hl or "consulta" in hl:
            col_preg = i
        elif hl in ("dy", "respuesta", "detalle", "solucion", "solución") or "resp" in hl:
            col_resp = i
        elif "clave" in hl or "keyword" in hl:
            col_kw = i

    # Si no encontró columna de respuesta explícita, usar la tercera columna con datos
    if col_resp == -1 and len(headers) >= 3:
        col_resp = 2

    out = [f"## Preguntas Frecuentes — {sheet_name}\n"]
    for r in rows[h_idx + 1:]:
        preg = _clean_val(r[col_preg]) if 0 <= col_preg < len(r) else ""
        resp = _clean_val(r[col_resp]) if 0 <= col_resp < len(r) else ""
        unidad = _clean_val(r[col_unidad]) if 0 <= col_unidad < len(r) else ""
        kw = _clean_val(r[col_kw]) if 0 <= col_kw < len(r) else ""

        if not preg or not resp:
            continue

        prefix = f"[{unidad}] " if unidad else ""
        bloque = [f"### {prefix}{preg}"]
        if kw:
            bloque.append(f"**Palabras clave:** {kw}")
        bloque.append(f"**Respuesta:**\n{resp}\n")
        out.append("\n".join(bloque))

    return out


def _is_header_repeat(vals: list[str], headers: list[str]) -> bool:
    """Detecta si una fila repite los nombres de las columnas en medio de la tabla."""
    matches = 0
    total = 0
    for i, v in enumerate(vals):
        if not v:
            continue
        total += 1
        h = headers[i].lower() if i < len(headers) else ""
        vl = v.lower()
        if vl == h or (len(vl) > 3 and vl in h) or (len(h) > 3 and h in vl):
            matches += 1
    return total > 0 and (matches / total) >= 0.5


def _parse_directory_sheet(sheet_name: str, headers: list[str], rows: list[tuple], h_idx: int) -> list[str]:
    """Procesa directorios de atención, oficinas o unidades municipales."""
    out = [f"## Directorio y Atencion — {sheet_name}\n"]
    seccion_actual = ""

    for r in rows[h_idx + 1:]:
        vals = [_clean_val(c) for c in r]
        if not any(vals):
            continue

        # Saltar si es una repetición de encabezados
        if _is_header_repeat(vals, headers):
            continue

        # Detectar si es una fila de título/categoría mayor (ej. ['1.0', 'Alcaldía'])
        non_empty = [(i, v) for i, v in enumerate(vals) if v]
        if len(non_empty) == 1 and non_empty[0][0] <= 1:
            seccion_actual = non_empty[0][1]
            out.append(f"\n## {seccion_actual}\n")
            continue
        elif len(non_empty) == 2 and re.match(r"^\d+(\.\d+)?$", non_empty[0][1]):
            seccion_actual = non_empty[1][1]
            out.append(f"\n## {seccion_actual}\n")
            continue

        # Encontrar nombre principal para el ###
        nombre_unidad = ""
        detalles = []

        for i, val in enumerate(vals):
            if not val:
                continue
            h_name = headers[i] if i < len(headers) and headers[i] else f"Dato {i+1}"
            hl = h_name.lower()
            if not nombre_unidad and any(k in hl for k in ("unidad", "nombre", "oficina", "junta")):
                nombre_unidad = val
            else:
                detalles.append(f"- **{h_name}:** {val}")

        if not nombre_unidad:
            nombre_unidad = vals[0] if vals else "Registro"

        bloque = [f"### {nombre_unidad}"]
        if seccion_actual:
            bloque.append(f"- **Área/Dirección:** {seccion_actual}")
        bloque.extend(detalles)
        bloque.append("")
        out.append("\n".join(bloque))

    return out


def _parse_generic_table(sheet_name: str, headers: list[str], rows: list[tuple], h_idx: int) -> list[str]:
    """Procesa tablas genéricas estructuradas."""
    out = [f"## {sheet_name}\n"]
    for r in rows[h_idx + 1:]:
        vals = [_clean_val(c) for c in r]
        if not any(vals):
            continue
        titulo = vals[0] if vals[0] else "Registro"
        bloque = [f"### {titulo}"]
        for i, val in enumerate(vals[1:], start=1):
            if not val:
                continue
            h_name = headers[i] if i < len(headers) and headers[i] else f"Columna {i+1}"
            bloque.append(f"- **{h_name}:** {val}")
        bloque.append("")
        out.append("\n".join(bloque))
    return out


def excel_to_markdown(excel_path: str) -> str:
    """
    Convierte una planilla Excel a Markdown semántico optimizado para RAG.
    """
    p = Path(excel_path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {excel_path}")

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    doc_sections = [f"# Informacion Municipal — {p.stem}\n"]

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        # Omitir hojas ocultas si existen
        if sheet.sheet_state != "visible":
            continue

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue

        h_idx = _detect_header_row(rows)
        raw_headers = rows[h_idx]
        headers = [_clean_val(c) for c in raw_headers]

        # Llenar headers vacíos
        for i in range(len(headers)):
            if not headers[i]:
                headers[i] = f"Campo_{i+1}"

        headers_str = " ".join(headers).lower()

        # Determinar tipo de hoja
        if "pregunta" in headers_str:
            section_md = _parse_faq_sheet(sheet_name, headers, rows, h_idx)
        elif any(k in headers_str for k in ("unidad", "horario", "anexo", "atencion", "atención")):
            section_md = _parse_directory_sheet(sheet_name, headers, rows, h_idx)
        else:
            section_md = _parse_generic_table(sheet_name, headers, rows, h_idx)

        doc_sections.extend(section_md)

    return "\n\n".join(doc_sections).strip()
