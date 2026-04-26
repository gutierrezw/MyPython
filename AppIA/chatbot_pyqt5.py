import time
import sys
import os

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QTextEdit
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.runnables import RunnableLambda
from Openia_basico import chat_openai


modelo = RunnableLambda(chat_openai)

# Crear una plantilla de mensaje con LangChain
template = """
You are a helpful assistant. Respond concisely but informatively.

User: {user_input}
Assistant:
"""
prompt = PromptTemplate(input_variables=["user_input"], template=template)
chain = LLMChain(llm=llm, prompt=prompt)

class ChatbotApp(QWidget):
    def __init__(self):
        super().__init__()

        # Configurar la ventana principal
        self.setWindowTitle("Chatbot con PyQt5, LangChain y OpenAI")
        self.setGeometry(100, 100, 500, 600)

        # Crear el layout principal
        self.layout = QVBoxLayout()

        # Crear un área de chat para mostrar la conversación
        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)  # Solo lectura
        self.layout.addWidget(self.chat_area)

        # Crear una caja de texto para la entrada del usuario
        self.user_input = QLineEdit(self)
        self.layout.addWidget(self.user_input)

        # Crear un botón para enviar el mensaje
        self.send_button = QPushButton("Enviar", self)
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        # Establecer el layout
        self.setLayout(self.layout)

    def send_message(self):
        # Obtener el mensaje del usuario
        user_message = self.user_input.text()
        if user_message:
            # Mostrar el mensaje del usuario en el área de chat
            self.chat_area.append(f"Tú: {user_message}")
            # Obtener la respuesta del chatbot utilizando LangChain y OpenAI
            response = self.get_response(user_message)
            self.chat_area.append(f"Bot: {response}")
            # Limpiar la caja de texto de entrada
            self.user_input.clear()


    @staticmethod
    def get_response(self, user_message):
        # Obtener respuesta del chatbot usando LangChain
        response = chain.run(user_input=user_message)
        return response


if __name__ == "__main__":
    app = QApplication(sys.argv)
    chatbot = ChatbotApp()
    chatbot.show()
    sys.exit(app.exec_())
