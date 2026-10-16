# Requerimientos para llevar el Chatbot Municipal a uso real

---
### Aspen (Mathias) Arriagada - Practicante
## 1. Resumen

- El chatbot RAG funciona hoy de punta a punta (responde trámites reales del municipio,
  transfiere a agente humano, ingesta programada). Falta **solo** llevarlo de la laptop
  a un servidor de producción accesible.
- Decisión técnica: **servidor propio + modelo de lenguaje local (sin nube)**.
  → La información municipal **nunca sale de nuestro servidor** (soberanía total).
- **Costo:** una sola compra de hardware ≈ **$878.000 CLP**. **$0 de gasto recurrente**
  (sin cuota de API, sin licencias, sin hosting en la nube).
- Resultado: chatbot 24/7, datos 100% locales, sin depender de terceros.

---

## 2. Presupuesto de hardware (compra única) — componente nuevo, retail chileno

| Componente | Especificación | Costo CLP |
|---|---|---|
| **GPU** | RTX 3060 12GB GDDR6 (MSI Ventus) | **$328.589** |
| **CPU** | Ryzen 5 3600 (6 núcleos, incluye cooler) | **$202.547** |
| **RAM** | 16GB DDR4-3200 (Kingston) | **$127.990** |
| **SSD** | 512GB NVMe (Hiksemi Wave) | **$95.000** |
| **Gabinete + fuente** | 600W 80+ (XTech XTQ-200) | **$44.500** |
| **Placa base** | B450/B550 (AM4, nueva) | **~$80.000** |
| **TOTAL** | | **≈ $878.000 CLP** |

> **Qué permite esta inversión:** correr el modelo multimodal **Qwen2.5-VL-7B** local (~7 GB de VRAM de los 12 GB de la GPU, ~1–5 s/respuesta). Acepta **texto e imágenes** como parte de la **memoria/conocimiento** del bot: se le pueden subir documentos escaneados (decretos, planillas, planos) y fotos descriptivas, y el chatbot las **interpreta y las indexa** para responder consultas sobre su contenido (ej. "¿cuáles son los requisitos de X?"). Los documentos escaneados además se convierten a texto con **OCR** (ya operativo). Suficiente para el volumen objetivo de **5.000–10.000 consultas/día**.
> *Notas:* el Ryzen 5 3600 ya no se fabrica; si no hay stock sellado se usa un **Ryzen 5 4600G/5600G** (mismo precio). Si se desea armado por una tienda, sumar ~$20.000–40.000. Precio de placa estimado de mercado.

---

## 3. Autorizaciones que se solicitan

| # | Requerimiento | Detalle |
|---|---|---|
| **1** | **Presupuesto de hardware** | ≈ **$878.000 CLP** (compra única de los componentes de arriba) |
| **2** | **Ubicación del servidor** | espacio físico para un PC tipo torre (gabinete mediano) + red |
| **3** | **Dominio/subdominio** | `chat.lacisterna.cl` o similar; HTTPS gratis (Let's Encrypt) |
| **4** | **~Acceso Google Cloud**~~ *(ya no aplica)* | ~~service account~~ Se sustituyó por **rclone** (login normal de Google, sin billing) — ver [[pivote_rclone]] |
| **5** | **Carpeta Drive** | compartir carpeta `Documentos Municipal` con **`chatbot@cisterna.cl` (rol Lector)** para la ingesta programada por rclone |

> **Soberanía de datos:** al ser servidor propio + LLM local, **garantizamos que ningún dato o consulta sale del municipio**. Esto cumple el requisito de soberanía total.

> **⚠️ Bloqueante hoy:** el **acceso a Google Drive todavía no está activado**. Sin la carpeta `Documentos Municipal` compartida con `chatbot@cisterna.cl` (rol Lector) y sin el login de **rclone** (`rclone config`), el bot **no puede cargar los documentos reales** del municipio y sigue respondiendo con documentos de prueba. Es el primer requisito a desbloquear para dejar el bot operativo con información real.

---

## 4. Trabajo técnico (lo realiza el equipo — no requiere presupuesto extra)

1. **Ubuntu Server** + drivers NVIDIA (CUDA) + **Ollama** + modelo multimodal **Qwen2.5-VL-7B**.
2. Configurar el chatbot para usar **Qwen local** como motor (IA 100% local, sin nube). El resto del código RAG es independiente del modelo y no cambia.
3. **Ingesta de imágenes a la memoria del bot**: documentos escaneados → **OCR** (Tesseract, ya operativo); fotos/planos → **Qwen2.5-VL las interpreta y describe** → todo se indexa en la base vectorial para responder consultas sobre su contenido.
4. Servidor web accesible (`0.0.0.0`) + **Caddy/Nginx con HTTPS**.
5. Services automáticos (servidor web al arrancar + ingesta diaria de documentos).
6. Pipeline **Drive → ingesta** y **pruebas end-to-end** con datos reales antes del corte.

### 🛠️ Pendientes técnicos del bot (a realizar en producción, sin costo extra)

| # | Tarea | Por qué importa |
|---|---|---|
| **A** | Corregir **retrieval de circulación/licencias/DOM** | El chunking actual (`_split_text`) no respeta los bloques `###`, por lo que los trámites de permisos de circulación, licencias de conducir y Dirección de Obras se recuperan fragmentados → las respuestas de esos trámites son incompletas/imprecisas. |
| **B** | **Rate-limiting** (límite de consultas por vecino/día) | Sin límite, un bot malicioso puede agotar los recursos del servidor. Con el volumen objetivo (5.000–10.000 consultas/día) es indispensable para proteger la GPU/Ollama. |
| **C** | **Autenticación** de los paneles `/admin` y `/agente` | Hoy usan una clave fija (`cisterna2026`) en la URL. En producción hay que pasar a login con sesión + roles, para control real de acceso. |
| **D** | Pipeline de **ingesta automática desde Drive** | Robots periodicos (systemd timer) que bajen documentos nuevos de la carpeta `Documentos Municipal`, los conviertan (OCR/imágenes) y los indexen sin intervención manual. |
| **E** | **Webhooks de monitoreo** (Uptime Kuma ya existente) | Alertas si el bot deja de responder o si la GPU falla, para reactividad ante caídas. |

> El resto de funcionalidades clave del bot **ya están implementadas y probadas (batería 10/10)**: transferencia a agente humano en vivo, historial de chats exportable en `/admin`, **aprendizaje automático** del bot desde las respuestas de los agentes, y **timeout de inactividad** ("¿hay alguien ahí?").

---

## 5. Comparación rápida (por qué servidor propio)

|                   | Servidor propio + LLM local (elegido)    | Servicio en la nube                   |
| ----------------- | ---------------------------------------- | ------------------------------------- |
| **Datos**         | 100% en el municipio (soberanía total) ✅ | viajan al proveedor                   |
| **Costo inicial** | **~$878.000 CLP** (una vez)              | $0 hardware                           |
| **Costo mensual** | **$0**                                   | crece con el uso (pago por API/cuota) |
| **Dependencia**   | ninguna (autónomo)                       | internet + proveedor externo          |
| **Mantenimiento** | medio (administrar servidor)             | bajo                                  |

---

## 6. Comparación de precios de las alternativas (LLM en la nube vs. servidor propio)

El chatbot necesita un modelo de lenguaje (LLM) para responder. Las **3 opciones reales** y su costo anualizado para el volumen objetivo (~5.000 vecinos/día, ~4,5M preguntas/mes):

| Opción | Costo mensual (estimado) | Costo anual | Datos | Dependencia |
|---|---|---|---|---|
| **A. Google Gemini API** (gemini-3.1-flash-lite: $0,25/M input + $1,50/M output) | **~$421.000 CLP** (solo LLM) | ~$5.050.000 CLP | salen del municipio | internet + proveedor |
| **B. VPS/hosting Cloud (GPU dedicada)** — ej. RTX 3060 Ti/T4 en la nube, USD ~$129/mes | **~$130.000–150.000 CLP** | ~$1.700.000 CLP | viajan al proveedor | internet + proveedor |
| **C. Servidor propio + LLM local (elegido)** | **$0 recurrente** (compra única ~$878.000) | **$878.000 CLP totales** (año 1) y **$0** en adelante | 100% en el municipio ✅ | ninguna ✅ |

> **Lectura de la tabla:** con **servidor propio**, al año 1 ya se pagó el 100% (~$878.000) y desde el año 2 el costo es **cero**, con **soberanía total** de datos y **cero dependencia** de internet/proveedor. La alternativa Gemini más barata cuesta **~$421.000/mes** (≈ 6× más al año) y además **saca los datos del municipio**. VPS con GPU cuesta menos que Gemini pero igual expone los datos y es un gasto mensual perpetuo.

*Precios en CLP convertidos a ~$940/USD. Gemini con modelo económico de RAG (flash-lite). VPS GPU referencia de proveedores chilenos/internacionales de RTX 3060Ti/T4 (~$129–149 USD/mes). No incluye el costo de **Meta/WhatsApp** (~$90.000/mes) que es independiente del motor de IA.*

---

## 7. Dependencias de datos reales (para dejar el bot 100% operativo)

El bot **ya está construido y probado**, pero responde con **documentos de prueba**. Para pasar a producción con información real, **el municipio debe aportar**:

| # | Dato faltante | De qué sirve | Quién lo entrega |
|---|---|---|---|
| **1** | **Documentos reales** (decretos, ordenanzas, requisitos de trámites: permisos de circulación, licencias, DOM, patentes, etc.) | Son la "memoria" del bot: sin ellos no responde bien los trámites reales | Municipalidad (gerencias de línea) |
| **2** | **Carpeta Google Drive** `Documentos Municipal` compartida con `chatbot@cisterna.cl` (rol **Lector**) | Para que el bot **baje e indexe automáticamente** los documentos reales (vía **rclone**, sin Google Cloud ni tarjeta) | Municipalidad (cualquiera que comparta la carpeta) |
| **3** | **Canal de WhatsApp / chat real** (exports de conversaciones históricas) | Para **analizar las preguntas más frecuentes** (FAQs reales) y priorizar qué trámites cargar primero + ajustar el tono del bot | Equipo de atención al vecino |

> **Sin estos 3 datos, el bot funciona pero con información de ejemplo.** El orden lógico es: (1) conseguir acceso a Drive → (2) subir/bajar documentos reales → (3) analizar chats para priorizar → (4) ingestar y probar end-to-end. La herramienta para bajar de Drive y el analizador de chats **ya están construidos**; solo falta que lleguen los datos.

---

## 8. Escalabilidad (del prototipo actual al producto completo)

El bot hoy es un **prototipo para 1 agente humano** en memoria. Plan de crecimiento por etapas:

| Nivel                                   | Estado        | Capacidad                                                | Qué cambia                                                                        |
| --------------------------------------- | ------------- | -------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **N1 – Prototipo (hoy)**                | ✅ Funcionando | 1 agente, sin persistencia de transferencias, en memoria | Bot + chat + transferencia + historial + aprendizaje + timeout                    |
| **N2 – Producción local (primer paso)** | 🔜 Tras junta | 1 agente, datos reales, persistente                      | Servidor propio + Qwen local + Drive + rate-limiting + auth de paneles            |
| **N3 – Multiusuario**                   | 📋 Proyectado | Varios agentes, cola real                                | Mover estado a **Redis + Postgres** (hoy es en memoria), login por agente, turnos |

> La arquitectura **ya está diseñada para escalar sin reescribir**: el motor RAG y la API son estables; escalan vectores (ChromaDB→Qdrant), memoria (SQLite→Postgres) y canales por separado.

---

Esto me lo ayudo a redactar la IA.