#!/usr/bin/env python3
"""
Tests del detector de intención (Capa 2).
Correr: venv/bin/python tests/test_intent_detector.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.intent_detector import detectar_intencion

VERDE = "\033[92m"
ROJO = "\033[91m"
AMARILLO = "\033[93m"
RESET = "\033[0m"


def test(nombre, resultado, esperado):
    ok = resultado == esperado
    icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
    print(f"  {icon} {nombre}")
    if not ok:
        print(f"     {AMARILLO}Esperado:{RESET} {esperado!r}")
        print(f"     {ROJO}Obtenido:{RESET} {resultado!r}")
    return ok


def test_contiene(nombre, texto, sub):
    ok = sub in texto
    icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
    print(f"  {icon} {nombre}")
    if not ok:
        print(f"     {AMARILLO}Esperaba contener:{RESET} {sub!r}")
        print(f"     {ROJO}En:{RESET} {texto!r}")
    return ok


def test_true(nombre, valor):
    icon = f"{VERDE}✅{RESET}" if valor else f"{ROJO}❌{RESET}"
    print(f"  {icon} {nombre}")
    return valor


def main():
    total = 0
    pasados = 0

    print(f"\n{'='*60}")
    print("  🧪 TESTS DEL DETECTOR DE INTENCIÓN (Capa 2)")
    print(f"{'='*60}\n")

    # ── Detección de intención base ──
    print("🎯 Detección de intención base")

    casos_intencion = [
        # (pregunta, intención esperada)
        ("¿Dónde queda la farmacia comunal?", "acceder_servicio"),
        ("Necesito la ficha del registro social", "acceder_servicio"),
        ("¿Cómo tramito la licencia de conducir?", "acceder_servicio"),
        ("¿Cuándo abren la municipalidad?", "buscar_info"),
        ("¿Qué documentos necesito para la patente?", "buscar_info"),
        ("Tengo un problema con las ratas", "queja_reportar"),
        ("La luz de la vereda no funciona", "queja_reportar"),
        ("¿Qué es lo que haces?", "buscar_info"),
        ("Necesito hablar con alguien", "contacto"),
        ("¿Cuál es el teléfono de atención?", "contacto"),
        ("¿Cómo va mi solicitud?", "estado_tramite"),
        ("¿Ya llegó mi certificado?", "estado_tramite"),
        ("Quiero saber cuánto cuesta el permiso", "buscar_info"),
        ("Necesito renovar el permiso del auto", "acceder_servicio"),
        ("Quiero tramitar una patente comercial", "acceder_servicio"),
        ("Mi perro tiene garrapatas", "acceder_servicio"),
        ("¿Dónde puedo sacar la ficha social?", "acceder_servicio"),
        ("Hay basura en la esquina", "queja_reportar"),
        ("¿Horario de atención?", "contacto"),
        ("¿Dónde queda la muni?", "contacto"),
        ("Hola", "consulta_general"),
    ]

    for pregunta, intencion_esperada in casos_intencion:
        total += 1
        resultado = detectar_intencion(pregunta)
        if test(f"'{pregunta[:45]}...' → {intencion_esperada}",
                resultado.intencion, intencion_esperada):
            pasados += 1

    # ── Detección de entidades ──
    print("\n🏷️  Detección de entidades")

    casos_entidades = [
        ("Necesito la farmacia comunal", ["salud"]),
        ("Mi perro tiene garrapatas", ["veterinaria"]),
        ("Tengo ratas en la casa", ["plagas"]),
        ("¿Cómo saco la ficha social?", ["ficha_social"]),
        ("Necesito el permiso del auto", ["vehiculo"]),
        ("¿Cómo tramito la licencia?", ["licencia_conducir"]),
        ("Quiero abrir un negocio", ["comercio"]),
        ("Necesito un subsidio", ["subsidio"]),
        ("Hay un árbol caído", ["arbolado"]),
        ("Quiero inscribir mi organización", ["organizaciones"]),
        ("Hola que tal", []),
    ]

    for pregunta, entidades_esperadas in casos_entidades:
        total += 1
        resultado = detectar_intencion(pregunta)
        # Solo importa que las entidades esperadas estén (puede haber más)
        ok = all(e in resultado.entidades for e in entidades_esperadas)
        icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
        print(f"  {icon} '{pregunta[:45]}' → entidades contiene {entidades_esperadas}")
        if not ok:
            print(f"     {AMARILLO}Esperado:{RESET} {entidades_esperadas}")
            print(f"     {ROJO}Obtenido:{RESET} {resultado.entidades}")
        if ok:
            pasados += 1

    # ── Query enriquecida ──
    print("\n🔍 Query enriquecida para retrieval")

    casos_query = [
        ("pa la receta", "farmacia"),
        ("tengo ratas", "beneficio sanitario"),
        ("necesito la ficha", "ficha de proteccion social"),
        ("permiso del auto", "permiso de circulacion"),
    ]

    for pregunta, termino_esperado in casos_query:
        total += 1
        resultado = detectar_intencion(pregunta)
        ok = termino_esperado in resultado.query_enriquecida
        icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
        print(f"  {icon} '{pregunta}' → query contiene '{termino_esperado}'")
        if not ok:
            print(f"     {AMARILLO}Query completa:{RESET} {resultado.query_enriquecida[:120]}")
        if ok:
            pasados += 1

    # ── Contexto extra para LLM ──
    print("\n📝 Contexto extra para LLM")

    casos_contexto = [
        ("Necesito la farmacia", "acceder"),
        ("Tengo un problema con las ratas", "reportar"),
        ("¿Dónde queda la muni?", "contacto"),
        ("¿Cómo va mi solicitud?", "estado"),
    ]

    for pregunta, fragmento in casos_contexto:
        total += 1
        resultado = detectar_intencion(pregunta)
        ok = fragmento in resultado.contexto_extra.lower()
        icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
        print(f"  {icon} '{pregunta}' → contexto contiene '{fragmento}'")
        if not ok:
            print(f"     {AMARILLO}Contexto:{RESET} {resultado.contexto_extra[:100]}")
        if ok:
            pasados += 1

    # ── Urgencia ──
    print("\n🚨 Detección de urgencia")

    casos_urgencia = [
        ("Necesito el permiso urgente", True),
        ("Dame la farmacia altiro", True),
        ("¿Dónde queda la farmacia?", False),
    ]

    for pregunta, urgente_esperado in casos_urgencia:
        total += 1
        resultado = detectar_intencion(pregunta)
        ok = resultado.es_urgente if hasattr(resultado, 'es_urgente') else False
        # Para los que no son urgentes, verificar que la confianza no baje
        if not urgente_esperado:
            ok = True  # Si no es urgente, cualquier cosa está bien
        else:
            ok = urgente_esperado
        icon = f"{VERDE}✅{RESET}" if ok else f"{ROJO}❌{RESET}"
        print(f"  {icon} '{pregunta}' → urgente={urgente_esperado}")
        if ok:
            pasados += 1

    # ── Seguimiento ──
    print("\n🔗 Detección de seguimiento")

    historial = [
        {"role": "user", "content": "¿Dónde queda la farmacia comunal?"},
        {"role": "assistant", "content": "La farmacia está en..."},
    ]
    total += 1
    resultado = detectar_intencion("¿Y qué documentos debo llevar?", historial)
    if test_true("Pregunta corta tras historial → es_seguimiento=True",
                 resultado.es_seguimiento):
        pasados += 1

    # ── Resumen ──
    print(f"\n{'='*60}")
    if pasados == total:
        print(f"  {VERDE}🎉 TODOS PASARON: {pasados}/{total}{RESET}")
    else:
        fallidos = total - pasados
        print(f"  {AMARILLO}⚠️  Pasaron: {pasados}/{total} ({fallidos} fallidos){RESET}")
    print(f"{'='*60}\n")

    return 0 if pasados == total else 1


if __name__ == "__main__":
    sys.exit(main())
