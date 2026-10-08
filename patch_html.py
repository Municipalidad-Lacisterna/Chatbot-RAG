import sys

with open("static/admin.html", "r") as f:
    html = f.read()

# Buscar donde dice Sincronización y agregar botones
if 'class="section"' in html:
    # Insertar en la primera seccion (Sistema) o justo debajo de ella
    pass

# Lo mas facil es inyectar una seccion nueva
seccion_drive = """
  <div class="section">
    <h2>Sincronización con Google Drive</h2>
    <div style="margin-bottom:10px;">
      <button class="btn" onclick="revisarDrive()">🔍 ¿Qué hay de nuevo?</button>
      <button class="btn acc" onclick="sincronizarDrive()">📥 Sincronizar Drive</button>
    </div>
    <div id="log-sync" class="msg" style="font-family: monospace; white-space: pre-wrap;">Esperando acción...</div>
  </div>
"""

# Reemplazar la funcion sincronizarDrive original y agregar revisarDrive
js_viejo = """async function sincronizarDrive() {
      if (!CLAVE) return;
      document.getElementById('log-sync').textContent = "Iniciando sincronización en background...";
      try {
        await fetch('/admin_sync_drive?clave=' + CLAVE, { method: 'POST' });
        setTimeout(verEstadoSync, 2000);
      } catch (e) {
        document.getElementById('log-sync').textContent = "Error al iniciar sincronización.";
      }
    }"""

js_nuevo = """
    async function revisarDrive() {
      if (!CLAVE) return;
      const log = document.getElementById('log-sync');
      log.textContent = "Revisando Drive (puede demorar unos segundos)...";
      try {
        const r = await fetch('/admin_check_drive?clave=' + CLAVE, { method: 'POST' });
        const d = await r.json();
        if (d.ok) {
          let msg = `En Drive: ${d.en_drive} archivos\\nYa indexados: ${d.ya_indexados}\\nNuevos por descargar: ${d.nuevos_count}\\n`;
          if (d.nuevos_count > 0) {
            msg += "\\n--- Archivos Nuevos ---\\n" + d.nuevos.join("\\n");
          }
          log.textContent = msg;
        } else {
          log.textContent = "Error: " + (d.error || JSON.stringify(d));
        }
      } catch (e) {
        log.textContent = "Error de red al revisar Drive.";
      }
    }

    async function sincronizarDrive() {
      if (!CLAVE) return;
      document.getElementById('log-sync').textContent = "Iniciando sincronización en background...";
      try {
        await fetch('/admin_sync_drive?clave=' + CLAVE, { method: 'POST' });
        setTimeout(verEstadoSync, 2000);
      } catch (e) {
        document.getElementById('log-sync').textContent = "Error al iniciar sincronización.";
      }
    }
"""

# Inyectar seccion justo antes de "<!-- SEGUNDA COLUMNA -->" o al final de "<!-- PRIMERA COLUMNA -->"
html = html.replace('<!-- ================= PRIMERA COLUMNA ================= -->',
                    '<!-- ================= PRIMERA COLUMNA ================= -->\n' + seccion_drive)

html = html.replace(js_viejo, js_nuevo)

with open("static/admin.html", "w") as f:
    f.write(html)
