# =============================================================================
# Dockerfile — Bot RAG 'Cisternin' (Municipalidad de La Cisterna)
#
# Imagen ÚNICA multiuso: funciona en dev con Google Gemini (LLM_PROVIDER=google)
# y en producción con Ollama local (LLM_PROVIDER=ollama + servicio ollama).
# La configuración se pasa 100% por variables de entorno (.env).
#
# Build:
#   docker build -t cisternin-bot .
# Run (desarrollo):
#   docker run --rm -p 8000:8000 -v ./.env:/app/.env cisternin-bot
# Run (producción, con docker-compose: app + ollama + cron):
#   docker compose --profile prod up -d
# =============================================================================

FROM python:3.11-slim

# Sin prompts y UTC (Chile usa UTC-4/UTC-3; ajustar con TZ al desplegar)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema:
#  - libgomp1: OpenMP requerido por torch (sentence-transformers).
#  - libgl1: OpenGL para pymupdf en slim (a veces se necesita libglib).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        curl \
        bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Primero requirements (aprovecha caché de capas de Docker)
COPY requirements.txt ./
RUN pip install -r requirements.txt \
    && pip install langchain-ollama gdown wsproto

# Código de la aplicación (excluye lo que marca .dockerignore)
COPY app/ ./app/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY .env.example ./
COPY README.md ./

# Caché de modelos HuggingFace (embeddings) dentro del contenedor:
# montar un volumen en /app/.hf_cache para no re-descargar en cada arranque.
ENV HF_HOME=/app/.hf_cache

# Puerto HTTP de la API
EXPOSE 8000

# Salud: sin curl usamos urllib de la stdlib
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=5)" || exit 1

# Arranque: bind 0.0.0.0 para que Caddy/Nginx (o el túnel) encaminen hacia él.
# wsproto: transporte WebSocket exigido por el proyecto (no el default).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "wsproto"]