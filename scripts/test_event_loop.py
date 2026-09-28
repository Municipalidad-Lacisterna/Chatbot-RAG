"""
Mide si el event loop se bloquea durante una consulta real.

Lanza una consulta al modelo (tarda varios segundos) y, mientras corre,
mide cuánto tarda el servidor en responder un endpoint trivial (GET /).
Si el event loop está libre, / responde en milisegundos aunque haya una
consulta en curso. Si está bloqueado, / tarda lo mismo que la consulta.

Uso:  venv/bin/python scripts/test_event_loop.py [url]
"""
import json
import sys
import threading
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PREGUNTA = "¿Qué documentos necesito para el permiso de circulación 2026?"
UMBRAL_SANO = 0.5  # segundos; por encima de esto el loop está bloqueado

resultado = {}


def timed_get() -> float:
    inicio = time.monotonic()
    with urllib.request.urlopen(f"{BASE}/", timeout=120) as r:
        r.read()
    return time.monotonic() - inicio


def consulta_en_hilo() -> None:
    cuerpo = json.dumps(
        {"question": PREGUNTA, "session_id": "event_loop_test"}
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/query", data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    inicio = time.monotonic()
    with urllib.request.urlopen(req, timeout=120) as r:
        r.read()
    resultado["consulta"] = time.monotonic() - inicio


def main() -> int:
    print(f"Servidor: {BASE}")
    print("Lanzando una consulta real al modelo...")
    hilo = threading.Thread(target=consulta_en_hilo)
    hilo.start()

    time.sleep(0.7)  # dejar que la consulta se instale en el loop
    latencia = timed_get()
    hilo.join()

    print(f"\nConsulta al modelo:        {resultado['consulta']:.2f} s")
    print(f"GET / durante la consulta: {latencia:.3f} s")

    if latencia < UMBRAL_SANO:
        print("\nOK: el event loop está LIBRE. / respondió al instante mientras")
        print("el modelo pensaba, así que el WebSocket de atención humana sigue")
        print("funcionando durante una consulta.")
        return 0

    print("\nFALLA: el event loop está BLOQUEADO. Un endpoint trivial tardó")
    print(f"{latencia:.2f} s. En ese tiempo el servidor no atiende a nadie: los")
    print("WebSockets del vecino y del agente quedan congelados, así que el")
    print("traspaso a un humano se traba justo cuando más lo necesita.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
