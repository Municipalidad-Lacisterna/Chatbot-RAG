import os
import sys
import uuid

# Asegurar path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_collection

CHUNK_TARJETA_VECINO = """### [TARJETA VECINO] Información, Beneficios y Requisitos de la Tarjeta Vecino La Cisterna
**Descripción del trámite:**
La Tarjeta Vecino de La Cisterna es un beneficio comunal 100% gratuito que entrega descuentos y convenios exclusivos en farmacias, comercios locales, servicios médicos, gas licuado, eventos y talleres municipales para todos los residentes de la comuna de La Cisterna.

**Requisitos para obtenerla:**
1. Cédula de Identidad vigente (por ambos lados).
2. Acreditar residencia en la comuna de La Cisterna mediante uno de los siguientes documentos:
   - Cartola del Registro Social de Hogares (RSH) actualizada en la comuna.
   - Cuenta de servicios básicos a nombre del solicitante (luz, agua, gas).
   - Certificado de residencia emitido por la Junta de Vecinos respectiva.
   - Contrato de arriendo notariado.
3. Ser mayor de 18 años (para menores de edad la inscripción la realiza el padre, madre o tutor legal).

**¿Cómo y dónde solicitarla?:**
- **En línea (Digital):** Puede solicitarse directamente a través del portal web oficial: https://tarjetavecino.cisterna.cl o ingresando a www.cisterna.cl en la sección Tarjeta Vecino.
- **Presencial:** En la Dirección de Desarrollo Económico Local (DIDEL) / Oficina de Fomento Productivo, ubicada en Avenida El Parrón #548.
- **Horario de atención presencial:** Lunes a viernes de 08:30 a 14:00 horas.

**Costo del trámite:**
Totalmente gratuito.

**Teléfonos y contacto:**
- Teléfono / WhatsApp: +56 9 3435 8459
- Correo electrónico: tarjetavecino@cisterna.cl
- Dirección: Avenida El Parrón #548, La Cisterna."""

def indexar():
    col = get_collection()
    fuente = "tramites_comunes/tarjeta_vecino.md"
    
    # Limpiar previo si existe
    previos = col.get(where={"source": fuente})
    if previos and previos.get("ids"):
        col.delete(ids=previos["ids"])
        print(f"Limpiados {len(previos['ids'])} chunks previos de {fuente}")
        
    doc_id = str(uuid.uuid4())
    col.add(
        documents=[CHUNK_TARJETA_VECINO],
        metadatas=[{"source": fuente, "categoria": "DIDEL / Fomento Productivo", "chunk_index": 0}],
        ids=[doc_id]
    )
    print("✓ Tarjeta Vecino indexada exitosamente en ChromaDB!")

if __name__ == "__main__":
    indexar()
