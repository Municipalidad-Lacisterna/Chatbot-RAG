"""
CLI interactivo para probar el chatbot por consola (con memoria por sesión).

Uso:
    ./venv/bin/python -m tests.chat_cli
Escribe 'salir' para terminar, o 'reset' para limpiar la sesión.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import rag_engine

SESSION_ID = "cli"  # una única sesión de la consola


def main():
    print("--- Chatbot municipal iniciado (escribe 'salir' para terminar) ---")
    print("    (escribe 'reset' para borrar el historial de la sesión)\n")

    while True:
        question = input("Usuario: ").strip()
        if question.lower() == "salir":
            break
        if question.lower() == "reset":
            rag_engine.clear_history(SESSION_ID)
            print("  [historial de sesión borrado]")
            continue
        if not question:
            continue

        answer = rag_engine.query_chatbot(question, SESSION_ID)
        print(f"Chatbot: {answer}\n")


if __name__ == "__main__":
    main()