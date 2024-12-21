import time
import io
from api_binance import *
import pandas as pd
from datetime import *
import pprint
import globales
import numpy as np
import csv
import keyboard
import yfinance as yf
from tkinter import *
import tkinter as tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import rutinas
from bd_conect import *
from api_chart import get_yfinance
from main_crypto import performa_asset

account = 'B0000001'
date = "2024-07-16"

f_desde = datetime.strptime(date, "%Y-%m-%d")
(diaria, iy) = select_diaria_performance(account=account, date=f_desde, accion='desde')

datos = pd.DataFrame(diaria, columns=iy)
datos.set_index('Date', inplace=True)
pdatos = datos.groupby('Date')[['value', 'nr_gyp', 'costo_base']].sum().reset_index()
pdatos['performa'] = pdatos['nr_gyp'] / pdatos['costo_base']

pdatos['retorno'] = pdatos['performa'].pct_change()
pdatos['CumPort'] = (1 + pdatos['retorno']).cumprod()

print(pdatos)

#print(df_sum[['Date', 'nr_gyp', 'costo_base', 'performa']])