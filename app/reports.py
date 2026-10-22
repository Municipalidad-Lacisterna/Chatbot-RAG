"""
Módulo de generación de reportes y analítica para el chatbot municipal.

Provee:
1. Listado de documentos indexados en ChromaDB con metadatos.
2. Clasificación de consultas de vecinos y ranking de preguntas frecuentes.
3. Exportación estructurada en CSV y JSON para autoridades y jefatura.
4. Actualización persistente de contraseñas de administración y documentación.
"""
import os
import io
import csv
import json
import sqlite3
import datetime
from collections import Counter, defaultdict
from app import settings

CATEGORIAS_MUNICIPALES = [
    ("Licencias de Conducir", ["licencia", "conducir", "chofer", "duplicado", "examen"]),
    ("Permisos de Circulación", ["permiso", "circulacion", "circulación", "vehiculo", "auto", "tag", "multa", "traslado"]),
    ("Registro Social y Subsidios", ["ficha", "registro social", "rsh", "subsidio", "social", "beneficio", "estratificacion"]),
    ("Farmacia Comunal y Salud", ["farmacia", "medicamento", "remedio", "cesfam", "vacuna", "salud", "receta", "medico"]),
    ("Veterinaria y Mascotas", ["veterinaria", "perro", "gato", "mascota", "garrapata", "chip", "esteriliz"]),
    ("Aseo, Escombros y Plagas", ["escombro", "basura", "cachureo", "poda", "arbol", "árbol", "rata", "plaga", "limpieza", "desratizacion"]),
    ("Patentes y Comercio", ["patente comercial", "negocio", "comercio", "feria", "patentes"]),
    ("Alumbrado y Obras", ["alumbrado", "luz", "poste", "luminaria", "obra", "obras", "pavimento", "hoyo"]),
    ("Concejales y Autoridades", ["concejal", "alcalde", "alcaldesa", "autoridad", "audiencia", "concejales"]),
    ("Contacto y WhatsApp", ["agente", "humano", "transferencia", "transferir", "telefono", "contacto", "whatsapp"]),
]


def clasificar_pregunta(pregunta: str) -> str:
    """Clasifica una pregunta en un tema municipal según palabras clave."""
    p_low = (pregunta or "").lower()
    for cat, kws in CATEGORIAS_MUNICIPALES:
        if any(k in p_low for k in kws):
            return cat
    return "Otras Consultas Generales"


def obtener_documentos_indexados() -> dict:
    """Obtiene el inventario de documentos cargados en ChromaDB."""
    try:
        from app.database import get_collection
        col = get_collection()
        res = col.get()
        metas = res.get("metadatas", [])
        
        fuentes_map = defaultdict(lambda: {"chunks": 0, "categoria": "General"})
        for m in metas:
            if not m:
                continue
            src = m.get("source") or m.get("tipo") or "Documento"
            fuentes_map[src]["chunks"] += 1
            if "/" in src:
                fuentes_map[src]["categoria"] = src.split("/", 1)[0]
            elif "xlsx" in src or "xls" in src:
                fuentes_map[src]["categoria"] = "Atención al Público (Excel)"
            elif "csv" in src:
                fuentes_map[src]["categoria"] = "Transparencia Activa"
            else:
                fuentes_map[src]["categoria"] = "Institucional"

        fuentes_lista = []
        for src, info in sorted(fuentes_map.items(), key=lambda x: x[1]["chunks"], reverse=True):
            fuentes_lista.append({
                "archivo": src,
                "categoria": info["categoria"],
                "chunks": info["chunks"],
                "estado": "Indexado / Activo"
            })

        return {
            "total_documentos": len(fuentes_lista),
            "total_chunks": sum(f["chunks"] for f in fuentes_lista),
            "fuentes": fuentes_lista
        }
    except Exception as e:
        return {
            "total_documentos": 0,
            "total_chunks": 0,
            "fuentes": [],
            "error": str(e)
        }


def obtener_reporte_preguntas() -> dict:
    """Extrae las consultas reales de los vecinos de chat_history.db y genera estadísticas."""
    if not os.path.exists(settings.MEMORY_DB_PATH):
        return {
            "total_consultas": 0,
            "temas": [],
            "ultimas_preguntas": []
        }

    try:
        conn = sqlite3.connect(settings.MEMORY_DB_PATH)
        rows = conn.execute(
            "SELECT content, timestamp FROM chat_history WHERE role = 'user' ORDER BY timestamp DESC"
        ).fetchall()
        conn.close()

        total = len(rows)
        conteo_temas = Counter()
        ejemplos_por_tema = defaultdict(list)
        ultimas_preguntas = []

        for content, ts in rows:
            texto = content.strip()
            if not texto:
                continue
            cat = clasificar_pregunta(texto)
            conteo_temas[cat] += 1
            
            # Guardar hasta 3 ejemplos distintos
            if len(ejemplos_por_tema[cat]) < 3 and texto not in ejemplos_por_tema[cat]:
                ejemplos_por_tema[cat].append(texto)

            if len(ultimas_preguntas) < 25:
                fecha_str = datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
                ultimas_preguntas.append({
                    "pregunta": texto,
                    "tema": cat,
                    "fecha": fecha_str
                })

        temas_lista = []
        for cat, cnt in conteo_temas.most_common():
            pct = round((cnt / total * 100), 1) if total > 0 else 0
            temas_lista.append({
                "tema": cat,
                "conteo": cnt,
                "porcentaje": pct,
                "ejemplos": ejemplos_por_tema[cat]
            })

        return {
            "total_consultas": total,
            "temas": temas_lista,
            "ultimas_preguntas": ultimas_preguntas
        }
    except Exception as e:
        return {
            "total_consultas": 0,
            "temas": [],
            "ultimas_preguntas": [],
            "error": str(e)
        }


def generar_csv_reporte() -> str:
    """Genera un reporte completo en formato CSV para descarga directa en Excel."""
    docs = obtener_documentos_indexados()
    reporte_p = obtener_reporte_preguntas()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Encabezado institucional
    writer.writerow(["REPORTE OFICIAL DEL CHATBOT CISTERNIN - MUNICIPALIDAD DE LA CISTERNA"])
    writer.writerow(["Fecha de generación", datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
    writer.writerow(["Total documentos indexados", docs["total_documentos"]])
    writer.writerow(["Total fragmentos vectoriales (chunks)", docs["total_chunks"]])
    writer.writerow(["Total consultas registradas", reporte_p["total_consultas"]])
    writer.writerow([])

    # Sección 1: Documentos
    writer.writerow(["=== 1. DOCUMENTOS CARGADOS EN BASE DE CONOCIMIENTO (RAG) ==="])
    writer.writerow(["Archivo / Fuente", "Categoría", "Chunks", "Estado"])
    for f in docs["fuentes"]:
        writer.writerow([f["archivo"], f["categoria"], f["chunks"], f["estado"]])
    writer.writerow([])

    # Sección 2: Ranking de preguntas comunes
    writer.writerow(["=== 2. REPORTES DE PREGUNTAS Y TEMAS MÁS FRECUENTES ==="])
    writer.writerow(["Tema / Categoría", "Nº Consultas", "% del Total", "Preguntas Frecuentes de Ejemplo"])
    for t in reporte_p["temas"]:
        ejemplos_txt = " | ".join(t["ejemplos"])
        writer.writerow([t["tema"], t["conteo"], f"{t['porcentaje']}%", ejemplos_txt])
    writer.writerow([])

    # Sección 3: Historial reciente
    writer.writerow(["=== 3. CONSULTAS RECIENTES DE VECINOS ==="])
    writer.writerow(["Fecha y Hora", "Pregunta / Mensaje del Vecino", "Tema Asignado"])
    for q in reporte_p["ultimas_preguntas"]:
        writer.writerow([q["fecha"], q["pregunta"], q["tema"]])

    return output.getvalue()


def cambiar_clave(tipo: str, nueva_clave: str, clave_actual: str) -> tuple[bool, str]:
    """Actualiza la clave en memoria y persiste el cambio en el archivo .env."""
    if not nueva_clave or len(nueva_clave) < 4:
        return False, "La nueva contraseña debe tener al menos 4 caracteres."

    # Validar que la clave actual corresponda a la de administración
    clave_admin_valida = (clave_actual == settings.ADMIN_PANEL_CLAVE or clave_actual == settings.AGENTE_PANEL_CLAVE)
    
    if not clave_admin_valida:
        return False, "La clave actual de administración es incorrecta."

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")

    try:
        if tipo == "admin":
            settings.ADMIN_PANEL_CLAVE = nueva_clave
            settings.AGENTE_PANEL_CLAVE = nueva_clave
            _persistir_en_env(env_path, "ADMIN_PANEL_CLAVE", nueva_clave)
            _persistir_en_env(env_path, "AGENTE_PANEL_CLAVE", nueva_clave)
            return True, "Contraseña de Super Administrador (/admin) actualizada con éxito."
        elif tipo == "administrador":
            settings.ADMINISTRADOR_PASSWORD = nueva_clave
            _persistir_en_env(env_path, "ADMINISTRADOR_PASSWORD", nueva_clave)
            return True, "Contraseña de Administrador Municipal (/administrador) actualizada con éxito."
        elif tipo == "docs":
            settings.DOCS_PASSWORD = nueva_clave
            _persistir_en_env(env_path, "DOCS_PASSWORD", nueva_clave)
            return True, "Contraseña de documentación y reportes (/docs) actualizada con éxito."
        else:
            return False, f"Tipo de clave no válido: {tipo}"
    except Exception as e:
        return False, f"Error al guardar la clave: {e}"


def _persistir_en_env(env_path: str, variable: str, valor: str):
    """Reemplaza o inserta una variable en el archivo .env."""
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"{variable}={valor}\n")
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    encontrado = False
    nuevas_lineas = []
    for line in lineas:
        if line.strip().startswith(f"{variable}="):
            nuevas_lineas.append(f"{variable}={valor}\n")
            encontrado = True
        else:
            nuevas_lineas.append(line)

    if not encontrado:
        nuevas_lineas.append(f"{variable}={valor}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(nuevas_lineas)
