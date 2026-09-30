FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        curl \
        bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# Instalamos también las dependencias extra para RAG y websockets
RUN pip install -r requirements.txt \
    && pip install langchain-ollama gdown wsproto

# Crear carpetas necesarias para volúmenes y semilla
RUN mkdir -p /app/data /app/chroma_db /app/data_persist /seed/chroma_db

# Copiar la aplicación
COPY app/ ./app/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY docker/ ./docker/
COPY chroma_db/ /seed/chroma_db/
COPY .env.example ./

# Variables de entorno por defecto para contenedores
ENV HF_HOME=/app/.hf_cache
ENV PERSIST_DIRECTORY=/app/chroma_db
ENV MEMORY_DB_PATH=/app/data_persist/chat_history.db
ENV DATA_DIR=/app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://127.0.0.1:${APP_PORT:-8000}/ || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
