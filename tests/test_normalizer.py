#!/usr/bin/env python3
"""
Tests del normalizador de texto (Capa 1: modismos y comprensión).
Correr: venv/bin/python tests/test_normalizer.py
"""
import sys
import os

# Añadir la raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.text_normalizer import (
    normalizar_basico,
    corregir_texto,
    expandir_query,
    normalizar_para_patrones,
    _quitar_tildes,
)

# Colores para output
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


def main():
    total = 0
    pasados = 0

    print(f"\n{'='*60}")
    print("  🧪 TESTS DEL NORMALIZADOR DE TEXTO")
    print(f"{'='*60}\n")

    # ── Nivel 1: Normalización básica ──
    print("📝 Nivel 1: Normalización básica")
    tests_n1 = [
        ("Mayúsculas", normalizar_basico("FARMACIA COMUNAL"), "farmacia comunal"),
        ("Tildes", normalizar_basico("¿Dónde queda la farmacia?"), "donde queda la farmacia"),
        ("Signos especiales", normalizar_basico("¡Hola! ¿Cómo estás?"), "hola como estas"),
        ("Espacios extra", normalizar_basico("  hola   mundo  "), "hola mundo"),
        ("Mezcla", normalizar_basico("¿DÓNDE ESTÁ EL PERMISO DEL AUTO?!"), "donde esta el permiso del auto"),
        ("Sin cambios", normalizar_basico("hola"), "hola"),
        ("Vacío", normalizar_basico(""), ""),
        ("None", normalizar_basico(None), ""),
        ("Comillas y paréntesis", normalizar_basico('El "permiso" del auto (2026)'), "el permiso del auto 2026"),
    ]
    for nombre, res, esp in tests_n1:
        total += 1
        if test(nombre, res, esp):
            pasados += 1

    # ── Nivel 1b: Quitar tildes (función interna) ──
    print("\n📝 Nivel 1b: Quitar tildes")
    tests_tildes = [
        ("á→a", _quitar_tildes("áéíóú"), "aeiou"),
        ("ñ→n", _quitar_tildes("niño"), "nino"),
        ("ü→u", _quitar_tildes("pingüino"), "pinguino"),
        ("Mezcla", _quitar_tildes("Cisternaación"), "Cisternaacion"),
    ]
    for nombre, res, esp in tests_tildes:
        total += 1
        if test(nombre, res, esp):
            pasados += 1

    # ── Nivel 2: Corrección ortográfica + abreviaciones ──
    print("\n📝 Nivel 2: Corrección + abreviaciones")
    tests_n2 = [
        ("Error 'zirculacion'", corregir_texto("permiso de zirculacion"), "permiso de circulacion"),
        ("Error 'komunal'", corregir_texto("farmacia komunal"), "farmacia comunal"),
        ("Error 'condusir'", corregir_texto("licencia de condusir"), "licencia de conducir"),
        ("Error 'subcidio'", corregir_texto("subcidio unico familiar"), "subsidio unico familiar"),
        ("Error 'pencion'", corregir_texto("pencion de vejez"), "pension de vejez"),
        ("Error 'construcion'", corregir_texto("permiso de construcion"), "permiso de construccion"),
        ("Abrev 'pa'", corregir_texto("pa la receta"), "para la receta"),
        ("Abrev 'pa el'", corregir_texto("pa el auto"), "para el vehiculo particular"),
        ("Abrev 'toy'", corregir_texto("toy en la farmacia"), "estoy en la farmacia"),
        ("Abrev 'na'", corregir_texto("na que ver"), "nada que ver"),
        ("Modismo 'altiro'", corregir_texto("dame el permiso altiro"), "dame el permiso de inmediato"),
        ("Mezcla error+abrev", corregir_texto("pa farmacia komunal"), "para farmacia comunal"),
    ]
    for nombre, res, esp in tests_n2:
        total += 1
        if test(nombre, res, esp):
            pasados += 1

    # ── Nivel 3: Expansión de query (sinónimos → trámites) ──
    print("\n📝 Nivel 3: Expansión de query (sinónimos)")

    # Test farmacia
    res = expandir_query("pa la receta")
    tiene_farmacia = "farmacia comunal" in res
    total += 1
    if test("Farmacia: 'pa la receta' menciona 'farmacia comunal'", tiene_farmacia, True):
        pasados += 1

    # Test permiso circulación
    res = expandir_query("donde pago el permiso del auto")
    tiene_permiso = "permiso de circulacion" in res
    total += 1
    if test("Permiso: 'permiso del auto' menciona 'permiso de circulacion'", tiene_permiso, True):
        pasados += 1

    # Test licencia
    res = expandir_query("sacar licencia nueva")
    tiene_licencia = "licencia de conducir" in res
    total += 1
    if test("Licencia: 'sacar licencia' menciona 'licencia de conducir'", tiene_licencia, True):
        pasados += 1

    # Test ficha social
    res = expandir_query("necesito la ficha esa del registro")
    tiene_ficha = "ficha de proteccion social" in res
    total += 1
    if test("Ficha: 'ficha esa del registro' menciona 'ficha de proteccion social'", tiene_ficha, True):
        pasados += 1

    # Test veterinaria
    res = expandir_query("tengo un perro con garrapatas")
    tiene_vet = "atencion veterinaria" in res
    total += 1
    if test("Veterinaria: 'perro con garrapatas' menciona 'atencion veterinaria'", tiene_vet, True):
        pasados += 1

    # Test plagas
    res = expandir_query("tengo ratas en la casa")
    tiene_plaga = "beneficio sanitario domiciliario" in res
    total += 1
    if test("Plagas: 'tengo ratas' menciona 'beneficio sanitario domiciliario'", tiene_plaga, True):
        pasados += 1

    # Test=query que NO matchea nada (queda igual)
    res = expandir_query("hola que tal")
    total += 1
    if test("Genérico: 'hola que tal' queda igual (sin expansión)", res, "hola que tal"):
        pasados += 1

    # ── Nivel combinado: normalización + patrones ──
    print("\n📝 Nivel combinado: Patrones con normalización")
    tests_comb = [
        ("Identidad con tildes", normalizar_para_patrones("¿Quién eres tú?"), "quien eres tu"),
        ("Sensible con mayúsculas", normalizar_para_patrones("¿CUÁNTO GANA el alcalde?"), "cuanto gana el alcalde"),
        ("Despedida informal", normalizar_para_patrones("Nah, na que ver po"), "nah na que ver po"),
        ("Identidad informal", normalizar_para_patrones("¿Quién SOS, weón?"), "quien sos weon"),
    ]
    for nombre, res, esp in tests_comb:
        total += 1
        if test(nombre, res, esp):
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
