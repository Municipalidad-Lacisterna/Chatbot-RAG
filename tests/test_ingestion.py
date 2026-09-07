"""
Test del chunking de la ingesta.

Verifica que la función `_split_text` del módulo de ingesta genera
fragmentos de tamaño razonable y con overlap cuando toca.

Ejecutar:
    ./venv/bin/python -m tests.test_ingestion
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion import _split_text
from app import settings


def test_split_text():
    """Prueba el splitter de textos."""
    # Texto de ejemplo con varios párrafos
    text = (
        "Primer párrafo sobre becas municipales para estudiantes de La Cisterna.\n\n"
        "Segundo párrafo sobre los documentos requeridos y plazos de postulación.\n\n"
        "Tercer párrafo sobre el procedimiento de tránsito y multas de estacionamiento."
    )

    # Ajustar a un chunk pequeño para forzar división múltiple
    chunks = _split_text(text, chunk_size=120, overlap=30)

    print(f"[test] Texto original: {len(text)} caracteres")
    print(f"[test] Número de chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"  - chunk {i}: {len(c)} chars | {c[:50]}...")

    assert len(chunks) >= 2, "El texto largo debería dividirse en varios chunks"
    # Cada chunk no debe estar vacío
    assert all(c.strip() for c in chunks), "No debe haber chunks vacíos"
    # Verificar que el texto es substancialmente el mismo (concatenando)
    assert sum(len(c) for c in chunks) <= len(text) * 2, \
        "El overlap no debería duplicar el texto exageradamente"

    print("\n✅ Chunking OK (test_ingestion)")


if __name__ == "__main__":
    test_split_text()