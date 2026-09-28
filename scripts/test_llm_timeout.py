"""
Prueba del punto 5: timeout y reintentos del LLM.

Verifica dos cosas que antes fallaban:
  1. Un error de cuota agotada degrada a humano RÁPIDO. Antes LangChain
     reintentaba 6 veces con espera creciente; ahora con max_retries=1.
  2. Una consulta colgada se corta sola por timeout. Antes timeout=None
     (infinito) podía dejar al vecino esperando indefinidamente.

No llama a la API real: el primer caso inyecta una excepcion y el segundo
apunta a un servidor local que acepta la conexion y nunca contesta.

Uso:  venv/bin/python scripts/test_llm_timeout.py
"""
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

fallos = 0


def check(etiqueta: str, ok: bool, detalle: str = "") -> None:
    global fallos
    print(f"  [{'OK ' if ok else 'FALLA'}] {etiqueta}")
    if not ok:
        fallos += 1
        if detalle:
            print(f"         {detalle}")


def caso_cuota_rapida() -> None:
    """Un 429 debe degradar a humano sin gastar minutos reintentando."""
    from google.api_core.exceptions import ResourceExhausted

    from app import rag_engine
    from langchain_google_genai import ChatGoogleGenerativeAI

    intentos = {"n": 0}
    original = ChatGoogleGenerativeAI._generate

    def que_falla(self, *a, **kw):
        intentos["n"] += 1
        raise ResourceExhausted(
            "429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric "
            "'Generate Content API requests per minute'"
        )

    ChatGoogleGenerativeAI._generate = que_falla
    try:
        inicio = time.monotonic()
        r = rag_engine.query_chatbot(
            "hola, una consulta cualquiera", "ses_timeout_1"
        )
        took = time.monotonic() - inicio
    finally:
        ChatGoogleGenerativeAI._generate = original

    print(f"    intentos al proveedor: {intentos['n']}, tiempo: {took:.2f} s")
    # Guardas anti-verde-falso: si el proveedor nunca se llamo, el resto de
    # comprobaciones pasan en vacio y la prueba miente.
    check("el proveedor fue realmente invocado",
          intentos["n"] >= 1, f"intentos: {intentos['n']}")
    check("degrada con el mensaje de derivacion a humano",
          "[[TRANSFERIR]]" in r, r[:120])
    # La causa se comprueba sobre el detector, no sobre el texto del vecino:
    # el detalle tecnico va al log a proposito y no se le muestra a la gente.
    check("detecta el 429 como cuota agotada",
          rag_engine._es_error_cuota(ResourceExhausted(
              "429 RESOURCE_EXHAUSTED: Quota exceeded for quota metric")))
    check("no filtra el detalle tecnico al vecino",
          "429" not in r and "resource_exhausted" not in r.lower())
    check("no reintenta mas de 2 veces (antes eran 6 reintentos)",
          intentos["n"] <= 2, f"intentos: {intentos['n']}")
    check("degrada en menos de 20 s", took < 20, f"tomo {took:.2f} s")


def caso_timeout_corta() -> None:
    """Un servidor que acepta y no contesta debe cortarse por timeout."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    puerto = srv.getsockname()[1]
    conexiones = []

    def nunca_contesta():
        while True:
            try:
                c, _ = srv.accept()
                conexiones.append(c)  # se mantiene abierta, sin responder
            except OSError:
                return

    hilo = threading.Thread(target=nunca_contesta, daemon=True)
    hilo.start()

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        temperature=0,
        google_api_key="clave-falsa-para-prueba",
        base_url=f"http://127.0.0.1:{puerto}",
        timeout=3,
        max_retries=1,
    )
    try:
        inicio = time.monotonic()
        try:
            llm.invoke("hola")
            corto = False
            detalle = "no lanzo excepcion"
        except Exception as exc:  # noqa: BLE001 - aqui cualquier error es esperado
            corto = True
            detalle = type(exc).__name__
        took = time.monotonic() - inicio
    finally:
        srv.close()

    print(f"    excepcion: {detalle}, tiempo: {took:.2f} s")
    check("la consulta colgada lanza excepcion en vez de colgar", corto)
    check("el timeout corta antes de 25 s (timeout=3 x 2 intentos)",
          took < 25, f"tomo {took:.2f} s")


def main() -> int:
    print("Punto 5: timeout y reintentos del LLM\n")
    print("Caso 1: cuota agotada (debe derivar a humano rapido)")
    caso_cuota_rapida()
    print("\nCaso 2: servidor que nunca responde (debe cortar por timeout)")
    caso_timeout_corta()

    print("\n" + "=" * 50)
    if fallos == 0:
        print("TODO OK: la cuota agota rapido y el cuelgue se corta solo.")
    else:
        print(f"{fallos} COMPROBACIONES FALLARON.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
