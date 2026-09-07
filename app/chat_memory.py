"""
Memoria de conversación persistente en SQLite.

Guarda el historial de cada sesión para que sobreviva a reinicios del servidor.
Usamos SQLite (sin dependencias extra) porque es simple, local y suficiente
para un prototipo. El `session_id` identifica cada conversación.

Cada mensaje tiene un `canal`:
  - "bot"    → conversación del vecino con el chatbot automático (POST /query).
  - "agente" → conversación en vivo con un agente humano (transferencia WS).
Esto permite distinguir y exportar ambos tipos en el panel de administración.
"""
import sqlite3
import time
import contextlib
from app.settings import MEMORY_DB_PATH, MEMORY_LAST_TURNS, HISTORY_MAX_AGE

_SCHEMA_VERSION_KEY = "user_version"
_CANAL_BOT = "bot"
_CANAL_AGENTE = "agente"

# Retención del historial en segundos (por defecto 24 h). Se usa para el
# borrado automático por antigüedad (Ley 19.628: minimización/duración limitada).
_DEFAULT_MAX_AGE = 86400  # 24 horas


def _connect():
    """Abre conexión a la base SQLite y asegura tabla y esquema."""
    conn = sqlite3.connect(MEMORY_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            session_id TEXT NOT NULL,
            role       TEXT NOT NULL,   -- 'user' | 'assistant'
            content    TEXT NOT NULL,
            timestamp  REAL NOT NULL,
            canal      TEXT NOT NULL DEFAULT 'bot'
        )
        """
    )
    _migrar_canal(conn)
    return conn


@contextlib.contextmanager
def get_db():
    """
    Manejador de contexto para conexiones a SQLite.
    Asegura el commit automático si no hay errores y cierra la conexión
    incluso si ocurren excepciones, evitando fugas de memoria (leaks).
    """
    conn = _connect()
    try:
        with conn:  # Delega commit/rollback automático de la transacción
            yield conn
    finally:
        conn.close()


def _migrar_canal(conn):
    """
    Migración idempotente: añade la columna `canal` si la tabla antigua no la
    tiene (las filas existentes quedan marcadas como 'bot').
    """
    cols = [row[1] for row in conn.execute("PRAGMA table_info(chat_history)")]
    if "canal" not in cols:
        conn.execute("ALTER TABLE chat_history ADD COLUMN canal TEXT NOT NULL DEFAULT 'bot'")


def purge_old(max_age_secs: float = None) -> int:
    """
    Elimina los mensajes (y las sesiones resultantes vacías) más antiguos que
    `max_age_secs` segundos. Retorna el número de mensajes eliminados.

    Un mensaje se conserva mientras su `timestamp` sea mayor que
    `ahora - max_age_secs`. Todo lo más antiguo se borra de la base.
    """
    max_age_secs = max_age_secs if max_age_secs is not None else _DEFAULT_MAX_AGE
    if max_age_secs <= 0:
        raise ValueError("max_age_secs debe ser > 0")
    
    corte = time.time() - max_age_secs
    
    with get_db() as conn:
        cur = conn.execute("DELETE FROM chat_history WHERE timestamp < ?", (corte,))
        borrados = cur.rowcount
        # Limpiar sesiones que quedaron sin mensajes
        conn.execute(
            """
            DELETE FROM chat_history
            WHERE session_id NOT IN (SELECT session_id FROM chat_history)
            """
        )
        return borrados


def purge_old_if_needed(max_age_secs: float = None) -> int:
    """
    Limpieza perezosa: elimina mensajes antiguos si ha pasado suficiente
    tiempo desde la última limpieza (evita barrer la base en cada llamada).
    Retorna el número de mensajes eliminados (0 si no tocó limpiar).
    """
    max_age_secs = max_age_secs if max_age_secs is not None else _DEFAULT_MAX_AGE
    cfg = getattr(purge_old_if_needed, "_last_purge", 0.0)
    intervalo = min(max_age_secs, 3600)  # a lo más una vez por hora
    if time.time() - cfg >= intervalo:
        n = purge_old(max_age_secs)
        purge_old_if_needed._last_purge = time.time()
        return n
    return 0


def add_message(session_id: str, role: str, content: str, canal: str = _CANAL_BOT):
    """Guarda un mensaje en el historial de la sesión."""
    purge_old_if_needed()  # retención limitada (Ley 19.628)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_history (session_id, role, content, timestamp, canal) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, time.time(), canal),
        )


def add_agente_message(session_id: str, autor: str, content: str):
    """
    Guarda un mensaje de una conversación con agente humano.
    `autor` es 'vecino' o 'agente' (del protocolo WebSocket); se mapea a
    role 'user'/'assistant' para mantener consistencia con el resto.
    """
    role = "user" if autor == "vecino" else "assistant"
    add_message(session_id, role, content, canal=_CANAL_AGENTE)


def get_history(session_id: str, last_turns: int = None) -> list[dict]:
    """
    Devuelve las últimas `last_turns` interacciones de la sesión.
    """
    last_turns = last_turns or MEMORY_LAST_TURNS
    purge_old_if_needed()  # retención limitada (Ley 19.628)
    
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, last_turns * 2),  # 2 mensajes por turno
        ).fetchall()

    # Devolver en orden cronológico (del más antiguo al más reciente)
    history = [{"role": role, "content": content} for role, content in reversed(rows)]
    return history


def get_full_history(session_id: str) -> list[dict]:
    """
    Devuelve TODO el historial de una sesión (sin límite de turnos), en orden
    cronológico, con timestamp y canal. Para el registro/exportación.
    """
    purge_old_if_needed()  # retención limitada (Ley 19.628)
    
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, timestamp, canal FROM chat_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
            """,
            (session_id,),
        ).fetchall()
        
    return [
        {
            "role": role,
            "content": content,
            "timestamp": ts,
            "fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) if ts else "",
            "canal": canal,
        }
        for role, content, ts, canal in rows
    ]


def list_sessions() -> list[dict]:
    """
    Devuelve todas las sesiones distintas con metadatos:
    session_id, número de mensajes, tipo(s) de canal, primera y última actividad.
    Ordenadas por actividad más reciente primero.
    """
    purge_old_if_needed()  # retención limitada (Ley 19.628)
    
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT session_id,
                   COUNT(*) AS msgs,
                   COUNT(DISTINCT canal) AS canales_distintos,
                   MAX(canal) AS canal_ultimo,
                   MIN(timestamp) AS inicio,
                   MAX(timestamp) AS fin
            FROM chat_history
            GROUP BY session_id
            ORDER BY fin DESC
            """
        ).fetchall()
        
    sesiones = []
    for sid, msgs, canales, canal_ultimo, ini, fin in rows:
        sesiones.append(
            {
                "session_id": sid,
                "mensajes": msgs,
                "canal": canal_ultimo,
                "inicio": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ini)) if ini else "",
                "fin": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(fin)) if fin else "",
            }
        )
    return sesiones


def export_sessions() -> dict:
    """
    Arma el dataset completo (todas las sesiones con su historial) para
    exportar en CSV/JSON/TXT. Devuelve un dict {"sesiones": [...], "total": int}.
    """
    sesiones = list_sessions()
    resultado = []
    for s in sesiones:
        resultado.append(
            {
                "session_id": s["session_id"],
                "inicio": s["inicio"],
                "fin": s["fin"],
                "canal": s["canal"],
                "mensajes": get_full_history(s["session_id"]),
            }
        )
    return {"sesiones": resultado, "total": len(resultado)}


def clear_session(session_id: str):
    """Elimina todo el historial de una sesión (util para testing/reset)."""
    with get_db() as conn:
        conn.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))


def clear_all():
    """Elimina todo el historial de chats (todas las sesiones)."""
    with get_db() as conn:
        conn.execute("DELETE FROM chat_history")
