"""
Configuración central del chatbot RAG.

Carga la configuración desde variables de entorno (.env) con valores
por defecto sensatos para el prototipo. Mantener aquí todos los parámetros
de configuración evita dispersarlos por el resto de los módulos.
"""
import os
from dotenv import load_dotenv

# Directorio raíz del proyecto (una subida desde app/)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno desde el archivo .env (si existe)
load_dotenv(os.path.join(_BASE_DIR, ".env"))

# --- Proveedor del modelo LLM ---
# "google" (Gemini, por defecto en desarrollo, costo $0 free tier)
# "ollama"  (LLM local, Qwen2.5-VL, para el servidor de producción con GPU;
#            soberanía total de datos, la info nunca sale del servidor)
# Se controla con la variable LLM_PROVIDER en .env.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")

# --- Modelo LLM (Google / Gemini, solo cuando LLM_PROVIDER == "google") ---
# Nota (histórico de desarrollo): gemini-3.5-flash agota cuota diaria en free
# tier (429 RESOURCE_EXHAUSTED); gemini-3.1-flash-lite es el más estable y
# barato para el prototipo. En producción se usa IA local vía Ollama, no Gemini.
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")
# La API key de Google se lee por nombre estándar; si no está definida,
# la toma el SDK de google-genai desde su propio mecanismo de entorno.
def _read_secret(name: str, default: str = "") -> str:
    """Lee un secreto desde variable de entorno o desde archivo Docker Secret (/run/secrets/)."""
    val = os.getenv(name)
    if val:
        return val.strip()
    for path in (f"/run/secrets/{name}", f"/run/secrets/{name.lower()}"):
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
    return default

# =============================================================================
# CLAVE DE API (API KEY) DEL PROVEEDOR DE IA
# =============================================================================
# Aquí se guarda la clave del proveedor que contrate o use la municipalidad
# (Google Gemini, OpenAI, o cualquier servicio compatible en la nube).
# Si en el futuro la muni usa un servidor propio con IA local (Ollama),
# esta clave puede quedar vacía.
API_KEY = _read_secret("API_KEY", _read_secret("GOOGLE_API_KEY", ""))

# Mantenemos GOOGLE_API_KEY por compatibilidad con configuraciones previas
GOOGLE_API_KEY = API_KEY

# --- Tiempos y reintentos del LLM (para que el vecino no espere indefinido) ---
# LLM_TIMEOUT corta una consulta que quedó colgada. Las consultas reales
# resuelven en 5-10 s; 30 s deja margen sin dejar al vecino esperando de más.
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
# LLM_MAX_RETRIES: LangChain reintenta 6 veces por defecto, con espera
# creciente. Reintentar una cuota ya agotada solo demora la derivación a un
# humano, así que se deja un reintento para fallos de red momentáneos.
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# --- Modelo LLM (Ollama local, cuando LLM_PROVIDER == "ollama") ---
# Host del servidor Ollama (local en el servidor de producción).
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# Modelo multimodal local elegido para producción (Qwen2.5-VL ve texto e imágenes).
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-vl:7b")

# --- Retrieval (top-k balanceado para máxima precisión RAG) ---
TOP_K = int(os.getenv("TOP_K", "4"))

# --- Chunking (tamaño en caracteres; ~4 chars ≈ 1 token appx.) ---
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "2400"))  # ~600 tokens
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "240"))  # ~60 tokens

# --- Memoria de conversación ---
# Cantidad de últimas interacciones (pares pregunta/respuesta) por sesión
MEMORY_LAST_TURNS = int(os.getenv("MEMORY_LAST_TURNS", "3"))

# --- Retención del historial (Ley 19.628: minimización / duración limitada) ---
# Edad máxima de los mensajes en la base (segundos) antes de borrarse
# automáticamente. Por defecto 24 h (86400 s). Se cumple con el borrado
# perezoso en chat_memory.purge_old_if_needed().
HISTORY_MAX_AGE = int(os.getenv("HISTORY_MAX_AGE", "86400"))

# --- Datos de contacto para derivación a agente humano (editable) ---
# Usados cuando el RAG no encuentra la respuesta (cierre rápido, sin bucle).
# La gestión municipal puede editarlos en .env sin tocar el código.
CONTACTO_TELEFONO = os.getenv("CONTACTO_TELEFONO", "2 2345 6000")
CONTACTO_EMAIL = os.getenv("CONTACTO_EMAIL", "atencion@lacisterna.cl")
CONTACTO_OFICINA = os.getenv(
    "CONTACTO_OFICINA", "Departamento de Atención al Vecino"
)

# --- Transferencia a agente humano (en tiempo real) ---
# Horario en que los agentes operan (para ofrecer la derivación en vivo).
# Formato libre; también se usan AGENTE_HORA_INICIO/AGENTE_HORA_FIN (HH:MM,
# hora local del servidor) para saber si "ahora" hay agentes disponibles.
AGENTE_HORARIO_TEXTO = os.getenv(
    "AGENTE_HORARIO_TEXTO", "Lunes a Viernes, de 9:00 a 17:00 hrs."
)
AGENTE_HORA_INICIO = os.getenv("AGENTE_HORA_INICIO", "09:00")  # 24h local
AGENTE_HORA_FIN = os.getenv("AGENTE_HORA_FIN", "17:00")  # 24h local

# Claves de acceso a los paneles (Jerarquía de 3 niveles)
# Nivel 1: Super Administrador Supremo (/admin)
ADMIN_PANEL_CLAVE = _read_secret("ADMIN_PANEL_CLAVE", _read_secret("AGENTE_PANEL_CLAVE", "SuperSecretoCisterna2026"))
AGENTE_PANEL_CLAVE = ADMIN_PANEL_CLAVE
# Nivel 2: Administrador Municipal (/administrador)
ADMINISTRADOR_PASSWORD = _read_secret("ADMINISTRADOR_PASSWORD", "muni2026")
# Nivel 3: Documentación y Reportes (/docs)
DOCS_PASSWORD = _read_secret("DOCS_PASSWORD", "docs2026")

# Texto que se muestra cuando NO hay agente disponible en este momento
# (fuera de horario o agente ocupado). Se ofrece contacto tradicional.
AGENTE_NO_DISPONIBLE_TEXTO = os.getenv(
    "AGENTE_NO_DISPONIBLE_TEXTO",
    "Por este momento no hay agentes disponibles. "
    "Estos son nuestros canales de atención: "
    f"{os.getenv('CONTACTO_OFICINA', 'Departamento de Atención al Vecino')} "
    f"al teléfono {CONTACTO_TELEFONO} o correo {CONTACTO_EMAIL}.",
)

# --- Rutas ---
# Ruta a la base vectorial ChromaDB
PERSIST_DIRECTORY = os.getenv("PERSIST_DIRECTORY", os.path.join(_BASE_DIR, "chroma_db"))
# Ruta a la base SQLite de memoria conversacional
MEMORY_DB_PATH = os.getenv("MEMORY_DB_PATH", os.path.join(_BASE_DIR, "chat_history.db"))
# Carpeta con los PDFs a indexar
DATA_DIR = os.getenv("DATA_DIR", os.path.join(_BASE_DIR, "data"))
# --- MODO PILOTO Y DERIVACIÓN A AGENTE WHATSAPP ---
HABILITAR_DERIVACION_AGENTE = os.getenv("HABILITAR_DERIVACION_AGENTE", "True").lower() in ("true", "1", "yes")
MODO_PILOTO_WHATSAPP = os.getenv("MODO_PILOTO_WHATSAPP", "False").lower() in ("true", "1", "yes")
WHATSAPP_BUSINESS_URL = os.getenv("WHATSAPP_BUSINESS_URL", "https://wa.me/56912345678")
