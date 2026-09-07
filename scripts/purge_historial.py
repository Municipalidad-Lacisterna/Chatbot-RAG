#!/usr/bin/env python3
"""
Borrado PERIÓDICO del historial de conversaciones (retención limitada).

Aplica la política de retención de datos del chatbot (Ley 19.628, Chile:
minimización / duración limitada). Elimina los mensajes que superen la edad
máxima configurada (por defecto 24 horas) y las sesiones resultantes vacías.

A diferencia del borrado "perezoso" en `app/chat_memory.py` (que se dispara
con el tráfico), ESTE script garantiza la limpieza aunque el servidor esté
encendido pero sin actividad. Se programa con un timer de systemd
(ver systemd/purge_historial.timer) o un cron.

Los datos se mantienen ANÓNIMOS: `session_id` no es un dato personal, y aquí
solo se borran mensajes; no se recolecta ni expone información del titular.

Uso:
    venv/bin/python scripts/purge_historial.py            # borra >24h (o HISTORY_MAX_AGE)
    venv/bin/python scripts/purge_historial.py --dry-run  # solo indica cuántos borraría
    HISTORY_MAX_AGE=3600 venv/bin/python scripts/purge_historial.py  # retención custom
"""
import os
import sys

# Ajustar sys.path para poder importar el paquete `app` desde la raíz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app import settings
from app.chat_memory import purge_old


def main():
    dry_run = "--dry-run" in sys.argv
    max_age = settings.HISTORY_MAX_AGE

    if dry_run:
        # Mostrar cuántos mensajes superan la retención sin borrarlos
        # (reusamos la consulta de purge_old de forma no destructiva).
        import sqlite3
        conn = sqlite3.connect(settings.MEMORY_DB_PATH)
        n = conn.execute(
            "SELECT COUNT(*) FROM chat_history WHERE timestamp < ?",
            (__import__('time').time() - max_age,),
        ).fetchone()[0]
        conn.close()
        print(f"[purge] (dry-run) {n} mensaje(s) superarían las {max_age//3600} h de retención.")
        return 0

    borrados = purge_old(max_age)
    print(f"[purge] Historial limpiado: {borrados} mensaje(s) eliminado(s) "
          f"(retención {max_age//3600} h, Ley 19.628).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
