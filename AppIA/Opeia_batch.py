from dotenv import load_dotenv
import openai
import time
import os

# Configura tu clave API
load_dotenv()
# openai.api_key = os.environ.get('OPENAI_API_KEY')
# openai.api_key = ('sk-svcacct-6sqkThxL2mTJTMKsjaATul9VdE7nHbFS02iBOH-kaB94we9vaBQIGUpKogVmpgw'
#                  '5IHQdcT3BlbkFJbYJSlBKNPUmEqa5jTxli5t5ygE9gVU7ar-n34pucC3DbkBeFEhJCbCMHwb8Dkg0PmskAA')



solicitudes = [
    "¿Qué es Python?",
    "¿Cómo funciona una red neuronal?",
    "¿Cuáles son las ventajas de la energía solar?",
    "Explica la mecánica cuántica en términos simples.",
    "Dame una receta de pasta carbonara.",
]

def procesar_por_lotes(solicitudes, tamaño_lote=2):
    try:
        for i in range(0, len(solicitudes), tamaño_lote):
            lote = solicitudes[i:i + tamaño_lote]
            respuestas = [
                openai.ChatCompletion.create(
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


procesar_por_lotes(solicitudes, tamaño_lote=2)
