# Pivote: Google Drive con rclone (sin Google Cloud)

> **Fecha:** 4 de Septiembre de 2026
> **Decisión:** sustituir la **service account + Google Cloud Console** por
> **rclone** (login normal de Google) para bajar los documentos del municipio.

## Contexto

El plan original era crear una **service account** en Google Cloud Console para
que el servidor del bot descargara automáticamente los documentos de la carpeta
`Documentos Municipal` (ver [[decision_tono_y_presupuesto]] y [[requerimientos]]).

**Problema encontrado:** al intentar crear el proyecto en Google Cloud Console
(con `chatbot@cisterna.cl`), Google devuelve:

> *"no se pudo completar la configuración de facturación"*

Google Cloud **exige una forma de pago (tarjeta)** para crear un proyecto,
aunque la Google Drive API sea gratuita. Sin tarjeta no se crea el proyecto, y
por tanto no se puede crear la service account. Esto bloquea toda la vía de la
service account.

## La decisión: **rclone**

**rclone** resuelve el mismo problema (descargar documentos del Drive
municipal) **sin Google Cloud, sin billing y sin tarjeta**:

- Usa el **login normal de Google** (`chatbot@cisterna.cl`), igual que entrar
  a Gmail o Drive.
- Una vez autenticado, guarda el token localmente y puede automatizarse
  (timer diario a las 07:00).
- Es el estándar de facto para sincronizar con Drive.

### Comparación

| | Service Account (descartado) | **rclone** (elegido) |
|---|---|---|
| Requiere Google Cloud Console | Sí | **No** |
| Requiere tarjeta de pago (billing) | Sí (bloqueante) | **No** |
| Login | Cuenta de máquina | **Login normal `chatbot@cisterna.cl`** |
| Automatizable | Sí | **Sí** (token local) |
| Permisos que pide a la muni | Compartir carpeta con email service account | Compartir carpeta con **Lector** a `chatbot@cisterna.cl` |

## Cómo quedó implementado

Flujo (se ejecuta a las **07:00** diarias vía timer de systemd de usuario):

```
rclone copy "gdrive:Documentos Municipal" → data/
venv/bin/python -m app.ingestion   (indexa en ChromaDB)
```

- **Script:** `scripts/rclone_sync.sh`
- **Servicio:** `~/.config/systemd/user/rclone-sync.service`
- **Timer:** `~/.config/systemd/user/rclone-sync.timer` → diario 07:00
- **Log:** `/tmp/rclone_sync.log`
- **Guía de configuración:** `scripts/RCLONE_DRIVE.md`

### Permisos que necesita la municipalidad

Solo **una cosa**: compartir la carpeta `Documentos Municipal` con
`chatbot@cisterna.cl` en rol **Lector (Viewer)**. Nada de Google Cloud, nada
técnico. (Ver [[requerimientos]] §7.)

## Estatus

- ✅ rclone instalado (`v1.75.0`), timer de systemd activo (corre 07:00).
- ⏳ **Pendiente (paso interactivo de Aspen):** `rclone config` → login con
  `chatbot@cisterna.cl` en el navegador. Sin esto rclone no tiene cuenta/carpeta.
- ⏳ Pendiente: que la muni comparta la carpeta con rol Lector.

## Archivos descartados / en desuso

- `scripts/drive_download.py` (service account) — se mantiene en el repo pero
  **ya no es la vía** de descarga; se reemplaza por rclone.

## Enlaces relacionados

- [[requerimientos]] — dependencias de datos reales (§7)
- [[decision_tono_y_presupuesto]] — contexto de presupuesto (integración Drive)
- [[codigo_arquitectura]] — arquitectura y archivos
- `scripts/RCLONE_DRIVE.md` — guía operativa de rclone
