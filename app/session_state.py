"""
Estado de inactividad de las sesiones de chat (timeout "¿hay alguien ahí?").

El bot detecta cuando una conversación queda inactiva y la "despierta" con una
pregunta de confirmación. Flujo:

  1. Si el vecino tarda > 5 min en responder (desde la última interacción),
     el bot responde "¿Hay alguien ahí?" (NO procesa la pregunta aún) y guarda
     la pregunta pendiente. La sesión queda en estado "esperando_confirmacion".
  2. Si el vecino responde dentro de 3 min → se confirma y el bot procesa la
     pregunta pendiente (o la nueva). La sesión se mantiene.
  3. Si el vecino NO responde en 3 min → el chat se cierra: el bot responde
     con un mensaje de despedida y la sesión se reinicia (estado limpio).

Se mantiene en memoria (por sesión) con un lock para hilos. No es persistente
a reinicios del servidor, lo cual es correcto para una sesión en vivo.
"""
import threading
import time

import re

# Lista de groserías y faltas de respeto comunes
_GROSERIAS = {
    "conchetumare", "ctm", "weon", "wea", "huevon", "huevona", "aweonao",
    "pichula", "maricon", "puta", "mierda", "chucha", "concha de tu madre",
    "culiao", "chuchetumare", "qlo", "xuxa", "maraca", "perra", "imbecil", "idiota"
}

def _contiene_groseria(texto: str) -> bool:
    texto = texto.lower()
    for mala_palabra in _GROSERIAS:
        if re.search(r'\b' + re.escape(mala_palabra) + r'\b', texto):
            return True
    return False


# Tiempos configurables en segundos (por defecto 5 min y 3 min)
INACTIVO_MINS = 5
INACTIVO_SEG = INACTIVO_MINS * 60
CONFIRMAR_MINS = 3
CONFIRMAR_SEG = CONFIRMAR_MINS * 60

# Rate Limiting: máximo 10 mensajes en 60 segundos por sesión
RATE_LIMIT_MSG = 10
RATE_LIMIT_SEG = 60

# Estado por session_id
_estado: dict[str, dict] = {}
_lock = threading.Lock()


def _get(session_id: str) -> dict:
    st = _estado.get(session_id)
    if st is None:
        st = {
            "ultima_actividad": time.time(),
            "esperando_confirmacion": False,
            "pregunta_pendiente": None,
            "peticiones": [],
            "strikes": 0,
        }
        _estado[session_id] = st
    return st


def registrar_interaccion(session_id: str):
    """Marca que hubo actividad en la sesión (resetea la ventana de inactividad)."""
    with _lock:
        _get(session_id)["ultima_actividad"] = time.time()


def evaluar(session_id: str, pregunta: str) -> dict:
    """
    Evalúa la sesión ante una nueva pregunta del vecino.

    Devuelve un dict con una de estas acciones:
      { "accion": "procesar" }                     → procesar la pregunta normal.
      { "accion": "preguntar" }                    → responder "¿hay alguien ahí?",
                                                     guardar pendiente y NO procesar.
      { "accion": "confirmar", "pregunta": str }   → el vecino confirmó; procesar la
                                                     pregunta pendiente (o la nueva).
      { "accion": "cerrar" }                       → no respondió a tiempo; despedida.
      { "accion": "bloquear" }                     → rate limit excedido (muy rápido).
    """
    with _lock:
        st = _get(session_id)
        ahora = time.time()

        # RATE LIMITING: Limpiar peticiones viejas y chequear límite
        st["peticiones"] = [t for t in st["peticiones"] if ahora - t < RATE_LIMIT_SEG]
        if len(st["peticiones"]) >= RATE_LIMIT_MSG:
            return {"accion": "bloquear"}
        st["peticiones"].append(ahora)


        # FILTRO DE GROSERIAS (3 Strikes)
        if _contiene_groseria(pregunta):
            st["strikes"] += 1
            if st["strikes"] < 3:
                return {
                    "accion": "advertencia",
                    "mensaje": f"⚠️ Advertencia ({st['strikes']}/3): Por favor, mantengamos un lenguaje respetuoso para poder ayudarte."
                }
            else:
                st["strikes"] = 0
                return {
                    "accion": "cerrar",
                    "mensaje_personalizado": "🚫 Has excedido el límite de faltas de respeto (3/3). El chat ha sido cerrado."
                }

        # Si pasó mucho tiempo (> 5 min), reseteamos el historial corto
        # para que empiece una conversación fresca, pero respondemos su pregunta al tiro.
        if ahora - st["ultima_actividad"] > INACTIVO_SEG:
            from app.chat_memory import clear_session
            clear_session(session_id)
        
        st["ultima_actividad"] = ahora
        return {"accion": "procesar"}


def reset(session_id: str):
    """Limpia el estado de inactividad de una sesión (al cerrar o reiniciar)."""
    with _lock:
        _estado.pop(session_id, None)