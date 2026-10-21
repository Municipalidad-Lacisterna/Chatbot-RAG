# Despliegue con Docker - Servicio Municipal

Instrucciones para compilar y ejecutar el servicio en servidores de produccion utilizando Docker y Docker Compose.

## 1. Requisitos previos

- Docker Engine 24+ y Docker Compose v2.
- (Opcional) Tarjeta grafica NVIDIA con `nvidia-container-toolkit` configurado para aceleracion de inferencia local.

## 2. Configuracion de variables de entorno y API Key

Copiar la plantilla base y editar los parametros del sistema:

```bash
cp .env.example .env
nano .env
```

**Como cambiar la clave de Inteligencia Artificial (API Key) con `nano`:**
1. Al abrir `nano .env`, buscar con las flechas la linea `API_KEY=`.
2. Pegar la clave del proveedor contratado (con clic derecho o `Ctrl + Shift + V`).
3. Guardar el archivo: presionar `Ctrl + O` y luego `Enter`.
4. Salir de nano: presionar `Ctrl + X`.

Parametros principales a revisar:
- `API_KEY`: Clave del proveedor de IA (ej. Google Gemini, OpenAI u otro).
- `DOMAIN_NAME`: Dominio publico asignado para la emision automatica de certificados HTTPS mediante Caddy (ej. `chatbot.lacisterna.cl`). Si se define `localhost`, el proxy operara en HTTP estandar.
- `LLM_PROVIDER`: Proveedor de inferencia configurado (`google` para APIs en la nube, o `ollama` para ejecucion 100% local en el servidor propio).
- `ADMIN_PANEL_CLAVE`: Contraseña de administracion del sistema (`/admin`).
- `DOCS_PASSWORD`: Contraseña de acceso a reportes y documentacion (`/docs`).

Si el sistema ya esta en ejecucion y se actualizo la clave, reiniciar el servicio:
```bash
docker compose restart app
```

## 3. Despliegue automatizado con deploy.sh

El repositorio provee el script `deploy.sh` para simplificar la seleccion de perfiles de Docker Compose segun el hardware detectado:

```bash
bash deploy.sh
```

Comportamiento del script:
1. Comprueba la existencia del archivo `.env`. Si no existe, genera una copia desde `.env.example` y solicita su edicion.
2. Comprueba si existe aceleracion GPU disponible (`nvidia-smi`). Si se detecta, activa el perfil de GPU; de lo contrario, inicia los contenedores en modo CPU.
3. Si `DOMAIN_NAME` difiere de `localhost`, activa el servicio Caddy para la gestion automatica de certificados TLS.
4. Ejecuta la construccion de imagenes y levantamiento de servicios en segundo plano (`docker compose up -d --build`).

## 4. Servicios del stack

- **app**: Backend FastAPI con logica de consultas, endpoints REST y WebSockets.
- **ollama**: Motor de inferencia local para ejecucion de modelos de lenguaje y embeddings.
- **ollama-init**: Servicio auxiliar que verifica la presencia del modelo especificado antes del inicio del backend.
- **caddy**: Proxy inverso para enrutamiento web y gestion de conexiones cifradas HTTPS.
- **cron**: Tarea secundaria para la sincronizacion periodica de documentos y mantenimiento de la base vectorial.

## 5. Monitoreo y administracion

Para revisar los registros del sistema:
```bash
docker compose logs -f
```

Para detener los servicios conservando volumenes de datos:
```bash
docker compose down
```

## 6. Configuracion automatica de Red (Tailscale + Cloudflare Tunnel)

Para conectar el servidor municipal a la red segura y publicar el chatbot sin abrir puertos entrantes en el firewall institucional:

```bash
bash scripts/setup_red_cisternin.sh
```

El script se encarga de:
- Instalar e inicializar **Tailscale**, mostrando la IP privada (100.x.y.z) para administracion segura de `/admin` y `/docs`.
- Instalar y configurar el servicio de **Cloudflare Tunnel (`cloudflared`)** vinculado al subdominio municipal (`https://chatbot.lacisterna.cl`).
