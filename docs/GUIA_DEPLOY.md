# Guia de Despliegue en Servidor (Docker)

Procedimiento para instalar y poner en marcha el servicio en un servidor Linux (Ubuntu/Debian) mediante Docker Compose.

## Requisitos previos

1. **Docker Engine y Docker Compose v2** instalados y operativos.
2. (Opcional) **Controladores NVIDIA y NVIDIA Container Toolkit** instalados si el servidor dispone de aceleracion por GPU.

## Pasos de instalacion

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Municipalidad-Lacisterna/Chatbot-RAG.git
   cd Chatbot-RAG
   ```

2. **Generacion inicial del archivo de entorno:**
   Ejecutar el script de despliegue:
   ```bash
   ./deploy.sh
   ```
   El script creara un archivo `.env` inicial si no existe y solicitara su configuracion.

3. **Configuracion de variables (Cambiar API_KEY con nano):**
   Para configurar o cambiar la clave de Inteligencia Artificial (API Key) y los parametros del sistema, abrir el archivo de configuracion con el editor `nano`:
   ```bash
   nano .env
   ```
   Dentro del editor:
   - Navegar con las flechas del teclado hasta la linea `API_KEY=`.
   - Pegar la clave del proveedor de IA (puedes pegar con clic derecho o con `Ctrl + Shift + V`).
   - Ejemplo: `API_KEY=AIzaSyD-tu_clave_aqui`
   - Para guardar los cambios: presionar `Ctrl + O` y luego `Enter`.
   - Para salir de nano: presionar `Ctrl + X`.

   Parametros principales a revisar en `.env`:
   - `API_KEY`: Clave del proveedor de IA en la nube (ej. Google Gemini u otro).
   - `DOMAIN_NAME`: Dominio publico para emision de certificados TLS (ej. `chatbot.lacisterna.cl`).
   - `ADMIN_PANEL_CLAVE`: Clave de acceso administrativa para el panel web (`/admin`).
   - `DOCS_PASSWORD`: Clave de acceso al portal de documentacion y reportes (`/docs`).

   Si el servicio ya estaba corriendo, reiniciar el contenedor para aplicar los cambios:
   ```bash
   docker compose restart app
   ```

4. **Ejecucion del despliegue:**
   Ejecutar nuevamente el script:
   ```bash
   ./deploy.sh
   ```

El script detectara la disponibilidad de GPU, compilara los contenedores necesarios, verificara la disponibilidad del modelo en Ollama y levantara el stack en segundo plano.

5. **Configuracion automatica de Red (Tailscale + Cloudflare Tunnel):**
   Para configurar el acceso seguro y la publicacion web sin abrir puertos en el firewall municipal:
   ```bash
   bash scripts/setup_red_cisternin.sh
   ```
   Este script automatiza:
   - **Tailscale Mesh VPN:** Provee la IP privada (100.x.y.z) para acceder de forma segura a los paneles `/admin` y `/docs` desde cualquier dispositivo autorizado sin exponerlos a internet abierto.
   - **Cloudflare Tunnel:** Instala y levanta el servicio de túnel cifrado conectando el puerto 8000 con el subdominio municipal (`https://chatbot.lacisterna.cl`).
