#!/usr/bin/env bash
# =============================================================================
# docker_cron.sh — Mantenimiento programado dentro del contenedor (perfil prod)
#
# Replica los timers de systemd del despliegue local:
#   - purga del historial cada 6 h  (Ley 19.628 → retención máx. 24 h)
#   - sincronización del Drive a las 07:00 (ingesta de documentos nuevos)
#
# Diseñado para correr como entrypoint de un contenedor "cron" en compose,
# en un loop infinito con sleeps (sin depender de cron en la imagen).
# =============================================================================

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/app}"
PYTHON="${PYTHON:-python}"
LOG_PURGE="/tmp/purge_historial.log"
LOG_SYNC="/tmp/gdown_sync.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') — $*" | tee -a "/tmp/docker_cron.log"
}

log "Cron de mantenimiento iniciado (PROJECT_DIR=$PROJECT_DIR)"

# Marca de última purga (para purgar cada ~6 h, no en cada ciclo)
ULTIMA_PURGA="/tmp/.ultima_purga"
INTERVALO_PURGA=21600   # 6 h en segundos

while true; do
  AHORA=$(date +%H:%M)
  AHORA_EPOCH=$(date +%s)

  # ── Purga de historial cada ~6 h (Ley 19.628 → retención máx. 24 h) ─────
  ULTIMA=0
  [ -f "$ULTIMA_PURGA" ] && ULTIMA=$(cat "$ULTIMA_PURGA" 2>/dev/null || echo 0)
  if [ $((AHORA_EPOCH - ULTIMA)) -ge "$INTERVALO_PURGA" ]; then
    log "Purga de historial (última hace $(( (AHORA_EPOCH - ULTIMA) / 60 )) min)..."
    (cd "$PROJECT_DIR" && "$PYTHON" scripts/purge_historial.py) >>"$LOG_PURGE" 2>&1 || \
      log "⚠️ Purga falló (ver $LOG_PURGE)"
    date +%s > "$ULTIMA_PURGA"
  fi

  # ── Sincronización Drive a las 07:00 ─────────────────────────────────────
  if [ "$AHORA" = "07:00" ]; then
    log "Hora de sincronización del Drive (07:00): ejecutando gdown_sync..."
    bash "$PROJECT_DIR/scripts/gdown_sync.sh" || \
      log "⚠️ Sincronización falló (ver $LOG_SYNC)"
  fi

  # Duerme 57 min (margen para no desfasar la hora de 07:00)
  sleep 3420
done