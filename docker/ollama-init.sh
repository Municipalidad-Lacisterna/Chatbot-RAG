#!/usr/bin/env sh
set -e
OLLAMA_HOST=${OLLAMA_HOST:-"http://ollama:11434"}
OLLAMA_MODEL=${OLLAMA_MODEL:-"qwen2.5:7b"}

echo "⏳ Esperando a que Ollama inicie en $OLLAMA_HOST..."
while ! curl -s "$OLLAMA_HOST/api/tags" > /dev/null; do
    sleep 2
done

echo "✅ Ollama listo. Verificando modelo $OLLAMA_MODEL..."
if curl -s "$OLLAMA_HOST/api/tags" | grep -q "$OLLAMA_MODEL"; then
    echo "✅ Modelo $OLLAMA_MODEL ya está instalado."
else
    echo "⬇️ Descargando modelo $OLLAMA_MODEL (esto puede tomar varios minutos)..."
    curl -s -X POST "$OLLAMA_HOST/api/pull" -d "{\"name\": \"$OLLAMA_MODEL\"}"
    echo "✅ Modelo $OLLAMA_MODEL descargado."
fi
