"""
Motor RAG del chatbot: pipeline LCEL (LangChain Expression Language).

Flujo completo (pensado para cuidar el presupuesto público):

1. Se recupera el contexto relevante (retrieval nativo de ChromaDB) y el
   historial corto de la sesión (memoria SQLite).
2. Se invoca la cadena LCEL con una salida ESTRUCTURADA (JSON) que indica
   si la información fue encontrada o no.
3. Si NO se encontró información (respuesta de fallo), en lugar de entrar
   en un bucle de alucinaciones se emite UN único mensaje de cierre rápido
   con derivación a un agente humano o teléfonos de contacto.

Consideraciones de costo (Ver docs/consideraciones_presupuesto.md):
- La respuesta se entrega en UN solo bloque de texto (1 mensaje = 1 cargo).
- Prioridad a la atención reactiva (no difusión masiva).
- Cierre rápido ante fallo para no consumir saldo con respuestas erróneas.
"""
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app import settings
from app import chat_memory
from app.database import retrieve

# Límite de caracteres del contexto a inyectar (ahorro de tokens: ~750 tokens)
_MAX_CONTEXT_CHARS = 3000


def _build_prompt_template() -> ChatPromptTemplate:
    """
    Plantilla del prompt con las reglas de ahorro de presupuesto.

    La salida es JSON estructurado: {"respuesta": str, "encontrado": bool}.
    Esto permite detectar cuándo el RAG no halló la respuesta y aplicar un
    cierre rápido con derivación, sin que el modelo alucine en un bucle.
    """
    instr = (
        "Eres Cisternin, el asistente virtual amable y cercano de la "
        "Municipalidad de La Cisterna. Tienes personalidad: hablas con calidez, "
        "optimismo y un toque de simpatía, pero siempre con respeto y "
        "profesionalismo. Eres la cara digital de tu comuna.\n"
        "Identidad: cuando te pregunten quién eres o cómo te llamas, preséntate: "
        "eres Cisternin, el asistente virtual de la Municipalidad de La Cisterna, "
        "y estás para orientar a los vecinos en sus trámites municipales. Esto es "
        "tu propia identidad, NO necesitas contexto para responderlo (usa "
        "\"encontrado\": true).\n"
        "Regla de formato: entrega TODA tu respuesta en UN único bloque de "
        "texto (saludo breve + información + cierre), sin dividirla en "
        "múltiples mensajes ni usar listas extensas.\n"
        "Regla de contenido: responde en español usando el contexto "
        "proporcionado. Adopta un tono CÁLIDO, CERCANO y CONCISO pero siempre "
        "respetuoso: ve al punto con el dato solicitado, trato amable y "
        "confiable. Saluda de vez en cuando de forma natural (ej. '¡Hola!', "
        "'¡Con gusto!', 'Claro que sí') y despide con calidez ('¿Necesitas algo "
        "más?', '¡Quedo atento/a!') sin pasarte de 1 a 3 frases salvo que el "
        "trámite realmente lo requiera. Usa 'usted' o 'tú' de forma natural y "
        "cercana.\n"
        
        "Regla de confidencialidad (BLINDAJE DE DATOS SENSIBLES): Si el usuario "
        "pregunta por datos sensibles que pudieran estar en los documentos "
        "(como RUTs, sueldos específicos, nombres de funcionarios, información "
        "privada o gastos), NO los entregues bajo ninguna circunstancia. "
        "Responde EXACTAMENTE con esta frase: 'Por políticas de privacidad, no "
        "puedo entregar información sensible por este medio. Puedes consultar "
        "estos datos directamente en el Portal de Transparencia de la Municipalidad "
        "de La Cisterna.' y marca \"encontrado\": true.\n"
        "Regla de saludo (anti-repetición): NO repitas la misma frase de "
        "apertura en cada respuesta. Varía el saludo según la pregunta o "
        "salta directamente al dato cuando el usuario hace una consulta "
        "concreta, sin saludo redundante. Evita fórmulas fijas como "
        "'Estimado Vecino' en todas las respuestas.\n"
        "Regla anti-alucinación (CRÍTICA): si la información NO está en el "
        "contexto o no la sabes, NO inventes NADA y NO la adivines. Marca "
        "\"encontrado\": false. No rellenes con fechas, montos, plazos ni "
        "datos que no aparezcan literalmente en el contexto. (La excepción es "
        "tu propia identidad/presentación, que sí puedes responder.)\n"
        "Regla de mensaje ante falta de información (IMPORTANTE): cuando no "
        "encuentres la información, NO generes excusas ni frases tipo 'el "
        "contexto no proporciona', 'no se indica', 'la información "
        "disponible no menciona', etc. En ese caso devuelve en el campo "
        "\"respuesta\" SOLO el texto vacío \"\" y marca \"encontrado\": false. "
        "El sistema se encarga de redirigir al vecino con una persona de "
        "atención; tú NO debes explicar que te falta contexto.\n"
        "Regla de datos concretos (correo/teléfono/contacto): cuando el "
        "usuario pida un dato puntual de contacto (un CORREO electrónico, un "
        "TELÉFONO, una dirección de envío para su trámite) y ese dato NO "
        "aparezca literalmente en el contexto, marca \"encontrado\": false. "
        "NO respondas con un mensaje tipo 'no se dispone / no contamos con / "
        "no existe tal dato' marcado como encontrado=true: eso es una "
        "alucinación encubierta. Si el contexto solo menciona 'vía email' o "
        "una página web genérica pero NO una dirección de correo concreta, "
        "marca encontrado=false.\n"
        "Regla de veracidad: nunca agregues números, fechas, requisitos o "
        "direcciones que no estén escritos en el contexto proporcionado.\n\n"
        "Devuelve ÚNICAMENTE un objeto JSON con dos campos:\n"
        '- "respuesta": el texto completo para el vecino.\n'
        '- "encontrado": true si respondiste con base en el contexto, '
        "false si no encontraste la información.\n"
        'Ejemplo: {{"respuesta": "...", "encontrado": true}}'
    )
    return ChatPromptTemplate.from_messages(
        [
            ("system", instr),
            (
                "human",
                "Contexto relevante:\n{context}\n\n"
                "Historial de la conversación:\n{history}\n\n"
                "Pregunta del usuario:\n{question}",
            ),
        ]
    )


def _make_llm():
    """Crea el modelo LLM según LLM_PROVIDER (google | ollama).

    - "google": Gemini. Usa `LLM_MODEL` y `GOOGLE_API_KEY` (free tier, costo
      $0). Es el valor por defecto para desarrollo, sin hardware extra.
    - "ollama": LLM local (Qwen2.5-VL) vía Ollama, para el servidor de
      producción con GPU. MongoDB no sale del servidor (soberanía total).

    Los imports de cada proveedor se hacen aquí (perezosos) para que un
    proyecto no necesite las dependencias del otro.
    """
    provider = (settings.LLM_PROVIDER or "google").lower().strip()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_HOST,
            temperature=0,
        )

    # Por defecto: Google Gemini (prototipo / desarrollo)
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        temperature=0,
        google_api_key=settings.GOOGLE_API_KEY or None,
    )


def build_chain():
    """Construye la cadena RAG: prompt → LLM → StrOutputParser."""
    llm = _make_llm()
    return _build_prompt_template() | llm | StrOutputParser()


# Cadena compartida (se crea una sola vez al importar el módulo)
_chain = build_chain()


def _build_transfer_offer_message() -> str:
    """
    Mensaje que ofrece transferir al vecino a una persona real del Panel de
    Atención al Vecino, con tono cálido y cercano (personalidad de Cisternin).
    Incluye el token [[TRANSFERIR]] para que el frontend muestre los botones
    Sí/No. Un solo mensaje (regla de ahorro).
    """
    return (
        f"¡Con gusto te ayudo con eso, vecino! Para darte la información "
        f"más completa y al día, te conecto con una persona del Panel de "
        f"Atención al Vecino, que atiende {settings.AGENTE_HORARIO_TEXTO}. "
        f"¿Quieres que te transfiera ahora?\n[[TRANSFERIR]]"
    )


def _parse_answer(raw: str, question: str) -> tuple[str, bool]:
    """
    Intenta parsear la salida JSON del LLM.

    Devuelve (texto_respuesta, encontrado). Si el JSON no se puede parsear
    (p. ej. el modelo devolvió texto plano), trata el resultado como texto
    y asume encontrado=True para no romper la conversación.
    """
    raw = (raw or "").strip()

    # Quitar delimitadores de código si el modelo los incluyó
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        data = json.loads(raw)
        respuesta = str(data.get("respuesta", "")).strip()
        encontrado = bool(data.get("encontrado", True))
        if respuesta:
            return respuesta, encontrado
        # Respuesta JSON válida pero con texto vacío: respetar el campo
        # "encontrado". Si es false (el modelo indica que no halló info),
        # devolver texto vacío + no encontrado para que el bot derive.
        # NO caer al fallback, que devolvería el JSON crudo como texto.
        return respuesta, encontrado
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: si el modelo devolvió texto sin JSON, usarlo tal cual
    return raw, True


# Frases clave que indican que el modelo NO encontró el dato puntual pedido
# aunque haya marcado "encontrado": true (alucinación encubierta). Si la
# respuesta contiene alguna, la tratamos como "no encontrado" para disparar
# la transferencia/derivación correcta.
_NEGACIONES_NO_INFO = [
    "no se dispone",
    "no se cuenta con",
    "no contamos con",
    "no disponemos de",
    "no existe",
    "no hay un correo",
    "no hay una direcci",
    "no hay teléfono",
    "no tiene un correo",
    "no proporciona",
    "no informa",
    "no se encontró",
    "no encontramos",
    "carecemos",
    "no se ha especificado",
    "no se especifica",
    "no figura",
    "no aparece",
    # Muletillas frecuentes del LLM cuando le falta contexto (deben tratarse
    # como "no encontrado" y redirigir al vecino, NUNCA mostrarse como tal)
    "el contexto no",
    "contexto no proporcion",
    "contexto no ofrece",
    "contexto no indica",
    "contexto no menciona",
    "contexto no detalla",
    "contexto no contiene",
    "no se indica",
    "no se menciona",
    "no se detalla",
    "no se proporcion",
    "no está disponible",
    "no esta disponible",
    "no hay información",
    "no tengo información",
    "no tengo la información",
    "no dispongo de",
    "la información disponible no",
    "según la información disponible",
    "información proporcionada no",
    "entre los documentos no",
    "en los documentos no",
    "no encuentro información",
    "no encuentro esa información",
]


def _es_respuesta_no_info(texto: str) -> bool:
    """True si el texto parece una negación de falta de dato concreto."""
    t = (texto or "").lower()
    return any(neg in t for neg in _NEGACIONES_NO_INFO)


# Patrones de frases con las que el LLM a veces responde POR SU CUENTA con
# intención de transferir al vecino a un humano (aunque marque "encontrado":
# true). En esos casos el frontend debe mostrar SÍ el botón de transferencia.
# Si no detectamos estas frases, el vecino vería el texto pero SIN el botón de
# "Sí, transfíerame" (el token [[TRANSFERIR]] no se agregaría). Estas frases
# indican que el bot no resolvió la consulta y debe ofrecer el traspaso real.
_FRASES_TRANSFERENCIA = [
    "lo transferiré",
    "transferiré de inmediato",
    "transferiré con",
    "lo derivaré",
    "le transferiré",
    "le derivaré",
    "transferir a",
    "derivar a",
    "un ejecutivo del panel",
    "ejecutivo del panel de atención",
    "panel de atención al vecino",
    "con una persona del panel",
    "asistirle personalmente",
    "atenderá personalmente",
    "un agente lo atender",
    "un agente te atender",
    "le atenderá un",
    "lo atiende un",
    "comunicar con un agente",
    "conectar con un agente",
    "con un ejecutivo",
]


def _es_respuesta_transferencia(texto: str) -> bool:
    """True si el texto (aunque marque 'encontrado') expresa intención de
    transferir al vecino a un humano. En ese caso el bot debe ofrecer SÍ el
    botón de transferencia."""
    t = (texto or "").lower()
    return any(fr in t for fr in _FRASES_TRANSFERENCIA)


# Preguntas sobre la propia identidad/presentación de Cisternin (quién es,
# cómo se llama, qué es, para qué sirve). Estas NO son trámites y el bot debe
# presentarse con calidez sin derivar a transferencia ni depender del RAG.

_PATRONES_SENSIBLES = [
    "sueldo", "salario", "remuneracion", "remuneración", "pago", "cuanto gana", "cuánto gana",
    "rut ", "r.u.t", "carnet", "cedula de identidad", "cédula de identidad",
    "honorario", "contrato de", "sumario", "despido", "finiquito",
    "gastos de", "boleta de", "factura de", "datos personales"
]

def _es_pregunta_sensible(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in _PATRONES_SENSIBLES)

def _respuesta_sensible() -> str:
    return (
        "Por políticas de privacidad, no puedo entregar información sensible "
        "o personal por este medio. Puedes consultar estos datos directamente en el "
        "Portal de Transparencia de la Municipalidad de La Cisterna."
    )


_PATRONES_CHISTE = ["chiste", "estoy aburrido", "cuentame algo", "cuéntame algo"]
_PATRONES_SED = ["tengo sed", "una chela", "cerveza", "botilleria", "botillería"]
_PATRONES_AGUANTE = ["aguante la cisterna", "arriba la cisterna", "mejor comuna"]

def _es_easter_egg(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in _PATRONES_CHISTE + _PATRONES_SED + _PATRONES_AGUANTE)

def _respuesta_easter_egg(texto: str) -> str:
    t = texto.lower()
    if any(p in t for p in _PATRONES_CHISTE):
        return "¡Jaja! ¿Quieres un chiste municipal? Ahí va: ¿Por qué el semáforo de Gran Avenida se puso rojo? ¡Porque lo pillaron haciendo un trámite sin sacar número! 🚦😂 Pero ya, volviendo a lo nuestro... ¿en qué te puedo ayudar?"
    if any(p in t for p in _PATRONES_SED):
        return "¡Uf, hace sed! Te recomendaría un buen mote con huesillo ahí en el Paradero 24. Eso sí, recuerda que beber alcohol en la vía pública amerita parte municipal, ¡así que pórtense bien, vecinos! 🥤😎 ¿Buscabas ayuda con algún trámite?"
    if any(p in t for p in _PATRONES_AGUANTE):
        return "¡Esa es la actitud, vecino! ¡Puro aguante La Cisterna! 💪❤️ Aquí estamos trabajando para que la comuna sea cada día mejor. ¿En qué trámite te puedo orientar hoy?"
    return "¡Qué buen sentido del humor! 😄 ¿En qué trámite municipal te ayudo hoy?"

_PATRONES_IDENTIDAD = [

    "tu nombre", "cómo te llamas", "como te llamas", "quién eres", "quien eres",
    "qué eres", "que eres", "qué haces", "que haces", "para qué sirves",
    "para que sirves", "eres un bot", "eres una ia", "eres cisternin",
    "cuál es tu nombre", "cual es tu nombre", "preséntate", "presentate",
    "tu función", "tu funcion", "a qué te dedicas", "a que te dedicas",
    "qué puedes hacer", "que puedes hacer", "cómo te llamas tu", "como te llamas tu",
    "como te llamas tu", "te llamas", "quien sos", "quién sos",
]


def _es_pregunta_identidad(question: str) -> bool:
    """True si la pregunta es sobre la identidad/presentación de Cisternin."""
    t = (question or "").lower().strip("?¡!¿¿. ")
    return any(p in t for p in _PATRONES_IDENTIDAD)


def _respuesta_identidad() -> str:
    """Presentación cálida y con la personalidad de Cisternin."""
    return (
        "¡Hola! Soy Cisternin, el asistente virtual de la Municipalidad de "
        "La Cisterna. Estoy aquí para orientarte en tus trámites municipales: "
        "permisos de circulación, licencias de conducir, beneficios sociales, "
        "patentes y mucho más. ¿En qué puedo ayudarte hoy, vecino?"
    )


def query_chatbot(question: str, session_id: str = None) -> str:
    """
    Procesa una pregunta del usuario con arquitectura RAG y memoria.

    1. Recupera los fragmentos más relevantes de la base vectorial.
    2. Recupera el historial corto de la sesión.
    3. Invoca la cadena solicitando salida estructurada (JSON).
    4. Si no se encontró información, emite cierre rápido con derivación.
    5. Persiste la interacción (user + assistant) en la memoria.
    """
    session_id = session_id or "default"

    from app import session_state

    # Guardar el texto original que escribió el vecino (puede diferir de la
    # pregunta pendiente en el caso "confirmar")
    mensaje_usuario = question

    # 0. Timeout de inactividad ("¿hay alguien ahí?") y Rate Limiting:
    #    - Si el vecino envía demasiados mensajes rápido, lo frenamos (rate limit).
    #    - Si la sesión llevaba > 5 min inactiva, el bot pregunta "¿hay...
    accion = session_state.evaluar(session_id, question)

    if accion["accion"] == "bloquear":
        aviso = (
            "¡Wow, vas muy rápido! Dame un respiro de unos segunditos "
            "para poder procesar todo. 🙏"
        )
        # No lo guardamos en la memoria para que el historial no se llene de
        # bloqueos si el usuario (o bot malicioso) sigue insistiendo.
        return aviso


    if accion["accion"] == "advertencia":
        aviso = accion["mensaje"]
        # Persistir el intento con groseria y la advertencia
        chat_memory.add_message(session_id, "user", question)
        chat_memory.add_message(session_id, "assistant", aviso)
        return aviso

    if accion["accion"] == "preguntar":
        aviso = (
            "¿Hay alguien ahí? Lleva un rato sin responder, por eso le "
            "pregunto. Si está ahí, escriba cualquier mensaje para continuar "
            "con su consulta."
        )
        # Persistir en memoria la pregunta que motivó el aviso (como user) y
        # el aviso mismo (como assistant) para mantener el historial coherente.
        chat_memory.add_message(session_id, "user", question)
        chat_memory.add_message(session_id, "assistant", aviso)
        return aviso

    if accion["accion"] == "cerrar":
        session_state.reset(session_id)
        despedida = accion.get("mensaje_personalizado") or (
            "Como no hubo respuesta, he cerrado esta conversación. Cuando "
            "quiera retomar, puede volver a escribirme; con gusto le atenderé. "
            "Que tenga un buen día."
        )
        # Persistir el intento del vecino y la despedida
        chat_memory.add_message(session_id, "user", question)
        chat_memory.add_message(session_id, "assistant", despedida)
        return despedida

    # En el caso "confirmar" se procesa la pregunta pendiente original.
    if accion["accion"] == "confirmar":
        question = accion.get("pregunta", question)

# 0c. Corto-circuito: Datos Sensibles
    if _es_pregunta_sensible(question):
        respuesta_sensible = _respuesta_sensible()
        chat_memory.add_message(session_id, "user", question)
        chat_memory.add_message(session_id, "assistant", respuesta_sensible)
        return respuesta_sensible

    # 0b. Preguntas de identidad/presentación de Cisternin
    # inmediato con calidez (personalidad), SIN pasar por el RAG ni derivar a
    # transferencia. Esto garantiza que "¿cómo te llamas?" o "¿quién eres?"
    # siempre obtengan una respuesta propia.
    if _es_pregunta_identidad(question):
        respuesta_identidad = _respuesta_identidad()
        chat_memory.add_message(session_id, "user", mensaje_usuario)
        chat_memory.add_message(session_id, "assistant", respuesta_identidad)
        return respuesta_identidad


    # 0d. Corto-circuito: Easter Eggs (Humor municipal)
    if _es_easter_egg(question):
        respuesta_ee = _respuesta_easter_egg(question)
        chat_memory.add_message(session_id, "user", question)
        chat_memory.add_message(session_id, "assistant", respuesta_ee)
        return respuesta_ee

    # 1. Recuperar contexto de documentos

    docs = retrieve(question, k=settings.TOP_K)
    # Defensa en profundidad: eliminar posibles None/entradas vacías que
    # podrían romper el join (p. ej. en colecciones recién vaciadas o con
    # documentos sin contenido).
    docs = [d for d in docs if isinstance(d, str) and d.strip()]
    context = "\n\n".join(docs) if docs else "No hay información disponible."
    if len(context) > _MAX_CONTEXT_CHARS:
        context = context[:_MAX_CONTEXT_CHARS] + "..."

    # 2. Recuperar historial corto de la sesión
    history = chat_memory.get_history(session_id)
    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in history
    ) or "(sin historial previo)"

    # 3. Invocar la cadena RAG (salida estructurada)
    answer = _chain.invoke(
        {
            "question": question,
            "context": context,
            "history": history_text,
        }
    )

    # 4. Parsear la respuesta estructurada
    respuesta_texto, encontrado = _parse_answer(answer, question)
    # Defensa en profundidad: aunque el modelo marque "encontrado": true, si la
    # respuesta es en realidad una negación de falta de dato concreto
    # ("no se dispone de correo..."), la tratamos como no encontrado para
    # ofrecer la transferencia/derivación correcta (anti-alucinación).
    if encontrado and _es_respuesta_no_info(respuesta_texto):
        encontrado = False

    # El LLM a veces responde POR SU CUENTA con intención de transferir al
    # vecino a un humano (p. ej. "lo transferiré de inmediato con un ejecutivo
    # del Panel...") pero marcando "encontrado": true. En ese caso NO se
    # forzaba el token y el vecino veía el texto SIN el botón de transferencia.
    # Detectamos esa intención y garantizamos el token [[TRANSFERIR]].

    # Cada vez que el bot no pueda responder, SIEMPRE se ofrece la opción de
    # transferir a un agente humano (token [[TRANSFERIR]] que muestra Sí/No).
    # La disponibilidad real del agente se resuelve al conectar el WebSocket,
    # no aquí, para que el vecino nunca pierda la opción.
    if not encontrado:
        respuesta_texto = _build_transfer_offer_message()
    elif "[[TRANSFERIR]]" not in respuesta_texto and _es_respuesta_transferencia(respuesta_texto):
        # El modelo expresó que transferirá, pero sin token. Conservamos su
        # texto (es válido) y le agregamos el token al final para que el
        # frontend muestre el botón "Sí, transfíerame".
        _tf = respuesta_texto.rstrip()
        respuesta_texto = _tf + ("\n" if not _tf.endswith("\n") else "") + "[[TRANSFERIR]]"

    # 5. Persistir la interacción en la memoria
    chat_memory.add_message(session_id, "user", mensaje_usuario)
    chat_memory.add_message(session_id, "assistant", respuesta_texto)

    return respuesta_texto


def get_history(session_id: str) -> list[dict]:
    """Expone el historial de una sesión (para la API o depuración)."""
    return chat_memory.get_history(session_id)


def clear_history(session_id: str):
    """Limpia el historial de una sesión determinada."""
    chat_memory.clear_session(session_id)