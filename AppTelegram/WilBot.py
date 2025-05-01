from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Tu TOKEN de Bot de Telegram
TOKEN = '7900794114:AAH0xhQTDsIvqNxD459ZMc8g0PxPYSq68dE'
keyboard = [
    [InlineKeyboardButton("Comprar", callback_data='comprar')],
    [InlineKeyboardButton("Vender", callback_data='vender')],
    [InlineKeyboardButton("Visitar Binance", url='https://binance.com')]
]
reply_markup = InlineKeyboardMarkup(keyboard)


async def run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await update.message.reply_text('¡Hola! Soy tu bot de órdenes. Escribí /comprar o /vender.')
    await  update.message.reply_text('¿Qué deseas hacer?', reply_markup=reply_markup)

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        asset = context.args[0]
        cantidad = context.args[1]
        # Acá podrías enviar la orden a tu sistema
        respuesta = f"Orden de COMPRA recibida: {cantidad} de {asset}"
        await update.message.reply_text(respuesta)
    except IndexError:
        await update.message.reply_text('Formato incorrecto. Usa: /comprar ACTIVO CANTIDAD')

async def vender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        asset = context.args[0]
        cantidad = context.args[1]
        # Acá podrías enviar la orden a tu sistema
        respuesta = f"Orden de VENTA recibida: {cantidad} de {asset}"
        await update.message.reply_text(respuesta)
    except IndexError:
        await update.message.reply_text('Formato incorrecto. Usa: /vender ACTIVO CANTIDAD')

# Función para cualquier texto no reconocido
async def desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Comando no reconocido. ¿Qué dijiste?')

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", run))
app.add_handler(CommandHandler("comprar", comprar))
app.add_handler(CommandHandler("vender", vender))

# Cualquier mensaje que no sea comando va a desconocido
from telegram.ext import MessageHandler, filters
app.add_handler(MessageHandler(filters.TEXT, desconocido))


print("Bot corriendo...")
app.run_polling()
