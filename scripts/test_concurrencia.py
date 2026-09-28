"""
Verifica que varios vecinos pueden escribir a la vez sin romper SQLite.

Tras mover /query al threadpool, varias consultas corren en paralelo de
verdad. chat_memory abre una conexión por llamada y no configura timeout de
espera, así que dos escrituras simultáneas podrían chocar con
"database is locked". Este test lanza consultas concurrentes y revisa que
todas respondan y que el log no registre errores de SQLite.

Uso:  venv/bin/python scripts/test_concurrencia.py [url] [n]
"""
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5
PREGUNTAS = [
    "¿Qué documentos necesito para el permiso de circulación 2026?",
    "¿A qué hora atiende la Oficina de Rentas?",
    "¿Cómo solicito un permiso de obra menor?",
    "¿Qué necesito para la licencia de conducir?",
    "¿Dónde postulo a la farmacia comunal?",
]


def consultar(i: int) -> tuple[int, str, float]:
    cuerpo = json.dumps(
        {"question": PREGUNTAS[i % len(PREGUNTAS)],
         "session_id": f"test_concurrencia_{i}_{int(time.time())}"}
    ).encode()
    req = urllib.request.Request(
        f"{BASE}/query", data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    inicio = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = r.read().decode()
            return r.status, texto, time.monotonic() - inicio
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200], time.monotonic() - inicio


def main() -> int:
    print(f"Servidor: {BASE}")
    print(f"Lanzando {N} consultas SIMULTÁNEAS...")
    inicio_total = time.monotonic()
    with ThreadPoolExecutor(max_workers=N) as pool:
        resultados = list(pool.map(consultar, range(N)))
    total = time.monotonic() - inicio_total

    fallos = 0
    for i, (status, texto, dur) in enumerate(resultados):
        error = "database is locked" in texto.lower() or status != 200
        if error:
            fallos += 1
        marca = "FALLA" if error else "OK   "
        print(f"  [{marca}] consulta {i}: HTTP {status} en {dur:.2f} s")
        if error:
            print(f"         {texto}")

    print(f"\nTodas juntas: {total:.2f} s "
          f"(secuencial serían ~{sum(r[2] for r in resultados):.1f} s)")

    if fallos:
        print(f"\nFALLA: {fallos} consultas se rompieron bajo concurrencia.")
        return 1
    print("\nTODO OK: N vecinos simultáneos, sin errores de SQLite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
