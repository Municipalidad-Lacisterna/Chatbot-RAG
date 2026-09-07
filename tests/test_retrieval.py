"""
Prueba integral del chatbot RAG.

Verifica:
1. Ingesta de los PDFs de prueba con chunking (se generan múltiples chunks).
2. Retrieval semántico por tema (becas vs tránsito).
3. Conversación con memoria por sesión.

Ejecutar desde la raíz del proyecto:
    ./venv/bin/python -m tests.test_retrieval
"""
import os
import sys

# Asegurar que podemos importar los paquetes 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import ingestion, database, rag_engine, chat_memory


def test_ingestion_chunking():
    """Indexa los PDFs y comprueba que se crearon chunks."""
    total = ingestion.ingest_all()
    collection = database.get_collection()
    count = collection.count()
    print(f"\n[1] Ingesta: {total} chunks nuevos en la colección (total BD: {count})")
    assert total > 0, "No se indexó ningún chunk"
    print("    ✓ Ingesta con chunking OK")
    return count


def test_retrieval_by_topic():
    """Comprueba que el retrieval distingue temas (becas vs tránsito)."""
    docs_becas = database.retrieve("requisitos de las becas municipales", k=2)
    docs_transito = database.retrieve("multas de tránsito procedimiento", k=2)

    print(f"[2] Retrieval 'becas': {len(docs_becas)} fragmento(s)")
    print(f"    Retrieval 'tránsito': {len(docs_transito)} fragmento(s)")

    # Al menos devolver algo (no documentos vacíos)
    assert docs_becas, "No se recuperó nada para 'becas'"
    assert docs_transito, "No se recuperó nada para 'tránsito'"

    # Verificar que el texto recuperado es distinto entre temas
    combined_tr = " ".join(docs_transito).lower()
    combined_be = " ".join(docs_becas).lower()

    # Debe existir al menos distinción: si 'beca' aparece en tránsito no es fatal,
    # pero el texto no debe ser idéntico (chunking + retrieval funcionan)
    assert combined_be != combined_tr, "Ambos temas devolvieron texto idéntico"
    print("    ✓ Retrieval distingue temas OK")
    return True


def test_chat_con_memoria():
    """Comprueba que el chatbot responde y guarda historial por sesión."""
    session = "test-sesion-memoria"
    chat_memory.clear_session(session)

    # Pregunta con contexto disponible en los PDFs
    answer = rag_engine.query_chatbot(
        "¿Cuáles son los requisitos para una beca municipal?", session
    )
    print(f"[3] Respuesta del chatbot: {answer[:120]}...")

    # El historial debe tener 2 mensajes (user + assistant)
    history = rag_engine.get_history(session)
    print(f"    Historial guardado: {len(history)} mensajes")
    assert len(history) >= 2, "El historial debería guardar pregunta + respuesta"
    assert history[0]["role"] == "user"
    assert history[-1]["role"] == "assistant"
    print("    ✓ Conversación con memoria OK")

    return True


if __name__ == "__main__":
    print("=== TEST DEL CHATBOT RAG ===\n")
    test_ingestion_chunking()
    test_retrieval_by_topic()
    test_chat_con_memoria()
    print("\n✅ Todos los tests pasaron correctamente.")