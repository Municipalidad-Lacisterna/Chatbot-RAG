import requests
import concurrent.futures
import time
import sys

URL = "http://127.0.0.1:8000/query"

def send_msg(session_id, text):
    try:
        resp = requests.post(URL, json={"question": text, "session_id": session_id}, timeout=35)
        return resp.status_code, resp.json()
    except Exception as e:
        return 0, str(e)

print("=== PRUEBA DE ESTRES HUMANO ===")

# 1. Ortografia terrible
print("\n1. Probando ortografia terrible...")
status, data = send_msg("estres-ortografia", "ola nesesito el subcidio como lo ago xfa")
if status == 200:
    print(f"  [OK] El servidor sobrevivio a la mala ortografia. Respuesta: {data.get('answer')[:100]}...")
else:
    print(f"  [FALLA] Error en ortografia. Status: {status}")

# 2. Efecto Ametralladora (5 mensajes en paralelo simulando enter rapido)
print("\n2. Probando ametralladora (5 mensajes rapidos)...")
mensajes = ["hola", "nesesito", "ayuda", "con", "patente"]
resultados = []

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futuros = [executor.submit(send_msg, "estres-ametralladora", m) for m in mensajes]
    for futuro in concurrent.futures.as_completed(futuros):
        resultados.append(futuro.result())

fallas = 0
for i, (status, data) in enumerate(resultados):
    if status == 200:
        print(f"  Mensaje {i+1} [OK]")
    else:
        print(f"  Mensaje {i+1} [FALLA] Status {status}, Error: {data}")
        fallas += 1

if fallas == 0:
    print("\n✅ TODO OK: El bot resiste la brutalidad humana sin caerse.")
    sys.exit(0)
else:
    print("\n❌ FALLARON algunas peticiones.")
    sys.exit(1)
