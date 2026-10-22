"""
Módulo de escaneo y extracción de páginas web para el RAG municipal.

Función experimental:
Permite ingresar una URL pública de la municipalidad, descargar su contenido HTML,
eliminar elementos de navegación/scripts, y convertirlo a Markdown estructurado
para indexarlo en ChromaDB o encolarlo para las 03:00 AM.
"""
import os
import re
import datetime
import urllib.parse
import requests
from bs4 import BeautifulSoup
from app import settings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}


def _generar_slug(texto: str) -> str:
    """Convierte un título o URL en un nombre de archivo seguro."""
    s = texto.lower()
    s = re.sub(r"https?://", "", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return s[:45] if s else "pagina_web"


def escanear_pagina(url: str) -> dict:
    """Descarga una URL y la convierte en texto Markdown limpio."""
    url = (url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"ok": False, "mensaje": "La URL debe comenzar con http:// o https://"}

    try:
        # Petición HTTP con timeout seguro
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if resp.status_code != 200:
            return {"ok": False, "mensaje": f"El sitio web respondió con código HTTP {resp.status_code}."}

        soup = BeautifulSoup(resp.content, "html.parser")

        # Extraer título
        titulo = ""
        if soup.title and soup.title.string:
            titulo = soup.title.string.strip()
        elif soup.h1:
            titulo = soup.h1.get_text().strip()
        else:
            titulo = urllib.parse.urlparse(url).path.strip("/").replace("/", " - ") or "Página Municipal"

        # Eliminar elementos irrelevantes / ruido
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form", "svg", "iframe"]):
            tag.decompose()

        # Buscar contenedor principal de contenido
        contenedor = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", class_=re.compile(r"(content|entry-content|post-content|page-content|detalle)", re.I)) or
            soup.find("body") or
            soup
        )

        # Extraer líneas y estructurar en Markdown
        lineas_md = []
        for elem in contenedor.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
            txt = elem.get_text(separator=" ", strip=True)
            if not txt:
                continue

            tag_name = elem.name.lower()
            if tag_name == "h1":
                lineas_md.append(f"\n# {txt}\n")
            elif tag_name == "h2":
                lineas_md.append(f"\n## {txt}\n")
            elif tag_name in ("h3", "h4"):
                lineas_md.append(f"\n### {txt}\n")
            elif tag_name == "li":
                lineas_md.append(f"- {txt}")
            else:
                lineas_md.append(f"\n{txt}\n")

        contenido_md = "\n".join(lineas_md)
        # Limpieza de saltos múltiples
        contenido_md = re.sub(r"\n{3,}", "\n\n", contenido_md).strip()

        if len(contenido_md) < 80:
            return {
                "ok": False,
                "mensaje": "Se extrajo muy poco contenido de la página. Es posible que el sitio use renderizado dinámico en JavaScript o bloquee el acceso automatizado."
            }

        palabras = len(contenido_md.split())
        caracteres = len(contenido_md)
        slug = _generar_slug(titulo or url)

        return {
            "ok": True,
            "url": url,
            "titulo": titulo,
            "markdown": contenido_md,
            "palabras": palabras,
            "caracteres": caracteres,
            "slug": slug,
            "preview": contenido_md[:400] + ("..." if len(contenido_md) > 400 else "")
        }

    except requests.exceptions.Timeout:
        return {"ok": False, "mensaje": "Tiempo de espera agotado al intentar conectar con el sitio web."}
    except requests.exceptions.SSLError:
        return {"ok": False, "mensaje": "Error de certificado SSL en el sitio web de destino."}
    except Exception as e:
        return {"ok": False, "mensaje": f"Error al escanear la página: {str(e)}"}


def procesar_escaneo_web(url: str, categoria: str = "Páginas Web", programar: bool = True) -> dict:
    """Escanea la página web y la guarda en inbox o la indexa de inmediato."""
    datos = escanear_pagina(url)
    if not datos["ok"]:
        return datos

    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    slug = datos["slug"]
    nombre_archivo = f"web_{slug}.md"

    # Encabezado institucional con metadatos
    doc_completo = f"""# {datos['titulo']}
- **Fuente Oficial:** {datos['url']}
- **Categoría:** {categoria}
- **Fecha de Digitalización:** {fecha_hoy}
- **Tipo de Origen:** Escaneo de Página Web (Experimental)

{datos['markdown']}
"""

    if programar:
        inbox_dir = os.path.join(settings.DATA_DIR, "inbox")
        os.makedirs(inbox_dir, exist_ok=True)
        destino = os.path.join(inbox_dir, nombre_archivo)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(doc_completo)

        chunks_est = max(1, len(doc_completo) // settings.CHUNK_SIZE)
        return {
            "ok": True,
            "programado": True,
            "titulo": datos["titulo"],
            "archivo": nombre_archivo,
            "palabras": datos["palabras"],
            "caracteres": datos["caracteres"],
            "chunks_estimados": chunks_est,
            "preview": datos["preview"],
            "mensaje": f"Página '{datos['titulo']}' escaneada exitosamente y encolada en inbox para la sincronización de las 03:00 AM."
        }
    else:
        # Indexar de inmediato en ChromaDB
        from app.ingestion import _indexar_texto
        fuente_id = f"{categoria}/{nombre_archivo}"
        n_chunks = _indexar_texto(doc_completo, fuente_id)
        return {
            "ok": True,
            "programado": False,
            "titulo": datos["titulo"],
            "archivo": nombre_archivo,
            "palabras": datos["palabras"],
            "caracteres": datos["caracteres"],
            "chunks": n_chunks,
            "preview": datos["preview"],
            "mensaje": f"Página '{datos['titulo']}' escaneada e indexada de inmediato con {n_chunks} fragmentos vectoriales."
        }
