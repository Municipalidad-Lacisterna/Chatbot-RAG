# Despliegue en Docker - Chatbot Cisternin (WhatsApp Municipal)

Este documento explica cómo desplegar el Chatbot Municipal RAG (Cisternin) usando su script automatizado y Docker Compose. El diseño actual está optimizado para garantizar **Soberanía de Datos total**, ejecutando incluso el motor LLM (Ollama) localmente en el servidor, e integrando los módulos de ingesta vectorial, Caddy HTTPS y tareas programadas.

## 1. Requisitos Previos
- Docker y Docker Compose instalados en el servidor.
- *(Opcional pero muy recomendado)* GPU NVIDIA con `nvidia-container-toolkit` instalado, para obtener aceleración por hardware al correr modelos de inteligencia artificial locales de manera eficiente.

## 2. Preparar el Entorno (.env)
Toda la configuración se rige mediante las variables de entorno. Hay una plantilla provista:

```bash
cp .env.example .env
```

Edita el `.env` con tus preferencias:
- `DOMAIN_NAME`: Si asignarás un dominio real para Caddy (ej. `chatbot.lacisterna.cl`), de lo contrario déjalo en `localhost`.
- `LLM_PROVIDER` / `LLM_MODEL`: Permite elegir usar Ollama con modelos descargados localmente, o alternativamente un proveedor web (ej. Gemini/Google) si deseas evitar el cómputo pesado local.

## 3. Uso del Script `deploy.sh` (Despliegue "One-Click")
El proyecto incluye un script inteligente (`deploy.sh`) que autodetecta tu entorno, si posees GPU y si utilizas un dominio válido, para inyectar los "perfiles" correctos de Docker Compose en tiempo de ejecución.

Simplemente colócate en la raíz del proyecto y ejecuta:

```bash
bash deploy.sh
```

### ¿Qué sucede al ejecutar `deploy.sh`?
1. **Verificación inicial:** Verifica que exista el `.env`. Si no, lo crea de la plantilla y se detiene pidiendo que lo configures.
2. **Detección de GPU (`--profile gpu`):** Si detecta `nvidia-smi` en el sistema, habilita la aceleración por hardware e inyecta dinámicamente un archivo override temporal (`docker-compose.gpu.yml`) para reservar la GPU para el contenedor del LLM. De lo contrario, levanta en modo CPU (`--profile cpu`).
3. **Detección de HTTPS (`--profile web`):** Si el dominio en tu `.env` es diferente a `localhost`, activa Caddy para que solicite certificados TLS automáticos.
4. **Construcción y Lanzamiento:** Ejecuta de fondo un `docker-compose ... up -d --build` con todos los parámetros ajustados automáticamente.

## 4. Arquitectura de Contenedores
El stack levanta la siguiente infraestructura local y en red compartida (`cisternin-net`):
- **app**: El núcleo en FastAPI del chatbot (RAG, WebSockets, Historial).
- **ollama**: Motor para ejecutar el modelo generativo y de embeddings localmente (si está configurado).
- **ollama-init**: Un microservicio temporal que se asegura de invocar la descarga del modelo a Ollama antes de encender la `app`.
- **caddy**: Proxy inverso de alto rendimiento para enrutar el tráfico externo y proveer HTTPS "out of the box".
- **cron**: Un contenedor clon de `app` que ejecuta un script de limpieza/sincronización y duerme en bucle, manteniendo la base de datos vectorial Chroma actualizada sin bloquear a la aplicación principal.

## 5. Monitoreo y Verificación
Para observar cómo fluyen los mensajes y cómo contesta el RAG, revisa los logs unificados del stack:

```bash
docker-compose logs -f
```

*(Si usas versiones modernas de Docker, puedes usar `docker compose logs -f` en su lugar).*