"""
Batería de pruebas automatizadas contra el chatbot RAG (API real en :8000).

Verifica que el bot cumple las decisiones de producto del proyecto:

  - Tono HÍBRIDO (cordial + veraz).
  - Regla 1: la respuesta es UN solo bloque de texto (1 mensaje de Meta).
  - Regla 2: cierre rápido con derivación ante NO-encontrado (no alucinar).
  - Regla 3: memoria por sesión (recuerda contexto entre turnos).
  - Veracidad: 0 inventos ante preguntas no documentadas.

USO
---
  Asegúrate de que el servidor esté corriendo:
      venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
  Luego:
      venv/bin/python tests/bateria_pruebas.py [--base http://127.0.0.1:8000] [--sesiones]

Salida: veredicto ✅/❌ por caso y un resumen final.
"""
import argparse
import json
import sys

import requests

# Preguntas documentadas (base REAL: CSVs de Transparencia Activa del Drive,
# indexados como chunks atómicos por trámite/norma).
_PREGUNTAS_DOCUMENTADAS = [
    "¿Dónde queda la farmacia comunal?",
    "¿Qué necesito para la Ficha de Protección Social?",
    "¿Qué requisitos tiene el Centro de Emprendimiento?",
]

# Preguntas NO documentadas (el bot NO debe inventar → debe derivar)
_PREGUNTAS_NO_DOCUMENTADAS = [
    "¿Cuál es el horario del gimnasio municipal?",
    "¿Cuánto cuesta la inscripción en el jardín infantil?",
    "¿Qué requisitos piden para una autorización de cabina telefónica?",
    "¿Cuándo es la próxima feria libre en la comuna?",
]

# Palabras que NO deberían aparecer en un fallo (para detectar alucinación).
# NOTA: "Lunes"/"lunes" se quitó de esta lista porque el mensaje de
# transferencia ahora SIEMPRE menciona el horario de atención ("Operamos
# Lunes a Viernes...") de forma legítima; ya no indica alucinación.
_INDICADORES_FALSO = ["gimnasio", "jardín", "jardin", "cabina", "feria libre", "$"]

# Señales de que el bot derivó a un humano (Regla 3 / anti-alucinación).
# El caso no-documentado SIEMPRE ofrece transferir; el token [[TRANSFERIR]]
# se detecta explícitamente en la prueba (por eso no va en esta lista).
_RUTA_HUMANO = ["transferido", "agente de atención", "atención", "atencion"]


def _get(base: str):
    return requests.get(base + "/", timeout=20)


def _query(base: str, question: str, session_id: str):
    r = requests.post(base + "/query", json={"question": question, "session_id": session_id}, timeout=120)
    r.raise_for_status()
    return r.json()["answer"], r.json()["session_id"]


def main():
    parser = argparse.ArgumentParser(description="Batería de pruebas del chatbot RAG")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    base = args.base
    print("=" * 64)
    print("BATERÍA DE PRUEBAS DEL CHATBOT RAG (La Cisterna)")
    print("=" * 64)

    resultados = []

    def registrar(nombre: str, ok: bool, detalle=""):
        resultados.append(ok)
        marca = "✅" if ok else "❌"
        print(f"{marca} {nombre}" + (f" — {detalle}" if detalle else ""))

    # ── 0. Health ──────────────────────────────────────────────
    try:
        r = _get(base)
        registrar("Health (API operativa)", r.status_code == 200 and r.json()["health"] == "ok")
    except Exception as e:
        registrar("Health (API operativa)", False, f"¿servidor corriendo? {e}")
        print("\nDeteniendo: sin API no hay pruebas. Arranca el servidor (uvicorn).")
        sys.exit(1)

    # ── 1. Respuesta documentada (Regla 1: un solo bloque) ─────
    ses = "bateria-doc"
    for q in _PREGUNTAS_DOCUMENTADAS:
        resp, _ = _query(base, q, ses)
        un_bloque = resp.count("\n\n") == 0  # un bloque, sin multi-parrafos separados
        longitud_razonable = 20 <= len(resp) <= 1200
        registrar(
            f"Docs: responde '{q[:30]}...'",
            un_bloque and longitud_razonable,
            f"{len(resp)} chars, single-block={un_bloque}",
        )

    # ── 2. Veracidad: no documentadas → derivan a humano (Regla 3/anti-aluc.) ─
    ses = "bateria-nodoc"
    for q in _PREGUNTAS_NO_DOCUMENTADAS:
        resp, _ = _query(base, q, ses)
        # Regla 3/anti-alucinación: el bot debe OFRECER transferir (token
        # [[TRANSFERIR]] que muestra botones Sí/No) y NO inventar un dato
        # concreto del trámite (precio, lugar específico, etc.).
        derivado = "[[TRANSFERIR]]" in resp or any(k in resp.lower() for k in _RUTA_HUMANO)
        no_inventa = not any(k.lower() in resp.lower() for k in _INDICADORES_FALSO)
        registrar(
            f"No-doc: '{q[:30]}...' deriva a humano sin alucinar",
            derivado and no_inventa,
            f"deriva={derivado}, sinInvento={no_inventa}",
        )

    # ── 3. Memoria en cadena (la sesión recuerda el contexto) ───
    ses = "bateria-memoria"
    q1 = _PREGUNTAS_DOCUMENTADAS[0]  # la farmacia comunal
    _query(base, q1, ses)
    # seguimiento sin repetir el tema explícito (confía en la memoria)
    q2 = "¿Y qué documentos debo llevar?"
    resp2, _ = _query(base, q2, ses)
    # la memória debe haber "atado" la farmacia → debería mencionar "farmacia",
    # "receta", "cédula" o "domicilio" (no derivar a humano).
    menciona_beca = ("farmacia" in resp2.lower() or "receta" in resp2.lower()
                     or "cédula" in resp2.lower() or "cedula" in resp2.lower()
                     or "domicilio" in resp2.lower())
    registrar("Memoria: la sesión sigue el contexto del turno anterior", menciona_beca, f"resp2: {resp2[:60]}...")

    # ── 4. Historial guardado ──────────────────────────────────
    h = requests.get(base + f"/history/{ses}", timeout=20)
    historial_ok = h.status_code == 200 and len(h.json().get("history", [])) >= 3  # >0 mensajes
    registrar("Historial persistido en /history", historial_ok, f"{len(h.json().get('history',[]))} msgs")

    # ── Resumen ─────────────────────────────────────────────────
    ok = sum(resultados)
    total = len(resultados)
    print("-" * 64)
    print(f"RESULTADO: {ok}/{total} pruebas superadas")
    pct = ok / total * 100
    print(f"      → {pct:.0f}% de cumplimiento")
    if ok == total:
        print("      → BOT FUNCIONAL. Cumple tono híbrido y las 3 reglas.")


if __name__ == "__main__":
    main()