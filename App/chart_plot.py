import mplfinance as mpf
import ta
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from ta.momentum import RSIIndicator

from globales import *


def chartborde(master=None, canvas=None, fre=0, panel=None, scala=None):
    #
    # carga widgets de graficos
    #
    fw = 5.9 if canvas in ('cv2', 'cv3', 'cv4') else 5.5
    fh = 2.9 if canvas in ('cv2', 'cv3', 'cv4') else 2.7
    if gchar:
        fig = chart(gchar, fw, fh)
    else:
        fig = Figure(figsize=(fw, fh), dpi=110)

    if canvas == 'cv0':
        cv0 = FigureCanvasTkAgg(fig, master=pn0)
        cv0.draw()
        cv0.get_tk_widget().pack()

    if canvas == 'cv1':
        cv1 = FigureCanvasTkAgg(fig, master=panel)
        cv1.draw()
        cv1.get_tk_widget().pack()

    if canvas == 'cv2':
        cv2 = FigureCanvasTkAgg(fig, master=panel)
        cv2.draw()
        cv2.get_tk_widget().pack()

    if canvas == 'cv3':
        cv3 = FigureCanvasTkAgg(fig, master=panel)
        cv3.draw()
        cv3.get_tk_widget().pack()

    if canvas == 'cv4':
        cv4 = FigureCanvasTkAgg(fig, master=panel)
        cv4.draw()
        cv4.get_tk_widget().pack()

    master.update()
    master.after(fre, lambda: chartborde(master, canvas, fre, panel, scala))


def chart(gchar, fw, fh) -> object:
    Tick = gchar['ticket']
    Prcm = gchar['avgCost']
    Pobj = gchar['Obje']
    titl = gchar['name']

    hoy = datetime.now()
    ini = hoy - timedelta(days=1800)
    #
    #
    #  1d, 1wk 1mo 3mo
    fre = "1wk"
    datos = yf.download(Tick, progress=False, interval=fre, period='1y' )
    n = datos.shape[0]
    imax = 360 if fre == '1wk' else 60 if fre == "1mo" else 40 if fre == '3mo' else n
    x = n - imax if n > imax else n
    x = 0
    pdatos = datos.iloc[x:]
    pclose = datos['Close'].iloc[x:]

    rsi_indicator = RSIIndicator(close=pclose, window=13)
    sh = rsi_indicator.rsi()
    ln = sh.rolling(window=55).mean()

    fup = dict(y1=sh.values, y2=ln.values, where=(sh > ln), color="green", alpha=0.3, interpolate=True)
    fdn = dict(y1=sh.values, y2=ln.values, where=(sh < ln), color="red", alpha=0.3, interpolate=True)
    lim = dict(y1=30, y2=70, alpha=0.2, color='white')

    datos['EMA144'] = ta.trend.ema_indicator(datos['Close'], window=144)
    datos['EMA055'] = ta.trend.ema_indicator(datos['Close'], window=55)
    datos['EMA021'] = ta.trend.ema_indicator(datos['Close'], window=21)
    datos['EMA009'] = ta.trend.ema_indicator(datos['Close'], window=9)

    print(n, x, pdatos.shape[0], sh.shape[0], fw, fh)
    rsi_plot = [
        # mpf.make_addplot(sh, color='green',panel=1, type='line',alpha=0.8)
        # , mpf.make_addplot(ln, color='red',  panel=1, type='line',alpha=0.8)
        # , mpf.make_addplot(ln, color='green',panel=1, fill_between=[fup,fdn])
        # , mpf.make_addplot(ln, color='green',panel=1, fill_between=lim)
        # , mpf.make_addplot(datos['EMA144'].iloc[x:], color='yellow', panel=0)
        # , mpf.make_addplot(datos['EMA055'].iloc[x:], color='blue',   panel=0)
        mpf.make_addplot(datos['EMA021'].iloc[x:], color='blue', panel=0)
        , mpf.make_addplot(datos['EMA009'].iloc[x:], color='white', panel=0)
    ]

    reg_plot = [dict(y1=Prcm, y2=Pobj, alpha=0.3, color='green')]
    mc = mpf.make_marketcolors(base_mpf_style='charles', up='green', down='red', volume={'up': 'blue', 'down': 'orange'})
    st = mpf.make_mpf_style(base_mpl_style='dark_background', marketcolors=mc, y_on_right=False, edgecolor='grey')

    fig, axs = mpf.plot(pdatos, type='candle', style=st, tight_layout=False,
                        datetime_format=' %m-%y', xrotation=60,
                        figscale=2, panel_ratios=(1, .3), figsize=(fw, fh),
                        axisoff=False, volume=True,
                        addplot=rsi_plot,
                        #fill_between=reg_plot,
                        ylabel_lower='RSI ',
                        scale_width_adjustment=dict(ohlc=.5, lines=0.45, candle=.5),
                        returnfig=True)
    return fig