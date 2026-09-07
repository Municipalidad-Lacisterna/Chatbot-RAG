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
from app.ingestion import ingest_pdf, delete_original_file


def _es_doc(nombre: str) -> bool:
    return nombre.lower().endswith((".pdf", ".md"))


def main():
    dry_run = "--dry-run" in sys.argv
    inbox = os.path.join(settings.DATA_DIR, "inbox")
    data = settings.DATA_DIR
    os.makedirs(inbox, exist_ok=True)

    # Recolectar documentos del inbox
    nuevos = [f for f in os.listdir(inbox) if _es_doc(f) and os.path.isfile(os.path.join(inbox, f))]
    if not nuevos:
        print(f"[ingesta] No hay documentos nuevos en {inbox}")
        return 0

    print(f"[ingesta] {len(nuevos)} documento(s) pendiente(s) en inbox:")
    for f in sorted(nuevos):
        print(f"   - {f} ({os.path.getsize(os.path.join(inbox, f))//1024} KB)")

    if dry_run:
        print("\n[ingesta] (dry-run) no se procesó nada.")
        return 0

    procesados = 0
    fallidos = []
    for f in sorted(nuevos):
        origen = os.path.join(inbox, f)
        destino = os.path.join(data, f)
        t0 = time.time()
        try:
            # Mover al directorio de datos (donde ingest_pdf lo busca)
            if os.path.abspath(origen) != os.path.abspath(destino):
                shutil.move(origen, destino)
            n = ingest_pdf(f)
            if n == 0:
                raise RuntimeError("no se extrajo texto (¿PDF vacío o corrupto?)")
            # Digitalizar: eliminar el original, conservar chunks
            delete_original_file(f)
            dt = time.time() - t0
            print(f"  [✓] {f}: {n} chunks ({dt:.0f}s) — original eliminado")
            procesados += 1
        except Exception as e:
            # Si falló, devolver el archivo al inbox para reintentar después
            if os.path.exists(destino) and not os.path.exists(origen):
                shutil.move(destino, origen)
            fallidos.append((f, str(e)))
            print(f"  [x] {f}: ERROR {e}")
            print(f"      (devuelto a inbox para reintentar)")

    print(f"\n[ingesta] Resumen: {procesados} procesados, {len(fallidos)} fallidos.")
    if fallidos:
        for f, e in fallidos:
            print(f"   - {f}: {e}")
    return 0 if not fallidos else 1


if __name__ == "__main__":
    sys.exit(main())