# Chatbot Municipal (Transparencia)

---

## 1. Resumen del bot

Para que el chatbot responda con información **real y actualizada** del municipio,
basta con **subir los documentos a una carpeta de Google Drive** que estará
compartida con el sistema. Todo lo demás (leer, procesar y actualizar la memoria del bot) ocurre **solo y sin costo**.

---

## 2. Así funciona (flujo para transparencia)

```
  [1] Usted sube un documento a la carpeta
       de Drive compartida ("Documentos Municipal chatbot")
                     │
                     ▼
  [2] El sistema lo descarga automáticamente
      (vía una identidad técnica de Google)
                     │
                     ▼
  [3] Un proceso programado (todos los días a las 17:01)
      lo lee, lo "digitaliza" y lo agrega a la memoria del chatbot
                     │
                     ▼
  [4] El chatbot ya responde con esa información
```

**Lo único que tiene que hacer usted:** subir (o reemplazar) el documento en la carpeta de Drive. **No tiene que avisar ni pedir nada** — el sistema lo recoge solo.

---

## 3. Qué documentos conviene subir

Sumamos al chatbot todo documento **público y consultable** que los vecinos pregunten con frecuencia. En orden de utilidad:

| Prioridad | Tipo de documento | Ejemplos |
|---|---|---|
| Alta | Trámites y requisitos | Permisos de circulación, licencias de conducir, patentes, becas (deportiva, educación superior), retiro de escombros, certificados |
| Alta | Ordenanzas y decretos | Ordenanza de Aseo y Ornato, Reglamento de Beca Deportiva |
| Media | Formularios y manuales | Manual de Permisos de Edificación, formularios de postulación |
| Media | Contactos y horarios | Dónde y cuándo se realiza cada trámite |

**Formatos aceptados:** PDF (recomendado), y también documentos de Google
(Google Docs, Hojas, Presentaciones) — el sistema los convierte solo a PDF.

> 💡 **Regla de oro:** si el vecino puede preguntarlo, súbalo. Si el documento **cambia** (nuevo valor, nuevo plazo, nueva dirección), **reemplace el archivo** en la carpeta y el chatbot quedará actualizado al día siguiente (17:01).

---

## 4. Costo: $0

El sistema completo opera **sin costo de licencias ni mensajería**:

| Concepto | Costo |
|---|---|
| Carpeta compartida de Google Drive | **$0** |
| Descarga automática de documentos (Google API) | **$0** |
| Procesamiento y "memoria" del chatbot (modelo de IA gratuito en modo básico) | **$0** hoy |
| Mantenimiento (proceso automático diario) | **$0** |

> **No hay costo mensual por el volumen de documentos.** El único costo futuro previsible es el del motor de IA cuando el uso crezca mucho (es opcional y se decide en otra etapa); la **carga y actualización de documentos siempre es $0**.

---

## 5. Espacio recomendado

El sistema es **liviano**. Se midió que la memoria del chatbot (los documentos procesados + la conversación histórica de 5 años) cabe en **~26 GB**.

| Escenario | Espacio necesario |
|---|---|
| Prototipo actual (17 MB de documentos) | < 1 GB |
| Escala plena a 5 años (todo el municipio) | ~26 GB |
| **Respaldo recomendado (holgura para crecer sin límite)** | **500 GB** |

**Propuesta**: disponer de **500 GB de espacio** (por ejemplo, en la
carpeta de Drive del municipio o en el servidor). Es una cifra **ampliamente sobrada** con holgura para crecer, subir documentos históricos, y nunca preocuparse por quedarse cortos al escalar. Aun así, el consumo real será de decenas de GB como máximo.

---

## 6. Importante (lo que el chatbot hace y NO hace)

- ✅ **Sí** responde con la información de los documentos que USTED sube.
- ✅ **Sí** se actualiza solo al día siguiente de subir un documento nuevo o cambiado.
- ✅ **No alucina**: si una pregunta no está en los documentos, el bot **no inventa** la respuesta; deriva al vecino al equipo humano de Atención al Vecino (teléfono/email).
- ❌ **No reemplaza** al personal humano en trámites complejos; lo complementa respondiendo preguntas frecuentes en 24/7.

---

## 7. Qué necesitamos de la ejecutiva (acciones)

1. **Crear/definir la carpeta** de Drive "Documentos Municipal chatbot" (o la que prefieran).
2. **Compartirla** con la identidad técnica del sistema (le entregamos el correo exacto; rol de **Lector**). Paso de una sola vez.
3. **Disponer 500 GB** de espacio (en Drive o en el servidor) como respaldo de crecimiento.
4. **Avisarnos** al subir el primer lote para validar el flujo end-to-end.

Con eso, la casa queda montada y el equipo de Transparencia **solo sube documentos** cuando corresponda, sin intervención técnica.

---
