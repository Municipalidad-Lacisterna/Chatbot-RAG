# 🏛️ Cisternin: Chatbot Municipal RAG
Asistente virtual de la Municipalidad de La Cisterna, diseñado para automatizar la atención ciudadana con **Soberanía de Datos Total (100% Local)** y **Arquitectura RAG** (Generación Aumentada por Recuperación).

Cisternin lee documentos municipales (PDFs, Markdown, CSVs de Transparencia) inyectados automáticamente y responde las dudas de los vecinos de forma cálida, sin alucinar y en tiempo real.

## ✨ Características Principales
* **100% Soberanía de Datos:** Toda la información y el procesamiento (base vectorial e historial) ocurren de forma local en el servidor municipal, respaldado por IA local (Ollama).
* **Modo Piloto (Horario de Oficina):** Interceptor configurable (`MODO_PILOTO_WHATSAPP`) que redirige a los vecinos automáticamente al WhatsApp oficial con ejecutivos humanos durante el horario hábil, y libera a la IA para atender en horario inhábil.
* **Escudo de Privacidad:** Bloqueo automático de datos sensibles (RUTs, sueldos). Si se consultan, deriva al Portal de Transparencia.
* **Filtro de Respeto (3 Strikes):** Sistema automático que cierra la sesión ante groserías reiteradas.
* **Handoff a Agentes (WebSocket):** Si el bot no tiene la información documentada, no inventa. Deriva el chat en vivo a un agente municipal sin cortar la sesión del vecino.
* **Privacidad (Ley 19.628):** El historial de chat es anónimo y se purga automáticamente cada 24 horas.
* **Ingesta desde Google Drive:** Sincronización transparente de los documentos oficiales directamente desde el Drive de la Municipalidad.

## 🚀 Despliegue y Arquitectura

El sistema está diseñado para exponerse de forma segura sin abrir puertos en el servidor, utilizando **Cloudflare Tunnels**. 

### Requisitos Previos
- Python 3.11+
- Base de datos vectorial: ChromaDB (integrada)
- LLM Provider: **Ollama** (ej. `santi-gemma` o `qwen2.5:7b`) o **Google Gemini** como fallback/alternativa.

### Instalación Rápida
1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/Municipalidad-Lacisterna/Chatbot-RAG
   cd Chatbot-RAG
   ```

2. **Entorno Virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configuración (.env):**
   Copia la plantilla y configura tus variables (modelo, proveedor, base de datos, URL de WhatsApp):
   ```bash
   cp .env.example .env
   ```
   *Nota: Configura `MODO_PILOTO_WHATSAPP=true` para activar la restricción de horario de oficina.*

4. **Arrancar el Servidor Principal:**
   ```bash
   setsid nohup venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --ws wsproto > logs/uvicorn.log 2>&1 < /dev/null & disown
   ```
   *El panel del vecino estará disponible internamente en `http://127.0.0.1:8000/chat` y públicamente mediante el túnel configurado (ej. `https://bot.tu-dominio.com`).*

## 📁 Estructura General
* `/app`: Core del chatbot (RAG, Interceptor Piloto, WebSockets, Memoria SQLite, Seguridad).
* `/data`: Carpeta de almacenamiento temporal para documentos previo a su indexación.
* `/static`: Interfaces de usuario responsivas y limpias (Vecino, Panel Agente, Panel Admin) con formateo inteligente de enlaces.
* `/docs`: Documentación interna y manuales para el municipio.
* `/docker`: Scripts de orquestación y despliegue rápido para producción (Dockerfile, docker-compose).

---
*Desarrollado con ❤️ para agilizar y modernizar el contacto con los vecinos.*
