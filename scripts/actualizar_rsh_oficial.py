#!/usr/bin/env python3
"""
actualizar_rsh_oficial.py — Actualiza la información oficial del Registro Social de Hogares (RSH)
según instrucción directa de Jefatura (Elias Garcés):
- Oficina: Oficina C (Pedro Aguirre Cerda #0101)
- Correo oficial: huribe@cisterna.cl
- Teléfono / WhatsApp: +56973892910
- Documentos requeridos:
  * Certificado de residencia emitido por la junta de vecinos o comunidad de edificios
  * Cédula de identidad de todos los integrantes del hogar
"""
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.database import get_collection

def actualizar_rsh():
    col = get_collection()

    # Eliminar versiones previas de rsh oficial si existían
    existing = col.get(where={"source": "rsh_oficial_dideco"})
    if existing and existing.get("ids"):
        col.delete(ids=existing["ids"])
        print(f"[RSH] Eliminados {len(existing['ids'])} chunks previos de rsh_oficial_dideco.")

    doc_texto = """### [DIDECO] Registro Social de Hogares (RSH): Atención, Contacto y Documentos Requeridos
**Palabras clave:** registro social de hogares, rsh, sacar registro social, actualizar registro social, cartola rsh, ficha social, tramitar rsh, hora registro social
**Respuesta:**
Para solicitar, actualizar o inscribir integrantes en el Registro Social de Hogares (RSH) en la Municipalidad de La Cisterna:

**Atención Presencial:**
- **Dirección:** Pedro Aguirre Cerda #0101, **Oficina C** (Dirección de Desarrollo Comunitario - DIDECO).

**Canales de Contacto Directo:**
- **Teléfono:** **+56973892910**
- **Correo Electrónico:** **huribe@cisterna.cl**

**Documentos Obligatorios a Presentar:**
1. **Certificado de residencia** emitido por la junta de vecinos respectiva o por la comunidad de edificios.
2. **Cédula de identidad** de todos los integrantes del hogar.

**Trámite Digital:**
También puedes consultar tu cartola y actualizar datos en línea con Clave Única en https://registrosocial.gob.cl."""

    col.add(
        documents=[doc_texto],
        metadatas=[{
            "source": "rsh_oficial_dideco",
            "categoria": "Atención al Público (Excel)",
            "chunk_index": 0,
            "origen": "jefatura_dideco"
        }],
        ids=["rsh-oficial-dideco-1"]
    )
    print("[RSH] [OK] Información oficial de Registro Social de Hogares indexada exitosamente en ChromaDB.")

if __name__ == "__main__":
    actualizar_rsh()
