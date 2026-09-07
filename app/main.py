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

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app import rag_engine  # motor RAG (carga el modelo de embeddings al arrancar)


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
    description="Chatbot RAG de atención municipal (La Cisterna). Prototipo.",
    version="0.1.0",
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


@app.get("/")
async def root():
    return {
        "message": "Chatbot API operativo",
        "health": "ok",
        "docs": "/docs",
        "chat": "/chat",
    }


@app.get("/chat", include_in_schema=False)
async def chat_ui():
    """Sirve la interfaz web del chat (si existe el HTML)."""
    html = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(html):
        return FileResponse(html)
    return {"error": "No se encontró static/index.html"}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Responde a una pregunta del usuario, con memoria por sesión."""
    answer = rag_engine.query_chatbot(request.question, request.session_id)
    return QueryResponse(answer=answer, session_id=request.session_id)


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Devuelve el historial de una conversación."""
    return {"session_id": session_id, "history": rag_engine.get_history(session_id)}


@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
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
async def admin_ui(username: str = Depends(verificar_auth_paneles)):
    """Sirve el panel de administración (estado del servidor y de la base)."""
    html = os.path.join(_STATIC_DIR, "admin.html")
    if os.path.isfile(html):
        return FileResponse(html)
    return {"error": "No se encontró static/admin.html"}


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
    if not _admin_valida(clave):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    background_tasks.add_task(_correr_sincronizacion_drive)
    return {"status": "Sincronización iniciada en segundo plano."}

@app.get("/admin_sync_status")
async def admin_sync_status(clave: str = ""):
    """Lee las últimas líneas del log de sincronización."""
    if not _admin_valida(clave):
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

    Protegido por clave (se pasa como ?clave=...). Requiere la clave del
    panel de administración (AGENTE_PANEL_CLAVE en settings/.env) o reutiliza
    la del agente para que no haya que recordar varias claves.
    """
    from app import settings
    if clave != settings.AGENTE_PANEL_CLAVE:
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
# Transferencia a agente humano (centro de atención / demo)
# ---------------------------------------------------------------------------
@app.get("/agente", include_in_schema=False)
async def agente_ui(username: str = Depends(verificar_auth_paneles)):
    """Sirve el panel del agente humano (dashboard)."""
    html = os.path.join(_STATIC_DIR, "agente.html")
    if os.path.isfile(html):
        return FileResponse(html)
    return {"error": "No se encontró static/agente.html"}


@app.post("/agente_auth")
async def agente_auth(request: AuthRequest):
    """Valida la clave del panel del agente (prototipo: clave compartida)."""
    from app import settings
    return {"ok": request.clave == settings.AGENTE_PANEL_CLAVE}


# ---------------------------------------------------------------------------
# WebSockets en vivo (vecino ↔ agente). Reutilizan la lógica de ws_routes.
# ---------------------------------------------------------------------------
from app import ws_routes


@app.websocket("/ws/vecino/{session_id}")
async def ws_vecino(session_id: str, websocket: WebSocket):
    """Chat en vivo vecino → agente."""
    await ws_routes.ws_vecino(websocket, session_id)


@app.websocket("/ws/agente")
async def ws_agente(websocket: WebSocket):
    """Panel del agente: cola de espera + respuesta en vivo."""
    await ws_routes.ws_agente(websocket)


# ---------------------------------------------------------------------------
# Registro histórico de chats (panel /admin)
# ---------------------------------------------------------------------------
def _admin_valida(clave: str) -> bool:
    """Valida la clave del panel admin (compartida con el agente)."""
    from app import settings
    return clave == settings.AGENTE_PANEL_CLAVE


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