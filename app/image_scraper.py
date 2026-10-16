"""
Extractor y Scraper Multimodal de Imágenes y Afiches Municipales.

Recorre el portal de la municipalidad (cisterna.cl), identifica afiches,
volantes e infografías, los analiza usando Visión por Inteligencia Artificial
(Google Gemini Vision o IA local multimodal) y genera fragmentos Markdown atómicos
listos para ser indexados en ChromaDB.
"""
import os
import re
import json
import base64
import urllib.parse
import hashlib
from pathlib import Path
import requests
from bs4 import BeautifulSoup

from app import settings

BASE_MUNI_URL = "https://www.cisterna.cl"
DIR_AFICHES = os.path.join(settings.DATA_DIR, "afiches")
CACHE_FILE = os.path.join(DIR_AFICHES, ".cache_imagenes.json")

# Exclusiones de imágenes genéricas que no son afiches
EXCLUSIONES_URL = [
    "logo", "icon", "favicon", "facebook", "instagram", "twitter", "whatsapp",
    "arrow", "banner-pattern", "divider", "transparencia_logo", "footer", "header"
]


def _asegurar_dirs():
    os.makedirs(DIR_AFICHES, exist_ok=True)


def _cargar_cache() -> dict:
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _guardar_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[scraper-img] Aviso: no se guardó cache: {e}")


def extraer_urls_imagenes(paginas: list[str] = None) -> list[dict]:
    """
    Rastrea las páginas clave del municipio para encontrar afiches y fotos informativas
    junto con su contexto (título, enlace que rodea la imagen y texto alternativo).
    """
    if not paginas:
        paginas = [
            BASE_MUNI_URL,
            f"{BASE_MUNI_URL}/#noticias",
            f"{BASE_MUNI_URL}/pages/body/noticias",
            f"{BASE_MUNI_URL}/pages/body/beneficios",
            f"{BASE_MUNI_URL}/pages/body/tramites"
        ]

    candidatos = []
    vistos = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("[scraper-img] Buscando imágenes en el portal municipal...")
    for pag in paginas:
        try:
            r = requests.get(pag, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, "html.parser")

            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if not src:
                    continue

                full_url = urllib.parse.urljoin(pag, src)
                if full_url in vistos:
                    continue
                vistos.add(full_url)

                src_low = full_url.lower()
                # Filtrar extensiones válidas de imagen
                if not any(src_low.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    continue

                # Filtrar íconos comunes
                if any(exc in src_low for exc in EXCLUSIONES_URL):
                    continue

                alt = img.get("alt", "").strip()
                # Buscar enlace padre si lo tiene (ej: si el afiche lleva a un trámite o PDF)
                parent_a = img.find_parent("a")
                link_destino = urllib.parse.urljoin(pag, parent_a.get("href")) if parent_a and parent_a.get("href") else ""

                # Contexto cercano (título h2/h3 de la noticia si existe)
                contexto_txt = ""
                parent_article = img.find_parent(["article", "div", "section"])
                if parent_article:
                    h = parent_article.find(["h1", "h2", "h3", "h4"])
                    if h:
                        contexto_txt = h.get_text(strip=True)

                candidatos.append({
                    "url": full_url,
                    "alt": alt,
                    "enlace_asociado": link_destino,
                    "contexto": contexto_txt
                })
        except Exception as e:
            print(f"[scraper-img] Error al raspar {pag}: {e}")

    print(f"[scraper-img] Se encontraron {len(candidatos)} imágenes candidatas.")
    return candidatos


def descargar_imagen(url: str, destino_path: str) -> bool:
    """Descarga la imagen a disco."""
    try:
        r = requests.get(url, timeout=15, stream=True)
        if r.status_code == 200:
            with open(destino_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            # Descartar archivos minúsculos (< 8 KB, suelen ser separadores o íconos rotos)
            if os.path.getsize(destino_path) < 8192:
                os.remove(destino_path)
                return False
            return True
    except Exception:
        return False
    return False


def analizar_imagen_con_vision_ia(img_path: str, meta_contexto: dict) -> str:
    """
    Envía la imagen a Gemini Vision (vía API oficial de Google) o IA local para
    extraer toda la información en Markdown atómico.
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        print("[scraper-img] AVISO: No hay GOOGLE_API_KEY configurada para visión.")
        return ""

    with open(img_path, "rb") as f:
        img_bytes = f.read()
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    ext = img_path.lower().rsplit(".", 1)[-1]
    mime_type = "image/jpeg" if ext in ("jpg", "jpeg") else ("image/png" if ext == "png" else "image/webp")

    prompt = f"""Eres el digitalizador oficial de información de la Municipalidad de La Cisterna.
Analiza con total precisión esta imagen, afiche, infografía o comunicado municipal.
Extrae TODO el contenido informativo relevante y estructúralo de forma limpia en formato Markdown.

Contexto adicional detectado en la página web:
- Título/Tema relacionado: {meta_contexto.get('contexto', 'No especificado')}
- Texto alternativo: {meta_contexto.get('alt', 'No especificado')}
- Enlace asociado al afiche: {meta_contexto.get('enlace_asociado', 'Ninguno')}

Debes generar una ficha con este formato estricto:
### [Título descriptivo del trámite, beneficio o evento]
- Descripción completa: (explica detalladamente de qué se trata)
- Fechas y horarios: (cuándo se realiza, plazos, días de atención o vigencia)
- Lugar y dirección: (dirección física exacta, plaza, recinto o departamento municipal)
- Requisitos y documentos: (todo lo que debe llevar o cumplir el vecino)
- Costo o gratuidad: (si es gratis o monto en pesos chilenos)
- Enlaces y sitios web: (páginas web o URLs mencionadas para postular, pagar o inscribirse)
- Contacto y teléfonos: (correos, WhatsApp, teléfonos fijos o anexos indicados)

IMPORTANTE: Si en el afiche o en el enlace asociado se indica una URL para realizar el trámite (ej: tarjetavecino.cisterna.cl), asegúrate de incluirla de forma explícita.
Si la imagen es solo decorativa, un paisaje o no contiene información útil para trámites de vecinos, responde únicamente: NO_RELEVANTE.
"""

    url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_img
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024
        }
    }

    try:
        resp = requests.post(url_gemini, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                texto = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if "NO_RELEVANTE" in texto:
                    return ""
                return texto
        else:
            print(f"[scraper-img] Error en API Gemini Vision: HTTP {resp.status_code}")
    except Exception as e:
        print(f"[scraper-img] Error al consultar API de visión: {e}")

    return ""


def ejecutar_scraper_imagenes():
    """Ejecuta el pipeline completo de raspado, visión e indexación en ChromaDB."""
    _asegurar_dirs()
    cache = _cargar_cache()
    candidatos = extraer_urls_imagenes()

    nuevos_analizados = 0
    fichas_generadas = []

    for c in candidatos:
        url_img = c["url"]
        h = hashlib.md5(url_img.encode("utf-8")).hexdigest()

        if h in cache:
            # Ya fue procesada previamente
            continue

        nombre_archivo = f"afiche_{h[:10]}." + url_img.rsplit(".", 1)[-1].split("?")[0]
        ruta_local = os.path.join(DIR_AFICHES, nombre_archivo)

        print(f"[scraper-img] Descargando imagen: {url_img}")
        if not descargar_imagen(url_img, ruta_local):
            cache[h] = {"estado": "descartado_descarga"}
            continue

        print(f"[scraper-img] Analizando afiche con Visión IA: {nombre_archivo}")
        md_resultado = analizar_imagen_con_vision_ia(ruta_local, c)

        if md_resultado and len(md_resultado) > 40:
            # Guardar ficha Markdown
            md_path = os.path.join(DIR_AFICHES, f"{nombre_archivo}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(f"<!-- Origen: {url_img} -->\n" + md_resultado)
            
            fichas_generadas.append((f"afiches/{nombre_archivo}.md", md_resultado))
            cache[h] = {"estado": "indexado", "archivo": nombre_archivo}
            nuevos_analizados += 1
            print(f"[scraper-img] ✓ Ficha generada con éxito para {nombre_archivo}")
        else:
            cache[h] = {"estado": "sin_texto_relevante"}
            # Si no fue relevante, borrar la imagen para no ocupar disco
            if os.path.exists(ruta_local):
                os.remove(ruta_local)

    _guardar_cache(cache)

    # Si se generaron fichas nuevas, indexarlas de inmediato en ChromaDB
    if fichas_generadas:
        print(f"[scraper-img] Indexando {len(fichas_generadas)} fichas de afiches en ChromaDB...")
        try:
            from app.database import get_collection
            import uuid
            col = get_collection()
            for fuente, texto in fichas_generadas:
                previos = col.get(where={"source": fuente})
                if previos and previos.get("ids"):
                    col.delete(ids=previos["ids"])
                col.add(
                    documents=[texto],
                    metadatas=[{"source": fuente, "categoria": "Afiches y Avisos Web"}],
                    ids=[str(uuid.uuid4())]
                )
            print("[scraper-img] ✓ Indexación completada en ChromaDB.")
        except Exception as e:
            print(f"[scraper-img] Error al indexar en ChromaDB: {e}")

    print(f"[scraper-img] Proceso finalizado. Total nuevos afiches procesados: {nuevos_analizados}")
    return nuevos_analizados


if __name__ == "__main__":
    ejecutar_scraper_imagenes()
