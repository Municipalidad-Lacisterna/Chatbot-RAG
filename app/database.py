"""
Acceso a la base vectorial ChromaDB.

ChromaDB se usa como vector store local (privado, sin dependencias de red).
La colección almacena los fragmentos (chunks) de los documentos indexados,
cada uno con su embedding multilingüe para búsqueda semántica en español.
"""
import chromadb
from chromadb.utils import embedding_functions
from app import settings

# Inicializar cliente persistente local
client = chromadb.PersistentClient(path=settings.PERSIST_DIRECTORY)

# Embedding multilingüe (optimizado para español)
_emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)


def get_collection(name: str = "municipal_docs"):
    """Obtiene (o crea) la colección de documentos."""
    return client.get_or_create_collection(name=name, embedding_function=_emb_fn)


def retrieve(question: str, k: int = None) -> list[str]:
    """
    Recupera los k fragmentos más relevantes para una pregunta.

    Retorna una lista de textos (strings), o lista vacía si no hay resultados.
    Es la función que el pipeline RAG usa como "retriever", envuelta luego
    como RunnableLambda para integrarse en la cadena LCEL.
    """
    k = k or settings.TOP_K
    collection = get_collection()
    results = collection.query(query_texts=[question], n_results=k)

    docs = results.get("documents") or []
    if not docs or not docs[0]:
        return []

    # Filtrar entradas None (ChromaDB puede devolver [None] en colecciones
    # vacías o con documentos sin contenido), para no romper el join posterior.
    return [d for d in docs[0] if isinstance(d, str) and d.strip()]