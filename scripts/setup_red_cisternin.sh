#!/usr/bin/env bash
# =============================================================================
# setup_red_cisternin.sh — Instalación y configuración de Red Segura
# (Tailscale Mesh VPN + Cloudflare Tunnel) para el Chatbot Cisternin
# =============================================================================
# Este script automatiza la configuración de red en el servidor municipal:
# 1. Instala y configura Tailscale (VPN privada para administración remota sin abrir puertos).
# 2. Instala y configura Cloudflared (túnel público seguro con HTTPS para los vecinos).
# 3. Vincula el túnel al servicio local de Cisternin (puerto 8000).
# =============================================================================

set -euo pipefail

# Colores para la terminal
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARILLO='\033[1;33m'
ROJO='\033[0;31m'
NC='\033[0m' # Sin color

info()  { echo -e "${AZUL}[INFO]${NC} $1"; }
ok()    { echo -e "${VERDE}[OK]${NC} $1"; }
warn()  { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
error() { echo -e "${ROJO}[ERROR]${NC} $1"; exit 1; }

echo -e "${VERDE}"
echo "=========================================================="
echo "   CONFIGURACIÓN DE RED SEGURA: CISTERNIN MUNICIPAL"
echo "        (Tailscale Mesh VPN + Cloudflare Tunnel)         "
echo "=========================================================="
echo -e "${NC}"

# 1. Comprobar permisos de superusuario (sudo / root)
if [ "$EUID" -ne 0 ]; then
    warn "Este script requiere permisos de administrador para instalar servicios de red."
    warn "Reejecutando con sudo..."
    exec sudo bash "$0" "$@"
fi

# -----------------------------------------------------------------------------
# PARTE 1: INSTALACIÓN Y CONFIGURACIÓN DE TAILSCALE
# -----------------------------------------------------------------------------
info "Paso 1: Verificando Tailscale (VPN Mesh WireGuard)..."

if command -v tailscale &>/dev/null; then
    ok "Tailscale ya está instalado en el sistema."
else
    info "Instalando Tailscale desde el repositorio oficial..."
    curl -fsSL https://tailscale.com/install.sh | sh
    systemctl enable --now tailscaled
    ok "Tailscale instalado y servicio iniciado exitosamente."
fi

# Verificar si el nodo ya está conectado a una red Tailnet
TAILSCALE_STATUS=$(tailscale status 2>/dev/null || true)
if echo "$TAILSCALE_STATUS" | grep -q "100\."; then
    TAILSCALE_IP=$(tailscale ip -4)
    ok "El servidor ya está conectado a Tailscale. IP privada: ${VERDE}${TAILSCALE_IP}${NC}"
else
    info "El servidor aún no está conectado a una red Tailscale."
    
    # Si viene pasada una Auth Key por variable de entorno, usarla
    TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-}"
    if [ -n "$TAILSCALE_AUTHKEY" ]; then
        info "Conectando usando la clave de autenticación provista..."
        tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="cisternin-server" --accept-routes
    else
        warn "Se generará un enlace de inicio de sesión de Tailscale."
        warn "Abre el enlace en tu navegador para autorizar este servidor en tu red:"
        echo ""
        tailscale up --hostname="cisternin-server" --accept-routes || true
    fi
    
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "Pendiente de login")
    ok "IP asignada de Tailscale: ${VERDE}${TAILSCALE_IP}${NC}"
fi

# -----------------------------------------------------------------------------
# PARTE 2: INSTALACIÓN Y CONFIGURACIÓN DE CLOUDFLARE TUNNEL (CLOUDFLARED)
# -----------------------------------------------------------------------------
echo ""
info "Paso 2: Verificando Cloudflare Tunnel (cloudflared)..."

if command -v cloudflared &>/dev/null; then
    ok "cloudflared ya está instalado en el sistema."
else
    info "Descargando e instalando binario oficial de cloudflared..."
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  CF_ARCH="amd64" ;;
        aarch64) CF_ARCH="arm64" ;;
        armv7l)  CF_ARCH="arm" ;;
        *)       CF_ARCH="amd64" ;;
    esac

    # En sistemas basados en Debian/Ubuntu intentar con paquete .deb
    if command -v apt-get &>/dev/null; then
        TEMP_DEB="/tmp/cloudflared-${CF_ARCH}.deb"
        curl -fsSL -o "$TEMP_DEB" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}.deb"
        dpkg -i "$TEMP_DEB" || apt-get install -f -y
        rm -f "$TEMP_DEB"
    else
        # Binario directo en /usr/local/bin
        curl -fsSL -o /usr/local/bin/cloudflared "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}"
        chmod +x /usr/local/bin/cloudflared
    fi
    ok "cloudflared instalado con éxito."
fi

# Configurar el servicio de túnel si se provee el Token de Cloudflare
CLOUDFLARED_TOKEN="${CLOUDFLARED_TOKEN:-}"

# Si no está en variable, verificar si existe en .env del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

if [ -z "$CLOUDFLARED_TOKEN" ] && [ -f "$ENV_FILE" ]; then
    CLOUDFLARED_TOKEN=$(grep -E '^CLOUDFLARED_TOKEN=' "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || true)
fi

if [ -z "$CLOUDFLARED_TOKEN" ]; then
    echo ""
    warn "No se detectó un TOKEN de túnel de Cloudflare automático."
    echo -e "Si ya tienes tu token del panel de Cloudflare Zero Trust, pégalo aquí."
    echo -e "Si prefieres configurarlo después o usar Docker, solo presiona ${AMARILLO}ENTER${NC}."
    read -r -p "Token de Cloudflare (opcional): " USER_TOKEN
    CLOUDFLARED_TOKEN=$(echo "$USER_TOKEN" | tr -d '[:space:]')
fi

if [ -n "$CLOUDFLARED_TOKEN" ]; then
    info "Instalando servicio systemd del túnel de Cloudflare..."
    cloudflared service install "$CLOUDFLARED_TOKEN" || {
        warn "El servicio ya existía o requiere reinicio; recargando..."
        systemctl restart cloudflared || true
    }
    systemctl enable --now cloudflared
    ok "Túnel de Cloudflare configurado y activo como servicio del sistema."
    
    # Guardar en .env para persistencia
    if [ -f "$ENV_FILE" ]; then
        if grep -q '^CLOUDFLARED_TOKEN=' "$ENV_FILE"; then
            sed -i "s|^CLOUDFLARED_TOKEN=.*|CLOUDFLARED_TOKEN=${CLOUDFLARED_TOKEN}|" "$ENV_FILE"
        else
            echo "CLOUDFLARED_TOKEN=${CLOUDFLARED_TOKEN}" >> "$ENV_FILE"
        fi
        ok "Token guardado en el archivo .env para Docker Compose."
    fi
else
    info "Se omitió la instalación del token de Cloudflare."
    info "Para levantarlo vía Docker cuando tengas el token, agrégalo a tu .env y ejecuta:"
    echo "    docker compose --profile cloudflared up -d"
fi

# -----------------------------------------------------------------------------
# PARTE 3: VERIFICACIÓN DEL CHATBOT LOCAL
# -----------------------------------------------------------------------------
echo ""
info "Paso 3: Verificando estado local de Cisternin (puerto 8000)..."

if curl -s -f http://127.0.0.1:8000/ &>/dev/null; then
    ok "El backend de Cisternin está respondiendo correctamente en el puerto 8000."
else
    warn "El backend en http://127.0.0.1:8000 aún no está en ejecución."
    warn "Inícialo con Docker o con systemd:"
    echo "    docker compose up -d"
    echo "    o bien: systemctl --user start cisternin"
fi

# -----------------------------------------------------------------------------
# RESUMEN FINAL DE ARQUITECTURA
# -----------------------------------------------------------------------------
echo ""
echo -e "${VERDE}=========================================================="
echo "          RESUMEN DE INFRAESTRUCTURA DE RED"
echo "==========================================================${NC}"
echo -e " ${AZUL}1. Red Privada Segura (Administrador TI / Jefatura via Tailscale):${NC}"
echo -e "   - IP Servidor:     ${VERDE}${TAILSCALE_IP}${NC}"
echo -e "   - Panel Admin:     ${AZUL}http://${TAILSCALE_IP}:8000/admin${NC}"
echo -e "   - Documentación:   ${AZUL}http://${TAILSCALE_IP}:8000/docs${NC}"
echo -e "   - Acceso seguro sin exponer puertos de administración a Internet."
echo ""
echo -e " ${AZUL}2. Red Pública Ciudadana (Túnel Cloudflare):${NC}"
echo -e "   - Tráfico web:     ${VERDE}Cifrado TLS de extremo a extremo${NC}"
echo -e "   - Puertos abiertos: ${VERDE}0 puertos entrantes en el firewall${NC}"
echo -e "   - URL de Atención: https://chatbot.lacisterna.cl/chat (o tu subdominio configurado)"
echo "=========================================================="
echo ""
ok "Configuración de red completada con éxito."
