#!/usr/bin/env bash
set -e

# Esperar a Ollama si estamos usando el LLM local
if [ "$LLM_PROVIDER" = "ollama" ]; then
    OLLAMA_URL="${OLLAMA_HOST:-http://ollama:11434}"
    TARGET_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
    echo "⏳ Esperando a que el modelo $TARGET_MODEL en Ollama esté listo..."
    
    while ! curl -s "$OLLAMA_URL/api/tags" | grep -q "$TARGET_MODEL"; do
        sleep 5
    done
    echo "✅ Modelo LLM listo para responder."
fi

# Seed ChromaDB si está vacía
if [ ! -f "$PERSIST_DIRECTORY/chroma.sqlite3" ]; then
    echo "🌱 ChromaDB vacía. Copiando base de conocimiento (seed)..."
    if [ -d "/seed/chroma_db" ]; then
        cp -r /seed/chroma_db/* "$PERSIST_DIRECTORY/"
        echo "✅ Conocimiento municipal indexado."
    else
        echo "⚠️ No se encontró directorio de seed."
    fi
fi

echo "🚀 Arrancando el chatbot municipal..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}" --ws wsproto
