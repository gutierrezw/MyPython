from dotenv import load_dotenv
import openai
import time
import os


# load_dotenv()
openai.api_key = ('sk-proj-5sAtCO7J_H4mG3ZH-Q3--IY0V3gIORDrZjncR3yDLVSNWTeCJ1tfaAfBKOaapJal029Xpbvqw'
                   'XT3BlbkFJIP91t7QqB3Wt_4wWBC6Z3t29rBgSUjKNljgU876jrBLC71ipVfvo7jY9acMKiJRbpvUBQMHvgA')

# Hacer una consulta a GPT
def chat(x_message=None):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": x_message}]
        )
        return response
    except Exception as e:
        print("Chat(): {}".format(e))

# Mostrar la respuesta
message = "¿Qué es LangChain?"
resp = chat(message)
print(resp)
