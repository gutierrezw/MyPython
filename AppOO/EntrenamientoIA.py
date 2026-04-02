from Modulos_Mysql import RepositorioOportunidadesBuySell
from Class_IA_modelos import ModeloOportunidadesSell
from Class_DashBot import Chatbot

Repositorio = RepositorioOportunidadesBuySell()
modelo = ModeloOportunidadesSell()
bot = Chatbot()

datos = bot.obtener_dataframe_entrenamiento_IA()
print(datos)

# oportunidades = Repositorio.obtener_por_tipo(tipo='venta')
# df = modelo..preparar_dataframe(oportunidades)
# modelo.entrenar(df)
# modelo.guardar("modelo_ventas.pkl")
