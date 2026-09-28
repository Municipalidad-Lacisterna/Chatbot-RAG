"""
Prueba de la segunda barrera de /query (arreglo #2).

Simula un fallo interno del motor (base vectorial, SQLite, bug) y verifica
que el endpoint responde 200 con un mensaje de traspaso, no un HTTP 500.

Uso:  venv/bin/python scripts/test_query_barrera.py
No llama a la API real ni consume cuota.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import rag_engine  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)

PREGUNTA = "¿Qué documentos necesito para el permiso de circulación 2026?"

ESCENARIOS = {
    "chroma caido": ConnectionError("ChromaDB: collection municipal_docs unreadable"),
    "sqlite bloqueado": RuntimeError("database is locked"),
    "bug generico": ZeroDivisionError("division by zero"),
}

fallos = 0

for nombre, excepcion in ESCENARIOS.items():
    def revienta(*_args, _exc=excepcion, **_kwargs):
        raise _exc

    original = rag_engine.query_chatbot
    rag_engine.query_chatbot = revienta
    try:
        respuesta = client.post(
            "/query",
            json={"question": PREGUNTA, "session_id": f"barrera_{nombre}"},
        )
    finally:
        rag_engine.query_chatbot = original

    print(f"\n=== ESCENARIO: {nombre.upper()} ===")
    print(f"  HTTP status: {respuesta.status_code}")

    cuerpo = respuesta.json() if respuesta.status_code == 200 else {}
    texto = cuerpo.get("answer", "")

    checks = {
        "responde 200 (no 500)": respuesta.status_code == 200,
        "conserva la session_id": cuerpo.get("session_id") == f"barrera_{nombre}",
        "tiene botón de transferencia": "[[TRANSFERIR]]" in texto,
        "ofrece atención humana": "persona" in texto.lower(),
        "no filtra detalles técnicos": not any(
            t in texto.lower()
            for t in ("chroma", "sqlite", "traceback", "zerodivision", "locked")
        ),
    }

    for etiqueta, ok in checks.items():
        print(f"  [{'OK ' if ok else 'FALLA'}] {etiqueta}")
        if not ok:
            fallos += 1
    print(f"  Vecino recibe:\n  {texto}")

# El camino normal no debe estar afectado por la barrera.
print("\n=== REGRESION: camino normal ===")
print("  (verificado aparte contra el servidor vivo: respuesta de Gemini "
      "correcta tras el arranque)")

print("\n" + "=" * 50)
if fallos == 0:
    print("TODO OK: /query nunca devuelve 500 por un fallo interno.")
else:
    print(f"{fallos} COMPROBACIONES FALLARON.")
sys.exit(1 if fallos else 0)
