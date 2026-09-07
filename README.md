# 🏛️ Cisternin: Chatbot Municipal RAG
Asistente virtual de la Municipalidad de La Cisterna, diseñado para automatizar la atención ciudadana con **Soberanía de Datos Total (100% Local)**.

Cisternin utiliza Arquitectura RAG (Generación Aumentada por Recuperación) para leer documentos municipales (PDFs, Markdown, CSVs de Transparencia) y responder las dudas de los vecinos de forma cálida, sin alucinar y en tiempo real.

## ✨ Características Principales
* **100% Soberanía de Datos:** Toda la información y el procesamiento (base vectorial e historial) ocurren de forma local en el servidor municipal.
* **Escudo de Privacidad:** Bloqueo automático de datos sensibles (RUTs, sueldos). Si se consultan, deriva al Portal de Transparencia.
* **Filtro de Respeto (3 Strikes):** Sistema automático que cierra la sesión ante groserías reiteradas.
* **Handoff a Agentes (WebSocket):** Si el bot no tiene la información documentada, no inventa. Deriva el chat en vivo a un agente municipal sin cortar la sesión del vecino.
* **Privacidad (Ley 19.628):** El historial de chat es anónimo y se purga automáticamente cada 24 horas.

## 🚀 Instalación y Arranque

1. **Clonar el repositorio:**
   ```bash
   git clone [<tu-repo>](https://github.com/Municipalidad-Lacisterna/Chatbot-RAG)
   cd Alcaldia_Practica
   ```

2. **Entorno Virtual:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configuración (.env):**
   Copia la plantilla y configura tus variables (modelo, proveedor, base de datos):
   ```bash
   cp .env.example .env
   ```

4. **Arrancar el Servidor:**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --ws wsproto
   ```
   *El panel del vecino estará disponible en `http://127.0.0.1:8000/chat`*

## 📁 Estructura General
* `/app`: Core del chatbot (RAG, WebSockets, Memoria SQLite, Seguridad).
* `/data`: Carpeta de almacenamiento temporal para documentos previo a su indexación.
* `/static`: Interfaces de usuario (Vecino, Panel Agente, Panel Admin).
* `/docs`: Documentación interna del municipio.
