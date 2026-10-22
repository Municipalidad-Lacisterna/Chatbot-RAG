# Decisión de Tono y Presupuesto — Chatbot RAG La Cisterna

> **Contexto:** El chatbot es un prototipo de gestión de transformación digital. Prioridad: **costo $0** hoy, escalabilidad después.

---

## 1. Comparación de tonos de respuesta

Se probaron **3 estilos de system prompt** contra **10 preguntas** (7 documentadas + 3 no-documentadas). La prueba se validó con un LLM de referencia; el resultado (el diseño del tono) se aplica por igual con la IA local elegida para producción. Se mide precisión, alucinación y el score global (70% precisión + 30% anti-alucinación).

| Tono | Prom. (s) | Chars | Precisión | Alucinación | Global |
|------|-----------|-------|-----------|-------------|--------|
| **frío** | 3.2 | 99 | 79.8% | **0%** | **85.8%**  |
| balanceado | 4.7 | 169 | 79.8% | 67% | 65.8% |
| humano | 2.4 | 447 | 82.1% | 67% | 67.5% |

**Hallazgo clave:** los tonos más extensos/conversacionales (balanceado y humano) **alucinaron en el 67% de las preguntas no documentadas** — rellenan con fechas, montos y datos inventados. El tono **frío** no alucinó nunca (respondió "No tengo esa información" en las 3 no-documentadas).

---
![[Pasted image 20260902122451.png]]
## 2. Decisión: Tono HÍBRIDO

**Motivo del híbrido:** usar el tono **frío** puro puede sonar frío/descortés al vecino; usar el **balanceado/humano** arriesga alucinaciones costosas.

**Solución adoptada** (en `app/rag_engine.py`):
- **Rostro cordial** del tono balanceado (saludo "Estimado vecino", trato de "usted", 1-3 frases, 1 solo bloque).
- **Regla anti-alucinación del modo frío** reforzada en el system prompt:
  > "Si la información NO está en el contexto o no la sabes, NO inventes NADA... Marca 'encontrado': false. No rellenes con fechas, montos, plazos ni datos que no aparezcan literalmente en el contexto."
- **Cierre rápido por código**: si `encontrado=false`, se devuelve automáticamente el mensaje de fallo con derivación (teléfono + email + oficina), SIN pasar por el LLM.

**Verificación exitosa:**
- Pregunta documentada ("requisitos beca") → respuesta cordial y correcta.
- Pregunta no documentada ("renovar licencia") → **1.6s**, no alucinó, derivó a Atención al Vecino.

---

## 3. Motor de IA: local (sin nube)

- La comparación de tonos se hizo con un modelo de referencia. En producción, el motor
  es **Qwen2.5-VL-7B** corriendo **local** en el servidor del municipio (Ollama).
- **El tono híbrido es independiente del modelo**: el system prompt y las reglas
  anti-alucinación viven en `app/rag_engine.py` y se aplican igual con IA local.
- **Ventaja:** costo $0 recurrente, soberanía total (nada sale del servidor).

> El modelo exacto puede ajustarse al migrar a local; el comportamiento (tono híbrido,
> anti-alucinación, cierre rápido) se mantiene por diseño, no por el modelo elegido.
---

## 4. Presupuesto (servidor propio + IA local)

**Modelo de costo:** compra única de hardware + $0 recurrente. La IA corre **local** en el
servidor del municipio (no se paga por consulta, token ni mensaje).

| Ítem | Costo |
|------|-------|
| Hardware (GPU RTX 3060 12GB + piezas, compra única) | ≈ **$878.000 CLP** |
| Operación mensual (energía + mantenimiento) | **$0** de servicio |
| **Total a 1 año** | **≈ $878.000 CLP** |

> **Por qué no hay costo por consulta:** a diferencia de una API en la nube (que cobra por
> token), el modelo local usa solo la GPU del servidor. El volumen objetivo de
> **5.000–10.000 consultas/día** queda cubierto por el hardware sin gasto recurrente.

### Volumen real por persona (evidencia)
El volumen esperado de consultas por vecino es bajo y ya documentado:

> Estudio de referencia (Følstad & Bjerkreim-Hanssen, 2023) sobre **2.663 diálogos** de
> chatbots de **6 municipios**:
> - **77% de los diálogos = 1 sola pregunta** del usuario.
> - **15% = 2 preguntas**.
> - **8% = 3 o más preguntas**.

Promedio real de **~1-2 preguntas por persona**. El hardware elegido cubre con holgura
miles de consultas diarias sin costo variable.

---

## 5. Reglas de diseño para respuestas de calidad

Estas 3 reglas guían el comportamiento del chatbot para dar respuestas **útiles y
seguras** (independientes del costo de un canal). Nacen del análisis de tono de la
sección 2 y protegen tanto la calidad como el buen uso del modelo.

### Regla 1 — Un solo mensaje por consulta
El bot **consolida toda la respuesta en un único mensaje** de texto claro y ordenado,
en lugar de trocear la información en varios fragmentos. Facilita la lectura del vecino y
evita cadenas innecesarias.

### Regla 2 — Atención reactiva, no difusión masiva
El bot está diseñado para **responder cuando el vecino pregunta** (bajo demanda). Se evita
el envío proactivo de avisos masivos. El foco está en atender consultas reales, sin saturar.

### Regla 3 — Cierre rápido cuando no hay respuesta
Cuando el RAG **no encuentra** la información en los documentos, el bot **no inventa**
(evita alucinaciones). **Cierra rápido:** emite un mensaje breve de no-encontrado y
**deriva al vecino a un canal humano** (teléfono, email u oficina municipal). De esta forma
no se generan respuestas falsas ni consultas sin resolver.

> **En una frase:** el bot responde con datos reales de los documentos, en un solo mensaje,
> sin alucinar y derivando a una persona cuando no sabe. Eso también hace un uso eficiente
> del modelo.

---

## 6. Integración con Google Drive (obtención de documentos)

Para alimentar al bot con **documentos reales del municipio**, se preparó una carga automatizada desde Google Drive vía **rclone** (login normal de Google, sin Google Cloud ni tarjeta). Ver [[pivote_rclone]].

### Precio: $0

| Concepto | Costo |
|----------|-------|
| rclone (herramienta open source) | **$0** |
| Google Drive (cuenta normal `chatbot@cisterna.cl`) | **$0** |
| Descarga / exportación de documentos del Drive | **$0** |
| Chatbot RAG (IA local, servidor propio) | **$0** recurrente |

> **No hay ningún costo.** La limitante no es económica sino de **acceso**:
> necesitamos que la municipalidad **comparta la carpeta** `Documentos Municipal`
> con `chatbot@cisterna.cl` (rol Lector) y que el login de rclone se complete.

### Contexto del acceso

- **No se necesita Google Cloud ni tarjeta de pago.**
- Se usa **rclone** con el **login normal de Google** (`chatbot@cisterna.cl`):
  autentica una vez en el navegador y queda listo para automatizar.
- La municipalidad **solo comparte la carpeta** de Drive con rol **Lector**
  (sin tocar Google Cloud).

### Proceso completo (paso a paso)

**Fase A — Configurar rclone** (una sola vez, en la laptop con navegador)

1. Instalar rclone y ejecutar `rclone config`.
2. Crear el remote `gdrive` (storage `drive`), `auto config y` → se abre el
   navegador → login con **`chatbot@cisterna.cl`** → autorizar.
3. Verificar que ve la carpeta: `rclone lsd gdrive:`.

**Fase B — Compartir la carpeta de Drive**

4. En Google Drive, la municipalidad crea/comparte la carpeta
   **`Documentos Municipal`** con los PDFs (o Docs/Hojas) del municipio.
5. Compartirla con **`chatbot@cisterna.cl`** en rol **Lector**.
   > Sin este paso, rclone no puede ver la carpeta.

**Fase C — Sincronizar e indexar**

6. Descargar los documentos (automatizado con timer diario a las 07:00):
   ```bash
   scripts/rclone_sync.sh
   ```
   (rclone baja Drive → `data/` → `app.ingestion` indexa en ChromaDB).
7. Ver el log: `tail /tmp/rclone_sync.log`.

> **Detalle:** ️ la ingesta **borra los PDFs físicos de `data/`** tras indexar
> (el conocimiento queda en ChromaDB). Usa el `BACKUP_DIR` del script si quieres
> conservar copia local.

### Documentos a priorizar

- Con los chats de WhatsApp analizados (`scripts/analizar_chats.py`) se
  obtiene el ranking de **preguntas frecuentes reales**.
- Se priorizan los **3-5 trámites TOP** (los más consultados) como documentos
  de arranque. Calidad y cobertura > cantidad: top-k=2 limita la utilidad de
  demasiados documentos.

### Archivos relacionados
- `scripts/rclone_sync.sh` — sincronizador rclone (baja Drive → indexa).
- `scripts/RCLONE_DRIVE.md` — guía de configuración de rclone.
- `scripts/analizar_chats.py` — análisis de chats para detectar FAQs.
- (`scripts/drive_download.py` — descargador por service account, **en desuso** tras el pivote a rclone).

---
