#!/usr/bin/env bash
# Renderiza todas las escenas de la visualización IA.
# Uso: ./render_all.sh [qualidad]
#   qualidad: l (baja), m (media, default), h (alta)
set -e

QUAL="${1:-m}"
cd "$(dirname "$0")"

echo "🎬 Renderizando escenas (calidad: $QUAL)..."
for escena in PipelineCompleto FlujoDatos GrafoConocimiento; do
    echo "  → $escena"
    manim -q$QUAL pipeline_ia.py "$escena"
done

echo ""
echo "✅ Listo! Videos en media/videos/pipeline_ia/"