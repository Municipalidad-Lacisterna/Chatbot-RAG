"""
Regresión del canal de traspaso a humano tras el arreglo del event loop.

Se cambió _push() a async y su escritura a SQLite pasó a un hilo. Este test
recorre el canal completo para confirmar que el traspaso sigue funcionando:
vecino en cola -> mensaje del vecino llega al agente -> el agente toma la
sesión -> responde -> el vecino recibe la respuesta -> todo queda en el
historial.

Uso:  venv/bin/python scripts/test_traspaso_ws.py [url]
"""
import asyncio
import json
import sys
import urllib.request

import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
WS = BASE.replace("http://", "ws://")
SID = "test_traspaso_ws_1"
TIMEOUT = 15

fallos = 0


def check(etiqueta: str, ok: bool, detalle: str = "") -> None:
    global fallos
    print(f"  [{'OK ' if ok else 'FALLA'}] {etiqueta}")
    if not ok:
        fallos += 1
        if detalle:
            print(f"         {detalle}")


async def recv_json(ws, tipo_esperado=None, timeout=TIMEOUT):
    """Lee mensajes hasta encontrar el tipo esperado (o el primero si None)."""
    limite = asyncio.get_event_loop().time() + timeout
    while True:
        restante = limite - asyncio.get_event_loop().time()
        if restante <= 0:
            return None
        try:
            crudo = await asyncio.wait_for(ws.recv(), timeout=restante)
        except asyncio.TimeoutError:
            return None
        datos = json.loads(crudo)
        if tipo_esperado is None or datos.get("tipo") == tipo_esperado:
            return datos


async def recv_del_agente(ws, timeout=TIMEOUT):
    """Lee hasta encontrar un mensaje de tipo texto con autor 'agente'.

    El vecino también recibe el eco de sus propios mensajes, así que filtrar
    solo por tipo no alcanza: hay que distinguir por autor.
    """
    limite = asyncio.get_event_loop().time() + timeout
    while True:
        restante = limite - asyncio.get_event_loop().time()
        if restante <= 0:
            return {}
        try:
            crudo = await asyncio.wait_for(ws.recv(), timeout=restante)
        except asyncio.TimeoutError:
            return {}
        datos = json.loads(crudo)
        if datos.get("tipo") == "texto" and datos.get("autor") == "agente":
            return datos


async def main() -> int:
    print(f"Servidor: {BASE}")
    print("Conectando el panel del agente y el vecino...")

    async with websockets.connect(f"{WS}/ws/agente") as agente, \
            websockets.connect(f"{WS}/ws/vecino/{SID}") as vecino:
        # El agente recibe la cola actual al conectarse
        await recv_json(agente, "cola")

        # Al conectarse el vecino, el agente debe ver la cola actualizada
        cola = await recv_json(agente, "cola", timeout=TIMEOUT)
        check(
            "el vecino aparece en la cola del agente",
            bool(cola and any(s.get("session_id") == SID
                              for s in cola.get("cola", []))),
            f"cola recibida: {cola}",
        )

        # El vecino escribe. El agente NO lo recibe en vivo aún: `_push` solo
        # reenvía al agente cuando YA atiende la sesión. Al tomar, le llega el
        # historial. Escribir aquí que "debe llegar en vivo" sería un falso.
        await vecino.send(json.dumps(
            {"tipo": "texto", "texto": "Necesito hablar con alguien, por favor."}))

        # El agente toma la sesión
        await agente.send(json.dumps({"accion": "tomar", "session_id": SID}))
        tomada = await recv_json(agente, "tomada")
        check("el agente puede tomar la sesión",
              bool(tomada and tomada.get("session_id") == SID),
              f"recibido: {tomada}")

        # Al tomar, el agente debe recibir el historial de la sesión, incluido
        # lo que escribió el vecino.
        historial_agente = await recv_json(agente, "msg")
        htexto = ((historial_agente or {}).get("msg") or {}).get("texto", "")
        check("al tomar, el agente recibe lo que escribió el vecino",
              "alguien" in htexto, f"recibido: {historial_agente}")

        # El agente responde: el vecino debe recibirla (no su propio eco).
        await agente.send(json.dumps({
            "accion": "responder", "session_id": SID,
            "texto": "Buenas, le atiendo. ¿En qué le puedo ayudar?"}))
        respuesta = await recv_del_agente(vecino)
        check("la respuesta del agente llega al vecino",
              "ayudar" in respuesta.get("texto", ""),
              f"recibido: {respuesta}")

        # El agente cierra la atención
        await agente.send(json.dumps({"accion": "finalizar", "session_id": SID}))
        fin = await recv_json(agente, "finalizado")
        check("el agente puede finalizar la atención", fin is not None,
              f"recibido: {fin}")

    # El historial debe tener los mensajes del canal agente (persistidos en hilo)
    with urllib.request.urlopen(f"{BASE}/history/{SID}", timeout=TIMEOUT) as r:
        historial = json.loads(r.read()).get("history", [])
    textos = [h.get("content", "") for h in historial]
    check("el mensaje del vecino quedó en el historial",
          any("alguien" in t for t in textos), f"historial: {textos}")
    check("la respuesta del agente quedó en el historial",
          any("ayudar" in t for t in textos), f"historial: {textos}")

    print("\n" + "=" * 50)
    if fallos == 0:
        print("TODO OK: el traspaso a humano sigue intacto tras el arreglo.")
    else:
        print(f"{fallos} COMPROBACIONES FALLARON.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
