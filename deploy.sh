#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "========================================================="
echo "🐻💙 Despliegue Automatizado - Cisternin (Papá Oso)"
echo "========================================================="

# 1. Verificar .env
if [ ! -f ".env" ]; then
    echo "⚠️ No se encontró '.env'. Copiando plantilla desde '.env.example'..."
    cp .env.example .env
    echo "🛑 DETENIENDO. Por favor, edita el archivo .env con tus claves y vuelve a ejecutar ./deploy.sh"
    exit 1
fi

source .env

# Detectar comando compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ ERROR: No se encontró Docker Compose instalado."
    exit 1
fi

PROFILES="--profile cron"

# 2. Detectar GPU
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU NVIDIA detectada. Habilitando aceleración por hardware."
    PROFILES="$PROFILES --profile gpu"
    
    # Crear override temporal para inyectar recursos GPU
    cat << 'GPU_EOF' > docker-compose.gpu.yml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
GPU_EOF
    COMPOSE_CMD="$COMPOSE_CMD -f docker-compose.yml -f docker-compose.gpu.yml"
else
    echo "⚠️ No se detectó GPU NVIDIA. Funcionando en modo CPU."
    PROFILES="$PROFILES --profile cpu"
    rm -f docker-compose.gpu.yml
fi

# 3. Detectar Dominio (Caddy)
if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "localhost" ]; then
    echo "🌐 Dominio '$DOMAIN_NAME' detectado. Habilitando HTTPS automático (Caddy)."
    PROFILES="$PROFILES --profile web"
fi

echo "========================================================="
echo "🚀 Construyendo y levantando contenedores..."
echo "Comando: $COMPOSE_CMD $PROFILES up -d --build"
echo "========================================================="

$COMPOSE_CMD $PROFILES up -d --build

echo "========================================================="
echo "✅ Despliegue completado."
echo "Puedes ver los logs con: $COMPOSE_CMD logs -f"
echo "========================================================="
