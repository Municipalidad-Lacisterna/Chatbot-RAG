#!/usr/bin/env python3
"""
Ingesta PROGRAMADA de documentos nuevos.

Barre la carpeta `data/inbox/` buscando PDFs nuevos (los que caen desde el
Google Drive del municipio, o copia manual), los indexa en ChromaDB y ELIMINA
el original tras digitalizarlo (conservando los chunks en el vector store).

Está pensado para ejecutarse en un momento de bajo uso (p. ej. 17:01), porque
el OCR/parseo de PDFs escaneados es costoso en CPU. Se programa con un timer
de systemd (ver systemd/ingest_programado.timer) o un cron.

Uso:
    venv/bin/python scripts/ingest_programado.py            # procesa todo el inbox
    venv/bin/python scripts/ingest_programado.py --dry-run  # solo lista, no procesa
"""
import os
import sys
import shutil
import time

# Ajustar sys.path para poder importar el paquete `app` desde la raíz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import settings
from app.document_analyzer import procesar_cola_inbox


def main():
    dry_run = "--dry-run" in sys.argv
    inbox = os.path.join(settings.DATA_DIR, "inbox")
    os.makedirs(inbox, exist_ok=True)

    # Recolectar documentos del inbox
    nuevos = [f for f in os.listdir(inbox) if not f.startswith(".") and os.path.isfile(os.path.join(inbox, f))]
    if not nuevos:
        print(f"[ingesta] No hay documentos nuevos en {inbox}")
        return 0

    print(f"[ingesta] {len(nuevos)} documento(s) pendiente(s) en inbox:")
    for f in sorted(nuevos):
        print(f"   - {f} ({os.path.getsize(os.path.join(inbox, f))//1024} KB)")

    if dry_run:
        print("\n[ingesta] (dry-run) no se procesó nada.")
        return 0

    res = procesar_cola_inbox()
    print(f"\n[ingesta] Resumen: {res['mensaje']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())