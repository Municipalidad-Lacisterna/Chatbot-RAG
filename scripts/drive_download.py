"""
Descargar documentos del municipio desde Google Drive (Service Account).

OBJETIVO
--------
Bajar automáticamente los PDFs (o exportar Docs/Sheets/Slides a PDF) de una
carpeta de Google Drive compartida con la service account, y guardarlos en
`data/` para que el chatbot los indexe.

REQUISITOS (una sola vez, en Google Cloud Console)
--------------------------------------------------
1. Crear un proyecto en https://console.cloud.google.com
2. Habilitar la Google Drive API de ese proyecto.
3. Crear una "Service Account":
   - IAM y administración → Cuentas de servicio → Crear.
   - En "Claves" crear clave JSON → descarga `credentials.json`.
   - Copiar el EMAIL de la service account (termina en gserviceaccount.com).
4. En Google Drive, crear una carpeta (ej. "Documentos Municipal") y
   COMPARTIRLA con el email de la service account (rol Lector).

CONFIGURACIÓN
-------------
- Colocar el archivo JSON de credenciales en `config/google-drive-credentials.json`
  (el script también acepta la ruta por `--creds`).
- La carpeta de Drive a leer se pasa por `--folder` (nombre exacto), o por
  defecto se lee la raíz compartida.

USO
---
  venv/bin/python scripts/drive_download.py --folder "Documentos Municipal"
  venv/bin/python scripts/drive_download.py --creds config/mi-creds.json --out data/

NOTA
----
La service account NO puede acceder a archivos en tu Drive personal a menos
que le compartas la carpeta específica. Compartir la carpeta es el paso clave.
"""
import argparse
import io
import os
import sys
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# Base del proyecto (un nivel arriba de scripts/)
_BASE = Path(__file__).resolve().parent.parent
DEFAULT_CREDS = _BASE / "config" / "google-drive-credentials.json"
DEFAULT_OUT = _BASE / "data"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Tipos de archivo de Google que deben EXPORTARSE a PDF (en vez de descargarse)
GOOGLE_MIME_TO_PDF = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
    "application/vnd.google-apps.drawing": "application/pdf",
}


def _autenticar(creds_path: Path):
    """Construye el servicio de Drive usando las credenciales de la service account."""
    creds = service_account.Credentials.from_service_account_file(
        str(creds_path), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def _buscar_carpeta(service, nombre: str):
    """
    Busca el ID de una carpeta por nombre en el Drive de la service account.
    """
    response = (
        service.files()
        .list(
            q=f"name='{nombre}' and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false",
            fields="files(id,name)",
        )
        .execute()
    )
    files = response.get("files", [])
    if not files:
        print(f"[drive] ✗ No encontré la carpeta '{nombre}' compartida con la service account.")
        sys.exit(1)
    if len(files) > 1:
        print(f"[drive] Ojo: hay {len(files)} carpetas con ese nombre. Uso la primera.")
    return files[0]["id"]


def _listar_archivos(service, folder_id: str):
    """Lista todos los archivos (no subcarpetas) dentro de la carpeta."""
    response = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id,name,mimeType)",
            pageSize=200,
        )
        .execute()
    )
    return response.get("files", [])


def _descargar_exportar(service, file_id: str, nombre: str, mime_type: str, out_dir: Path):
    """
    Descarga el archivo a `out_dir`. Si es un Google Doc/Sheet/Slide, lo
    exporta a PDF. Retorna la ruta final o None si falla.
    """
    destino = out_dir / nombre
    # Si es un archivo nativo de Google, lo exportamos a PDF
    if mime_type in GOOGLE_MIME_TO_PDF:
        export_mime = GOOGLE_MIME_TO_PDF[mime_type]
        nombre_pdf = nombre
        if not nombre_pdf.lower().endswith(".pdf"):
            nombre_pdf = os.path.splitext(nombre_pdf)[0] + ".pdf"
        destino = out_dir / nombre_pdf
        print(f"[drive]   ↳ {nombre} (Google) → exportando a PDF")
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"[drive]   ... {int(status.progress() * 100)}%")

    if fh.getbuffer().nbytes == 0:
        print(f"[drive]   ⚠ {nombre}: archivo vacío, no se guarda.")
        return None

    destino.write_bytes(fh.getvalue())
    kb = fh.getbuffer().nbytes / 1024
    print(f"[drive]   ✓ {destino.name} ({kb:.1f} KB)")
    return destino


def main():
    parser = argparse.ArgumentParser(description="Bajá documentos de Google Drive (service account)")
    parser.add_argument("--creds", default=str(DEFAULT_CREDS), help="Ruta al JSON de credenciales")
    parser.add_argument("--folder", required=True, help="Nombre exacto de la carpeta de Drive")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Carpeta destino (def. data/)")
    args = parser.parse_args()

    creds_path = Path(args.creds)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not creds_path.exists():
        print(
            f"[drive] ✗ No encuentro las credenciales en {creds_path}.\n"
            "         Pon ahí el credentials.json de la service account "
            "(ver docstring del script para el paso de Google Cloud Console)."
        )
        sys.exit(1)

    service = _autenticar(creds_path)
    print(f"[drive] ✓ Autenticado como service account")

    folder_id = _buscar_carpeta(service, args.folder)
    print(f"[drive] Carpeta '{args.folder}' → id {folder_id}")

    archivos = _listar_archivos(service, folder_id)
    if not archivos:
        print("[drive] La carpeta está vacía (o no hay archivos accesibles).")
        return

    print(f"[drive] {len(archivos)} archivo(s) encontrad(os).\n")
    descargados = 0
    for f in archivos:
        ruta = _descargar_exportar(service, f["id"], f["name"], f["mimeType"], out_dir)
        if ruta:
            descargados += 1

    print(f"\n[drive] ✓ Listo. {descargados} archivo(s) en {out_dir}")
    print("[drive] Ahora puedes indexarlos con: venv/bin/python -m app.ingestion")


if __name__ == "__main__":
    main()