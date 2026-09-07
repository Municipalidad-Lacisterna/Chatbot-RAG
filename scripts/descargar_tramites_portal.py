#!/usr/bin/env python3
"""
Descarga trámites públicos del Portal de Transparencia de La Cisterna
(transparencia.cisterna.cl) y los deja listos para la ingesta RAG.

Fuente: http://transparencia.cisterna.cl  (abierto / sin clave)

Qué hace:
  1. Descarga las páginas HTML de trámites municipales (patentes, aseo,
     oficina de partes, Dirección de Obras, permisos de circulación,
     licencias de conducir).
  2. Las convierte a PDF (con chromium headless) para que el pipeline
     `app/ingestion.py` (PDF -> Markdown -> chunks -> ChromaDB) las procese
     sin tocar el código.
  3. Descarga el Manual de Permisos de Edificación (ya es PDF).
  4. Coloca todos los PDFs en `data/` con nombres claros.

Uso:
  venv/bin/python scripts/descargar_tramites_portal.py
  Luego: venv/bin/python -m app.ingestion   (indexa todo data/)

Nota técnica: se usa chromium --headless --print-to-pdf para convertir el
HTML a PDF de forma fiel (la página usa tablas de trámites que conviene
preservar). Si chromium no está en el PATH, configúlalo en CHROMIUM_BIN.
"""
import os
import subprocess
import sys
import shutil
import tempfile

# Ruta al binario de chromium (ajustar si difiere)
CHROMIUM_BIN = os.getenv("CHROMIUM_BIN", "chromium")

# Directorio base del proyecto (dos niveles arriba de scripts/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = tempfile.mkdtemp(prefix="tramites_")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# (nombre_local, url_remota) — pares que se convertirán a PDF (el nombre
# local es el que se guardará en data/ sin extensión)
PAGINAS_HTML = {
    "tramites_patentes_comerciales": (
        "http://transparencia.cisterna.cl/tram_munic_patentes_com.html"
    ),
    "tramites_aseo_ornato": (
        "http://transparencia.cisterna.cl/tram_munic_aseo_ornato.html"
    ),
    "tramites_oficina_partes": (
        "http://transparencia.cisterna.cl/tram_munic_oficina_partes.html"
    ),
    "tramites_direccion_obras": (
        "http://transparencia.cisterna.cl/tramites_requisitos_acceso_servicios-obras.html"
    ),
    "tramites_permisos_circulacion": (
        "http://transparencia.cisterna.cl/tram_munic_direcc_transito_circulacion.html"
    ),
    "tramites_licencias_conducir": (
        "http://transparencia.cisterna.cl/tram_munic_direcc_transito_licencia.html"
    ),
}

# PDFs que ya vienen en ese formato y solo se descargan (nombre local, url)
PDFS_DIRECTOS = {
    "manual_permisos_edificacion.pdf": (
        "http://transparencia.cisterna.cl/archivos/MANUAL/"
        "MANUAL.PROCEDIMIENTO.PERMISOS.EDIFICACION/Manual.Permisos.Edificacion.pdf"
    ),
}


def descargar(url: str, destino: str) -> bool:
    """Descarga `url` a `destino` usando curl. Devuelve True si fue bien."""
    r = subprocess.run(
        [
            "curl", "-s", "-L", "--max-time", "40",
            "-A", USER_AGENT, "-o", destino, url,
        ]
    )
    if r.returncode != 0:
        print(f"  [x] curl falló para {url}")
        return False
    if not os.path.exists(destino) or os.path.getsize(destino) == 0:
        print(f"  [x] archivo vacío para {url}")
        return False
    return True


def html_to_pdf(html_path: str, pdf_path: str) -> bool:
    """Convierte un HTML local a PDF con chromium headless."""
    uri = "file://" + html_path
    r = subprocess.run(
        [
            CHROMIUM_BIN, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--print-to-pdf=" + pdf_path, "--no-pdf-header-footer", uri,
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0 or not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 1000:
        print(f"  [x] falló conversión chromium para {html_path}")
        return False
    return True


def main():
    if not shutil.which(CHROMIUM_BIN):
        print(
            "[!] No se encontró 'chromium' en el PATH.\n"
            f"    Instálalo o define CHROMIUM_BIN (ej: /usr/bin/chromium)."
        )
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    n = 0

    # 1) Páginas HTML -> PDF
    for nombre, url in PAGINAS_HTML.items():
        html_local = os.path.join(TMP_DIR, nombre + ".html")
        print(f"[1/2] Descargando HTML: {nombre}")
        if not descargar(url, html_local):
            continue
        print(f"      Convirtiendo a PDF...")
        pdf_local = os.path.join(TMP_DIR, nombre + ".pdf")
        if html_to_pdf(html_local, pdf_local):
            final = os.path.join(DATA_DIR, nombre + ".pdf")
            shutil.move(pdf_local, final)
            sz = os.path.getsize(final)
            print(f"      ✓ {os.path.basename(final)}  ({sz//1024} KB)")
            n += 1
        else:
            print(f"      [x] no se pudo convertir {nombre}")

    # 2) PDFs directos (y páginas ordenanza que en realidad es texto HTML)
    for nombre, url in PDFS_DIRECTOS.items():
        ext = os.path.splitext(nombre)[1] or ".pdf"
        destino_tmp = os.path.join(TMP_DIR, nombre)
        print(f"[2/2] Descargando directo: {nombre}")
        if not descargar(url, destino_tmp):
            continue
        # Si el destino es un HTML (no PDF), convertirlo a PDF (caso ordenanza)
        with open(destino_tmp, "rb") as f:
            head = f.read(8)
        if head.startswith(b"<") or head.strip().startswith(b"<!DOCTYPE"):
            print(f"      El recurso es HTML; convirtiendo a PDF...")
            pdf_tmp = os.path.join(TMP_DIR, "ord.pdf")
            if not html_to_pdf(destino_tmp, pdf_tmp):
                print(f"      [x] no se pudo convertir {nombre}")
                continue
            destino_tmp = pdf_tmp
        final = os.path.join(DATA_DIR, nombre)
        shutil.move(destino_tmp, final)
        sz = os.path.getsize(final)
        print(f"      ✓ {os.path.basename(final)}  ({sz//1024} KB)")
        n += 1

    print(f"\nListo: {n} documentos descargados a {DATA_DIR}")
    print("Ejecuta ahora:  venv/bin/python -m app.ingestion")


if __name__ == "__main__":
    main()