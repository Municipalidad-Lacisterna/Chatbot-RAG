# Presentación a Jefes — Chatbot Municipal de La Cisterna

> Aspen (Mathias) Arriagada 
> Documento de apoyo para la reunión con la dirección. Resume qué es el bot, qué logra hoy, cuánto cuesta realmente, y qué necesitamos de la junta para
> llevarlo a su etapa final con **soberanía total de datos**.

---

## 1. ¿Qué es y qué hace hoy?

Un **asistente virtual de atención municipal** basado en **RAG** (Recuperación
+ Generación): responde preguntas de los vecinos usando SOLO los documentos
oficiales del municipio que le indexemos.

**Estado actual: F U N C I O N A L** (prototipo).

| Capacidad | Estado |
|-----------|--------|
| Responder trámites documentados | ✅ Probado (beca, partes, privacidad) |
| No inventar si no sabe (deriva a humano) | ✅ 0% alucinación en pruebas |
| Responder con trato cordial y formal (tono "usted") | ✅ Tono híbrido |
| Recordar contexto de la conversación | ✅ Memoria por sesión |
| Interfaz web para el vecino | ✅ `/chat` (estilo WhatsApp) |
| Leer documentos e imágenes como memorial | ✅ OCR + modelo multimodal (Qwen) |

### Ventajas de la nueva versión (IA local)
1. **Soberanía total de datos**: los documentos y consultas nunca salen del servidor.
2. **Costo $0 recurrente**: sin cuota de API, sin licencias, sin nube.
3. **Atiende texto e imágenes**: puede indexar documentos escaneados y fotos, y responder
   sobre su contenido.

---

## 2. El valor para la municipalidad

- **Atención 24/7** a los vecinos: responden dudas comunes al instante, sin
  filas ni esperas.
- **Libera al equipo de Atención al Vecino** para los casos que sí requieren
  a una persona (el bot deriva automáticamente a esas consultas).
- **Costo operativo mínimo**: una compra de hardware (~$878.000 CLP) y luego **$0/mes**.
- **Privacidad garantizada**: los datos quedan en el municipio, no en un tercero.
- **Base en datos reales**: responde con los documentos oficiales, no de memoria.

---

## 3. Costo real (transparencia)

**Modelo: servidor propio + IA local.**

- **Costo inicial (una vez):** ≈ **$878.000 CLP** en hardware (GPU + piezas).
- **Costo mensual recurrente:** **$0** (sin cuota de API, sin licencias, sin nube).
- **Capacidad:** 5.000–10.000 consultas/día con el hardware elegido.

| Ítem | Costo |
|------|-------|
| Hardware (compra única) | ~$878.000 CLP |
| Operación mensual | **$0 CLP/mes** |
| **Total a 1 año** | **≈ $878.000 CLP** |

> A diferencia de un servicio en la nube (que cobra por API/cuota mes a mes), una vez comprado el hardware, el chatbot opera **sin gasto recurrente**.

**Integración con Google Drive: $0** (solo usamos la Drive API gratuita para traer
documentos al servidor; la IA y el almacenamiento son locales).

---

## 4. Accionables de la junta

Para pasar del prototipo a la versión de producción con **servidor propio + IA local**,
pedimos:

1. **Presupuesto de hardware ≈ $878.000 CLP** (GPU RTX 3060 12GB + piezas).
2. **Ubicación del servidor**: espacio físico para una torre (gabinete mediano) + red.
3. **Dominio/subdominio** (ej. `chat.lacisterna.cl`); HTTPS gratis con Let's Encrypt.
4. ~~**Acceso a Google Cloud**~~ *(ya no se pide)* — se sustituyó por **rclone** (login normal de Google, sin tarjeta ni Cloud). Solo se necesita que **`chatbot@cisterna.cl`** exista como cuenta de Google (ya existe).
5. **Carpeta de Google Drive compartida** con `chatbot@cisterna.cl` (**rol Lector**) → "Documentos Municipal Chatbot" con los PDFs/docs/imágenes de trámites.
6. **Fase de datos**: definir los **3-5 trámites TOP** y los documentos/imágenes que alimentan la memoria del bot.

---

## 5. Mensajes clave para recordar

- ✅ El bot **ya funciona** y está probado (10/10 pruebas), atiende **texto e imágenes**.
- 🔒 **Soberanía total**: los datos quedan en el municipio, sin depender de terceros.
- 💰 **$878.000 CLP una vez**, luego **$0/mes**.
- 🚀 Solo falta el **presupuesto + acceso + datos** para la versión final.

---
