"""
Prueba del camino de error de la UI (arreglo #4).

No necesita navegador: ejecuta el JavaScript real de static/index.html en Node
con un DOM mínimo y deja que `enviarMensaje()` haga su recorrido completo con la
red caida. Asi se ejercita el `catch` de verdad, no una llamada suelta a la
funcion de ayuda.

Uso:  venv/bin/python scripts/test_ui_error.py
"""
import json
import subprocess
import sys
from pathlib import Path

HTML = Path(__file__).resolve().parent.parent / "static" / "index.html"
JS_HARNESS = Path("/tmp/ui_error_harness.js")

fallos = 0


def check(etiqueta: str, ok: bool, detalle: str = "") -> None:
    global fallos
    print(f"  [{'OK ' if ok else 'FALLA'}] {etiqueta}")
    if not ok:
        fallos += 1
        if detalle:
            print(f"         {detalle}")


HARNESS_JS = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const cuerpos = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]);
if (cuerpos.length === 0) { console.error('sin script'); process.exit(3); }
const cuerpo = cuerpos.join('\n');

function elem(tag) {
  return {
    tagName: tag, style: {}, className: '', textContent: '', value: '',
    disabled: false, children: [],
    classList: { add(){}, remove(){}, toggle(){} },
    appendChild(c){ this.children.push(c); },
    removeChild(){}, setAttribute(){}, getAttribute(){ return null; },
    addEventListener(){}, focus(){}, scrollIntoView(){}, click(){},
    insertAdjacentHTML(){}, remove(){}, closest(){ return null; },
  };
}

const porId = new Map();
global.document = {
  createElement: elem,
  getElementById: (id) => {
    if (!porId.has(id)) porId.set(id, elem('div'));
    return porId.get(id);
  },
  querySelector: () => elem('div'),
  querySelectorAll: () => [],
  addEventListener(){},
  body: elem('body'),
};
global.window = {
  location: { host: 'localhost', protocol: 'http:' }, addEventListener(){}
};
global.localStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.sessionStorage = { getItem: () => null, setItem(){}, removeItem(){} };
global.WebSocket = class { constructor(){} send(){} close(){} addEventListener(){} };
global.WebSocket.OPEN = 1;
global.navigator = { clipboard: { writeText: async () => {} } };
global.alert = () => {};
global.confirm = () => true;
const modoRed = process.argv[3] === 'red';
global.fetch = async () => {
  if (modoRed) throw new Error('red caida');
  return { ok: true, status: 200,
           json: async () => ({ answer: 'Si, lleva el padron vigente.' }) };
};

const modo = process.argv[3] || 'red';
const registro = { burbujas: [], transferidas: [] };

const disparador = `
  bubble = function(txt, autor) { registro.burbujas.push({txt, autor}); };
  mostrarBotonesTransferir = function() { registro.transferidas.push(1); };
  entrada.value = 'hola, necesitas el permiso de circulacion?';
  enviar.disabled = false;
  enModoAgente = false;
  ws = null;
  return enviarMensaje();
`;

(async () => {
  try {
    await new Function('registro', cuerpo + disparador)(registro);
  } catch (e) {
    console.error('ERROR AL EJECUTAR EL SCRIPT: ' + e.message);
    process.exit(2);
  }
  console.log(JSON.stringify(registro));
})();
"""


def ejecutar(modo: str) -> dict:
    print(f"\n--- escenario: {modo} ---")
    JS_HARNESS.write_text(HARNESS_JS, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(JS_HARNESS), str(HTML), modo],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        print("  [FALLA] no se pudo ejecutar el script de la UI:")
        print(f"         {(proc.stderr or proc.stdout)[:600]}")
        return {"error": True}
    line = [l for l in proc.stdout.strip().splitlines() if l.startswith("{")][-1]
    return json.loads(line)



def main() -> int:
    reg = ejecutar("red")
    if reg.get("error"):
        return 1
    vecino = [b for b in reg["burbujas"] if b["autor"] == "user"]
    bot = [b for b in reg["burbujas"] if b["autor"] == "bot"]

    print(f"\nMensajes que ve el vecino: {len(reg['burbujas'])} "
          f"(propios: {len(vecino)}, del bot: {len(bot)})")
    for b in reg["burbujas"]:
        print(f"  ({b['autor']}) {b['txt']}")

    texto = " ".join(b["txt"] for b in bot).lower()
    check("se muestra un mensaje del bot al vecino", len(bot) == 1)
    check("el mensaje del vecino se muestra primero", len(vecino) == 1)
    check("ofrece transferir a una persona",
          "persona" in texto and "transfiera" in texto, f"texto: {texto}")
    check("no finge que no encontro la informacion", "no encontre" not in texto)
    check("no filtra detalles tecnicos",
          not any(t in texto for t in ("http", "fetch", "error", "exception")))
    check("se ofrecen los botones de transferencia",
          len(reg["transferidas"]) == 1,
          f"llamadas: {len(reg['transferidas'])}")

    # Escenario 2: el servidor responde bien. Regresion del camino feliz: no
    # debe aparecer el mensaje de falla ni ofrecerse la transferencia.
    reg2 = ejecutar("ok")
    if reg2.get("error"):
        return 1
    bot2 = [b for b in reg2["burbujas"] if b["autor"] == "bot"]
    for b in reg2["burbujas"]:
        print(f"  ({b['autor']}) {b['txt']}")
    texto2 = " ".join(b["txt"] for b in bot2).lower()
    check("el camino feliz muestra la respuesta del servidor", len(bot2) == 1)
    check("el camino feliz no inventa una falla", "problema" not in texto2)
    check("el camino feliz no ofrece transferencia",
          len(reg2["transferidas"]) == 0)

    print("\n" + "=" * 50)
    if fallos == 0:
        print("TODO OK: la UI degrada con honestidad y sin romper el camino feliz.")
    else:
        print(f"{fallos} COMPROBACIONES FALLARON.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
