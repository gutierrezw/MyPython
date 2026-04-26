from langchain_core.runnables import RunnableLambda
from Openia_basico import chat_openai
import time
import os

modelo = RunnableLambda(chat_openai)

# Hacer una consulta al modelo
respuesta = modelo.invoke("¿Qué es LangChain?")
print("Respuesta del modelo:", respuesta)
