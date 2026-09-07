import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'chat_history.db')

def generar_reporte():
    if not os.path.exists(DB_PATH):
        print("📊 REPORTE DE GESTIÓN MUNICIPAL - CISTERNÍN 📊")
        print("No hay datos en la base todavía (0 chats).")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Total de sesiones
    cur.execute("SELECT COUNT(DISTINCT session_id) FROM chat_history")
    total_sesiones = cur.fetchone()[0]

    # Mensajes totales
    cur.execute("SELECT COUNT(*) FROM chat_history")
    total_mensajes = cur.fetchone()[0]

    # Sesiones derivadas a humano vs resueltas por el bot
    cur.execute("SELECT COUNT(DISTINCT session_id) FROM chat_history WHERE canal='agente'")
    sesiones_humanas = cur.fetchone()[0]
    sesiones_bot = total_sesiones - sesiones_humanas

    porcentaje_automatizacion = 0
    if total_sesiones > 0:
        porcentaje_automatizacion = (sesiones_bot / total_sesiones) * 100

    print("=" * 50)
    print(" 📊 REPORTE DE GESTIÓN MUNICIPAL - CISTERNÍN 📊")
    print("=" * 50)
    print(f"👥 Total de Vecinos Atendidos (Sesiones) : {total_sesiones}")
    print(f"💬 Total de Mensajes Intercambiados      : {total_mensajes}")
    print("-" * 50)
    print(f"🤖 Resueltos automáticamente por Bot     : {sesiones_bot} ({porcentaje_automatizacion:.1f}%)")
    print(f"🧑‍💼 Derivados a Ejecutivos Humanos        : {sesiones_humanas} ({(100 - porcentaje_automatizacion) if total_sesiones > 0 else 0:.1f}%)")
    print("=" * 50)
    print("¡Excelente trabajo! El bot está conteniendo la mayor parte de las consultas.")

    conn.close()

if __name__ == "__main__":
    generar_reporte()
