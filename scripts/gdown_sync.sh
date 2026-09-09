#!/usr/bin/env bash
# =============================================================================
# gdown_sync.sh — Baja los documentos del municipio desde Google Drive (enlace
# público) y los indexa en el chatbot (ChromaDB).
#
# Por qué gdown y no rclone:
#   - rclone (v1.75) exige un Client ID propio de Google Cloud, cuya creación
#     requiere una cuenta con facturación (billing) configurada. La cuenta del
#     municipio NO tiene billing, así que rclone y la service account quedan
#     bloqueados.
#   - gdown descarga carpetas/archivos PÚBLICOS de Drive SIN autorización ni
#     billing: solo se necesita que la muni comparta la carpeta como
#     "Cualquier persona con el enlace puede ver" (lectura).
#
# FLUJO:
#   1. gdown descarga la carpeta pública del municipio → data/
#      CONSERVANDO la estructura de subcarpetas (p. ej. "Marco normativo" y
#      "Tramites" dentro de "Chat bot Cisterna").
#   2. La ingesta (app/ingestion.py) indexa los PDFs/MD/CSV de data/ en
#      ChromaDB y borra los físicos. Cada chunk queda etiquetado con su
#      subcarpeta/categoría (origen).
#
# USO:
#   scripts/gdown_sync.sh            # una sola vez
#   (el timer de systemd lo corre a las 07:00)
#
# NOTA: la ingesta borra los archivos físicos de data/ tras indexarlos.
#   Para conservar una copia local, activa BACKUP_DIR abajo.
# =============================================================================

set -euo pipefail

# ---------- Configuración ----------
# Ruta base del proyecto. En la laptop usa el default; en Docker se overrida
# con el entorno (PROJECT_DIR=/app).
PROJECT_DIR="${PROJECT_DIR:-/home/aspen/Alcaldia_Practica}"
DATA_DIR="$PROJECT_DIR/data"
# Enlace PÚBLICO del Drive de la carpeta que compartió la muni (abajo, el
# nombre de sección o una carpeta pública "Cualquier persona con el enlace").
# Formato: https://drive.google.com/drive/folders/<FOLDER_ID>
DRIVE_URL="${DRIVE_URL:-16paTbHeCuQw9YWH-ldniMJbxzuQvjBLD}"   # ID de la carpeta pública "Chat bot Cisterna"
# Opcional: conservar copia local de los archivos (ruta absoluta). Vacío = no.
BACKUP_DIR="${BACKUP_DIR:-}"
# Log (se usa para monitorear con Uptime Kuma etc.)
LOG_FILE="${LOG_FILE:-/tmp/gdown_sync.log}"
# Intérprete de Python. En la laptop usa el venv; en Docker, "python".
PYTHON="${PYTHON:-$PROJECT_DIR/venv/bin/python}"

# ---------- Validaciones ----------
if [ -z "$DRIVE_URL" ]; then
  echo "ERROR: define DRIVE_URL en $0 con el enlace público de la carpeta."
  echo "Formato esperado: https://drive.google.com/drive/folders/<FOLDER_ID>"
  exit 1
fi

GDOWN="$(command -v gdown || echo "$PROJECT_DIR/venv/bin/gdown")"
# Si el PYTHON definido no existe (caso Docker sin venv), usar python del PATH.
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

# ---------- Funciones ----------
log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') — $*" | tee -a "$LOG_FILE"
}

log "=== INICIO sincronización (gdown) ==="

if [ -n "$BACKUP_DIR" ]; then
  mkdir -p "$BACKUP_DIR"
  log "Respaldo antes de ingesta en: $BACKUP_DIR"
fi

log "Descargando '$DRIVE_URL' → $DATA_DIR"
mkdir -p "$DATA_DIR"

# Descargar la carpeta pública recursivamente. --folder descarga todo el
# contenido, incluida la estructura de subcarpetas. El directorio destino
# no debe existir aún para que gdown cree una subcarpeta; usamos un temporal
# y movemos el contenido para no mezclar con chats/ e inbox/.
STAGE_DIR="$DATA_DIR/.gdown_stage"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"
if ! "$GDOWN" --folder --continue "$DRIVE_URL" -O "$STAGE_DIR" >>"$LOG_FILE" 2>&1; then
  log "ERROR: falló la descarga con gdown (¿la carpeta es pública?)."
  rm -rf "$STAGE_DIR"
  exit 1
fi

# Mover a data/ conservando subcarpetas. Si gdown creó una subcarpeta raíz,
# la "subimos" un nivel; si descargó al frente del stage, movemos todo.
if ls "$STAGE_DIR"/*/ >/dev/null 2>&1 && [ -d "$STAGE_DIR/$(ls -d "$STAGE_DIR"/*/ 2>/dev/null | head -1 | xargs basename)" ]; then
  # Caso típico: una única subcarpeta raíz (el nombre de la carpeta de Drive)
  for d in "$STAGE_DIR"/*/; do
    if [ -z "$(find "$STAGE_DIR" -mindepth 1 -maxdepth 1 -type f | head -1)" ]; then
      # No hay archivos al frente del stage, solo una carpeta → subimos su contenido
      mv "$d"/* "$DATA_DIR"/ 2>/dev/null || true
      rm -rf "$d"
    fi
  done
fi

# Mover cualquier archivo o subcarpeta restante al frente de data/
shopt -s dotglob nullglob
for item in "$STAGE_DIR"/*; do
  [ -e "$item" ] && mv "$item" "$DATA_DIR"/ 2>/dev/null || true
done
shopt -u dotglob nullglob
rm -rf "$STAGE_DIR"

if [ -n "$BACKUP_DIR" ]; then
  find "$DATA_DIR" -type f \( -name '*.pdf' -o -name '*.md' -o -name '*.csv' \) \
    -exec cp --parents {} "$BACKUP_DIR"/ \; 2>/dev/null || true
  log "Copia de respaldo guardada en $BACKUP_DIR"
fi

log "Descarga completada."

# 2. Indexar en el chatbot (recorre data/ recursivamente, acepta pdf/md/csv).
#    La ingesta borra los archivos físicos tras indexarlos; los chunks quedan
#    en ChromaDB con el origen (subcarpeta/nombre).
if find "$DATA_DIR" -type f \( -name '*.pdf' -o -name '*.md' -o -name '*.csv' \) | grep -q .; then
  log "Indexando documentos en el chatbot..."
  (cd "$PROJECT_DIR" && "$PYTHON" -m app.ingestion) >>"$LOG_FILE" 2>&1
  log "Ingesta finalizada."
else
  log "No hay PDFs/MD/CSV nuevos en data/ (nada que indexar por ahora)."
fi

log "=== FIN sincronización OK ==="
