# Visualización IA — Chatbot Cisternin

Animaciones con **Manim** que muestran cómo funciona la IA del bot.
Perfectas para presentaciones a jefes, demos o material de difusión.

## Escenas disponibles

| Escena | Descripción | Duración aprox |
|---|---|---|
| `PipelineCompleto` | El pipeline completo: pregunta → Capa 1 (normalización) → Capa 2 (intención) → Capa 3 (retrieval) → LLM → respuesta + cortocircuitos + estadísticas | ~50s |
| `FlujoDatos` | Mini-demo de 15s: cómo "pa la receta" se transforma en la respuesta de la Farmacia Comunal | ~15s |
| `GrafoConocimiento` | El grafo de conocimiento municipal: trámites conectados alrededor de Cisternin | ~20s |

## Cómo renderizar

```bash
# Todo de una vez (calidad media)
manim -qm pipeline_ia.py PipelineCompleto
manim -qm pipeline_ia.py FlujoDatos
manim -qm pipeline_ia.py GrafoConocimiento

# O un solo render
manim -ql pipeline_ia.py PipelineCompleto   # calidad baja (rápido, prueba)
manim -qm pipeline_ia.py PipelineCompleto   # calidad media
manim -qh pipeline_ia.py PipelineCompleto   # calidad alta (mejor)
```

## Dónde quedan los videos

```
media/videos/pipeline_ia/
├── 480p15/  → calidad baja (480p)
└── 720p30/  → calidad media (720p)
```

## Personalizar colores

Toda la paleta está en las constantes al inicio del archivo:

```python
COLOR_FONDO     = "#0a0a1a"   # Fondo oscuro
COLOR_PRIMARIO  = "#25D366"   # Verde WhatsApp / Cisternin
COLOR_CAPA1     = "#4FC3F7"   # Normalización (azul)
COLOR_CAPA2     = "#FF8A65"   # Intención (naranja)
COLOR_CAPA3     = "#AED581"   # Retrieval (verde claro)
COLOR_LLM       = "#CE93D8"   # LLM (lila)
```

## Requisitos

```bash
pip install manim   # Manim Community v0.21+
ffmpeg              # Necesario para renderizar video
```