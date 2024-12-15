from datetime import datetime

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import mplfinance as mpf
import ta
from ta.momentum import RSIIndicator

from bd_conect import *
from rutinas import *


def chart_symbol(keys=None, datos=None, fg=None, cv=None):

    def m_emaplot(tipo):

        zone_sell, zone_buy = dict(), dict()
        vmin = pdatos['Low'].min()
        ema09, ema21 = pdatos['EMA009'].iloc[-1], pdatos['EMA021'].iloc[-1]

        ndatos = numero_fib(n=pdatos.shape[0])
        minimax = pdatos[['High', 'Low']].tail(ndatos)
        xmax = minimax['High'].max()
        desde = minimax.loc[minimax['High'] == xmax].index[0]
        xmin = minimax['Low'].loc[desde.strftime('%Y-%m-%d'):].min()
        xmax = minimax['High'].max()

        long, t_alcista, t_bajista, zone_fib0, zone_fib1, zone_fib2, zone_fib3, zone_fib4, zone_fib5 = (
            retrocesos_fib(low=xmin, high=xmax.max(), ema09=ema09, ema21=ema21, datos=pdatos, desde=desde))

        rsi_indicator = RSIIndicator(close=pclose, window=13)
        sh = rsi_indicator.rsi()
        ln = sh.rolling(window=55).mean()

        fup = dict(y1=sh.values, y2=ln.values, where=(sh > ln), color="green", alpha=0.3, interpolate=True)
        fdn = dict(y1=sh.values, y2=ln.values, where=(sh < ln), color="red", alpha=0.3, interpolate=True)
        lim = dict(y1=30, y2=70, alpha=0.2, color='white')

        f_above = dict(y1=pdatos['EMA009'].values, y2=pdatos['EMA021'].values, alpha=0.4, color='blue',
                       interpolate=True, where=(pdatos['EMA009'] > pdatos['EMA021'].values))
        f_below = dict(y1=pdatos['EMA009'].values, y2=pdatos['EMA021'].values, alpha=0.4, color='orange',
                       interpolate=True, where=(pdatos['EMA009'] < pdatos['EMA021'].values))

        l_above = dict(y1=vmin, y2=pdatos['Close'].values, alpha=0.4, color='blue', interpolate=True,
                       where=(vmin > pdatos['Close'].values))
        l_below = dict(y1=vmin, y2=pdatos['Close'].values, alpha=0.4, color='red', interpolate=True,
                       where=(vmin < pdatos['Close'].values))
        if keys['position']:
            buy_signal, x1, x2 = operaciones_book(tipo='O', frame=keys['booktrading'], df=pclose)
            zone_buy = dict(y1=x1, y2=x2, color='Olive', alpha=0.3)
            zone_sell = dict(y1=x2, y2=vmax, color='DarkCyan', alpha=0.2)
            if tipo != 'line':
                ema = [
                    mpf.make_addplot(pdatos['EMA009'], color='orange', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA021'], color='blue', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA055'], color='cyan', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA144'], color='purple', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA009'], fill_between=[f_above, f_below], ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA021'], fill_between=zone_buy, ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA009'], color='Olive', fill_between=zone_buy, ax=ae, alpha=0.1),
                    mpf.make_addplot(pdatos['EMA009'], color='blue', fill_between=zone_sell, ax=ae, alpha=0.1),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib0, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib1, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib2, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib3, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib4, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib5, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['ivolume'], type='bar', ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color='green', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='red', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=lim)]
            else:
                ema = [
                    mpf.make_addplot(pdatos['Close'], fill_between=[l_above, l_below], ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA009'], color='Olive', fill_between=zone_buy, ax=ae, alpha=0.1),
                    mpf.make_addplot(pdatos['EMA009'], color='blue', fill_between=zone_sell, ax=ae, alpha=0.1),
                    mpf.make_addplot(pdatos['ivolume'], type='bar', ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color='green', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='red', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=lim)]
        else:
            if tipo != 'line':
                ema = [
                    mpf.make_addplot(pdatos['EMA009'], color='orange', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA021'], color='blue', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA055'], color='cyan', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA144'], color='purple', ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA009'], fill_between=[f_above, f_below], ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib0, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib1, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib2, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib3, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib4, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['EMA009'], color='green', fill_between=zone_fib5, ax=ax, alpha=0.01),
                    mpf.make_addplot(pdatos['ivolume'], type='bar', ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color='green', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='red', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=lim) ]
            else:
                ema = [
                    mpf.make_addplot(pdatos['Close'], fill_between=[l_above, l_below], ax=ax, alpha=0.6),
                    mpf.make_addplot(pdatos['ivolume'], type='bar', ax=av, alpha=0.6),
                    mpf.make_addplot(sh, color='green', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='red', ax=av, type='line', alpha=0.8),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=[fup, fdn]),
                    mpf.make_addplot(ln, color='green', ax=av, fill_between=lim)]

        return ema, t_alcista, t_bajista, long, desde, zone_buy, zone_sell

    def add_plot(ax, ae, tipo) -> list:

        def view_position():
            ix = pdatos.index[-1]
            l_ix = len(pdatos.index)

            ae.text(0, keys['mkPrice'], currency(keys['mkPrice']), fontsize=5, ha="left", color=keys['pcolor'])
            ae.plot(l_ix, keys['mkPrice'], marker='>', color=keys['pcolor'])

            y = float(keys['avgCost']) * 1.1
            ax.axhline(keys['avgCost'], linewidth=0.6, ls='--', color='yellow')
            ax.text(0, y, 'base: ' + currency(keys['avgCost']), fontsize=5, ha="left", color='yellow')
            ae.plot(l_ix, keys['avgCost'], marker='>', color='yellow')

            if keys['position']:
                ae.text(0.5, zone_buy['y2'], 'Zone Sell', transform=ae.transAxes, fontsize=10, color='gray',
                        alpha=0.5, va='bottom', rotation=90)

            return st, emaplot, emaline, long, desde, t_alcista, t_bajista, zone_sell, zone_buy

        emaplot, emaline, vmin = list(), list(), pdatos['Low'].min()

        mc = mpf.make_marketcolors(base_mpf_style='charles', up='green', down='red',
                                   volume={'up': 'blue', 'down': 'orange'})
        st = mpf.make_mpf_style(base_mpl_style='dark_background', marketcolors=mc,
                                y_on_right=False, edgecolor='grey')

        if tipo != 'line':
            emaplot, t_alcista, t_bajista, long, desde, zone_buy, zone_sell = m_emaplot(tipo)
            mpf.plot(pdatos, type=tipo, style=st, ax=ax, addplot=emaplot, datetime_format='%b-%Y',
                             scale_width_adjustment=dict(ohlc=1.5, lines=0.45, volume=.8))
            #
            # draw() de texto fibonacci
            #
            fdesde = pdatos.index.get_loc(desde)
            l_ix = len(pdatos.index)
            ndesde = fdesde + int((l_ix - fdesde) / 2)
            ax = nivel_fib(ax, ndesde, t_alcista, t_bajista, long)

        if tipo == 'line':
            mpf.plot(pdatos, type=tipo, style=st, ax=ax, addplot=emaline, datetime_format='%b-%Y',
                             scale_width_adjustment=dict(ohlc=1.5, lines=0.45, volume=.8))

        #
        # draw() de proyeccción de precios forward
        #
        if keys['position']:
            view_position()

        return st, emaplot, emaline, long, desde, t_alcista, t_bajista, zone_sell, zone_buy

    # limpia y define partes del gráfico
    fg.clear()
    gs = fg.add_gridspec(2, 2, width_ratios=(6, 1), height_ratios=(5, 1),
                                left=0.1, right=0.92, bottom=0.11, top=0.9,
                                wspace=0.05, hspace=0.05)
    ax = fg.add_subplot(gs[0, 0])
    av = fg.add_subplot(gs[1, 0], sharex=ax)
    ae = fg.add_subplot(gs[0, 1])

    ax.set_facecolor(keys['gcolor'])
    av.set_facecolor(keys['gcolor'])
    ae.set_facecolor(keys['gcolor'])

    ticket = keys['ticket'].replace('USDT', "-USD")
    titl = keys['name']
    periodo = keys['periodo']
    tipo = keys['tipo']

    # prepara Dataframe() de entrada
    hoy = datetime.now()
    ohlcv_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    pdatos = datos.resample(periodo).agg(ohlcv_dict)

    n = pdatos.shape[0]
    fmin = pdatos.index.min()
    fmax = pdatos.index.max()
    pclose = pdatos['Close']
    vmax = pdatos['High'].max()
    pdatos['EMA144'] = ta.trend.ema_indicator(pclose, window=144)
    pdatos['EMA055'] = ta.trend.ema_indicator(pclose, window=55)
    pdatos['EMA021'] = ta.trend.ema_indicator(pclose, window=21)
    pdatos['EMA009'] = ta.trend.ema_indicator(pclose, window=9)
    pdatos['ivolume'] = (100 * (pdatos['Volume'] - pdatos['Volume'].min()) /
                         (pdatos['Volume'].max() - pdatos['Volume'].min()))

    icolor = ['orange', 'blue', 'cyan', 'purple']
    ilabel = ['EMA(09)', 'EMA(21)', 'EMA(55)', 'EMA(144)']
    st, emaplot, emaline, long, desde, t_alcista, t_bajista, zone_sell, zone_buy = add_plot(ax, ae, tipo)

    # setup de ejes de cordenadas
    ax.spines[["left", "top", "right", "bottom"]].set_visible(False)
    ax.xaxis.set_visible(True)
    ax.yaxis.set_visible(True)
    ax.grid(True, color='gray', linewidth=0.3)
    ax.set_ylabel('Precio($)', fontsize='x-small', color=keys['tcolor'])
    plt.setp(ax.get_xticklabels(), ha='right', rotation=30, fontsize=5)
    plt.setp(ax.get_yticklabels(), ha='right', fontsize=6, color=keys['tcolor'])
    plt.rcParams.update({"axes.labelsize": 6, "xtick.labelsize": 6, "ytick.labelsize": 6})

    # indicadores de gráfico
    av.xaxis.set_visible(True)
    av.set_ylabel('RSI', fontsize='x-small', color=keys['tcolor'])
    plt.setp(av.get_xticklabels(), ha='right', rotation=30, fontsize=5, color=keys['ecolor'])
    plt.setp(av.get_yticklabels(), ha='right', fontsize=6, color=keys['ecolor'])

    # setup de eje de proyeccción
    ae.spines.top.set_visible(False)
    ae.spines.left.set_visible(True)
    ae.set_ylabel('Forwad ($)', fontsize='x-small', color=keys['tcolor'])
    ae.yaxis.set_label_position('right')
    ae.yaxis.tick_right()
    ae.set_ylim(ax.get_ylim())
    ae.xaxis.set_visible(False)
    ae.yaxis.set_visible(True)
    plt.setp(ae.get_xticklabels(), ha='right', fontsize=5, color=keys['ecolor'])
    plt.setp(ae.get_yticklabels(), ha='left', fontsize=6, color=keys['ecolor'])

    # prepara titulo y leyenda del grafico
    titulo = keys['ticket'] + ':: ' + keys['name'] + ' - (' + periodo + ')'
    patch = list()
    for i in range(len(ilabel)):
        patch.append(mpatches.Patch(color=icolor[i], label=ilabel[i]))

    fg.legend(handles=patch, loc='outside lower right', fontsize=6)
    fg.suptitle(titulo, color=keys['tcolor'], fontsize='medium')

    return fg, cv


def operaciones_book(tipo='C', frame=None, df=None):
    """
    @param tipo:  de operación compra o venta
    @param frame:  de operaciones del activo
    @param df:  dataframe 'Close'
    @return:  lista de operaciones de compra o venta
    """

    signal = list()
    setix = df.index
    xmin = float(frame['preciotrans'].min())
    xmax = float(frame['preciotrans'].max())

    for date, values in frame.iterrows():

        if (date.strftime("%Y-%m-%d") in setix) and (values['codigo'] == tipo):
            signal.append(float(values['preciotrans']) * 0.99)
        else:
            signal.append(np.nan)

    return signal, xmin, xmax


def belowzero(percent, price):

    signal = list()
    previous = -1.0
    for date, value in percent.items():
        if (value < 0) and (previous >= 0):
            signal.append(price[date]*0.99)
        else:
            signal.append(np.nan)
        previous = value
    return signal


def aboveone(percent, price):

    signal = list()
    previous = 2
    for date, value in percent.items():
        if (value > 1) and (previous <= 1):
            signal.append(price[date]*1.01)
        else:
            signal.append(np.nan)
        previous = value
    return signal


if __name__ == '__main__':
    ch = tk.Tk()
    dw = 700
    dh = 400
    df = 190
    dimension = "%dx%d+0+0" % (dw, dh)
    ch.geometry(dimension)
    ch.title("Prueba v4.0")
    ch.config(bg="black")
    frame = tk.Frame(ch)
    frame.pack()

    keys = dict()
    keys['ticket'] = '^GSPC'
    keys['avgCost'] = 25.842
    keys['Obje'] = 42.29
    keys['name'] =  keys['ticket'] + ' \n 1wk'
    chart(keys, frame)
    ch.mainloop()
