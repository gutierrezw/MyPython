import tkinter as tk
from datetime import datetime, timedelta

import mplfinance as mpf
import ta
import yfinance as yf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ta.momentum import RSIIndicator


def chart(keys, win):
    print(keys)
    Tick = keys['ticket']
    Prcm = keys['avgCost']
    Pobj = keys['Obje']
    titl = keys['name']

    hoy = datetime.now()
    ini = hoy - timedelta(days=1800)
    print('inicio ', ini)
    #
    #
    #  1d, 1wk 1mo 3mo
    fre = "1mo"
    datos = yf.download(Tick, start=ini, progress=False, interval=fre)

    rsi_indicator = RSIIndicator(close=datos['Close'], window=13)
    sh = rsi_indicator.rsi()
    ln = sh.rolling(window=55).mean()

    fup = dict(y1=sh.values, y2=ln.values, where=(sh > ln), color="green",alpha=0.3,interpolate=True)
    fdn = dict(y1=sh.values, y2=ln.values, where=(sh < ln), color="red",  alpha=0.3,interpolate=True)
    lim = dict(y1=30, y2=70, alpha=0.2, color='white')

    datos['EMA144'] = ta.trend.ema_indicator(datos['Close'], window=144)
    datos['EMA055'] = ta.trend.ema_indicator(datos['Close'], window=55)
    datos['EMA021'] = ta.trend.ema_indicator(datos['Close'], window=21)
    datos['EMA009'] = ta.trend.ema_indicator(datos['Close'], window=9)

    print(datos.shape[0], sh.shape[0], len(datos['EMA144']), len(datos['EMA055']))
    rsi_plot = [
                 mpf.make_addplot(datos['EMA021'], color='blue', panel=0)
               , mpf.make_addplot(datos['EMA009'], color='white', panel=0)
                ]


    reg_plot = [dict(y1=Prcm, y2=Pobj, alpha=0.3, color='green')]

    mc = mpf.make_marketcolors(base_mpf_style='charles', up='green', down='red', volume={'up':'blue','down':'orange'})
    st = mpf.make_mpf_style(base_mpl_style='dark_background', marketcolors=mc, y_on_right=True, edgecolor='grey')

    fig, axs = mpf.plot(datos, type='candle', style=st, tight_layout=False,
                        datetime_format=' %m-%y', xrotation=60,
                        figscale=2, panel_ratios=(1, .3), figsize=(5.0, 3.5),
                        axisoff=False, volume=True,
                        main_panel=0, volume_panel=1, num_panels=2,
                        addplot=rsi_plot,
                        #fill_between=reg_plot,
                        ylabel_lower=' ',
                        scale_width_adjustment=dict(ohlc=1.5, lines=0.45, candle=1.5, volume=.8),
                        returnfig=True)


    canvas = FigureCanvasTkAgg(fig,  master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(pady=10)

ch = tk.Tk()
dw=700
dh=400
df=190
dimension = "%dx%d+0+0" % (dw,dh)
ch.geometry(dimension)
ch.title("Prueba v4.0")
ch.config(bg="black")
frame = tk.Frame(ch)
frame.pack()

keys = dict()
keys['ticket']  = '^GSPC'
keys['avgCost'] = 25.842
keys['Obje'] = 42.29
keys['name'] = 'SP 500\n 1wk'
chart(keys, frame)
ch.mainloop()
