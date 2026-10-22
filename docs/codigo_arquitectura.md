# Código y Arquitectura del Chatbot — Fácil de entender + Escalabilidad

> Documentación técnica del chatbot RAG de la Alcaldía de La Cisterna.
> Explica **qué hace cada pieza del código** y **cómo escalar** cuando se
> pase del prototipo a producción. Esta nota complementa
> [[decision_tono_y_presupuesto]].

---

## 1. Vista general: ¿cómo funciona el bot en una imagen?

```text
Vecino ──▶ [ UI web /chat ]          (frontend, static/index.html)
           │          │
    (POST /query)  (WS /ws/vecino)
           ▼          ▼
      [ FastAPI ] ◀─▶ [ Handoff / WebSockets ] ◀─▶ (WS /ws/agente) ◀─ Agente Humano
           │               (app/ws_routes.py)
         llama
           ▼
   [ RAG Engine ]               (app/rag_engine.py — el cerebro)
     │        │
     │        └──▶ recupera documentos (app/database.py → ChromaDB)
     │
     ▼  +  memoria por sesión (app/chat_memory.py → SQLite)
     │
     ▼
[ LLM Multiproveedor ] (app/settings.py -> LLM_PROVIDER)
     │       ├── 'google' (API Gemini, ideal para desarrollo ágil)
     │       └── 'ollama' (Qwen2.5-VL IA local, para soberanía en producción)
     ▼
respuesta en 1 bloque al vecino
```

**Las 4 "cajas" del sistema:**
1. **Frontend** — la cara que ve el vecino y el panel del agente.
2. **API (FastAPI) y WebSockets** — el mensajero que recibe preguntas del bot o maneja el chat en vivo.
3. **Motor RAG** — el cerebro que busca en los documentos y genera la respuesta.
4. **Handoff** — el puente que conecta al vecino con un agente humano cuando el bot no sabe la respuesta.

---

## 2. Los archivos del código, explicados uno a uno

### `app/settings.py` — "La billetera de configuración"
- Centraliza **todos los parámetros** en un solo lugar (no dispersos).
- Lee del archivo `.env` con valores por defecto sensatos.
- Lo más importante:
  - `LLM_PROVIDER` → Permite alternar entre `google` (Gemini, para programar rápido en laptops) y `ollama` (para el servidor de la municipalidad, soberanía total).
  - `OLLAMA_HOST` / `OLLAMA_MODEL` → URL y modelo del LLM local (ej. Qwen2.5-VL).
  - `TOP_K = 2` → cuántos fragmentos de documentos trae (bajo = ahorra tokens).
  - `CHUNK_SIZE = 2400` → tamaño de los trozos en que se parte un PDF.
  - Contactos de derivación (teléfono/email) para cuando no hay respuesta.
- **Por qué importa**: si quieres cambiar de proveedor de IA, ajustar cuánto contexto recuperar o los datos de contacto, se hace aquí sin tocar otra cosa.

### `app/main.py` — "La puerta de entrada (API)"
- Es un servidor **FastAPI**: recibe peticiones HTTP y levanta conexiones WebSocket.
- Endpoints que expone:
  | Ruta | Método | Qué hace |
  |------|--------|----------|
  | `/` | GET | Estado/health de la API |
  | `/chat` | GET | Sirve la página web del chat del vecino |
  | `/admin` y `/agente` | GET | Sirven los paneles de administración y atención humana |
  | `/query` | POST | Recibe una pregunta, devuelve respuesta del bot |
  | `/history/{sesion}` | GET/DELETE | Devuelve o limpia el historial de una conversación |
  | `/ws/vecino/{sesion}` | WS | WebSocket para el vecino (chat en tiempo real) |
  | `/ws/agente` | WS | WebSocket para el agente (atención de cola) |
  | Endpoints `/admin_*` | Varios | Gestión de historial y aprendizajes (requieren `?clave=`) |
- **Por qué importa**: es el "único punto de entrada". Si mañana quieres que WhatsApp hable con el bot, se conecta aquí.

### `app/ws_routes.py` — "El puente telefónico (Handoff y WebSockets)"
- Maneja la transferencia en tiempo real entre un vecino y un funcionario de la municipalidad.
- Mantiene el estado de la cola de espera y quién está atendiendo a quién (`_vivos`, `_mensajes`).
- Asegura que los mensajes fluyan bidireccionalmente: si el vecino escribe, el agente lo lee al instante, y viceversa.
- Al cerrar el chat, avisa al módulo de aprendizaje para que el bot estudie la conversación.
- **Por qué importa**: Evita que el vecino quede a la deriva si el bot no sabe la respuesta, brindando atención cálida y humana.

### `app/rag_engine.py` — "El cerebro (RAG)"
- Orquesta el flujo de cada pregunta automática:
  1. **Recupera** contexto de los documentos (ChromaDB) y memoria corta.
  2. **Arma** un prompt con la personalidad de "Cisternín" (amable y cercano).
  3. **Llama al LLM** (Google u Ollama según configuración).
  4. **Verifica** si encontró la info (`encontrado: true/false`).
  5. Si **no** la encontró → **no inventa** y **SIEMPRE ofrece transferir** a un agente humano con el token `[[TRANSFERIR]]`.
- Tiene "cortocircuitos" rápidos (por ejemplo, sabe presentarse si le preguntan quién es, sin ir a buscar documentos).
- **Por qué importa**: aquí se decide la CALIDAD y el COSTO de cada respuesta automática.

### `app/database.py` — "La enciclopedia vectorial"
- Conexión a **ChromaDB** (base de datos de vectores).
- Guarda los fragmentos de los documentos con sus **embeddings** (representación numérica para búsqueda semántica en español).
- `retrieve()` busca los `k` fragmentos más relevantes a una pregunta.

### `app/session_state.py` — "El vigilante de inactividad (timeout)"
- A los **5 min** sin mensajes de un vecino, el bot responde **"¿Hay alguien ahí?"**.
- Si el vecino responde en ≤ **3 min** → el chat sigue. Si no → se **cierra con despedida**.

### `app/learning.py` — "El alumno (aprende de los agentes)"
- Cuando un agente humano termina de atender a un vecino, este módulo extrae las preguntas y respuestas dadas y las **indexa en ChromaDB** (`origen='agente_vivo'`).
- La próxima vez que alguien pregunte lo mismo, el bot responde solo basándose en lo que le enseñó el humano.

### `app/chat_memory.py` — "La memoria de la conversación"
- Base **SQLite** (local). Guarda cada interacción (`bot` o `agente`) por sesión.
- **Retención limitada (Ley 19.628, Chile)**: borra mensajes automáticamente pasadas **24 horas** mediante limpiezas perezosas y un script de systemd.

### `app/ingestion.py` — "El bibliotecario (ingesta de documentos)"
- Lee recursivamente archivos PDF, MD y CSV desde la carpeta `data/`.
- `_split_text()` **respeta los encabezados Markdown (`###`)**, de modo que un bloque conceptual (un trámite) nunca se corta a la mitad.
- Los archivos CSV de transparencia se convierten fila a fila a texto, permitiendo que cada trámite sea un bloque independiente y perfecto para el motor RAG.
- La ingesta es idempotente: limpia bloques viejos y asegura que la base siempre esté fresca antes de borrar el archivo físico de `data/`.

### `static/index.html` — "La cara al vecino (frontend)"
- Página web con look tipo WhatsApp (verde #25D366). Maneja el POST al bot y levanta el WebSocket si el usuario acepta transferirse a un humano.

### Scripts de apoyo (automatización):
- `scripts/gdown_sync.sh` — ¡La estrella de la sincronización! Descarga automáticamente la carpeta PÚBLICA del Google Drive de la municipalidad usando `gdown` (sin requerir tarjeta de crédito ni Google Cloud). Conserva las subcarpetas e indexa los archivos.
- `scripts/purge_historial.py` — Borra el historial antiguo por retención legal 24h.
- `scripts/analizar_chats.py` — Para minar FAQs desde exportaciones de WhatsApp.

---

## 3. Flujo de datos típico (de principio a fin)

Ejemplo: *"¿Cuáles son los requisitos para la beca?"*

1. El vecino escribe en **`/chat`**.
2. El JS hace `POST /query` con `{question, session_id}`.
3. El motor RAG trae los fragmentos de ChromaDB y el historial de SQLite.
4. Se arma el prompt y se consulta al LLM (Gemini u Ollama).
5. Se devuelve la respuesta en 1 bloque al vecino.

Si en cambio se pregunta algo **no documentado**:
- El motor no encuentra info → `encontrado: false`.
- Responde amablemente y manda el token `[[TRANSFERIR]]`.
- El frontend dibuja los botones "Sí, hablar con agente".
- Si el vecino acepta, se levanta el **WebSocket** y la conversación pasa a ser en vivo, manejada por `app/ws_routes.py`.
- Al finalizar, `app/learning.py` memoriza la respuesta.

---

## 4. Opciones de escalabilidad

El prototipo actual es **monolítico y local**. Estas son las vías para crecer:

### Nivel 1 — Escalar sin cambiar arquitectura (lo más simple)
- **Más documentos**: El script `gdown_sync.sh` ya lo hace solo al leer el Drive.
- **Dominio propio y HTTPS**: Poner el servidor local detrás de un túnel Cloudflare o un proxy inverso Caddy/Nginx.

### Nivel 2 — Mejorar el retrieval (más precisión)
- **Hybrid search**: Combinar búsqueda semántica + palabras clave (BM25).
- **Re-ranking**: Pasar los top-K por un modelo reranker para elegir mejor.

### Nivel 3 — Conectar canales reales (WhatsApp)
- **WhatsApp Business API** (Meta): Conectar la API oficial de WhatsApp a `/query`.
  *(Ver detalles de costos de los mensajes de servicio de Meta en la documentación de negocio).*
- Requiere autenticación y el manejo de los webhooks de Meta.

### Nivel 4 — Escalar la infraestructura
- **Contenerizar** (Docker) cada pieza: API, ChromaDB, ingesta.
- **Bases de datos gestionadas**: Qdrant/Pinecone en vez de ChromaDB; PostgreSQL/Redis en vez de SQLite.

### Nivel 5 — Producto completo (visión a futuro)
- **Panel de administración avanzado** con métricas y gráficas.
- **Multi-canal unificado** (web + WhatsApp + redes) con un solo motor.

---

## 5. Decisión de arquitectura: qué se mantiene y qué cambia

| Componente | Mantiene (no escala fácil) | Cambia (por qué) |
|-----------|---------------------------|------------------|
| Motor RAG (rag_engine.py) |  Lógica estable | — |
| Handoff WebSockets |  Tiempo real robusto | Escalable con Redis pub/sub |
| FastAPI (main.py) |  API estable | Añade auth real/rate-limit |
| ChromaDB local | Aceptable en prototipo | → gestionada (Qdrant/Pinecone) |
| SQLite (memoria) | Aceptable en prototipo | → Postgres/Redis |
| Uvicorn single-process | Aceptable en dev | → contenedores + autoescalado |

> **Regla general de escalabilidad:** el **motor RAG y la API** apenas cambian. Lo que escala es **dónde se guarda** y **cómo se accede**. Diseñamos así a propósito: el código del prototipo **no se tira**, se le van añadiendo capas.

---

## 6. Archivos que componen este proyecto (referencia rápida)

| Ruta | Rol |
|------|-----|
| `app/main.py` | API FastAPI (puerta de entrada y montura WS) |
| `app/ws_routes.py` | Puente WebSockets para chat en vivo y encolado |
| `app/rag_engine.py` | Motor RAG (cerebro IA) |
| `app/database.py` | ChromaDB (enciclopedia vectorial) |
| `app/chat_memory.py` | SQLite (memoria de conversación con auto-purga) |
| `app/session_state.py` | Vigilante de inactividad (timeout 5'/3') |
| `app/learning.py` | Aprende de las respuestas de los humanos |
| `app/settings.py` | Configuración central (`LLM_PROVIDER`, URLs, etc) |
| `app/ingestion.py` | Biblioteca de documentos (Convierte PDF/CSV a vectores) |
| `static/` | Frontend web (vecino, agente, administrador) |
| `scripts/gdown_sync.sh` | Sincroniza Drive público → data/ e indexa |
| `scripts/purge_historial.py` | Borra historial por retención legal |
| `scripts/analizar_chats.py` | Análisis de FAQs |
| `tests/bateria_pruebas.py` | Batería de pruebas del bot E2E |

## Ver también
- [[decision_tono_y_presupuesto]] — tono híbrido y costos.
- [[requerimientos]] — resumen para la junta y presupuesto.
- [[inventario_servidor_municipal]] — checklist del servidor a pedir.
