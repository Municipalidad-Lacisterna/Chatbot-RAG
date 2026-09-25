"""
Normalizador de texto para el chatbot Cisternin.

Capa 1 del sistema de comprensión: normaliza, corrige y expande el lenguaje
coloquial chileno para que el retrieval y los patrones de detección funcionen
sin importar cómo escriba el vecino.

Niveles:
  1. Básico:    minúsculas, quitar tildes, limpiar puntuación
  2. Corrección: errores ortográficos comunes + abreviaciones coloquiales
  3. Sinónimos:  modismos chilenos → nombres formales de trámites

Uso típico:
  from app.text_normalizer import normalizar_basico, expandir_query
  norm = normalizar_basico("¿Dónde queda la FARMACIA?")  # "donde queda la farmacia"
  expandida = expandir_query("pa la receta")  # "pa la receta receta farmacia comunal..."
"""
import unicodedata
import re


# ---------------------------------------------------------------------------
# Nivel 1: Normalización básica
# ---------------------------------------------------------------------------

def _quitar_tildes(texto: str) -> str:
    """Elimina tildes/acentos de cualquier carácter Unicode (NFD decomposition)."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalizar_basico(texto: str) -> str:
    """
    Normalización básica para matching de patrones y comparaciones.
    - Minúsculas
    - Quita tildes
    - Limpia puntuación excesiva
    - Normaliza espacios múltiples
    """
    t = (texto or "").lower()
    t = _quitar_tildes(t)
    # Quitar signos de puntuación pero conservar espacios
    t = re.sub(r"[¿?!¡.,;:()\"\'\[\]{}]", " ", t)
    # Normalizar espacios múltiples
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# Nivel 2: Corrección ortográfica + abreviaciones coloquiales
# ---------------------------------------------------------------------------

# Mapa de correcciones: errores frecuentes → forma correcta
# Las claves ya están en minúsculas y sin tildes.
_CORRECCIONES = {
    # Errores ortográficos comunes
    "zirculacion": "circulacion",
    "zirculacion": "circulacion",
    "circulcion": "circulacion",
    "criculacion": "circulacion",
    "permio": "permiso",
    "permisod": "permiso de",
    "farmacia": "farmacia",
    "farmacia": "farmacia",
    "farmacia komunal": "farmacia comunal",
    "farmaia": "farmacia",
    "farpmacia": "farmacia",
    "comunal": "comunal",
    "komunal": "comunal",
    "condusir": "conducir",
    "conducir": "conducir",
    "conducir": "conducir",
    "licensia": "licencia",
    "licencia": "licencia",
    "licensia": "licencia",
    "pension": "pension",
    "pencion": "pension",
    "pencion": "pension",
    "subsidio": "subsidio",
    "subcidio": "subsidio",
    "subcidio": "subsidio",
    "patente": "patente",
    "patette": "patente",
    "edififcacion": "edificacion",
    "edifcacion": "edificacion",
    "demolicion": "demolicion",
    "demolicion": "demolicion",
    "construccion": "construccion",
    "construcion": "construccion",
    "esterializacion": "esterilizacion",
    "esterilisacion": "esterilizacion",
    "vacunacion": "vacunacion",
    "vacunasion": "vacunacion",
    "podologo": "podologo",
    "podologico": "podologico",
    "podologico": "podologico",
    "empadronamiento": "empadronamiento",
    "empadronamientoo": "empadronamiento",
    "certificado": "certificado",
    "certifcado": "certificado",
    "certifado": "certificado",
    "organizacion": "organizacion",
    "organisacion": "organizacion",
    "organisacion": "organizacion",
    "asociacion": "asociacion",
    "asociacion": "asociacion",
    "residencia": "residencia",
    "residencia": "residencia",
    "feria": "feria",
    "feria": "feria",
    "escombros": "escombros",
    "escombos": "escombros",
    "arboles": "arboles",
    "arboles": "arboles",
    "arbol": "arbol",
    "arbol": "arbol",
    "ramas": "ramas",
    "ramas": "ramas",
    "poda": "poda",
    "poda": "poda",
    "control": "control",
    "control": "control",
    "vacunacion": "vacunacion",
    "garrapatas": "garrapatas",
    "garrapatas": "garrapatas",
    "castracion": "castracion",
    "castracion": "castracion",
    "desratizacion": "desratizacion",
    "desratizacion": "desratizacion",
    "desinsectacion": "desinsectacion",
    "desinsectacion": "desinsectacion",
    "sanitizacion": "sanitizacion",
    "sanitizacion": "sanitizacion",
    "propaganda": "propaganda",
    "publicidad": "publicidad",
    "loteo": "loteo",
    "fusion": "fusion",
    "fusion": "fusion",
    "subdivision": "subdivision",
    "subdivision": "subdivision",
    "predial": "predial",
    "predial": "predial",
    "expropiacion": "expropiacion",
    "expropiacion": "expropiacion",
    "recepcion": "recepcion",
    "recepcion": "recepcion",
    "urbanizacion": "urbanizacion",
    "urbanizacion": "urbanizacion",
    "anteproyecto": "anteproyecto",
    "inspeccion": "inspeccion",
    "inspeccion": "inspeccion",
    "denuncio": "denuncio",
    "cobertizo": "cobertizo",
    "grua": "grua",
    "grua": "grua",
    "excavacion": "excavacion",
    "faena": "faena",
    "faena": "faena",
    "letrero": "letrero",
    "comodato": "comodato",
    "concejo": "concejo",
    "concejo": "concejo",
}

# Abreviaciones y jerga coloquial chilena → forma expandida
_ABREVIACIONES = {
    # Contracciones chilenas típicas
    "pa": "para",
    "pa la": "para la",
    "pa el": "para el",
    "pa los": "para los",
    "pa las": "para las",
    "po": "por",
    "na": "nada",
    "toy": "estoy",
    "tai": "estai",
    "tay": "estay",
    "doi": "doy",
    "soi": "soy",
    "voh": "tu",
    "vo": "tu",
    "wea": "cosa",
    "weas": "cosas",
    "cachai": "entiendes",
    "cachai?": "entiendes",
    "altiro": "ahora mismo",
    "al toque": "ahora mismo",
    "al tiro": "ahora mismo",
    "rato": "momento",
    "al rato": "despues",
    "encue": "encuesta",
    "feri": "feriado",
    "auto": "vehiculo particular",
    "casa": "domicilio",
    "pie": "a pie",
    "loko": "loco",
    "bacan": "buena onda",
    "fome": "aburrido",
    " filete": "bueno",
    " FILETE": "bueno",
    "cana": "carcel",
    "gamba": "buena persona",
    "polola": "novia",
    "pololo": "novio",
    "pololeo": "noviazgo",
    "once": "merienda",
    "oncear": "tomar once",
    "oncear": "tomar once",
    "onceo": "tomar once",
    "onceo": "tomar once",
    "carrete": "fiesta",
    "carretear": "ir de fiesta",
    "pololo": "novio",
    "polola": "novia",
    "pega": "trabajo",
    "pegar": "trabajar",
    "pega": "trabajo",
    "guita": "dinero",
    "plata": "dinero",
    "luca": "mil pesos",
    "luca": "mil pesos",
    "omega": "un peso",
    "loco": "amigo",
    "loca": "amiga",
    "compa": "compañero",
    "compa": "compañero",
    "bro": "hermano",
    "mano": "hermano",
    "weon": "tonto",
    "weona": "tonta",
    "weon": "amigo",
    "weona": "amiga",
    "pucha": "ay",
    "csm": "intraducible",
    "ctm": "intraducible",
    "wena": "buena",
    "weno": "bueno",
    "wena": "buena",
    "buena onda": "amable",
    "seca": "habil",
    "seco": "habil",
    "penca": "malo",
    "penca": "malo",
    "rajado": "generoso",
    "rajado": "generoso",
    "copado": "divertido",
    "copado": "divertido",
    "cachai": "sabes",
    "pillai": "encuentras",
    "pillai": "encuentras",
    "doi": "doy",
    "toy": "estoy",
    "toy": "estoy",
    "tai": "estas",
    "tay": "estas",
    "voh": "tu",
    "po": "pues",
    "altiro": "de inmediato",
    "na": "nada",
    "na": "nada",
}


def corregir_texto(texto: str) -> str:
    """
    Corrige errores ortográficos comunes y expande abreviaciones.
    Trabaja sobre texto ya normalizado (minúsculas, sin tildes).
    """
    t = (texto or "").strip()

    # 1. Aplicar correcciones ortográficas (reemplazo de palabra completa
    #    o substring largo primero, para evitar colisiones)
    for mal, bien in sorted(_CORRECCIONES.items(), key=lambda x: -len(x[0])):
        t = t.replace(mal, bien)

    # 2. Expandir abreviaciones (de mayor a menor longitud para evitar
    #    que "pa la" se expanda antes que "pa")
    for abrev, exp in sorted(_ABREVIACIONES.items(), key=lambda x: -len(x[0])):
        # Usar word boundaries para no reemplazar dentro de otras palabras
        patron = r"(?<!\w)" + re.escape(abrev) + r"(?!\w)"
        t = re.sub(patron, exp, t)

    # Re-normalizar espacios tras las correcciones
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# Nivel 3: Diccionario de sinónimos y modismos para trámites municipales
# ---------------------------------------------------------------------------

# Cada entrada mapea una lista de palabras/frases coloquiales al nombre
# oficial del trámite (o una query expandida que ChromaDB pueda matchear).
# Las claves ya están en minúsculas y sin tildes.

_TRAMITES_SINONIMOS = {
    # --- Farmacia ---
    "farmacia comunal": [
        "farmacia", "la farmacia", "la farmacia comunal", "medicamentos",
        "remedio", "remedios", "pastillas", "medicina barata",
        "medicamentos baratos", "receta", "receta medica",
        "pa la receta", "pa comprar remedios", "onde farmacia",
        "donde queda la farmacia", "farmacia municipal",
    ],
    # --- Ficha de Protección Social ---
    "ficha de proteccion social": [
        "ficha social", "ficha proteccion", "ficha de proteccion",
        "la ficha esa", "ficha del registro", "registro social",
        "registro social de hogares", "rsh", "folio de registro social",
        "pertenecer al registro social", "necesito la ficha",
        "como saco la ficha", "obtener ficha", "ficha para subsidios",
        "ficha para beneficios",
    ],
    # --- Centro de Emprendimiento ---
    "centro de emprendimiento": [
        "emprendimiento", "el centro de emprendimiento",
        "emprender", "negocio propio", "quiero emprender",
        "ayuda para emprender", "capsule emprendimiento",
        "ayuda economico para negocio",
    ],
    # --- Permisos de Circulación ---
    "permiso de circulacion": [
        "permiso", "permiso del auto", "permiso del vehiculo",
        "permiso vehicular", "permiso pa circular", "permiso de circulacion",
        "el permiso", "reno var el permiso", "renovar permiso",
        "permiso vencido", "permiso 2026", "permiso auto",
        "pague el permiso", "impuesto de circulacion",
        "impuesto vehicular", "el impuesto del auto",
        "permiso pa la moto", "permiso moto",
        "donde pago el permiso", "como renuevo el permiso",
    ],
    # --- Licencia de Conducir ---
    "licencia de conducir": [
        "licencia", "la licencia", "licencia de manejo",
        "licencia de manejar", "licencia de conducir",
        "sacar licencia", "nueva licencia", "renovar licencia",
        "licencia nueva", "licencia primera vez", "examen de conducir",
        "examen de manejo", "clase de licencia", "licencia clase b",
        "licencia clase a", "duplicado de licencia",
        "perdi la licencia", "me robaron la licencia",
        "licencia por primera vez", "prueba de manejo",
    ],
    # --- Patentes Comerciales ---
    "patente comercial": [
        "patente", "la patente", "patente de comercio",
        "patente comercial", "abrir negocio", "permiso de negocio",
        "permiso para vender", "licencia de funcionamiento",
        "patente de vendedora ambulante", "vendedora ambulante",
        "feria libre", "feria", "puesto en feria",
        "patente de feria", "patente industrial",
        "patente microempresa", "patente profesional",
        "propaganda", "publicidad en via publica",
        "cartel en la calle", "letrero publicitario",
    ],
    # --- Certificados ---
    "certificado de residencia": [
        "certificado", "certificado de domicilio",
        "certificado de residencia", "donde vivo",
        "comprobante de domicilio", "donde vivo comunal",
        "certificado para subsidy", "certificado para subsidio",
        "certificado para la municipalidad",
    ],
    # --- Subsidios ---
    "subsidio": [
        "subsidio", "ayuda social", "ayuda economica",
        "subsidio unico familiar", "suf", "subsidio maternal",
        "subsidio al agua", "subsidio al aseo",
        "subsidio aseo domiciliario", "subsidio agua potable",
        "subsidio discapacidad", "ayuda pa los hijos",
        "ayuda pa los cabros", "platita pa la casa",
        "ayuda para la luz", "ayuda para el gas",
    ],
    # --- Pensiones ---
    "pension basica solidaria": [
        "pension", "jubilacion", "jubilar",
        "pension de vejez", "pension de invalidez",
        "pension basica", "pension solidaria",
        "jubilarse", "ya no puedo trabajar",
        "pension por vejez", "pension por invalidez",
    ],
    # --- Perros/Gatos ---
    "atencion veterinaria": [
        "veterinario", "veterinaria", "perro", "gato",
        "mascota", "animal", "castrar", "esterilizar",
        "vacuna", "vacunar", "garrapata", "garrapatas",
        "desparasitar", "desparasitacion",
        "atencion para mi perro", "atencion para mi gato",
        "perro con garrapatas", "gato con garrapatas",
    ],
    # --- Desinsectación / Plagas ---
    "beneficio sanitario domiciliario": [
        "cucaracha", "cucarachas", "cacho negro", "cachos negros",
        "rata", "ratas", "raton", "ratones",
        "plaga", "plagas", "chinche", "chinches",
        "pulga", "pulgas", "desratizacion",
        "desinsectacion", "sanitizacion",
        "fumigar", "fumigacion",
        "tengo ratas", "tengo cucarachas",
        "hay plagas en mi casa", "limpieza sanitaria",
    ],
    # --- Arbolado ---
    "servicio de arbolado": [
        "arbol", "arboles", "rama", "ramas",
        "poda", "poda de arboles", "rebaje de arboles",
        "levantamiento de ramas", "retiro de ramas",
        "arbol caido", "arbol en la vereda",
        "arbol tapa la luz", "arbol tapa el paso",
        "requerimiento de arboles", "plantar arboles",
        "sembrar arboles", "necesito un arbol",
    ],
    # --- Retiro de escombros ---
    "retiro de escombros": [
        "escombros", "retiro de escombros",
        "basura en la calle", "micro basural",
        "maderas viejas", "escombros de construccion",
        "limpiar el terreno", "retirar basura",
        "basural", "tengo escombros",
    ],
    # --- Ferias ---
    "limpieza de ferias": [
        "feria sucia", "limpiar feria", "feria lagunosa",
        "limpieza de feria", "feria necesita limpieza",
        "lavar la feria", "feria muy sucia",
    ],
    # --- Organizaciones sociales ---
    "constitucion de organizaciones": [
        "organizacion", "organizacion social",
        "organizacion vecinal", "junta de vecinos",
        "sindicato", "cooperativa", "club",
        "asociacion de vecinos", "fundar una organizacion",
        "crear una organizacion", "constituir una organizacion",
        "inscribir una organizacion", "personeria juridica",
    ],
    # --- Residencia extranjeros ---
    "tramite de residencia extranjero": [
        "residencia", "residencia para extranjeros",
        "visa", "permiso de residencia",
        "residencia temporaria", "residencia permanente",
        "residencia sujeta a contrato", "tramite de extranjeros",
        "documentacion extranjero", "permanencia definitiva",
        "extranjero", "inmigrante", "venezolano", "colombiano",
        "haitiano", "boliviano", "peruano",
    ],
    # --- Fondos concursables ---
    "fondos concursables": [
        "fondo", "fondos", "fondo social", "fondo municipal",
        "fondo concursable", "subvencion", "subvencion municipal",
        "postular a un fondo", "ayuda economica del municipio",
        "medio millon", "fondo medio millon",
    ],
    # --- Becas ---
    "beca": [
        "beca", "beca indigena", "beca presidencial",
        "ayuda estudiantil", "ayuda escolar",
        "beca para estudiar", "beca para mis hijos",
        "beca para los cabros", "beca escolar",
        "postular a beca",
    ],
    # --- Informe social ---
    "informe social": [
        "informe social", "el informe", "necesito un informe",
        "informe para el juzgado", "informe para carabineros",
        "informe para la municipalidad", "certificado social",
    ],
    # --- Pension basica ---
    "obtener pension": [
        "pension", "jubilacion", "jubilar",
        "pension de vejez", "pension de invalidez",
        "pension basica", "pension solidaria",
    ],
    # --- Subsidio aseo ---
    "subsidio al aseo domiciliario": [
        "subsidio aseo", "ayuda aseo", "aseo domiciliario",
        "basura gratuita", "no pago basura", "gratuidad basura",
        "ayuda con la basura", "pago basura rebajado",
    ],
    # --- Empadronamiento vehiculos ---
    "empadronamiento vehicular": [
        "empadronar", "empadronar auto", "empadronar vehiculo",
        "remucar", "remolque", "vehiculo menor",
        "bicimoto", "motocicleta", "quad",
        "vehiculo no motorizado",
    ],
    # --- Edificación ---
    "permiso de edificacion": [
        "permiso de edificacion", "permiso de construccion",
        "construir", "ampliar la casa", "ampliacion",
        "obra nueva", "obra menor", "permiso de obra",
        "permiso para ampliar", "permiso para construir",
        "levantar una pieza", "gregar una pieza",
        "hacer una bodega", "remodelar",
    ],
    # --- Demolición ---
    "permiso de demolicion": [
        "demoler", "demolicion", "tirar una pared",
        "tirar la casa", "demoler la casa", "demoler edificio",
        "permiso de demolicion",
    ],
    # --- División predial / Loteo ---
    "division predial": [
        "dividir terreno", "dividir predio", "lotear",
        "loteo", "subdividir", "solar", "un solar en dos",
        "partir el terreno", "partir la propiedad",
        "fusion de terrenos", "juntar terrenos",
        "solar unico", "solar compartido",
    ],
    # --- Atencion ministerio ---
    "atencion ministerio": [
        "ministro", "ministro de fe", "organizar algo",
        " HOURA ministro", "hora ministro",
        "organizar evento", "consejo vecinal",
    ],
    # --- Cursos / Centro ceremonial ---
    "cursos centro ceremonial": [
        "curso", "cursos", "aprender algo", "taller",
        "capacitacion", "curso de cocina", "curso de manualidades",
        "curso de computacion", "inscribirse a curso",
        "centro ceremonial",
    ],
    # --- Feria Costumbrista ---
    "feria costumbrista": [
        "feria costumbrista", "feria tipica", "feria navideña",
        "feria de septiembre", "fondas", "fonda",
        "actividades de septiembre", "fiestas patrias",
        "actividades de diciembre", "navidad",
        "actividades navideñas",
    ],
    # --- Informe para concejo ---
    "informe concejo": [
        "informe para el concejo", "comodato",
        "preparar informe", "entregar comodato",
    ],
    # --- Apoyo laboral extranjeros ---
    "apoyo laboral extranjero": [
        "trabajo para extranjeros", "buscar trabajo",
        "empleo", "cv", "curriculum", "insercion laboral",
        "trabajo para inmigrantes", "empleo extranjeros",
    ],
    # --- Asesoria CONADI ---
    "asesoria conadi": [
        "conadi", "discapacidad", "discapacitado",
        "persona con discapacidad", "pcd", "lumbroso",
        "certificado de discapacidad", "trámite con discapacidad",
    ],
    # --- Insercion escolar ---
    "insercion escolar": [
        "matricular", "matricula", "inscribir al colegio",
        "inscripcion escolar", "colegio", "escuela",
        "necesito colegio para mi hijo", "colegio para los niños",
        "documentos para el colegio",
    ],
    # --- Español para haitianos ---
    "curso de espanol haitiano": [
        "aprender español", "curso de español",
        "haitiano", "curso para haitianos",
        "español para inmigrantes",
    ],
}


def expandir_query(texto: str) -> str:
    """
    Expande una pregunta del vecino agregando sinónimos y nombres formales
    de trámites para mejorar el retrieval de ChromaDB.

    Flujo:
    1. Normalizar y corregir el texto
    2. Buscar en el diccionario de sinónimos qué trámite parece preguntar
    3. Devolver la query original + los términos formales encontrados

    Ejemplo:
      "pa la receta" → "pa la receta farmacia comunal receta medica medicamentos"
    """
    norm = corregir_texto(normalizar_basico(texto))

    # Buscar coincidencias en el diccionario de sinónimos
    terminos_extra = []
    for tramite_clave, variaciones in _TRAMITES_SINONIMOS.items():
        for variacion in variaciones:
            # Coincidencia por substring (la variación está en la query
            # normalizada, o la query normalizada está en la variación)
            if variacion in norm or norm in variacion:
                # Agregar el nombre formal del trámite y sus variaciones
                terminos_extra.append(tramite_clave)
                terminos_extra.extend(variaciones[:5])  # Top 5 variaciones
                break  # Un match por trámite es suficiente

    if terminos_extra:
        # Deduplicar manteniendo orden
        vistos = set()
        unicos = []
        for t in terminos_extra:
            if t not in vistos:
                vistos.add(t)
                unicos.append(t)
        return f"{texto} {' '.join(unicos)}"

    return texto


# ---------------------------------------------------------------------------
# Función combinada para los patrones de detección
# ---------------------------------------------------------------------------

def normalizar_para_patrones(texto: str) -> str:
    """
    Normalización para los patrones de detección (identidad, sensible,
    despedidas, easter eggs). Quita tildes, minúsculas y puntuación.
    NO expande sinónimos (eso es solo para retrieval).
    """
    return normalizar_basico(texto)
