import re

with open("static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

patch_js = """
    // --- VARIABLES MODO PILOTO ---
    let configUI = { modo_piloto: false, horario_habil: false, whatsapp_url: "" };

    fetch('/ui_config').then(r => r.json()).then(data => {
      configUI = data;
      if (configUI.modo_piloto && configUI.horario_habil) {
         // Inyectar un mensaje inicial automático
         setTimeout(() => {
           bubble(`¡Hola! Estamos en horario de oficina. Puedes hablar directamente con un humano haciendo <a href="${configUI.whatsapp_url}" target="_blank">clic aquí</a>.`, 'bot');
         }, 1000);
      }
    }).catch(e => console.error("Error al cargar config", e));

    // Función original de conectarConAgente modificada
"""

# Reemplazamos la definición del btnAgente.addEventListener si lo hay, 
# o modificamos conectarConAgente. Lo mas seguro es parchar conectarConAgente().

pattern = r'(function conectarConAgente\(\) \{)'
replacement = r"""\1
      // --- INTERVENCIÓN MODO PILOTO ---
      if (configUI.modo_piloto && configUI.horario_habil) {
          window.open(configUI.whatsapp_url, '_blank');
          return;
      }
"""

html = re.sub(pattern, replacement, html)

# Añadir el fetch de ui_config justo después de la declaración de variables DOM
pattern_vars = r'(const chatDiv = document.getElementById\("chat"\);)'
html = re.sub(pattern_vars, patch_js + r'\n\1', html)


with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("index.html parchado exitosamente.")
