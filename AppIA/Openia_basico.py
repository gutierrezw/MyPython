from openai import OpenAI
import time
import os

Cai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])


# Hacer una consulta a GPT
def chat_openai(x_message=None):
    try:
        response = Cai.chat.completions.create(model="gpt-4o-mini",
                                               messages=[{"role": "user", "content": x_message}])
        return response.choices[0].message.content
    except Exception as e:
        print("Chat(): {}".format(e))


if __name__ == "__main__":
    message = "¿Qué es LangChain?"
    resp = chat_openai(message)

    print(resp)
