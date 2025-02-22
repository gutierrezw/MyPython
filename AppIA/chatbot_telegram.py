from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, filters

# ⚠️ Reemplaza con tu Token de BotFather
TOKEN = "7517894179:AAG62H0YbMJH8puuI8Q4ARhXtDrNoNnvuWU"

# Función para responder al comando /start
def start(update: Update, context: CallbackContext):
    update.message.reply_text("¡Hola! Soy tu chatbot de Telegram en Windows.")

# Función para manejar mensajes de texto
def responder(update: Update, context: CallbackContext):
    mensaje_usuario = update.message.text.lower()
    if "hola" in mensaje_usuario:
        update.message.reply_text("¡Hola! ¿En qué puedo ayudarte?")
    elif "adiós" in mensaje_usuario:
        update.message.reply_text("¡Hasta luego!")
    else:
        update.message.reply_text("No entiendo, pero estoy aprendiendo. 😊")

# Configuración del bot
def main():
    updater = Updater(TOKEN, use_context)
    dp = updater.dispatcher

    # Agregar comandos
    dp.add_handler(CommandHandler("start", start))

    # Manejar mensajes de texto
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, responder))

    # Iniciar el bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
