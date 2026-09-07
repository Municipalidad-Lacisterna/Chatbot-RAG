#!/usr/bin/env python3
"""
Extrae los TRÁMITES MUNICIPALES del Portal de Transparencia de La Cisterna
(transparencia.cisterna.cl) desde las páginas HTML descargadas y los escribe
como archivos Markdown limpos en `data/`.

Motivo: las páginas usan tablas HTML; si se convierten a PDF el texto queda
lleno de ruido (`|`, `<br>`, mayúsculas) y los embeddings del RAG degradan.
En Markdown limpio el texto es natural y el retrieval funciona bien.

Uso:
  venv/bin/python scripts/extraer_tramites_markdown.py
  Luego: venv/bin/python -m app.ingestion   (indexa data/ completos)
"""
import os
import re
import html as html_mod
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# (archivo html local, nombre_markdown de salida, título de la sección)
PAGINAS = [
    ("tramites_patentes_comerciales.html", "tramites_patentes_comerciales.md"),
    ("tramites_aseo_ornato.html", "tramites_aseo_ornato.md"),
    ("tramites_oficina_partes.html", "tramites_oficina_partes.md"),
    ("tramites_direccion_obras.html", "tramites_direccion_obras.md"),
    ("tramites_permisos_circulacion.html", "tramites_permisos_circulacion.md"),
    ("tramites_licencias_conducir.html", "tramites_licencias_conducir.md"),
]

# Nombres de las columnas de la tabla de trámites (en el orden real del HTML)
CAMPOS = [
    "Descripción del servicio",
    "Requisitos",
    "¿Se puede hacer en línea?",
    "Trámites o etapas",
    "Valor",
    "Lugar donde se realiza",
    "Información complementaria",
]


def _limpia(segmento_html: str) -> str:
    """Convierte un fragmento de celda HTML a texto limpio."""
    t = re.sub(r"<br\s*/?>", "\n", segmento_html, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html_mod.unescape(t)
    # normalizar espacios (una palabra por línea de <br>)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def _extraer_trámites(h: str):
    """Devuelve lista de trámites: cada uno es dict campo->texto."""
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S | re.I)
    tramites = []
    for r in rows:
        celdas = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S | re.I)
        if not celdas:
            continue
        textos = [_limpia(c) for c in celdas]
        # descartar filas vacías o solo header
        if not any(textos):
            continue
        tramites.append(textos)
    return tramites


def _formatear(tramite: list[str], titulo_pagina: str) -> str:
    """Convierte una fila de celdas en bloques markdown legibles."""
    # Tratar de casar con las columnas conocidas
    d = {}
    for i, txt in enumerate(tramite):
        campo = CAMPOS[i] if i < len(CAMPOS) else f"Campo {i+1}"
        d[campo] = txt
    # El primer campo suele ser el nombre del trámite
    nombre = d.get("Descripción del servicio") or tramite[0]
    # Separar requisitos / etapas que en el HTML a veces van en la misma celda
    bloque = [f"### {nombre}"]
    if d.get("Descripción del servicio") and len(d["Descripción del servicio"]) > len(nombre):
        bloque.append(f"**Trámite:** {d['Descripción del servicio']}")
    for campo in CAMPOS[1:]:
        val = d.get(campo)
        if val and val != "NO" and val.lower() not in ("-", "n/d"):
            if campo == "¿Se puede hacer en línea?":
                val = "Sí" if val.upper() in ("SI", "SÍ", "YES") else val
                bloque.append(f"**¿En línea?:** {val}")
            else:
                bloque.append(f"**{campo}:** {val}")
    return "\n\n".join(bloque)


def main():
    # Buscar los HTML en el directorio temporal y/o scripts
    # Prioridad: mismo dir que el script, luego /tmp/tramhtml
    srcdir = os.path.dirname(os.path.abspath(__file__))
    candidatos = [srcdir, "/tmp/tramhtml"]
    html_local = {}
    for hf, _ in PAGINAS:
        encontrado = None
        for d in candidatos:
            p = os.path.join(d, hf)
            if os.path.exists(p):
                encontrado = p
                break
        if not encontrado:
            print(f"[!] No se encontró {hf} (probá antes descargar_tramites_portal.py)")
        else:
            html_local[hf] = encontrado

    os.makedirs(DATA_DIR, exist_ok=True)
    total = 0
    for hf, md in PAGINAS:
        if hf not in html_local:
            continue
        h = open(html_local[hf], encoding="latin1", errors="ignore").read()
        # Título de sección
        h2 = re.search(r"<h2[^>]*>(.*?)</h2>", h, re.S | re.I)
        titulo = _limpia(h2.group(1)) if h2 else os.path.splitext(md)[0]
        tramites = _extraer_trámites(h)
        # encabezado
        partes = [f"# TRÁMITES MUNICIPALES — {titulo}\n",
                  "Fuente: Portal de Transparencia de la Municipalidad de La Cisterna "
                  "(transparencia.cisterna.cl). Información pública.\n"]
        n = 0
        for tr in tramites:
            md_text = _formatear(tr, titulo)
            if md_text and len(md_text) > 30:
                partes.append(md_text)
                n += 1
        if n == 0:
            print(f"[x] {hf}: no se extrajeron trámites útiles")
            continue
        salida = os.path.join(DATA_DIR, md)
        with open(salida, "w", encoding="utf-8") as f:
            f.write("\n\n".join(partes) + "\n")
        print(f"[✓] {md}: {n} trámites extraídos -> {salida}")
        total += n

    print(f"\nTotal: {total} trámites escritos en data/*.md")
    print("Ejecuta luego:  venv/bin/python -m app.ingestion")


if __name__ == "__main__":
    main()