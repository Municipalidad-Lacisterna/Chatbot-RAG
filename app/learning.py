"""
Aprendizaje del bot a partir de las respuestas de los agentes de atención
al vecino (auto al cerrar la conversación + revisión desde /admin).

Cuando un agente humano finaliza una atención por transferencia WebSocket,
el sistema:
  1. Lee el historial persistido de esa sesión (canal 'agente').
  2. Extrae los pares (pregunta del vecino → respuesta del agente).
  3. Indexa cada par como un fragmento QA en ChromaDB, marcado con
     `origen='agente_vivo'`.

A partir de entonces, el RAG puede recuperar esas respuestas aprendidas para
futuros vecinos con preguntas similares, sin que tengan que pasar por un
agente humano. Desde el panel /admin se puede listar, ver y "desaprender"
(eliminar) cualquier aprendizaje puntual si resultó malo o desactualizado.

Los IDs de los chunks aprendidos son determinísticos (`qa-{session_id}-{i}`):
si la misma sesión se aprende dos veces, los chunks previos se reemplazan
en vez de duplicarse.
"""
import time
import uuid

from app import settings
from app import chat_memory
from app.database import get_collection

# Metadatos que distinguen el conocimiento aprendido de un agente en vivo
ORIGEN_APRENDIDO = "agente_vivo"
FUENTE_APRENDIDO = "aprendido:agente_vivo"


def _pares_qa(session_id: str) -> list[tuple[str, str]]:
    """
    Extrae los pares (pregunta_vecino, respuesta_agente) de una sesión de
    transferencia. Solo considera mensajes con canal='agente'.
    Recorre en orden cronológico y empareja cada pregunta del vecino (user)
    con la respuesta del agente (assistant) que le sigue en el tiempo.

    Devuelve lista de tuplas (pregunta, respuesta). Omite preguntas muy cortas
    (probablemente ruido del protocolo) y respuestas vacías.
    """
    historial = chat_memory.get_full_history(session_id)
    # Solo mensajes de la conversación con agente vivo
    msg_agente = [m for m in historial if m.get("canal") == "agente"]

    pares = []
    pendiente = None
    for m in msg_agente:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role == "user" and content:
            pendiente = content
        elif role == "assistant" and content and pendiente:
            # Emparejar la última pregunta con esta respuesta del agente
            if len(pendiente) >= 6 and len(content) >= 6:
                pares.append((pendiente, content))
            pendiente = None
    return pares


def aprender_sesion(session_id: str) -> int:
    """
    "Aprende" una sesión de agente: extrae sus pares QA y los indexa en
    ChromaDB bajo el origen 'agente_vivo'. Devuelve cuántos pares se
    aprendieron. Re-aprender la misma sesión reemplaza (no duplica).
    """
    pares = _pares_qa(session_id)
    if not pares:
        return 0

    collection = get_collection()

    # 1. Rebuild: eliminar aprendizajes previos de esta sesión
    # La condición con 2 campos requiere $and explícito en ChromaDB.
    prev = collection.get(
        where={"$and": [{"session_id": session_id}, {"origen": ORIGEN_APRENDIDO}]}
    )
    if prev and prev.get("ids"):
        collection.delete(ids=prev["ids"])

    # 2. Construir documentos QA + metadatos + IDs determinísticos
    docs = []
    metadatas = []
    ids = []
    ts = time.time()
    fecha = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    for i, (pregunta, respuesta) in enumerate(pares):
        texto_qa = f"Pregunta: {pregunta}\nRespuesta: {respuesta}"
        docs.append(texto_qa)
        metadatas.append(
            {
                "source": FUENTE_APRENDIDO,
                "origen": ORIGEN_APRENDIDO,
                "session_id": session_id,
                "tipo": "qa",
                "pregunta": pregunta,
                "chunk_index": i,
                "fecha": fecha,
                "timestamp": ts,
            }
        )
        ids.append(f"qa-{session_id}-{i}")

    collection.add(documents=docs, metadatas=metadatas, ids=ids)
    print(f"[aprendizaje] ✓ sesión '{session_id}': {len(pares)} par(es) QA aprendido(s)")
    return len(pares)


def listar_aprendizajes():
    """
    Lista todo el conocimiento aprendido de agentes en vivo.
    Devuelve una lista de dicts con id y metadatos útiles para /admin.
    """
    collection = get_collection()
    res = collection.get(where={"origen": ORIGEN_APRENDIDO}, limit=2000)
    ids = res.get("ids") or []
    metas = res.get("metadatas") or []
    docs = res.get("documents") or []
    aprendizajes = []
    for i in range(len(ids)):
        m = metas[i] or {}
        aprendizajes.append(
            {
                "qa_id": ids[i],
                "session_id": m.get("session_id", ""),
                "pregunta": m.get("pregunta", ""),
                "fecha": m.get("fecha", ""),
                "texto": docs[i] if i < len(docs) else "",
            }
        )
    return aprendizajes


def olvidar_aprendizaje(qa_id: str) -> bool:
    """Elimina un chunk aprendido concreto (devuelve True si se eliminó)."""
    collection = get_collection()
    res = collection.get(ids=[qa_id], where={"origen": ORIGEN_APRENDIDO})
    if res and res.get("ids"):
        collection.delete(ids=[qa_id])
        print(f"[aprendizaje] ✗ olvidado: {qa_id}")
        return True
    return False


def olvidar_aprendizajes_sesion(session_id: str) -> int:
    """Elimina todos los aprendizajes de una sesión. Devuelve cuántos se quitaron."""
    collection = get_collection()
    res = collection.get(
        where={"$and": [{"session_id": session_id}, {"origen": ORIGEN_APRENDIDO}]}
    )
    if res and res.get("ids"):
        collection.delete(ids=res["ids"])
        print(f"[aprendizaje] ✗ sesión '{session_id}': {len(res['ids'])} aprendizajes olvidados")
        return len(res["ids"])
    return 0