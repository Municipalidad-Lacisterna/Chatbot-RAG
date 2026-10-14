# Sistema de Atencion Ciudadana y Consultas - Municipalidad de La Cisterna

Servicio web y API de orientacion ciudadana para la Municipalidad de La Cisterna.

El sistema procesa documentacion municipal oficial (tramites, ordenanzas, horarios de atencion y preguntas frecuentes) mediante indexacion vectorial, permitiendo responder consultas de vecinos de forma contextualizada y derivar solicitudes complejas a funcionarios municipales en tiempo real.

## Caracteristicas funcionales

- **Procesamiento y almacenamiento local:** El motor de indexacion vectorial (ChromaDB), la base de datos de historial (SQLite) y el motor de inferencia (Ollama) operan de forma local en el servidor, sin dependencias obligatorias de servicios externos.
- **Canal de atencion en vivo (WebSocket):** Cuando una consulta requiere atencion personalizada o no cuenta con informacion en los registros, el sistema permite transferir la sesion en tiempo real a funcionarios en el panel de atencion.
- **Proteccion de datos sensibles:** Filtros preventivos ante consultas sobre remuneraciones o datos protegidos, derivando directamente a los canales formales del Portal de Transparencia municipal.
- **Control de sesiones:** Moderacion automatica ante lenguaje inadecuado y limpieza programada de historiales conversacionales cada 24 horas en cumplimiento con la normativa de proteccion de datos (Ley 19.628).
- **Sincronizacion documental:** Modulo de actualizacion periodica para incorporar nuevos documentos tecnicos y decretos desde carpetas compartidas de Google Drive.

## Requisitos del sistema

- Python 3.11+
- Base de datos vectorial: ChromaDB (embebida)
- Base de datos de sesiones: SQLite
- Motor LLM: Ollama local (`qwen2.5:7b`) o proveedor compatible mediante variable de entorno

## Instalacion y ejecucion

### 1. Clonar el repositorio
```bash
git clone https://github.com/Municipalidad-Lacisterna/Chatbot-RAG.git
cd Chatbot-RAG
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuracion de entorno
Copiar la plantilla de configuracion y ajustar parametros de conexion:
```bash
cp .env.example .env
```

Variables principales:
- `LLM_PROVIDER`: Proveedor de inferencia (`ollama` o `google`).
- `OLLAMA_HOST` / `OLLAMA_MODEL`: Host y modelo local (por defecto `http://127.0.0.1:11434` y `qwen2.5:7b`).
- `DRIVE_URL`: Identificador de la carpeta publica de Google Drive para sincronizacion de documentos.
- `AGENTE_PANEL_CLAVE`: Clave de acceso al panel de agentes de atencion.

### 4. Indexar documentacion inicial
```bash
python -m app.ingestion
```

### 5. Iniciar servicio
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --ws wsproto
```

Para ejecucion en segundo plano en servidor:
```bash
setsid nohup venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --ws wsproto > logs/uvicorn.log 2>&1 < /dev/null & disown
```

Endpoints disponibles:
- **Chat ciudadano:** `http://127.0.0.1:8000/chat`
- **Panel de funcionarios:** `http://127.0.0.1:8000/agente`
- **Panel de administracion:** `http://127.0.0.1:8000/admin`
- **Documentacion OpenAPI:** `http://127.0.0.1:8000/docs`

## Estructura del repositorio

```
.
├── app/               # Modulos del backend (API, logica de recuperacion, WebSockets, memoria)
│   ├── main.py        # Endpoints FastAPI y gestion de rutas
│   ├── rag_engine.py  # Pipeline de consulta, recuperacion y respuesta
│   ├── ingestion.py   # Procesamiento de documentos (PDF, Markdown, CSV)
│   ├── ws_routes.py   # Conexiones WebSocket para vecinos y funcionarios
│   └── settings.py    # Carga de configuracion desde variables de entorno
├── data/              # Directorio de documentos base para indexacion
├── static/            # Archivos estaticos para interfaz de usuario y paneles
├── scripts/           # Utilidades de sincronizacion y pruebas automatizadas
└── docker/            # Configuraciones para empaquetado y despliegue contenerizado
```
