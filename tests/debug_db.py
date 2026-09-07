"""
Utilitario para inspeccionar el contenido de la base vectorial ChromaDB.

Uso:
    ./venv/bin/python -m tests.debug_db
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_collection


def main():
    collection = get_collection()
    count = collection.count()
    print(f"Total de chunks en la colección: {count}")

    if count > 0:
        peek = collection.peek(limit=5)
        print("\nMuestra de los primeros chunks:")
        for i, doc in enumerate(peek.get("documents", [])):
            meta = (peek.get("metadatas") or [{}])[i]
            print(f"\n  [{i}] (fuente: {meta.get('source')}, chunk {meta.get('chunk_index')})")
            print(f"      {doc[:100]}...")
    else:
        print("La colección está vacía. Ejecuta primero la ingesta: ./venv/bin/python -m app.ingestion")


if __name__ == "__main__":
    main()