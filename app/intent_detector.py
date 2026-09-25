"""
Detector de intención del chatbot Cisternin.

Capa 2 del sistema de comprensión: entiende QUÉ quiere hacer el vecino,
no solo qué palabras escribe. Funciona sin LLM, usando reglas inteligentes
que aprovechan el normalizador de la Capa 1.

Intenciones detectadas:
  - buscar_info:    quiere saber algo (horarios, requisitos, direcciones)
  - hacer_tramite:  quiere iniciar/realizar un trámite
  - estado_tramite: quiere saber el ESTADO de algo que ya hizo
  - queja_reportar: quiere denunciar/reportar algo
  - contacto:       quiere hablar con alguien / obtener datos de contacto
  - acceder_servicio: quiere acceder a un servicio concreto
  - consulta_general: no encaja en ninguna (el LLM decidirá)

Cada intención viene con un "template de enriquecimiento" que se agrega a la
query para mejorar el retrieval ChromaDB.

Uso típico:
  from app.intent_detector import detectar_intencion
  resultado = detectar_intencion("necesito plata para mis hijos")
  # resultado.intencion == "acceder_servicio"
  # resultado.entidades == ["subsidio", "beneficio"]
  # resultado.query_enriquecida == "subsidio beneficio plata hijos"
"""
import re
from dataclasses import dataclass, field
from app.text_normalizer import normalizar_basico, corregir_texto


# ---------------------------------------------------------------------------
# Estructura de resultado
# ---------------------------------------------------------------------------

@dataclass
class Intencion:
    """Resultado de la detección de intención."""
    intencion: str  # Clase de intención
    confianza: float  # 0.0 a 1.0
    entidades: list[str] = field(default_factory=list)  # Entidades detectadas
    query_enriquecida: str = ""  # Query expandida para retrieval
    contexto_extra: str = ""  # Contexto adicional para el prompt del LLM
    es_seguimiento: bool = False  # ¿Es continuación de tema anterior?


# ---------------------------------------------------------------------------
# Reglas de intención (orden importa: primera coincidencia gana)
# ---------------------------------------------------------------------------

# Palabras clave que indican TIPO de intención
_INTENCION_POR_PALABRAS = {
    # Estado de trámite / seguimiento
    "estado_tramite": [
        "estado", "avance", "proceso", "resultado", "ya me llego",
        "ya llego", "cuando llega", "cuando quedo", "cuando me llega",
        "cuando lo tengo", "cuando esta listo", "cuando puedo retirar",
        "ya quedo", "sigue mi tramite", "como va mi tramite",
        "mi solicitud", "mi peticion", "mi reclamo", "seguimiento",
        "Consultas CON Arquitectos de Turno", "certificado de numero",
        "aprobacion", "fue aprobado", "fue rechazado",
    ],
    # Queja / reporte / denuncia
    "queja_reportar": [
        "denuncio", "denuncia", "reportar", "reporte", "queja",
        "reclamo", "problema", "mal funcionamiento", "no funciona",
        "esta roto", "esta sucio", "hay un hoyo", "hay basura",
        "hay ratas", "hay cucarachas", "hay plagas", "ruido",
        "molestia", "molesta", "alboroto", "pelea", "golpe",
        "vandalismo", "robbery", "robo", "asalto",
        "arbol caido", "alumbrado", "luz apagada", "luz no funciona",
        "agua no sale", "agua cortada", "bache", "via en mal estado",
        "vereda rota", "acera rota", "contaminacion", "humo",
        "olor fuerte", "vertimiento", "desague tapado",
    ],
    # Contacto / hablar con alguien
    "contacto": [
        "hablar con", "llamar a", "telefono", "correo", "email",
        "direccion", "donde quedan", "donde queda la oficina",
        "atencion presencial", "ir a la municipalidad",
        "horario de atencion", "a que hora abren", "a que hora cierran",
        "como llego", "como llego alla", "direccion de la muni",
        "donde queda la muni", "muni",
    ],
    # Acceder a servicio específico
    "acceder_servicio": [
        "necesito", "quiero", "necesito sacar", "necesito obtener",
        "necesito renovar", "necesito tramitar", "como puedo",
        "como hago para", "como saco", "como tramito",
        "como obtengo", "como renuevo", "donde puedo",
        "donde saco", "donde tramito", "donde obtengo",
        "donde pago", "donde renovar",
        # Servicios directos
        "farmacia", "medicamento", "remedio", "receta",
        "vacuna", "vacunar", "castrar", "esterilizar",
        "veterinario", "garrapata", "desparasitar",
        "podologia", "podologo", "pie", "pies",
        "feria", "puesto", "vender",
        "curso", "taller", "capacitacion",
    ],
    # Búsqueda de información general
    "buscar_info": [
        "que es", "que son", "que haces", "como funciona",
        "cuales son", "cuales son los", "cuanto cuesta",
        "cuanto vale", "que requisitos", "que documentos",
        "que necesito", "que debo llevar", "que pasos",
        "horario", "cuando atienden", "cuando abren",
        "cuando es", "cuando vence", "cuando es la fecha",
    ],
}


# ---------------------------------------------------------------------------
# Entidades: categorías de trámites/servicios
# ---------------------------------------------------------------------------

_ENTIDADES_POR_PALABRAS = {
    # Salud / Bienestar
    "salud": [
        "farmacia", "medicamento", "remedio", "receta", "salud",
        "medico", "doctor", "enfermo", "enfermedad", "pastilla",
    ],
    "veterinaria": [
        "perro", "gato", "mascota", "animal", "veterinario",
        "vacuna", "castrar", "esterilizar", "garrapata", "desparasitar",
    ],
    "podologia": [
        "pie", "pies", "podologia", "podologo", "uña", "callon",
    ],
    # Subsidios / Beneficios
    "subsidio": [
        "subsidio", "ayuda", "plata", "dinero", "beneficio",
        "bono", "asignacion", "pension", "jubilacion",
        "fondo", "beca", "beca escolar",
    ],
    "ficha_social": [
        "ficha", "ficha social", "ficha proteccion", "registro social",
        "rsh", "registro de hogares",
    ],
    # Vehículos
    "vehiculo": [
        "auto", "vehiculo", "carro", "camioneta", "moto",
        "permiso", "circulacion", "patente vehicular",
    ],
    "licencia_conducir": [
        "licencia", "conducir", "manejo", "manejar", "examen de manejo",
    ],
    # Vivienda / Edificación
    "edificacion": [
        "construir", "construccion", "edificar", "edificacion",
        "ampliar", "ampliacion", "remodelar", "demoler", "demolicion",
        "obra", "permiso de obra",
    ],
    "vivienda": [
        "casa", "vivienda", "departamento", "domicilio", "hogar",
    ],
    # Comercio
    "comercio": [
        "negocio", "comercio", "tienda", "local", "patente comercial",
        "vender", "venta", "feria libre",
    ],
    # Animales / Plagas
    "plagas": [
        "rata", "ratas", "raton", "ratones", "cucaracha", "cucarachas",
        "plaga", "plagas", "fumigar", "desratizar", "desinsectar",
    ],
    # Arbolado / Espacios
    "arbolado": [
        "arbol", "arboles", "rama", "ramas", "poda", "vereda",
    ],
    "espacios": [
        "calle", "vereda", "parque", "plaza", "basural",
        "escombros", "basura", "limpieza",
    ],
    # Organizaciones
    "organizaciones": [
        "organizacion", "junta de vecinos", "sindicato", "cooperativa",
        "asociacion", "club", "fundar",
    ],
    # Trámites generales
    "certificados": [
        "certificado", "constancia", "constancia de",
    ],
    "permisos": [
        "permiso", "autorizacion", "habilitacion",
    ],
}


# ---------------------------------------------------------------------------
# Palabras que indican urgencia
# ---------------------------------------------------------------------------

_URGENCIA_PALABRAS = [
    "urgente", "ya", "rapido", "altiro", "al toque", "de inmediato",
    "no puedo esperar", "necesito ya", "hoy", "ahora", "ya mismo",
    "es urgente", "emergencia", "peligro", "peligroso",
]


# ---------------------------------------------------------------------------
# Funciones de detección
# ---------------------------------------------------------------------------

def _detectar_intencion_base(texto_norm: str) -> tuple[str, float]:
    """
    Detecta la intención principal por palabras clave.
    Devuelve (intencion, confianza).
    """
    mejor_intencion = "consulta_general"
    mejor_score = 0.0

    for intencion, palabras in _INTENCION_POR_PALABRAS.items():
        score = 0
        for palabra in palabras:
            if palabra in texto_norm:
                # Palabras más largas = más específicas = más peso
                score += len(palabra)
        if score > mejor_score:
            mejor_score = score
            mejor_intencion = intencion

    # Calcular confianza basada en cuántas palabras matchearon
    if mejor_score == 0:
        return "consulta_general", 0.3

    # Confianza: normalizada entre 0.5 y 1.0
    # Más palabras matchean = más confianza
    total_palabras_match = sum(
        1 for intencion_palabras in _INTENCION_POR_PALABRAS.values()
        for p in intencion_palabras if p in texto_norm
    )
    confianza = min(1.0, 0.5 + (total_palabras_match * 0.1))
    return mejor_intencion, confianza


def _detectar_entidades(texto_norm: str) -> list[str]:
    """Detecta categorías de entidades (trámites/servicios) en el texto."""
    entidades = []
    for entidad, palabras in _ENTIDADES_POR_PALABRAS.items():
        for palabra in palabras:
            if palabra in texto_norm:
                entidades.append(entidad)
                break  # Una match por categoría es suficiente
    return entidades


def _detectar_urgencia(texto_norm: str) -> bool:
    """True si el vecino parece urgido."""
    return any(palabra in texto_norm for palabra in _URGENCIA_PALABRAS)


def _construir_query_enriquecida(
    texto_original: str,
    texto_norm: str,
    intencion: str,
    entidades: list[str],
) -> str:
    """
    Construye una query enriquecida para el retrieval ChromaDB.
    Agrega términos de la intención y entidades detectadas.
    """
    extras = []

    # Agregar términos de la intención
    terminos_intencion = {
        "buscar_info": ["requisitos", "documentos", "informacion", "como"],
        "hacer_tramite": ["solicitud", "proceso", "pasos", "requisitos"],
        "estado_tramite": ["estado", "avance", "seguimiento"],
        "queja_reportar": ["reporte", "denuncia", "problema", "reclamo"],
        "contacto": ["contacto", "telefono", "correo", "direccion"],
        "acceder_servicio": ["servicio", "obtener", "solicitar"],
        "consulta_general": [],
    }
    extras.extend(terminos_intencion.get(intencion, []))

    # Agregar términos de entidades
    terminos_entidad = {
        "salud": ["farmacia", "medicamentos"],
        "veterinaria": ["atencion veterinaria", "mascota"],
        "podologia": ["centro podologico", "atencion podologica"],
        "subsidio": ["subsidio", "beneficio social"],
        "ficha_social": ["ficha de proteccion social", "registro social"],
        "vehiculo": ["permiso de circulacion", "vehiculo"],
        "licencia_conducir": ["licencia de conducir", "examen"],
        "edificacion": ["permiso de edificacion", "construccion"],
        "vivienda": ["vivienda", "domicilio"],
        "comercio": ["patente comercial", "comercio"],
        "plagas": ["beneficio sanitario", "desinsectacion"],
        "arbolado": ["servicio de arbolado", "poda"],
        "espacios": ["limpieza", "espacios publicos"],
        "organizaciones": ["organizacion social", "constitucion"],
        "certificados": ["certificado"],
        "permisos": ["permiso", "autorizacion"],
    }
    for entidad in entidades:
        extras.extend(terminos_entidad.get(entidad, []))

    # Construir query final
    vistos = set()
    unicos = []
    for t in extras:
        t_norm = normalizar_basico(t)
        if t_norm not in vistos:
            vistos.add(t_norm)
            unicos.append(t)

    if unicos:
        return f"{texto_original} {' '.join(unicos)}"
    return texto_original


def _construir_contexto_extra(
    intencion: str,
    entidades: list[str],
    es_urgente: bool,
) -> str:
    """
    Construye contexto extra para el prompt del LLM.
    Le dice al modelo QUÉ quiere hacer el vecino y con qué urgencia.
    """
    partes = []

    intenciones_texto = {
        "buscar_info": "El vecino está buscando información sobre un trámite o servicio.",
        "hacer_tramite": "El vecino quiere iniciar o realizar un trámite municipal.",
        "estado_tramite": "El vecino quiere saber el estado de un trámite en curso.",
        "queja_reportar": "El vecino quiere reportar un problema o hacer una queja.",
        "contacto": "El vecino busca datos de contacto u horarios de atención.",
        "acceder_servicio": "El vecino quiere acceder a un servicio municipal.",
        "consulta_general": "El vecino tiene una consulta general.",
    }
    if intencion in intenciones_texto:
        partes.append(intenciones_texto[intencion])

    if entidades:
        partes.append(f"Servicios relacionados: {', '.join(entidades)}.")

    if es_urgente:
        partes.append("⚠️ El vecino expresa urgencia.")

    return " ".join(partes)


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------

def detectar_intencion(
    texto: str,
    historial: list[dict] | None = None,
) -> Intencion:
    """
    Detecta la intención, entidades y urgencia de una pregunta del vecino.

    Args:
        texto: Pregunta original del vecino.
        historial: Historial de la conversación (para detectar seguimientos).

    Returns:
        Intencion con intencion, confianza, entidades, query_enriquecida
        y contexto_extra.
    """
    texto_norm = normalizar_basico(texto)
    texto_corr = corregir_texto(texto_norm)

    # 1. Detectar intención base
    intencion, confianza = _detectar_intencion_base(texto_corr)

    # 2. Detectar entidades
    entidades = _detectar_entidades(texto_corr)

    # 3. Detectar urgencia
    es_urgente = _detectar_urgencia(texto_corr)

    # 4. Detectar seguimiento (si el historial sugiere continuidad)
    es_seguimiento = False
    if historial and len(historial) >= 2:
        # Si las últimas 2-3 preguntas son muy cortas (1-3 palabras) o
        # contienen pronombres/demostrativos, probablemente es seguimiento
        ultimas = [m["content"] for m in historial[-3:] if m["role"] == "user"]
        for msg in ultimas:
            msg_norm = normalizar_basico(msg)
            if len(msg_norm.split()) <= 3 or any(
                pron in msg_norm
                for pron in ["el", "la", "los", "las", "ese", "esa",
                             "esto", "eso", "aqui", "y ", "que ", "como "]
            ):
                es_seguimiento = True
                break

    # 5. Si es seguimiento, boostear la confianza
    if es_seguimiento:
        confianza = min(1.0, confianza + 0.15)

    # 6. Construir query enriquecida para retrieval
    query_enriquecida = _construir_query_enriquecida(
        texto, texto_corr, intencion, entidades
    )

    # 7. Construir contexto extra para el LLM
    contexto_extra = _construir_contexto_extra(
        intencion, entidades, es_urgente
    )

    return Intencion(
        intencion=intencion,
        confianza=confianza,
        entidades=entidades,
        query_enriquecida=query_enriquecida,
        contexto_extra=contexto_extra,
        es_seguimiento=es_seguimiento,
    )
