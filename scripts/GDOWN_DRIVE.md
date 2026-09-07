# Sincronización de documentos del Drive con gdown (enlace público)

> **Actualización 4 de Sept 2026.** Se reemplazó **rclone** por **gdown**.

## ¿Por qué el cambio?

- **rclone** (v1.75) ahora **exige un `client_id`** propio para Google Drive. Google
  retiró el `client_id` compartido/usuario final de rclone durante 2026 (y va a
  cobrar por el embebido). Crear un `client_id` propio requiere un proyecto en
  **Google Cloud Console** con **facturación (billing)** configurada.
- La cuenta del municipio **no tiene billing** y no se puede configurar (y la
  service account también lo exige). → **rclone y service account quedan descartados.**
- **`gdown`** descarga carpetas/archivos de Drive que estén compartidos como
  **"Cualquier persona con el enlace" (público, solo lectura)**, **sin
  autorización ni billing**. Es totalmente automatizable con un timer.

## Requisito (lo que tiene que hacer la muni)

- La muni debe compartir la carpeta **`Chat bot Cisterna`** con la opción:
  **"Cualquier persona con el enlace puede ver"** (rol **Lector / Viewer**).
  Esto NO da permiso para editar; solo permite leer/descargar.
- Ese enlace tiene la forma:
  `https://drive.google.com/drive/folders/<FOLDER_ID>`
  (o simplemente el `<FOLDER_ID>`).

## Configuración (una sola vez)

1. **Conseguir el enlace público** de la carpeta (pásaselo al chat:
   `scripts/gdown_sync.sh`).
2. **Editar** `scripts/gdown_sync.sh` y poner el enlace en la variable `DRIVE_URL`:
   ```bash
   DRIVE_URL="https://drive.google.com/drive/folders/<FOLDER_ID>"
   ```
3. (Opcional) si quieres conservar copia local de los archivos, activa `BACKUP_DIR`.
4. **gdown ya está instalado** en el venv del proyecto (`venv/bin/gdown`, v6.1.1).

## Ejecutar

```bash
# Manual (una vez)
/home/aspen/Alcaldia_Practica/scripts/gdown_sync.sh

# Automático (timer de usuario, todos los días a las 07:00)
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user status gdown-sync.timer
systemctl --user start gdown-sync.service   # forzar corrida manual
```

El flujo del script:
1. `gdown --folder` descarga la carpeta **conservando subcarpetas** → `data/`
   (separa `Marco normativo/` y `Tramites/`).
2. La ingesta (`app/ingestion.py`) indexa PDF/MD/CSV en ChromaDB y **borra los
   físicos** (cada chunk queda etiquetado con su subcarpeta/categoría).

## Estado del timer (verificado)

- `gdown-sync.timer` **activo**, programado todos los días a las **07:00**
  (`OnCalendar=*-*-* 07:00:00`, `Persistent=true`).
- El antiguo `rclone-sync.timer` fue deshabilitado/removido.
- Reintento automático: 3 veces con 5 min de espera si falla (red, etc.).

## Nota sobre la descarga de carpetas

La primera vez que obtengas el enlace, ejecuta `gdown_sync.sh` **a mano** y
revisa `/tmp/gdown_sync.log` para confirmar que la estructura de subcarpetas
llegó bien a `data/`. Luego la automatización diaria sigue el mismo camino.

## Verificación

```bash
tail -20 /tmp/gdown_sync.log
# Debe terminar con: === FIN sincronización OK ===
# y haber indexado N chunks de los documentos.
```
