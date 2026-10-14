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

3. **Configuracion de variables:**
   Editar el archivo `.env`:
   ```bash
   nano .env
   ```
   Parametros principales:
   - `DOMAIN_NAME`: Dominio publico para emision de certificados TLS (ej. `consultas.lacisterna.cl`).
   - `AGENTE_PANEL_CLAVE`: Clave de acceso administrativa para el panel de agentes.
   - `DRIVE_URL`: ID de la carpeta de Google Drive donde residen los documentos municipales.

4. **Ejecucion del despliegue:**
   Ejecutar nuevamente el script:
   ```bash
   ./deploy.sh
   ```

El script detectara la disponibilidad de GPU, compilara los contenedores necesarios, verificara la disponibilidad del modelo en Ollama y levantara el stack en segundo plano.
