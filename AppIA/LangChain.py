from dotenv import load_dotenv
import openai
import os

load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

response = llm.invoke(
    "Explain concisely like I was 12 ¿Qué es LangChain?"
)

print(response.content)
