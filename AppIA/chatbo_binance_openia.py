import os
import openai
from API_vehiculos import client_spot, ClientError

openai.api_key = os.environ["OPENAI_API_KEY"]
client = client_spot()


def chatbot(message):
    # Integra ChatGPT
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Actúa como un experto en trading. {message}",
        max_tokens=150
    )
    return response['choices'][0]['text']

def consultar_precio(symbol):
    ticker = client.get_ticker(symbol=symbol)
    return f"El precio actual de {symbol} es {ticker['lastPrice']} USDT."

# Ejemplo de interacción
print(chatbot("¿Qué opinas del mercado?"))
print(consultar_precio("BTCUSDT"))
