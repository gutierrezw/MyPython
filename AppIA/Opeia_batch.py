from dotenv import load_dotenv
from openai import OpenAI
import time
import os

# Configura tu clave API
# load_dotenv()
# print(os.environ.get('OPENAI_API_KEY'))
# OpenAI.api_key = os.environ.get('OPENAI_API_KEY')

Ai = OpenAI()

def procesar_por_lotes(solicitudes=None, tamaño_lote=2):
    try:
        for i in range(0, len(solicitudes), tamaño_lote):
            lote = solicitudes[i:i + tamaño_lote]
            respuestas = [
                Ai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": pregunta}]
                )["choices"][0]["message"]["content"]
                for pregunta in lote
            ]
            for j, respuesta in enumerate(respuestas):
                print(f"Respuesta {i + j + 1}: {respuesta}\n")
            time.sleep(1)  # Evita exceder los límites de la API

    except EncodingWarning as e:
        print("procesar_por_lotes(): {}".format(e))

solicitudes = [
    "¿Qué es langchain?",
    "¿Cómo funciona langchain?",
    "¿Cuáles son las ventajas de langchain?",
    "Explica la mecánica cuántica en términos simples.",
    "Dame una receta de pasta carbonara.",
]
procesar_por_lotes(solicitudes, tamaño_lote=2)

