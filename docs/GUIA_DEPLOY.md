# Guía Rápida de Despliegue - Cisternin (Docker)

Esta guía explica cómo desplegar el chatbot municipal en un servidor limpio (Ubuntu/Debian) usando solo Docker.

## Prerrequisitos

1. **Docker y Docker Compose v2** instalados.
2. (Opcional) **Controladores NVIDIA y NVIDIA Container Toolkit** instalados (si el servidor tiene GPU).

## Instrucciones Paso a Paso

1. **Clonar/Copiar el repositorio** en el servidor municipal.
   ```bash
   git clone <URL> Alcaldia_Practica
   cd Alcaldia_Practica
   ```

2. **Primer intento de despliegue (Generación de .env)**
   Ejecuta el script de despliegue por primera vez:
   ```bash
   ./deploy.sh
   ```
   *El script se detendrá y te avisará que ha creado un archivo `.env` base.*

3. **Configurar Variables**
   Edita el archivo `.env` generado:
   ```bash
   nano .env
   ```
   **Datos críticos a cambiar:**
   - `DOMAIN_NAME`: Pon el dominio real (ej. `chatbot.lacisterna.cl`). Si dejas `localhost`, no se instalará el certificado HTTPS.
   - `AGENTE_PANEL_CLAVE`: Pon una clave segura para el panel administrativo.
   - `DRIVE_URL`: Asegura que sea la carpeta correcta si ha cambiado.

4. **Desplegar de verdad**
   Vuelve a ejecutar el script. Este detectará automáticamente si hay GPU y levantará los servicios que correspondan:
   ```bash
   ./deploy.sh
   ```

## ¿Qué sucede durante el primer arranque?

- Si el servidor tiene NVIDIA, habilitará la aceleración 3D en el compose de Ollama.
- El servicio `ollama-init` descargará el modelo de lenguaje automáticamente (puede tardar unos minutos).
- La app copiará el "Cerebro" base (base vectorial pre-entrenada) si el volumen local está vacío.
- Si configuraste un dominio real, Caddy pedirá el certificado SSL/TLS automáticamente a Let's Encrypt.
