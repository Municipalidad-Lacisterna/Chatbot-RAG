"""
Prueba del manejo de error del LLM (arreglo #1).

Simula que el proveedor falla (cuota agotada / red caída) y verifica que el
vecino recibe un mensaje usable con botón de transferencia, en vez de un 500.

Uso:  venv/bin/python scripts/test_llm_caida.py
No llama a la API real ni consume cuota.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import rag_engine  # noqa: E402


class CuotaAgotadaSimulada(Exception):
    pass


class RedCaidaSimulada(Exception):
    pass


class CadenaMuerta:
    """Sustituye a la cadena RAG real: siempre revienta."""

    def __init__(self, excepcion):
        self.excepcion = excepcion

    def invoke(self, payload):
        raise self.excepcion


CASOS = [
    ("cuota agotada", CuotaAgotadaSimulada("429 RESOURCE_EXHAUSTED: quota exceeded")),
    ("red caída", RedCaidaSimulada("ConnectionError: connection refused")),
]

PREGUNTA = "¿Qué documentos necesito para el permiso de circulación 2026?"

fallos = 0

for nombre, excepcion in CASOS:
    rag_engine._chain = CadenaMuerta(excepcion)
    session_id = f"test_caida_{nombre.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"

    try:
        salida = rag_engine.query_chatbot(PREGUNTA, session_id)
    except Exception as exc:
        print(f"[FALLA] {nombre}: la excepción escapó del motor -> "
              f"{type(exc).__name__}: {exc}")
        fallos += 1
        continue

    # El vecino NO debe enterarse de los detalles internos.
    filtra_internos = any(
        token in salida.lower()
        for token in ("429", "quota", "cuota", "resource_exhausted",
                      "connection", "exception", "traceback")
    )

    checks = {
        "llegó una respuesta": bool(salta := salida.strip()),
        "tiene botón de transferencia": "[[TRANSFERIR]]" in salida,
        "ofrece atención humana": "persona" in salida.lower()
        or "agente" in salida.lower(),
        "no miente diciendo 'no encontré'": "No logré encontrar" not in salida,
        "no filtra detalles técnicos": not filtra_internos,
    }

    print(f"\n=== CASO: {nombre.upper()} ===")
    print(f"Vecino recibe:\n  {salta}")
    for etiqueta, ok in checks.items():
        print(f"  [{'OK ' if ok else 'FALLA'}] {etiqueta}")
        if not ok:
            fallos += 1

    # El turno también debe quedar en el historial, no perder contexto.
    historial = rag_engine.get_history(session_id)
    guardado = len(historial) == 2 and historial[-1]["role"] == "assistant"
    print(f"  [{'OK ' if guardado else 'FALLA'}] turno guardado en el historial")
    if not guardado:
        fallos += 1

print("\n" + "=" * 50)
if fallos == 0:
    print("TODO OK: el bot degrada a humano ante cualquier fallo del LLM.")
else:
    print(f"{fallos} COMPROBACIONES FALLARON.")
sys.exit(1 if fallos else 0)
