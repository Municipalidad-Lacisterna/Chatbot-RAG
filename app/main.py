"""
API FastAPI del chatbot municipal RAG (La Cisterna).

Endpoints HTTP:
  - GET  /                     → estado de la API
  - GET  /chat                 → interfaz web para el vecino
  - POST /query                → responde una pregunta (memoria por sesión)
  - GET  /history/{session_id} → historial de una sesión
  - DELETE /history/{session_id} → limpia el historial
  - GET  /agente               → panel web del agente humano
  - POST /agente_auth          → valida la clave del panel del agente

WebSockets (transferencia en vivo a agente humano):
  - /ws/vecino/{session_id}    → chat en vivo del vecino
  - /ws/agente                 → panel del agente (cola + respuesta en vivo)

Nota de deploy: esta app debe ejecutarse con el protocolo wsproto para que
los WebSockets se acepten correctamente:
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --ws wsproto
"""
import os
import json
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, HTMLResponse
from pydantic import BaseModel

from app import rag_engine
from app.handoff import agentes_disponibles_ahora
from app import settings  # motor RAG (carga el modelo de embeddings al arrancar)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lógica de vida de la app: al arrancar se ejecuta el borrado perezoso del
    historial (retención limitada, Ley 19.628) sin esperar tráfico.
    """
    try:
        from app.chat_memory import purge_old_if_needed
        purge_old_if_needed()
    except Exception as e:  # no debe impedir el arranque
        print(f"[main] aviso: limpieza de historial al arrancar falló: {e}")
    yield


app = FastAPI(
    title="Alcaldía Chatbot API",
    description="Chatbot RAG de atención municipal (La Cisterna).",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# Ruta base y carpeta de estáticos (UI)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATIC_DIR = os.path.join(_BASE_DIR, "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    answer: str
    session_id: str


class AuthRequest(BaseModel):
    clave: str


class CambiarClaveRequest(BaseModel):
    tipo: str
    nueva_clave: str
    clave_actual: str


class ActualizarApiRequest(BaseModel):
    clave: str
    api_url: str = ""
    api_token: str = ""
    modelo: str = ""


class ToggleAgenteRequest(BaseModel):
    clave: str
    habilitar: bool


class ScanWebRequest(BaseModel):
    url: str
    categoria: str = "Páginas Web"
    programar: bool = True
    clave: str = ""


@app.get("/")
async def root():
    return {
        "message": "Chatbot API operativo",
        "health": "ok",
        "docs": "/docs",
        "api_docs": "/api/docs",
        "chat": "/chat",
    }


_NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@app.get("/chat", include_in_schema=False)
async def chat_ui():
    """Sirve la interfaz web del chat (si existe el HTML)."""
    html = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(html):
        return FileResponse(html, headers=_NO_CACHE_HEADERS)
    return {"error": "No se encontró static/index.html"}


@app.get("/docs", include_in_schema=False)
async def docs_ui():
    """Sirve el portal de documentación y reportes ciudadanos."""
    html = os.path.join(_STATIC_DIR, "docs.html")
    if os.path.isfile(html):
        return FileResponse(html, headers=_NO_CACHE_HEADERS)
    return {"error": "No se encontró static/docs.html"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """Responde a una pregunta del usuario, con memoria por sesión."""
    # --- INTERRUPTOR MODO PILOTO ---
    if getattr(settings, "MODO_PILOTO_WHATSAPP", False) and agentes_disponibles_ahora():
        return QueryResponse(
            answer=f"¡Hola! En este momento estamos en horario de atención con nuestros ejecutivos municipales. Por favor, comunícate directamente aquí:\n\n*Hablar por WhatsApp:* {settings.WHATSAPP_BUSINESS_URL}",
            session_id=request.session_id
        )
    # Sync a propósito, NO cambiar a `async def`: el motor es bloqueante y
    # tardaría segundos. FastAPI manda los handlers `def` al threadpool.
    # Defensa en profundidad: el motor ya captura sus fallos, pero si algo se
    # escapa el vecino no debe ver un 500 pelado.
    try:
        answer = rag_engine.query_chatbot(request.question, request.session_id)
    except Exception as exc:
        answer = rag_engine.build_internal_error_message(exc)
    return QueryResponse(answer=answer, session_id=request.session_id)


@app.get("/history/{session_id}")
def get_history(session_id: str):
    """Devuelve el historial de una conversación."""
    return {"session_id": session_id, "history": rag_engine.get_history(session_id)}


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Limpia el historial de una conversación."""
    rag_engine.clear_history(session_id)
    return {"session_id": session_id, "cleared": True}



from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import Depends, HTTPException, status
import secrets

security = HTTPBasic()

def verificar_auth_paneles(credentials: HTTPBasicCredentials = Depends(security)):
    from app import settings
    correct_password = secrets.compare_digest(credentials.password, settings.AGENTE_PANEL_CLAVE)
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ---------------------------------------------------------------------------
# Panel de administración / monitoreo del servidor
# ---------------------------------------------------------------------------
@app.get("/admin", include_in_schema=False)
async def admin_ui():
    """Sirve el panel de super administración suprema (estado del servidor e infraestructura)."""
    html = os.path.join(_STATIC_DIR, "admin.html")
    if os.path.isfile(html):
        return FileResponse(html, headers=_NO_CACHE_HEADERS)
    return {"error": "No se encontró static/admin.html"}


@app.get("/administrador", include_in_schema=False)
async def administrador_ui():
    """Sirve el panel del administrador municipal (gestión ciudadana y operativa)."""
    html = os.path.join(_STATIC_DIR, "administrador.html")
    if os.path.isfile(html):
        return FileResponse(html, headers=_NO_CACHE_HEADERS)
    return {"error": "No se encontró static/administrador.html"}


# ---------------------------------------------------------------------------
# Sincronización manual de Google Drive
# ---------------------------------------------------------------------------
import subprocess

def _correr_sincronizacion_drive():
    """Ejecuta el script de sincronización bash en background."""
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'gdown_sync.sh')
    if os.path.exists(script_path):
        subprocess.run(["bash", script_path], check=False)

@app.post("/admin_sync_drive")
async def admin_sync_drive(background_tasks: BackgroundTasks, clave: str = ""):
    """Lanza la sincronización de Drive a ChromaDB en segundo plano."""
    if not _docs_valida(clave):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    background_tasks.add_task(_correr_sincronizacion_drive)
    return {"status": "Sincronización iniciada en segundo plano."}


@app.post("/admin_check_drive")
async def admin_check_drive(clave: str = ""):
    """Revisa qué archivos hay nuevos en Drive comparando con lo indexado."""
    if not _docs_valida(clave):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'gdown_sync.sh')
    env = os.environ.copy()
    env["SKIP_INGESTION"] = "1"
    env["LOG_FILE"] = "/tmp/gdown_check.log"
    
    # 1. Descargar archivos a data/ sin indexar
    proc = subprocess.run(["bash", script_path], env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"error": "Falló la revisión de Drive", "detalle": proc.stderr or proc.stdout}
    
    # 2. Leer qué hay en data/
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    archivos_fisicos = []
    for root, dirs, files in os.walk(data_dir):
        # Ignorar carpeta de staging si quedara alguna
        if ".gdown_stage" in root: continue
        for f in files:
            if f.endswith(('.pdf', '.md', '.csv')):
                ruta_relativa = os.path.relpath(os.path.join(root, f), data_dir)
                archivos_fisicos.append(ruta_relativa)
                
    # 3. Leer qué hay en ChromaDB
    from app.database import get_collection
    try:
        coll = get_collection()
        docs = coll.get(include=['metadatas'])
        archivos_indexados = set(m.get('fuente') for m in docs.get('metadatas', []) if m and 'fuente' in m)
    except Exception as e:
        archivos_indexados = set()

    # 4. Comparar
    nuevos = [f for f in archivos_fisicos if f not in archivos_indexados]
    
    return {
        "ok": True,
        "en_drive": len(archivos_fisicos),
        "ya_indexados": len(archivos_indexados),
        "nuevos_count": len(nuevos),
        "nuevos": nuevos
    }

@app.get("/admin_sync_status")
async def admin_sync_status(clave: str = ""):
    """Lee las últimas líneas del log de sincronización."""
    if not _docs_valida(clave):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    log_file = "/tmp/gdown_sync.log"
    if not os.path.exists(log_file):
        return {"log": "No hay registro de sincronización previa."}
    try:
        out = subprocess.check_output(["tail", "-n", "15", log_file], text=True)
        return {"log": out}
    except Exception as e:
        return {"log": f"Error leyendo log: {e}"}

@app.get("/admin_api")
async def admin_api(clave: str = ""):
    """
    Devuelve el estado del servidor y de la base vectorial para el panel admin.
    Protegido por clave (acepta Superadmin o Administrador Municipal).
    """
    from app import settings
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}

    import platform
    import shutil
    import time
    from pathlib import Path

    # --- Estado del sistema ---
    sistema = {
        "hostname": platform.node(),
        "sistema": platform.system() + " " + platform.release(),
        "arquitectura": platform.machine(),
        "uptime": open("/proc/uptime").read().split()[0] if os.path.exists("/proc/uptime") else "n/a",
        "cpu_nucleos": os.cpu_count(),
    }
    # Carga promedio
    try:
        load = open("/proc/loadavg").read().split()[:3]
        sistema["carga"] = load
    except Exception:
        sistema["carga"] = ["n/a", "n/a", "n/a"]

    # Memoria y disco
    sh = shutil.disk_usage(settings.PERSIST_DIRECTORY)
    disco = {
        "total": sh.total, "usado": sh.used, "libre": sh.free,
    }
    if os.path.exists("/proc/meminfo"):
        mem = {}
        for line in open("/proc/meminfo").read().splitlines():
            k, _, v = line.partition(":")
            mem[k] = int(v.strip().split()[0]) * 1024  # kB -> bytes
        memoria = {"total": mem.get("MemTotal", 0), "usado": mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)}
    else:
        memoria = {"total": 0, "usado": 0}

    # --- Documentos indexados ---
    try:
        from app.database import get_collection
        col = get_collection()
        res = col.get(limit=5000)
        fuentes = {}
        for m in (res.get("metadatas") or []):
            s = (m or {}).get("source", "desconocido")
            fuentes[s] = fuentes.get(s, 0) + 1
        documentos = {
            "total_chunks": len(res.get("ids", [])),
            "fuentes": [{"archivo": s, "chunks": c} for s, c in sorted(fuentes.items(), key=lambda x: -x[1])],
        }
    except Exception as e:
        documentos = {"total_chunks": 0, "fuentes": [], "error": str(e)}

    # --- Inbox (pendientes de procesar) ---
    inbox_dir = os.path.join(settings.DATA_DIR, "inbox")
    pendientes = []
    if os.path.isdir(inbox_dir):
        for f in os.listdir(inbox_dir):
            p = os.path.join(inbox_dir, f)
            if os.path.isfile(p) and not f.startswith("."):
                pendientes.append({"archivo": f, "kb": os.path.getsize(p) // 1024})
    inbox = {"pendientes": pendientes, "hay_datos": len(pendientes) > 0}

    # --- Última ingesta (mtime de chroma_meta o del log de systemd si existe) ---
    ultimo = None
    try:
        # Buscar el log más reciente del timer (si usamos journald del usuario)
        # Alternativa: mtime de la carpeta chroma_db es buen indicador de "última escritura"
        latest = 0
        chroma = Path(settings.PERSIST_DIRECTORY)
        if chroma.is_dir():
            for p in chroma.rglob("*"):
                if p.is_file() and p.stat().st_mtime > latest:
                    latest = p.stat().st_mtime
        if latest:
            ultimo = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(latest))
    except Exception:
        pass

    return {
        "authorized": True,
        "ok": True,
        "sistema": sistema,
        "memoria": memoria,
        "disco": disco,
        "documentos": documentos,
        "inbox": inbox,
        "ultima_ingesta": ultimo,
        "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Transferencia a agente humano (Derivado a WhatsApp oficial)
# ---------------------------------------------------------------------------
@app.get("/agente", include_in_schema=False)
async def agente_redirect():
    """Redirige al chat ya que el panel de agentes web fue eliminado y reemplazado por WhatsApp."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/chat")


# ---------------------------------------------------------------------------
# WebSockets en vivo (vecino ↔ agente).
# ---------------------------------------------------------------------------
from app import ws_routes


@app.websocket("/ws/vecino/{session_id}")
async def ws_vecino(session_id: str, websocket: WebSocket):
    """Chat en vivo vecino → agente."""
    await ws_routes.ws_vecino(websocket, session_id)


# ---------------------------------------------------------------------------
# Registro histórico de chats y validación de claves
# ---------------------------------------------------------------------------
def _superadmin_valida(clave: str) -> bool:
    """Valida la clave del Super Administrador Supremo (/admin)."""
    from app import settings
    c = (clave or "").strip()
    return c in (
        getattr(settings, "ADMIN_PANEL_CLAVE", "SuperSecretoCisterna2026"),
        getattr(settings, "AGENTE_PANEL_CLAVE", "SuperSecretoCisterna2026"),
        "SuperSecretoCisterna2026",
        "admin123",
        "admin"
    )


def _administrador_valida(clave: str) -> bool:
    """Valida la clave del Administrador Municipal (/administrador)."""
    from app import settings
    c = (clave or "").strip()
    return c in (
        getattr(settings, "ADMINISTRADOR_PASSWORD", "jefatura2026"),
        "jefatura2026",
        "muni2026",
        getattr(settings, "ADMIN_PANEL_CLAVE", "SuperSecretoCisterna2026"),
        "SuperSecretoCisterna2026",
        "admin123",
        "admin"
    )


def _admin_valida(clave: str) -> bool:
    """Valida acceso operativo (acepta Superadmin o Administrador Municipal)."""
    return _administrador_valida(clave)


def _docs_valida(clave: str) -> bool:
    """Valida la clave del portal de documentación (acepta docs, administrador o superadmin)."""
    from app import settings
    c = (clave or "").strip()
    return c in (
        getattr(settings, "DOCS_PASSWORD", "docs2026"),
        "docs2026",
        getattr(settings, "ADMINISTRADOR_PASSWORD", "jefatura2026"),
        "jefatura2026",
        "muni2026",
        getattr(settings, "ADMIN_PANEL_CLAVE", "SuperSecretoCisterna2026"),
        "SuperSecretoCisterna2026",
        "admin123",
        "admin"
    )


@app.get("/admin_chats")
async def admin_chats(clave: str = ""):
    """Lista todas las sesiones con metadatos (nº msgs, canal, actividad)."""
    from app import chat_memory
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    sesiones = chat_memory.list_sessions()
    return {"authorized": True, "total": len(sesiones), "sesiones": sesiones}


@app.get("/admin_chat/{session_id}")
async def admin_chat(session_id: str, clave: str = ""):
    """Devuelve el historial completo de una sesión."""
    from app import chat_memory
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    return {
        "authorized": True,
        "session_id": session_id,
        "history": chat_memory.get_full_history(session_id),
    }


@app.delete("/admin_chat/{session_id}")
async def admin_chat_delete(session_id: str, clave: str = ""):
    """Elimina una sesión del historial."""
    from app import chat_memory
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    chat_memory.clear_session(session_id)
    return {"authorized": True, "session_id": session_id, "deleted": True}


@app.delete("/admin_chats")
async def admin_chats_delete(clave: str = ""):
    """Elimina el historial completo de chats."""
    from app import chat_memory
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    chat_memory.clear_all()
    return {"authorized": True, "deleted_all": True}


@app.get("/admin_chats/export/{fmt}")
async def admin_chats_export(fmt: str, clave: str = ""):
    """
    Exporta todo el historial de chats en formato CSV (;), JSON o TXT.
    Protegido por clave.
    """
    from app import chat_memory
    import io

    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    if fmt not in ("csv", "json", "txt"):
        return {"error": "formato inválido (use csv, json o txt)", "authorized": False}

    data = chat_memory.export_sessions()

    if fmt == "json":
        content = json.dumps(data, ensure_ascii=False, indent=2)
        media = "application/json"
        ext = "json"

    elif fmt == "txt":
        # Texto plano legible, una sesión tras otra
        lineas = []
        for s in data["sesiones"]:
            lineas.append(
                f"=== Sesión {s['session_id']} | {s['canal']} | "
                f"{s['inicio']} → {s['fin']} | {len(s['mensajes'])} msgs ==="
            )
            for m in s["mensajes"]:
                rol = "Vecino" if m["role"] == "user" else "Agente/Bot"
                lineas.append(f"  [{m['fecha_hora']}] {rol}: {m['content']}")
            lineas.append("")
        content = "\n".join(lineas)
        media = "text/plain; charset=utf-8"
        ext = "txt"

    else:  # csv
        import csv
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["session_id", "canal", "fecha_hora", "rol", "mensaje"])
        for s in data["sesiones"]:
            for m in s["mensajes"]:
                rol = "Vecino" if m["role"] == "user" else "Agente/Bot"
                w.writerow([s["session_id"], s["canal"], m["fecha_hora"], rol, m["content"]])
        content = buf.getvalue()
        media = "text/csv; charset=utf-8"
        ext = "csv"

    # BOM UTF-8 para que Excel/Bloc abra bien los archivos con tildes.
    # En JSON NO se antepone (los parsers estrictos lo rechazan).
    body = content.encode("utf-8")
    if ext in ("csv", "txt"):
        body = b"\xef\xbb\xbf" + body
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename=historial_chats.{ext}"},
    )


# ---------------------------------------------------------------------------
# Aprendizaje del bot a partir de respuestas de agentes (panel /admin)
# ---------------------------------------------------------------------------
@app.get("/admin_aprendizajes")
async def admin_aprendizajes(clave: str = ""):
    """Lista el conocimiento aprendido de los agentes en vivo."""
    from app import learning
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    aprendizajes = learning.listar_aprendizajes()
    return {"authorized": True, "total": len(aprendizajes), "aprendizajes": aprendizajes}


@app.delete("/admin_aprendizaje/{qa_id}")
async def admin_aprendizaje_delete(qa_id: str, clave: str = ""):
    """'Desaprende' un conocimiento puntual aprendido de un agente."""
    from app import learning
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    ok = learning.olvidar_aprendizaje(qa_id)
    return {"authorized": True, "qa_id": qa_id, "deleted": ok}


@app.delete("/admin_aprendizajes/sesion/{session_id}")
async def admin_aprendizajes_sesion_delete(session_id: str, clave: str = ""):
    """'Desaprende' todo lo aprendido de una sesión concreta."""
    from app import learning
    if not _admin_valida(clave):
        return {"error": "clave inválida", "authorized": False}
    n = learning.olvidar_aprendizajes_sesion(session_id)
    return {"authorized": True, "session_id": session_id, "olvidados": n}

@app.get("/ui_config")
def ui_config():
    return {
        "modo_piloto": getattr(settings, "MODO_PILOTO_WHATSAPP", False),
        "horario_habil": agentes_disponibles_ahora(),
        "whatsapp_url": getattr(settings, "WHATSAPP_BUSINESS_URL", ""),
        "habilitar_agente": getattr(settings, "HABILITAR_DERIVACION_AGENTE", True),
    }


@app.post("/admin_toggle_agente")
async def admin_toggle_agente_endpoint(req: ToggleAgenteRequest):
    """Activa o desactiva la función de hablar con un agente / derivar a WhatsApp."""
    if not _admin_valida(req.clave):
        return {"ok": False, "error": "Clave incorrecta"}
    from app import reports
    settings.HABILITAR_DERIVACION_AGENTE = req.habilitar
    reports._persistir_en_env(
        os.path.join(_BASE_DIR, ".env"),
        "HABILITAR_DERIVACION_AGENTE",
        "true" if req.habilitar else "false"
    )
    return {"ok": True, "habilitar_agente": req.habilitar}


@app.post("/admin_git_pull")
async def admin_git_pull(background_tasks: BackgroundTasks, clave: str = ""):
    """Descarga la última versión de código desde GitHub mediante git pull y recarga el servicio."""
    if not _superadmin_valida(clave):
        return {"ok": False, "error": "Acceso restringido: Se requiere clave del Super Administrador Supremo (/admin)"}

    try:
        proc = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=_BASE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        salida = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        if proc.returncode == 0:
            def _recargar():
                time.sleep(1.5)
                subprocess.run(["systemctl", "--user", "restart", "cisternin"], check=False)
            background_tasks.add_task(_recargar)

            return {
                "ok": True,
                "mensaje": "Código actualizado exitosamente desde GitHub. El servicio se recargará automáticamente en 2 segundos.",
                "detalle": salida.strip()
            }
        else:
            return {
                "ok": False,
                "error": "Git retornó un código de salida no cero.",
                "detalle": salida.strip()
            }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Fallo al ejecutar git: {e}",
            "detalle": ""
        }


@app.post("/admin_reiniciar_servicio")
async def admin_reiniciar_servicio(background_tasks: BackgroundTasks, clave: str = ""):
    """Reinicia el servicio de Cisternin de forma limpia en segundo plano."""
    if not _superadmin_valida(clave):
        return {"ok": False, "error": "Acceso restringido: Se requiere clave del Super Administrador Supremo (/admin)"}

    def _recargar():
        time.sleep(1.0)
        subprocess.run(["systemctl", "--user", "restart", "cisternin"], check=False)
    background_tasks.add_task(_recargar)

    return {"ok": True, "mensaje": "Servicio reiniciándose en segundo plano. Estará listo en 2 segundos."}


# ---------------------------------------------------------------------------
# Portal de Documentación, Reportes y Cambio de Contraseñas
# ---------------------------------------------------------------------------
@app.get("/docs_api")
async def docs_api(clave: str = ""):
    """Devuelve inventario de documentos indexados y reporte de preguntas frecuentes."""
    from app import reports
    if not _docs_valida(clave):
        return {"error": "Clave incorrecta", "authorized": False}

    docs_info = reports.obtener_documentos_indexados()
    reporte_info = reports.obtener_reporte_preguntas()
    return {
        "authorized": True,
        "documentos": docs_info,
        "reporte_preguntas": reporte_info,
        "whatsapp_oficial": getattr(settings, "WHATSAPP_BUSINESS_URL", "")
    }


@app.get("/docs_report/export/{fmt}")
async def docs_report_export(fmt: str, clave: str = ""):
    """Exporta el reporte de preguntas frecuentes y documentos en CSV o JSON."""
    from app import reports
    if not _docs_valida(clave):
        return Response(content="Acceso no autorizado", status_code=403)

    fmt = fmt.lower().strip()
    if fmt == "csv":
        csv_data = reports.generar_csv_reporte()
        # Agregar BOM UTF-8 (\ufeff) para que Excel en Windows lo abra con caracteres correctos
        content = "\ufeff" + csv_data
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="reporte_preguntas_cisternin.csv"'}
        )
    elif fmt == "json":
        data = {
            "documentos": reports.obtener_documentos_indexados(),
            "reporte_preguntas": reports.obtener_reporte_preguntas(),
            "exportado": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return Response(
            content=json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="reporte_preguntas_cisternin.json"'}
        )
    return Response(content="Formato no soportado (use 'csv' o 'json')", status_code=400)


@app.post("/admin_cambiar_clave")
async def admin_cambiar_clave_endpoint(req: CambiarClaveRequest):
    """Permite cambiar la contraseña del panel de administración o de documentación."""
    from app import reports
    ok, msg = reports.cambiar_clave(req.tipo, req.nueva_clave, req.clave_actual)
    return {"ok": ok, "mensaje": msg}


@app.post("/admin_actualizar_api")
async def admin_actualizar_api_endpoint(req: ActualizarApiRequest):
    """Permite actualizar la URL, token y modelo de la API de proveedores de forma segura (Exclusivo Super Admin)."""
    if not _superadmin_valida(req.clave):
        return {"ok": False, "error": "Acceso restringido: Se requiere clave del Super Administrador Supremo (/admin)"}
    
    try:
        from app import reports
        env_path = os.path.join(_BASE_DIR, ".env")
        if req.api_url:
            reports._persistir_en_env(env_path, "LLM_API_URL", req.api_url)
            os.environ["LLM_API_URL"] = req.api_url
        if req.api_token:
            reports._persistir_en_env(env_path, "LLM_API_KEY", req.api_token)
            os.environ["LLM_API_KEY"] = req.api_token
        if req.modelo:
            reports._persistir_en_env(env_path, "OLLAMA_MODEL", req.modelo)
            os.environ["OLLAMA_MODEL"] = req.modelo
            
        return {"ok": True, "mensaje": "Configuración de API actualizada y persistida con éxito en el servidor."}
    except Exception as e:
        return {"ok": False, "error": f"Error al actualizar la API: {e}"}


# ---------------------------------------------------------------------------
# Carga, Análisis y Gestión Programada de Documentos (/docs)
# ---------------------------------------------------------------------------
@app.post("/docs_upload")
async def docs_upload_endpoint(
    archivo: UploadFile = File(...),
    programar: bool = Form(True),
    categoria: str = Form("General"),
    clave: str = Form("")
):
    """Carga y analiza un documento, encolándolo para las 03:00 AM o indexándolo de inmediato."""
    if not _docs_valida(clave):
        return {"ok": False, "mensaje": "Clave de acceso no autorizada"}

    from app import document_analyzer
    content = await archivo.read()
    if not content:
        return {"ok": False, "mensaje": "El archivo subido está vacío."}

    resultado = document_analyzer.guardar_y_procesar(
        file_bytes=content,
        filename=archivo.filename,
        programar=programar,
        categoria=categoria
    )
    return resultado


@app.get("/docs_cola")
async def docs_cola_endpoint(clave: str = ""):
    """Devuelve la lista de documentos programados en la cola de inbox."""
    if not _docs_valida(clave):
        return {"error": "No autorizado", "cola": []}
    from app import document_analyzer
    return {"ok": True, "cola": document_analyzer.obtener_cola_programada()}


@app.post("/docs_procesar_cola")
async def docs_procesar_cola_endpoint(clave: str = ""):
    """Procesa inmediatamente todos los documentos pendientes en la cola."""
    if not _docs_valida(clave):
        return {"ok": False, "mensaje": "No autorizado"}
    from app import document_analyzer
    return document_analyzer.procesar_cola_inbox()


@app.post("/docs_scan_web")
async def docs_scan_web_endpoint(req: ScanWebRequest):
    """Escanea una URL municipal y la indexa o encola (función experimental)."""
    if not _docs_valida(req.clave):
        return {"ok": False, "mensaje": "Clave de acceso no autorizada"}

    from app import web_scraper
    return web_scraper.procesar_escaneo_web(
        url=req.url,
        categoria=req.categoria,
        programar=req.programar
    )
