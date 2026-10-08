import re

with open("app/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Añadir el import de agentes_disponibles_ahora si no está
if "agentes_disponibles_ahora" not in content:
    content = content.replace(
        "from app import rag_engine",
        "from app import rag_engine\nfrom app.handoff import agentes_disponibles_ahora\nfrom app import settings"
    )

# 2. Modificar el /query para bloquear en horario hábil si está activo el modo piloto
query_patch = """def query(request: QueryRequest):
    \"\"\"Responde a una pregunta del usuario, con memoria por sesión.\"\"\"
    # --- INTERRUPTOR MODO PILOTO ---
    if getattr(settings, "MODO_PILOTO_WHATSAPP", False) and agentes_disponibles_ahora():
        return QueryResponse(
            answer=f"¡Hola! 🏢 En este momento estamos en horario de atención con nuestros ejecutivos municipales. Por favor, comunícate directamente aquí:\n\n👉 *Hablar por WhatsApp:* {settings.WHATSAPP_BUSINESS_URL}",
            session_id=request.session_id
        )
"""
# Reemplazar la firma de def query (asumiendo que empieza con def query(request: QueryRequest): y un docstring)
# Usaremos regex para inyectarlo al inicio de la función query.
pattern = r'(def query\(request: QueryRequest\):\s+"""Responde a una pregunta del usuario, con memoria por sesión."""\n)'
content = re.sub(pattern, query_patch, content)

# 3. Añadir el endpoint /ui_config al final del archivo
ui_config_endpoint = """

@app.get("/ui_config")
def ui_config():
    return {
        "modo_piloto": getattr(settings, "MODO_PILOTO_WHATSAPP", False),
        "horario_habil": agentes_disponibles_ahora(),
        "whatsapp_url": getattr(settings, "WHATSAPP_BUSINESS_URL", "")
    }
"""
content += ui_config_endpoint

with open("app/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("main.py parchado exitosamente.")
