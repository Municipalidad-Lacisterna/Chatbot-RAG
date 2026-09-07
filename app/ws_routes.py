"""
WebSockets del centro de atención humana (transferencia en vivo).

Dos conexiones:
  - Vecino:   /ws/vecino/{session_id}
  - Agente:   /ws/agente

Cuando el vecino acepta la transferencia, el frontend abre su socket. El
agente (desde el panel) ve la lista de sesiones en espera; al tomar una,
marca "atendiendo" y queda conectado a esa sesión. A partir de ahí los dos
lados reciben/envían mensajes en vivo.

Para el prototipo (1 agente) se mantiene en memoria. No se persiste el
chat transferido: al reiniciar el servidor se pierde (válido para demo).
"""
import asyncio
import json
import threading

from fastapi import WebSocket, WebSocketDisconnect

from app import handoff
from app import chat_memory

# Conexiones live: session_id -> WebSocket (vecino / agente-nombre)
_vivos: dict[str, WebSocket] = {}
# Buffer de mensajes por sesión, para entregar historial al tomar la sesión
_mensajes: dict[str, list[dict]] = {}
_lock = threading.Lock()

# Nombres reservados de conexiones no-vecino
AGENTE_KEY = "agente"


# ---------------------------------------------------------------------------
# Manejo interno de mensajes
# ---------------------------------------------------------------------------
def _registrar(session_id: str, ws: WebSocket):
    with _lock:
        _vivos[session_id] = ws


def _desregistrar(session_id: str):
    with _lock:
        _vivos.pop(session_id, None)


def _push(session_id: str, msg: dict):
    """Guarda el mensaje en buffer y lo distribuye en vivo.

    Envía el mensaje al socket de la sesión (el vecino) y, si la sesión está
    siendo atendida por el agente y el mensaje es del vecino, lo reenvía
    también al agente para que lo vea en vivo.
    """
    with _lock:
        _mensajes.setdefault(session_id, []).append(msg)
    # Persistir los mensajes de texto de la transferencia (canal 'agente')
    # para que queden en el historial y sean exportables desde /admin.
    if msg.get("tipo") == "texto" and msg.get("autor") in ("vecino", "agente"):
        chat_memory.add_agente_message(
            session_id, msg.get("autor"), msg.get("texto", "")
        )
    ws = _vivos.get(session_id)
    if ws is not None:
        asyncio.create_task(ws.send_text(json.dumps(msg, ensure_ascii=False)))
    # Si el agente está atendiendo esta sesión, los mensajes NUEVOS del vecino
    # deben llegarle también (no solo el historial al tomar la sesión).
    if msg.get("autor") == "vecino" and handoff.sesion_actual_agente() == session_id:
        agente = _vivos.get(AGENTE_KEY)
        if agente is not None:
            asyncio.create_task(agente.send_text(
                json.dumps({"tipo": "msg", "msg": msg}, ensure_ascii=False)))


def _notificar_cola():
    """Empuja la cola de espera actual hacia el agente (si está conectado)."""
    cola = handoff.lista_esperando()
    agente = _vivos.get(AGENTE_KEY)
    if agente is not None:
        asyncio.create_task(
            agente.send_text(json.dumps({"tipo": "cola", "cola": cola}, ensure_ascii=False))
        )


# ---------------------------------------------------------------------------
# Endpoints WebSocket
# ---------------------------------------------------------------------------
async def ws_vecino(websocket: WebSocket, session_id: str):
    """Chat en vivo del vecino con el agente."""
    await websocket.accept()
    # Si el agente NO está atendiendo esta sesión ahora mismo, es un NUEVO
    # intento de transferencia (mismo session_id puede venir de otro vecino
    # anterior por el localStorage). Limpiar el buffer antiguo para no
    # entregar mensajes de una conversación previa.
    if handoff.sesion_actual_agente() != session_id:
        with _lock:
            _mensajes.pop(session_id, None)
    # El vecino llega aquí con la intención de hablar con una persona:
    # lo ponemos en la cola de espera para que el panel del agente lo vea.
    handoff.encolar(session_id)
    _notificar_cola()
    _registrar(session_id, websocket)
    # Enviar historial de mensajes que ya estaban en la sesión
    for m in _mensajes.get(session_id, []):
        try:
            await websocket.send_text(json.dumps(m, ensure_ascii=False))
        except Exception:
            break
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"tipo": "texto", "texto": data}
            if payload.get("tipo") == "cerrar":
                handoff.finalizar(session_id)
                break
            # Mensaje del vecino -> buffer (va al agente)
            msg = {"tipo": "texto", "autor": "vecino", "session_id": session_id,
                   "texto": payload.get("texto", ""), "hora": _hora()}
            _push(session_id, msg)
    except WebSocketDisconnect:
        pass
    finally:
        if handoff.sesion_actual_agente() == session_id:
            # El vecino se desconectó abruptamente (cerró el navegador) estando
            # a cargo del agente: liberar al agente para que pueda tomar a otro.
            handoff.finalizar(session_id)
            _notificar_cola()
            # No perder la conversación: aprendemos lo que el agente alcanzó a
            # responder (idempotente; si el agente ya finalizó antes, no duplica).
            try:
                from app import learning
                learning.aprender_sesion(session_id)
            except Exception as e:
                print(f"[ws] error aprendiendo de {session_id}: {e}")
        else:
            # El vecino se fue SIN haber sido atendido: sacarlo de la cola
            # para que el agente no vea una sesión fantasma que nunca responde.
            handoff.quitar_de_cola(session_id)
            _notificar_cola()
        # Limpiar el buffer de esta sesión (el historial ya quedó en chat_memory)
        with _lock:
            _mensajes.pop(session_id, None)
        _desregistrar(session_id)


async def ws_agente(websocket: WebSocket):
    """Panel del agente. Permite tomar sesiones y responder en vivo."""
    await websocket.accept()
    _registrar(AGENTE_KEY, websocket)
    # Notificar la cola actual al agente
    cola = handoff.lista_esperando()
    await _enviar(websocket, {"tipo": "cola", "cola": cola})
    actual = handoff.sesion_actual_agente()
    if actual:
        await _enviar(websocket, {"tipo": "en_curso", "session_id": actual})
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue  # ignorar mensajes malformados del panel

            accion = payload.get("accion")

            if accion == "tomar":
                sid = payload.get("session_id", "")
                if sid and _vivos.get(sid) is None:
                    # El vecino ya no está conectado (cerró la pestaña): sacarlo
                    # de la cola para que no quede como sesión fantasma.
                    handoff.quitar_de_cola(sid)
                    _notificar_cola()
                    await _enviar(websocket, {"tipo": "error",
                                              "texto": "El vecino se desconectó. Se quitó de la cola."})
                elif sid and handoff.tomar(sid):
                    # Mover la sesión a debug en el buffer para el agente
                    await _enviar(websocket, {"tipo": "tomada",
                                              "session_id": sid})
                    for m in _mensajes.get(sid, []):
                        await _enviar(websocket, {"tipo": "msg", "msg": m})
                else:
                    await _enviar(websocket, {"tipo": "error",
                                              "texto": "No se pudo tomar: ocupado o inexistente"})

            elif accion in ("finalizar", "cerrar"):
                sid = payload.get("session_id", "")
                if sid:
                    handoff.finalizar(sid)
                    _push(sid, {"tipo": "estado", "estado": "cerrado",
                                "texto": "El agente finalizó esta atención."})
                    # Limpiar el buffer de la sesión cerrada (el historial ya
                    # quedó en chat_memory vía _push).
                    with _lock:
                        _mensajes.pop(sid, None)
                    # APRENDIZAJE: al cerrar la atención, el bot aprende de las
                    # respuestas del agente (pares QA) para futuros vecinos.
                    try:
                        from app import learning
                        learning.aprender_sesion(sid)
                    except Exception as e:
                        print(f"[ws] error aprendiendo de {sid}: {e}")
                await _enviar(websocket, {"tipo": "finalizado", "session_id": sid})

            elif accion == "responder":
                sid = payload.get("session_id", "")
                texto = payload.get("texto", "")
                if sid and texto:
                    msg = {"tipo": "texto", "autor": "agente", "session_id": sid,
                           "texto": texto, "hora": _hora()}
                    _push(sid, msg)  # llega al vecino
    except WebSocketDisconnect:
        pass
    finally:
        # Al desconectarse el agente (cerró el panel), liberar la sesión que
        # estaba atendiendo para que un próximo agente pueda tomarla. Sin esto,
        # el prototipo (1 agente) queda "ocupado" para siempre con una sesión
        # cuyo panel ya se cerró, bloqueando el "tomar" de futuras sesiones.
        if handoff.sesion_actual_agente():
            act = handoff.sesion_actual_agente()
            handoff.finalizar(act)  # libera _agente_ocupado_con (marco 'cerrado')
        _desregistrar(AGENTE_KEY)


async def _enviar(ws: WebSocket, msg: dict):
    try:
        await ws.send_text(json.dumps(msg, ensure_ascii=False))
    except Exception:
        pass


def _hora() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H:%M")