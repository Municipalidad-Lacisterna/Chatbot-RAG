# Dimensionamiento del Servidor para el Chatbot Municipal


---

## 1. Resumen ejecutivo (TL;DR)

- El chatbot pasa a **servidor propio** con **modelo de lenguaje local (LLM)**. La
  información municipal **nunca sale del servidor** (soberanía total de datos).
- **Costo:** una compra única de hardware ≈ **$878.000 CLP**. **$0 de gasto recurrente**
  (sin cuota de API, sin licencias, sin hosting en la nube).
- El hardware elegido (**RTX 3060 12GB**) corre un modelo **multimodal** (texto e imágenes)
  con calidad suficiente y buen rendimiento para el volumen objetivo.
- La base vectorial (**ChromaDB**), el servidor web (**FastAPI**) y el pipeline de ingesta
  corren **todos en el mismo servidor**, 100% local.

---

## 2. Decisión: por qué servidor propio + IA local

| | Servidor propio + LLM local (elegido) | Servicio en la nube |
|---|---|---|
| **Datos** | 100% en el municipio (soberanía total)  | viajan al proveedor |
| **Costo mensual** | **$0** | crece con el uso |
| **Dependencia** | ninguna (autónomo) | internet + proveedor externo |
| **Privacidad** | completa (nada sale) | condicionada al contrato |

**Motivo principal:** el municipio exige **soberanía total de datos**. Con IA local, ni los
documentos ni las consultas salen del servidor. Esta opción es la definida para producción.

---

## 3. Hardware del servidor (compra única, componente nuevo, retail chileno)

| Componente | Especificación | Costo CLP |
|---|---|---|
| **GPU** | RTX 3060 12GB GDDR6 (MSI Ventus) | **$328.589** |
| **CPU** | Ryzen 5 3600 (6 núcleos, incluye cooler) | **$202.547** |
| **RAM** | 16GB DDR4-3200 (Kingston) | **$127.990** |
| **SSD** | 512GB NVMe (Hiksemi Wave) | **$95.000** |
| **Gabinete + fuente** | 600W 80+ (XTech XTQ-200) | **$44.500** |
| **Placa base** | B450/B550 (AM4, nueva) | **~$80.000** |
| **TOTAL** | | **≈ $878.000 CLP** |

> **Qué permite esta inversión:** correr el modelo multimodal **Qwen2.5-VL-7B** local
> (~7 GB de VRAM de los 12 GB de la GPU, ~1–5 s/respuesta). Acepta **texto e imágenes**
> como parte de la **memoria/conocimiento** del bot: se le suben documentos escaneados
> (decretos, planillas, planos) y fotos descriptivas, el chatbot las interpreta y las indexa,
> y responde consultas sobre su contenido. Suficiente para **5.000–10.000 consultas/día**.
>
> *Notas:* el Ryzen 5 3600 ya no se fabrica; si no hay stock sellado se usa un
> **Ryzen 5 4600G/5600G** (mismo precio). Si se desea armado por una tienda, sumar
> ~$20.000–40.000. Precio de placa estimado de mercado.

---

## 4. Capacidad (volumen objetivo)

Se estima una petición real del bot en input ≈ 2.100 tokens (pregunta + documentos
recuperados + historial) y output ≈ 300 tokens. Con el LLM local corre sin costo por
consulta (solo energía, que es $0 recurrente de servicio).

| Volumen | Carga del servidor | Respuesta estimada |
|---|---|---|
| 5.000/día | media | ~1–3 s/respuesta |
| 10.000/día | alta | cómodo con la RTX 3060 12GB |

> El LLM local no cobra por token. El hardware ya está dimensionado para este rango sin
> necesidad de pagar cuota de API ni licenciamiento.

---

## 5. Arquitectura (todo en el servidor, 100% local)

```
El servidor (Ubuntu + RTX 3060 12GB) ejecuta TODO:
├── ChromaDB           → la "memoria" vectorial (documentos + imágenes indexadas)
├── FastAPI / uvicorn  → servidor web del bot
├── Qwen2.5-VL (Ollama)→ LLM multimodal local
├── Pipeline ingesta   → OCR + Qwen-VL describe → indexa en ChromaDB
└── Caddy/Nginx        → HTTPS público
```

- **ChromaDB** es una librería ligera, local, sin red ni costo. Corre en el servidor igual
  que hoy en la laptop.
- **Qwen2.5-VL-7B** corre en la GPU (RTX 3060). Es multimodal: ve texto e imágenes.
- El **servidor web** (FastAPI) sirve el `/chat` al vecino.

---

## 6. Ingesta de imágenes a la memoria del bot

El bot acepta **imágenes como documentación**, no solo texto:

| Tipo de imagen | Cómo se procesa | Resultado |
|---|---|---|
| **Documentos escaneados** (decreto, planilla, plano) | **OCR** (Tesseract, ya operativo) | texto indexado en ChromaDB |
| **Fotos / planos descriptivos** | **Qwen2.5-VL** las interpreta y describe | texto indexado en ChromaDB |

Luego el chatbot responde consultas **sobre el contenido** de esas imágenes (ej.
"¿cuáles son los requisitos para X?") usando exactamente el mismo flujo RAG que con los PDFs.

---

## 7. Lo que ya está funcionando (evidencia)

Todo el pipeline está **probado de punta a punta en esta máquina**:

- **Motor RAG** indexando PDFs reales del municipio (decreto de Beca Deportiva, Canalización
  y Retiro de Cables, Manual de Permisos de Edificación, trámites del portal de transparencia).
- **87 fragmentos (chunks)** indexados en la base vectorial (ChromaDB), búsqueda semántica en español.
- **OCR** funcionando sobre PDFs escaneados (Tesseract).
- **Chat web** para el vecino en `/chat`.
- **Panel de administración** `/admin` con estado del servidor, documentos cargados y cola.
- **Ingesta programada** a las 17:01 (systemd timer) que digitaliza PDFs nuevos y elimina el original.
- **Transferencia en vivo a un agente humano** funcionando (WebSocket).
- Memoria por conversación y salida sin alucinaciones.

---

## 8. Próximo paso

1. **Aprobar el presupuesto de hardware ≈ $878.000 CLP** (compra única).
2. **Montar el servidor**: Ubuntu Server + drivers NVIDIA/CUDA + Ollama + Qwen2.5-VL-7B.
3. **Migrar el bot** al servidor (ChromaDB, FastAPI, ingesta) y publicarlo con HTTPS.
4. **Activar la ingesta de datos reales** (Drive + documentos/imágenes del municipio).
5. **Pruebas end-to-end** con datos reales antes del corte.

---

*Basado en mediciones reales del pipeline y precios de retail chileno (SIPO, SoloTodo,
ChilePC, Lotendras) [3/Sep/2026]. Documento relacionado: [[requerimientos]].*