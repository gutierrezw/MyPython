import tkinter as tk
from tkinter import scrolledtext
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain.chains import LLMChain
from Openia_basico import chat_openai

class ChatBot(tk.Frame):
    def __init__(self, parent=None, title=None, colors=None):
        super().__init__(parent)


        # Crea un modelo de chat con Langchain
        template = "Eres un chatbot amigable. Responde a las preguntas de manera clara y concisa. Pregunta: {input}"
        prompt = PromptTemplate(input_variables=["input"], template=template)
        self.chain = RunnableLambda(chat_openai)

        self.root = parent
        self.root.title("Chatbot Langchain")
        self.root.geometry("400x450")

        # Permitir que la ventana se expanda con weight
        self.root.grid_rowconfigure(0, weight=1)     # La fila 0 (chat) se expande
        self.root.grid_columnconfigure(0, weight=1)  # La columna 0 (chat) se expande
        self.root.grid_columnconfigure(1, weight=1)  # La columna 1 (entrada) también

        # Ventana para mostrar el chat
        self.chat_window = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=50, height=20, state=tk.DISABLED)
        self.chat_window.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)


        # Botón para enviar el mensaje
        self.send_button = tk.Button(self.root, text="Enviar", width=6, command=self.enviar_mensaje)
        self.send_button.grid(row=1, column=0, pady=10)

        # Campo de entrada de texto
        self.entry = tk.Entry(self.root, width=50)
        self.entry.grid(row=1, column=1, sticky="ew")


# Función para manejar el evento de enviar un mensaje
    def enviar_mensaje(self):
        try:
            user_input = self.entry.get()
            self.chat_window.insert(tk.END, "Tú: " + user_input + "\n")

            # Limpia el campo de entrada
            self.entry.delete(0, tk.END)

            response = self.chain.invoke(user_input)

            # responde y desplaza la ventana para mostrar la última respuesta
            self.chat_window.config(state=tk.NORMAL)
            self.chat_window.insert(tk.END, "Chatbot: " + response + "\n")
            self.chat_window.yview(tk.END)
            self.chat_window.config(state=tk.DISABLED)
        except EncodingWarning as e:
            print("enviar_mensaje(): {}".format(e))


if __name__ == "__main__":
    window = tk.Tk()
    Cbox = ChatBot(window)
    Cbox.grid()
    Cbox.mainloop()
