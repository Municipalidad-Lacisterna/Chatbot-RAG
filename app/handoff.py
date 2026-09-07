"""
Módulo de transferencia a agente humano (handoff).

Gestiona la COLA de espera de vecinos que pidieron hablar con una persona
real, y el enrutamiento de esos hilos hacia el agente. Diseñado para el
prototipo: UN agente atendiendo desde un navegador (panel /agente).

Estados de una sesión en transferencia:
    - "esperando": el vecino pidió hablar con un humano y está en la cola.
    - "atendiendo": un agente tomó la sesión; el chat está en vivo.
    - "cerrado": el agente finalizó la atención.

Todo se mantiene EN MEMORIA (dict). Sirve para el prototipo y demo. Para
escala real (varios agentes, persistencia, reinicios) se migra a Redis +
Postgres (ver nota de arquitectura escalabilidad).

También expone la lógica de HORARIO del agente: si "ahora" hay un agente
disponible según AGENTE_HORA_INICIO / AGENTE_HORA_FIN.
"""
import threading
from datetime import datetime

from app import settings

# Cola de espera: {session_id: {estado, llamada_entrante}}
_QUEUE: dict[str, dict] = {}
_lock = threading.Lock()

# Sesión actualmente atendida por el agente (prototipo: 1 agente).
_agente_ocupado_con: str | None = None


# ---------------------------------------------------------------------------
# Disponibilidad del agente según horario
# ---------------------------------------------------------------------------
def _parse_hm(txt: str):
    """Convierte 'HH:MM' a (hora, minuto)."""
    try:
        h, m = (int(x) for x in txt.split(":"))
        return h, m
    except (ValueError, AttributeError):
        return 9, 0


def agentes_disponibles_ahora() -> bool:
    """
    True si el día y la hora actual están dentro del horario de los agentes.
    Solo cuenta días de semana (lunes=0 .. viernes=4).
    """
    now = datetime.now()
    # Días de semana 0-4
    if now.weekday() > 4:
        return False
    hi = _parse_hm(settings.AGENTE_HORA_INICIO)
    hf = _parse_hm(settings.AGENTE_HORA_FIN)
    cur = (now.hour, now.minute)
    if hi <= hf:
        return hi <= cur < hf
    # horario que cruza medianoche (raro): tratarlo como dentro si está en [hi, 24) o [0, hf)
    return cur >= hi or cur < hf


def esta_ocupado() -> bool:
    """True si el (único) agente ya está atendiendo a alguien."""
    return _agente_ocupado_con is not None


# ---------------------------------------------------------------------------
# Cola de espera
# ---------------------------------------------------------------------------
def encolar(session_id: str) -> dict:
    """
    Agrega una sesión a la cola de espera y devuelve su estado.

    Idempotente por diseño:
    - Si el agente YA está atendiendo esa sesión (reconexión del vecino),
      NO se re-encola: se devuelve el estado actual ('atendiendo').
    - En cualquier otro caso se trata como una solicitud nueva ('esperando').
    """
    with _lock:
        if _agente_ocupado_con == session_id:
            return _QUEUE.setdefault(
                session_id, {"estado": "atendiendo", "session_id": session_id}
            )
        _QUEUE[session_id] = {"estado": "esperando", "session_id": session_id}
        return _QUEUE[session_id]


def obtener_estado(session_id: str) -> dict | None:
    """Devuelve el estado actual de una sesión en transferencia (o None)."""
    return _QUEUE.get(session_id)


def lista_esperando() -> list[dict]:
    """Sesiones en cola esperando agente (para el panel)."""
    with _lock:
        return [v for v in _QUEUE.values() if v["estado"] == "esperando"]


def tomar(session_id: str) -> bool:
    """
    Permite que el agente tome una sesión de la cola.
    Devuelve True si la sesión existía y estaba 'esperando'.
    """
    global _agente_ocupado_con
    with _lock:
        if _agente_ocupado_con is not None:
            # El agente ya está con alguien: no puede tomar otra ahora.
            return False
        s = _QUEUE.get(session_id)
        if not s or s["estado"] != "esperando":
            return False
        s["estado"] = "atendiendo"
        _agente_ocupado_con = session_id
        return True


def finalizar(session_id: str):
    """Marca una sesión atendida como cerrada y libera al agente."""
    global _agente_ocupado_con
    with _lock:
        s = _QUEUE.get(session_id)
        if s:
            s["estado"] = "cerrado"
        if _agente_ocupado_con == session_id:
            _agente_ocupado_con = None


def quitar_de_cola(session_id: str):
    """
    Saca por completo una sesión de la cola (sin estado residual).
    Se usa cuando el vecino se desconecta sin haber sido atendido.
    """
    with _lock:
        _QUEUE.pop(session_id, None)


def sesion_actual_agente() -> str | None:
    """Session_id que el agente está atendiendo ahora mismo (o None)."""
    return _agente_ocupado_con