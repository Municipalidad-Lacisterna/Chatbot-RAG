# Sincronización automática de Google Drive con rclone

El chatbot baja automáticamente los documentos del municipio desde Google Drive
y los indexa en ChromaDB **todos los días a las 07:00** (via systemd timer).

> Sin necesidad de Google Cloud Console ni tarjeta de facturación: rclone usa
> el **login normal de Google** (`chatbot@cisterna.cl`), como cuando entras a Gmail.

---

## 1. Qué permisos pedirle al municipio (para compartir la carpeta)

Que compartan la carpeta **`Documentos Municipal`** (o el nombre que sea)
con la cuenta **`chatbot@cisterna.cl`** y el rol **Lector (Viewer)**.

- ✅ **Lector** es suficiente: rclone solo necesita LEER/descargar los PDFs.
- No hace falta rol de editor ni comentarista.

---

## 2. Configurar rclone (UNA sola vez, tú con tu cuenta + navegador)

En la laptop, abrir terminal y ejecutar:

```bash
rclone config
```

Dentro de rclone:

1. Pulsa `n` → **new remote**.
2. name: escribe `gdrive`  (importante: el script espera este nombre).
3. Storage: escribe `drive` y Enter.
4. Client ID/Secret: deja vacío y Enter (usa el default de rclone).
5. Scope: déjalo en `drive` (lectura/escritura a tus archivos) o `drive.readonly` (solo lectura, más seguro). Enter.
6. Service account file: déjalo vacío (Enter).
7. Edit advanced config: `n` (no).
8. **Auto config: `y`** → se abre el navegador, inicias sesión con
   `chatbot@cisterna.cl` y autorizas.
9. Credenciales: `n`.
10. Confirmas que es correcto con `y`.

Al final verás `Current remotes: gdrive`. Listo.

Comprobar que ve la carpeta:
```bash
rclone lsd "gdrive:"
# debería listar la(s) carpeta(s) compartida(s), ej: "Documentos Municipal"
```

---

## 3. Verificar la sincronización manual (opcional)

```bash
scripts/rclone_sync.sh
# baja Drive → data/ → indexa en ChromaDB
tail -20 /tmp/rclone_sync.log
```

O solo descargar (sin indexar):
```bash
rclone copy "gdrive:Documentos Municipal" data/ --create-empty-src-dirs
```

---

## 4. Ver el estado del timer (corre solo a las 07:00)

```bash
systemctl --user list-timers rclone-sync.timer
systemctl --user status rclone-sync.service   # ver la última corrida
tail -50 /tmp/rclone_sync.log                  # log de las corridas
```

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `scripts/rclone_sync.sh` | Script que descarga + indexa |
| `~/.config/systemd/user/rclone-sync.service` | Servicio oneshot del script |
| `~/.config/systemd/user/rclone-sync.timer` | Programador diario 07:00 |
| `~/.config/rclone/rclone.conf` | Config/credencial de rclone (se crea al configurar) |
| `/tmp/rclone_sync.log` | Log de cada corrida |

---

## NOTA importante (borrado de originales)

`ingestion.py` **borra los PDFs de `data/`** tras indexarlos (el conocimiento
queda en ChromaDB, no en los archivos). Si quieres conservar copia local de
los PDFs, define `BACKUP_DIR` dentro de `scripts/rclone_sync.sh` con la ruta
donde guardarlos (ej: `/home/aspen/Alcaldia_Practica/data_backup`).
