#!/usr/bin/env bash
# =============================================================================
# scrape_municipal_images.py — Ejecuta el scraper de imágenes con visión IA
# =============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$DIR"

PYTHON="${PYTHON:-$DIR/venv/bin/python}"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

"$PYTHON" -m app.image_scraper
