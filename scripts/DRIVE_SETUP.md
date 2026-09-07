# Conectar Google Drive al chatbot (Service Account)

Guía para configurar la descarga automatizada de documentos del municipio
desde Google Drive. Se usa una **Service Account** (identidad de máquina)
para que el script `scripts/drive_download.py` baje los archivos sin que
tengas que autorizar manualmente cada vez.

> **Duración total:** ~10 min (tú) + 2 min (la municipalidad, solo compartir carpeta).
> **Cuenta:** `chatbot@cisterna.cl` (Google Workspace).

---

## Resumen de roles

| Quién | Qué hace | Tiempo |
|-------|----------|--------|
| **Tú (Aspen)** | Crear proyecto Google Cloud, service account, bajar clave JSON | ~10 min |
| **Municipalidad** | Compartir la carpeta `Documentos Municipal` con el email de la service account | ~2 min |
| **Tú (Aspen)** | Correr el script de descarga + ingesta | ~2 min |

> La municipalidad **NO toca Google Cloud**. Solo comparte una carpeta en Google Drive.

---

## Paso 1 — Crear un proyecto en Google Cloud (tú)

1. Entra a https://console.cloud.google.com con la cuenta **`chatbot@cisterna.cl`**.
2. Arriba, en el selector de proyecto, pulsa **Nuevo proyecto**.
3. Nómbralo: `chatbot-lacisterna` (o similar). Pulsa **Crear**.
4. Asegúrate de tener seleccionado ese proyecto (selector arriba a la izquierda).

> ⚠️ Google Cloud requiere una **forma de pago** (tarjeta) en el proyecto para habilitar APIs, aunque la Drive API es **gratuita** (cuota de 12.000 lecturas/día). La facturación será $0 mientras solo uses Drive API.

---

## Paso 2 — Habilitar la Google Drive API (tú)

1. En el menú de la izquierda: **APIs y servicios → Biblioteca**.
2. Busca **"Google Drive API"**.
3. Selecciónala y pulsa **Habilitar**.

---

## Paso 3 — Crear la Service Account (tú)

1. Menú: **IAM y administración → Cuentas de servicio**.
2. Pulsa **Crear cuenta de servicio**:
   - Nombre: `chatbot-bot`
   - ID/email se genera solo (algo como `chatbot-bot@chatbot-lacisterna.iam.gserviceaccount.com`).
   - Rol: puedes dejar "Seleccionar un rol" (sin rol es suficiente para solo leer Drive compartido).
   - Pulsa **Crear y continuar** y luego **Listo**.
3. En la lista, haz clic sobre la cuenta creada.
4. Ve a la pestaña **Claves** → **Añadir clave** → **Crear nueva clave**.
   - Tipo: **JSON** → **Crear**.
   - Se descarga un archivo `*.json`.
5. Copia ese archivo a tu proyecto:
   ```bash
   mkdir -p config
   cp ~/Downloads/nombre-del-archivo.json config/google-drive-credentials.json
   ```
6. Anota el **email de la service account** (lo necesitas para el Paso 4).

> ⚠️ `config/` está en `.gitignore` → la credencial NUNCA se subirá a Git.

---

## Paso 4 — Compartir la carpeta con la municipalidad (ellos)

Aquí es donde **la municipalidad participa**. Ellos solo necesitan hacer UNA cosa:

1. En Google Drive (drive.google.com), abren la carpeta **`Documentos Municipal`** (o la que contenga los documentos del municipio).
2. Botón derecho → **Compartir**.
3. En "Añadir personas" pegan el **email de la service account** que anotaste en el Paso 3.
4. Rol: **Lector** (solo lectura). Pulsa **Listo**.

> 💡 **Para pedirle esto a la municipalidad**, envíales este mensaje:
>
> *"Necesito que compartan la carpeta 'Documentos Municipal' de Google Drive con esta dirección de correo: [pegar email de service account]. Solo es dar acceso de lectura (Lector). Esto es para que el chatbot pueda leer los documentos y responder consultas de los vecinos."*

> 🔑 Este es el paso clave: sin compartir la carpeta, la service account NO la ve.

---

## Paso 5 — Descargar los documentos (tú)

Con el venv activado y las credenciales en `config/`:

```bash
venv/bin/python scripts/drive_download.py --folder "Documentos Municipal"
```

Lo que hace:
- Descarga **PDFs** tal cual.
- **Exporta a PDF** Google Docs / Hojas / Presentaciones (versátil si aún
  no sabes el formato de los archivos).
- Guarda todo en `data/`.

---

## Paso 6 — Indexar en el chatbot (tú)

```bash
venv/bin/python -m app.ingestion
```

Esto convierte los PDFs de `data/` en fragmentos con embeddings y los mete
en ChromaDB. Después el bot responde con esa información.

---

## ¿Y si quiero re-descargar porque cambian los documentos?

Vuelve a correr el Paso 5. Luego, para **re-indexar un PDF completo** tras
cambios:

```bash
venv/bin/python -m app.ingestion
```

(El propio `ingestion.py` reemplaza los chunks del documento si ya existe.)

---

## Solución de problemas

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `No encontré la carpeta 'X'` | No se compartió con la service account | Repetir Paso 4 exacto con el email |
| `403 permission denied` | Rol insuficiente o carpeta no compartida | Revisar compartir (rol Lector) |
| Archivo vacío | El .json no es el de la service account | Regenerar clave en Paso 3 |
| Google Cloud pide tarjeta | La Drive API es gratis, pero Cloud requiere billing habilitado | Agregar forma de pago (no se cobra si solo usas Drive API) |

## Seguridad

- La service account solo tiene acceso a lo que **le compartas** (no a todo tu Drive).
- `config/` está ignorada por Git (no se sube la credencial).
- Si se filtra la credencial, revócala en Google Cloud (Claves → Eliminar).
- La service account **NO tiene acceso a Gmail, Calendar ni otros servicios** de `chatbot@cisterna.cl`.
