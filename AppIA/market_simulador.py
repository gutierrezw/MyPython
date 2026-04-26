from Class_DataFrame import get_yfinance
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.dates import date2num
from mplfinance.original_flavor import candlestick_ohlc


def serie_datos(symbol=None, period='2y'):
    activo, pdatos = get_yfinance(ticket=symbol, vehiculo='download', period=period, interval='1h')

    date = pdatos.index
    return pdatos, date

# --- Simulación de Datos OHLC ---
np.random.seed(42)
n_periodos = 50  # Número de velas a simular
precio_inicial = 100
datos, fechas = serie_datos(symbol='HASI', period='2y')




# Generamos fechas horarias
# fechas = pd.date_range(start='2025-02-16 09:00', periods=n_periodos, freq='H')
# datos = []
# prev_close = precio_inicial


"""
for fecha in fechas:
    # Para cada vela, el precio de apertura es el cierre de la vela anterior
    open_ = prev_close
    # Simulamos un cambio aleatorio para determinar el cierre
    cambio = np.random.normal(loc=0, scale=1)
    close = open_ + cambio
    # Generamos el máximo y mínimo de la vela
    high = max(open_, close) + np.random.uniform(0, 0.5)
    low = min(open_, close) - np.random.uniform(0, 0.5)
    datos.append((fecha, open_, high, low, close))
    prev_close = close

# Convertimos los datos en un DataFrame
df = pd.DataFrame(datos, columns=['Date', 'Open', 'High', 'Low', 'Close'])

# Convertimos las fechas a números para poder graficarlas con candlestick_ohlc
df['Fecha_num'] = df['Fecha'].apply(date2num)

"""
print(datos.index)
print(datos.columns)
print(datos)
# Convertimos las fechas a números para poder graficarlas con candlestick_ohlc
datos.reset_index(inplace=True)
datos['Fecha_num'] = datos['Datetime'].apply(date2num)

# --- Configuración de la Figura y Animación ---
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_title("Simulación de Gráfico de Velas (Candlestick)")


def update(frame):
    ax.clear()  # Se limpia el eje para actualizar la gráfica
    # Seleccionamos los datos hasta el frame actual
    datos_actuales = datos.iloc[:frame + 1]

    # Configuramos títulos, etiquetas y cuadrícula
    ax.set_title("Simulación de Gráfico de Velas (Candlestick)")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Precio")
    ax.grid(True)

    # Ajustamos los límites del eje X en función de los datos actuales
    ax.set_xlim(datos_actuales['Fecha_num'].min() - 0.01,
                datos_actuales['Fecha_num'].max() + 0.01)

    # Convertimos los datos actuales en una lista de tuples con el formato requerido:
    # (fecha_num, open, high, low, close)
    ohlc = list(zip(datos_actuales['Fecha_num'],
                    datos_actuales['Open'],
                    datos_actuales['High'],
                    datos_actuales['Low'],
                    datos_actuales['Close']))

    # Dibujamos las velas; el parámetro width controla el ancho de cada vela
    candlestick_ohlc(ax, ohlc, width=0.02, colorup='g', colordown='r', alpha=0.8)

    # Formateamos el eje X para que muestre las fechas correctamente
    ax.xaxis_date()

    return ax,


# Creamos la animación. Se actualiza cada 500 milisegundos y se recorren los frames (cada vela)
ani = FuncAnimation(fig, update, frames=np.arange(0, len(datos)), interval=500, blit=False, repeat=False)

plt.show()
