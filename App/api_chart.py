from tkinter import *

import mpl_toolkits.axisartist.floating_axes as floating_axes
from fake_useragent import UserAgent
from matplotlib import ticker
from matplotlib.projections import PolarAxes
from matplotlib.sankey import Sankey
from mpl_toolkits.axisartist.grid_finder import (DictFormatter, FixedLocator, MaxNLocator)

from api_utilitis import *
from chart_ticket import *

session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'api_chart'

cchart = {'texto': 'white', 'titulo': 'cyan', 'fondo': 'black', 'axsy': 'gray', 'axsx': 'gray', '2eje': 'orange',
          'plot1': 'green', 'plot2': 'orange', 'plot3': 'red', 'plot4': 'yellow', 'plot5': 'DodgerBlue'}


def evaluar_fila(account=None, vehiculo=None, empresa=None, ticket=None):
    """
    @param account: id cuenta de inversión
    @param vehiculo: tipo de inversión
    @param empresa: name del activo
    @param ticket: simbolo a graficar
    @return:
    """
    if not is_null(ticket):
        window_estrategia(account=account, vehiculo=vehiculo, empresa=empresa, ticket=ticket)
    else:
        messagebox.showinfo("", "Para mostrar el grafico, posicione el cursor sobre el activo")


def window_estrategia(account='B0000001', vehiculo='Crypto', empresa=None, ticket=None):
    """
    @param account: id de inversión
    @param vehiculo: tipo de inversión
    @param empresa: name del activo
    @param ticket: simbolo a graficar
    @return:
    """
    def eexit() -> None:
        rns.destroy()
        rnb.destroy()

    def windows_analisis(account=account, rns=None, vehiculo=None, ticket=None):

        title = "Análisis de activo"
        dimension = "%dx%d+%d+%d" % (1900, 220, 0, 780)
        rns.geometry(dimension)
        rns.resizable(False, False)
        rns.attributes('-toolwindow', 1)
        rns.title(title)
        rns.config(bg="black")
        rns.protocol("WM_DELETE_WINDOW", eexit)

        win1 = tk.Frame(rns, bg='white', bd=2)
        win2 = tk.Frame(rns, bg='white', bd=2)
        win3 = tk.Frame(rns, bg='white', bd=2)

        win1.grid(row=0, column=0, padx=0, pady=1)
        win2.grid(row=0, column=1, padx=0, pady=1)
        win3.grid(row=0, column=2, padx=0, pady=1)

        fg1 = Figure(figsize=(5.72, 2.0), dpi=110)
        fg1.set_facecolor('black')
        cv1 = FigureCanvasTkAgg(fg1, master=win1)
        cv1.draw()
        cv1.get_tk_widget().pack()

        fg2 = Figure(figsize=(5.72, 2.0), dpi=110)
        fg2.set_facecolor('black')
        cv2 = FigureCanvasTkAgg(fg2, master=win2)
        cv2.draw()
        cv2.get_tk_widget().pack()

        fg3 = Figure(figsize=(5.72, 2.0), dpi=110)
        fg3.set_facecolor('black')
        cv3 = FigureCanvasTkAgg(fg3, master=win3)
        cv3.draw()
        cv3.get_tk_widget().pack()

        asset, xlist = dict(), list()
        simbolo = ticket.replace("USDT", "-USD")
        asset[simbolo] = 1
        xlist.append(ticket)

        (market, ix) = select_market(account=account, symbol=ticket)
        if market:
            c_text = market[0][ix.index('trazaDividends')].decode('utf-8')
            fw_div = market[0][ix.index('trailingAnnualDividendYield')]
            fw_div = fw_div if is_none(fw_div) else market[0][ix.index('dividendYield')]
            empresa = market[0][ix.index('shortName')]
            if not is_vacio(c_text) and fw_div > 0:
                s_json = json.loads(c_text)
                y_datos = pd.DataFrame(data=s_json['data'], columns=s_json['columns'], index=s_json['index'])
                y_datos.index = pd.to_datetime(y_datos.index, unit='ms')

                dlabl = {'symbol': ticket, 'buy': 'Zona buy', 'sell': 'Zona sell', 'legend': 'outside upper left'}
                asset = {'ticket': ticket, 'forward': fw_div, 'name': empresa, "aspect": 0.3}

                chart_rendimiento_dividendos(fg3, cv3, datos=y_datos, dlabl=dlabl, asset=asset)

        #
        #  Grafica performance acumulado para el ticket
        datos = performa_asset(account=account, vehiculo=vehiculo, tipo='token', asset=ticket)
        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
        dlabl = {symbol.replace("-USD", ""):  index_ref, '++ index': ticket, 'Value': 'Value Market',
                 'Costo': 'Cost basic', "legend": 'outside upper left', "aspect": 0.21}
        activo = convierte_ticket_crypto(ticket)
        performa_portafolio(fg1, cv1, datos, dlabl, 'Rendimiento (acumulativo) :: ' + activo)

        # datos proviene de Dataframe construido por select_performa_inversion('Vehiculo')
        #  y se debe cambiar el performa del activo en comparación el index

        sankey_estrategia(fg2, cv2)

    def gsetup(periodo, tipo, accion):

        gchar['periodo'] = periodo if accion == 'p' else gchar['periodo']
        gchar['tipo'] = tipo if accion == 't' else gchar['tipo']

        hoy = datetime.now()
        fmin = hoy - timedelta(days=1800)
        ticket = gchar['ticket'].replace('USDT', "-USD")
        # pdatos = yf.download(ticket, start=fmin, end=hoy)
        xdatos = pdatos.resample(periodo).mean()
        chart_symbol(gchar, xdatos, fg, cv)

        return gchar

    def activo_positión(win):

        tree = ttk.Treeview(win, columns=("fec", "prc", 'mkt', "cant", "gyp", "GPa"), height=10, style='TFrame')
        tree.column("#0", width=40, anchor='c')
        tree.column('fec', width=80, anchor='c')
        tree.column('cant', width=90, anchor='c')
        tree.column('prc', width=100, anchor='c')
        tree.column('mkt', width=100, anchor='c')
        tree.column('gyp', width=90, anchor='c')
        tree.column('GPa', width=90, anchor='c')
        tree.tag_configure("green", background="green", foreground='white')
        tree.tag_configure("red", background="red", foreground='white')

        tree.heading("#0", text="Nro")
        tree.heading("fec", text="Fecha")
        tree.heading("prc", text="Precio")
        tree.heading("mkt", text="mkPrice")
        tree.heading("cant", text="Cantidad")
        tree.heading("gyp", text="GyP")
        tree.heading("GPa", text="Acumulado")
        tree.grid(row=0, column=0, pady=6)

        cd = ['id', 'sec', 'categoria', 'divisa', 'cuenta', 'simbolo', 'idtrans', 'cantidad', 'preciocierre',
              'producto', 'tarifacomision', 'basico', 'gprealizadas', 'mtmgp', 'stock', 'activa', 'split']

        hist, ix = select_booktrading(accion='select*', account=gchar['account'], idivisa='USD', symbol=gchar['ticket'])

        if hist:

            frame_book = pd.DataFrame(hist, columns=ix)
            frame_book = frame_book.drop(cd, axis=1)
            frame_book['fechahora'] = frame_book['fechahora'].dt.date
            frame_book = frame_book.set_index('fechahora')

            gchar['booktrading'] = frame_book
            gchar['secType'] = hist[0][ix.index('categoria')]
            gchar['date'] = hist[0][ix.index('fechahora')]

            gypa, maxp = 0, 0
            for i in range(len(hist)):
                if hist[i][ix.index('codigo')] == 'O':
                    fech = hist[i][ix.index('fechahora')].date()
                    prec = hist[i][ix.index('preciotrans')]
                    cant = hist[i][ix.index('cantidad')]
                    gyp = (gchar['mkPrice'] - prec) * hist[i][ix.index('cantidad')]
                    gypa += gyp
                    lbg = 'green' if gyp > 0 else 'red'
                    items = tree.insert("", END, text=str(i + 1), values=(fech, '{:>10.6f}'.format(prec),
                                                                          '{:>10.6f}'.format(gchar['mkPrice']),
                                                                          '{:>+10.6f}'.format(cant),
                                                                          '{:>+10.2f}'.format(gyp),
                                                                          '{:>10.2f}'.format(gypa)), tags=(lbg,))

    global gperiodo, gtipo

    rnb = tk.Toplevel()
    rns = tk.Toplevel()
    title = "Grafico de activo"
    dimension = "%dx%d+%d+%d" % (600, 747, df+5, 0)
    rnb.geometry(dimension)
    rnb.resizable(False, False)
    rnb.attributes('-toolwindow', 1)
    rnb.title(title)
    rnb.config(bg="black")
    rnb.focus()
    rnb.grab_set()
    rnb.protocol("WM_DELETE_WINDOW", eexit)

    gchar['ticket'] = ticket
    gchar['gcolor'] = 'Silver'
    gchar['gcolor'] = 'CadetBlue'
    gchar['gcolor'] = 'DarkSeaGreen'
    gchar['tcolor'] = 'black'
    gchar['pcolor'] = 'black'
    gchar['ecolor'] = 'black'

    win1 = tk.Frame(rnb, bg='black', bd=2)
    win2 = tk.Frame(rnb, bg='black', bd=2)
    win3 = tk.Frame(rnb, bg='black', bd=2)

    win1.grid(row=0, column=0, padx=0, pady=2)
    win2.grid(row=1, column=0, padx=0, pady=2)
    win3.grid(row=2, column=0, padx=0, pady=2)

    win10 = tk.Frame(win1, bg='black', bd=2)
    win11 = tk.Frame(win1, bg='black', bd=2)
    win12 = tk.Frame(win1, bg='black', bd=2)
    win10.grid(row=0, column=0)
    win11.grid(row=0, column=1)
    win12.grid(row=0, column=2)

    bt1 = ttk.Button(win10, text="1wk", width=4, command=lambda: gsetup('W', gtipo, 'p'))
    bt2 = ttk.Button(win10, text="1mo", width=4, command=lambda: gsetup('ME', gtipo, 'p'))
    bt3 = ttk.Button(win10, text="3mo", width=4, command=lambda: gsetup('QE', gtipo, 'p'))
    bt4 = ttk.Button(win10, text="1y", width=4, command=lambda: gsetup('YE', gtipo, 'p'))

    bt1.grid(row=0, column=0)
    bt2.grid(row=0, column=1)
    bt3.grid(row=0, column=2)
    bt4.grid(row=0, column=3)

    imagen0, xlis = select_objeto(codigo=100)
    imagen = Image.open(io.BytesIO(imagen0))
    imagen = imagen.resize((16, 16), Image.ADAPTIVE)
    imagen_tk = ImageTk.PhotoImage(imagen)
    gt1 = tk.Button(win11, image=imagen_tk, bg='black', command=lambda: gsetup(gperiodo, 'candle', 't'))
    gt1.imagen = imagen_tk
    gt1.grid(row=0, column=0)

    imagen0, xlis = select_objeto(codigo=101)
    imagen = Image.open(io.BytesIO(imagen0))
    imagen = imagen.resize((16, 16), Image.ADAPTIVE)
    imagen_tk = ImageTk.PhotoImage(imagen)
    gt2 = tk.Button(win11,  image=imagen_tk, bg='black', command=lambda: gsetup(gperiodo, 'line', 't'))
    gt2.imagen = imagen_tk
    gt2.grid(row=0, column=1)

    et1 = ttk.Button(win12, text="e30", width=4, command=lambda: gestrategy('e30'))
    et2 = ttk.Button(win12, text="e50", width=4, command=lambda: gestrategy('e50'))
    et3 = ttk.Button(win12, text="e100", width=4, command=lambda: gestrategy('e100'))
    et1.grid(row=0, column=0)
    et2.grid(row=0, column=1)
    et3.grid(row=0, column=3)

    fg = Figure(figsize=(5.4, 4.0), dpi=110)
    fg.set_facecolor(gchar['gcolor'])
    cv = FigureCanvasTkAgg(fg, master=win2)
    cv.draw()
    cv.get_tk_widget().pack()

    style = ttk.Style(win3)
    style.configure('TFrame', font=('Courier', 8), foreground="white", background="black")
    style.configure('TLabel', font=('Courier', 8), foreground="white", background="black")
    position = select_inversion(tipoin=vehiculo, ticket=ticket)

    gchar['booktrading'] = pd.DataFrame()
    gchar['position'] = False
    gchar['objetivo'] = 0
    gchar['avgCost'] = 0
    gchar['account'] = 0
    gchar['mkPrice'] = 0
    gchar['periodo'] = 'ME'
    gchar['secType'] = 'Stock'
    gchar['name'] = empresa
    gchar['tipo'] = 'candle'
    gchar['date'] = datetime.now()

    if position:
        gchar['position'] = True
        gchar['objetivo'] = position[0]['objetivo']
        gchar['avgCost'] = position[0]['costobase'] / position[0]['position']
        gchar['account'] = position[0]['useraccount']
        gchar['mkPrice'] = position[0]['mktPrice']
        gchar['name'] = position[0]['empresa']
        activo_positión(win3)

    gtipo, gperiodo = 'candle', 'ME'
    ticket = gchar['ticket'].replace('USDT', "-USD")
    (activo, pdatos) = get_yfinance(ticket=ticket, vehiculo=vehiculo, period='5y')

    chart_symbol(gchar, pdatos, fg, cv)
    windows_analisis(rns=rns, vehiculo=vehiculo, ticket=gchar['ticket'])
    rnb.mainloop()


def sankey_estrategia(fg: object, cv: object):

    fg.clear()
    ax = fg.add_subplot(xticks=[], yticks=[], title="Estrategias de venta (long)")
    ax.set_facecolor(gchar['gcolor'])
    plt.setp(ax.get_xticklabels(), ha='right', fontsize=6)
    plt.setp(ax.get_yticklabels(), ha='left', fontsize=6)

    sankey = Sankey(ax=ax, scale=0.01, offset=0.2, head_angle=180, format='%.0f')
    sankey.add(flows=[0, 0, 30, -30, -30, -40, -50, -50, -0, -100],
               labels=['', '', '', '30%', '30%', '40%', '50%', '50%', '0%', '100%'],
               orientations=[-1, 1, 0, 1, 1, 1, -1, -1, -1, 0],
               pathlengths=[5.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15],
               patchlabel="Ganancias\nA")
    diagrams = sankey.finish()
    diagrams[0].texts[-1].set_color('r')
    diagrams[0].text.set_fontweight('bold')


def performa(fg: object, cv: object, data, parm):
    """
    @param fg: Objecto figura
    @param cv: objecto cava
    @param data: dict de 5 elementos
    @param parm: del gráfico
    @return: desempeño de inversión crypto
    """
    if data['Inversión'] > 0:
        cbar = ('orange', 'green', 'navy', 'red')
        group_data = list(data.values())
        group_names = list(data.keys())
        xmin = min(0, data['UnP&l'], data['Cash'])
        xmax = max(data['Inversión'], data['UnProfit'], data['Cash'])
        iy = round((xmax - xmin) / 3)
        i = is_magnitud(round((xmax - xmin) / 3))

        dx = int(iy * 10 ** (- i)) * (10 ** i)
        d0 = -dx if xmin < 0 else 0
        ix = [d0, dx, 2 * dx, 3 * dx]

        ltex = [3, 2, 1]
        if data['UnP&l'] == data['UnProfit']:
            data.pop('UnProfit')
            group_data = list(data.values())
            group_names = list(data.keys())
            ltex = [2, 1]

        fg.clear()
        fg.suptitle(parm['titulo'], color=cchart['titulo'], fontsize='medium')
        ax = fg.add_subplot()
        ax.set_box_aspect(parm['aspect'])
        ax.set_facecolor(cchart['fondo'])
        ax.barh(group_names, group_data, color=cbar)
        ax.set(xlim=[xmin, xmax])

        for i in ltex:
            xi = group_data[i] + 100 if group_data[i] > 0 else 100
            ax.text(xi, i, '{:> 4.1%}'.format(Decimal(group_data[i] / data['Inversión'])),
                     fontsize=6, va="center", color=cchart['texto'])

        ax.xaxis.set_major_formatter(currency)
        ax.spines.right.set_visible(False)
        ax.spines.left.set_visible(False)
        ax.spines.top.set_visible(False)

        ax.set_xlabel('', fontsize=6, color=cchart['texto'])

        xlabels = ax.get_xticklabels()
        ylabels = ax.get_yticklabels()
        plt.setp(xlabels, ha='right', fontsize=6, color=cchart['texto'])
        plt.setp(ylabels, ha='right', fontsize=6, color=cchart['texto'])
        ax.set_xticks(ix)

        ax.axvline(0, linewidth=0.6, ls='-', color=cchart['axsy'])
        ax.spines['bottom'].set_color(cchart['axsx'])
        ax.set_xlabel('', fontsize=6, color=cchart['axsx'])
        ax.tick_params(axis='x', colors=cchart['axsx'])
        ax.tick_params(axis='y', colors=cchart['axsy'])
        #cv.draw()



def asignacion(fg: object, cv: object, data, titulo):
    """
    @param fg: Objecto figura
    @param cv: objecto cava
    @param data: dict de 5 elementos
    @param titulo:  del gráfico
    @return:  chart de asignacion crypto en la inversion
    """
    size = 0.35

    vals = np.array(data['data'])
    cmap = plt.colormaps["tab20c"]
    outer_colors = cmap(np.arange(5) * 4)

    fg.clear()
    fg.suptitle(titulo, color=cchart['titulo'], fontsize='medium')
    ax = fg.add_subplot()
    ax.set_facecolor(cchart['fondo'])
    ax.set_box_aspect(0.75)

    wedges, texts = ax.pie(vals, wedgeprops=dict(width=size, edgecolor=cchart['fondo']))
    kw = dict(arrowprops=dict(arrowstyle="-"),  zorder=0, va="baseline",
              size=6, color=cchart['texto'])

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1) / 2.2 + p.theta1
        y = np.sin(np.deg2rad(ang))
        x = np.cos(np.deg2rad(ang))
        horizontalalignment = {-1: "right", 1: "left"}[int(np.sign(x))]
        connectionstyle = f"angle,angleA=1.2,angleB={ang}"
        kw["arrowprops"].update({"connectionstyle": connectionstyle})
        # ax.annotate(text=data['peso'][i], xy=(x, y), xytext=(1.135 * np.sign(x), 1.14 * y),
        ax.annotate(text=data['peso'][i], xy=(x, y), xytext=(1.12 * np.sign(x), 1.12 * y),
                    horizontalalignment=horizontalalignment, **kw)

    ax.set_xlabel('', fontsize='x-small', color=cchart['axsx'])
    ax.tick_params(axis='x', colors=cchart['axsx'])
    ax.tick_params(axis='y', colors=cchart['axsy'])


def distribucion(fg: object, cv: object, data, titulo):
    """

    @return: gráfico de costo base, performan y debit por activo
    """
    fg.clear()
    fg.suptitle(titulo, color=cchart['titulo'], fontsize='medium')
    ax = fg.add_subplot()
    ax.set_box_aspect(0.35)
    width = 0.25
    multiplier = 0

    x = np.arange(len(data['series']['Inversión']))
    unpyl = np.sum(data['series']['Profit'])
    cbar = ['red', 'green', 'orange']

    imax = max(data['series']['Inversión'])
    pmin = min(data['series']['Profit'])

    xmax = max(unpyl, imax, pmin)
    xmin = min(0, unpyl)

    it = xmax - xmin
    iy = round(it / 3)
    i = is_magnitud(iy)

    dy = int(iy * 10 ** (- i)) * (10 ** i)
    d0 = -dy if xmin < 0 else 0
    ix = [0, d0, dy, 2*dy, 3*dy, 4*dy]
    ix = [0, d0, dy, 2 * dy, 3 * dy]

    for attribute, measurement in data['series'].items():
        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute, color=cbar[multiplier])
        multiplier += 1

    ax.set_facecolor(cchart['fondo'])
    ax.yaxis.set_major_formatter(currency)
    ax.spines.bottom.set_visible(False)
    ax.spines.right.set_visible(False)
    ax.spines.top.set_visible(False)

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    # ax.set_title(titulo, fontsize='smaller', color=cchart['titulo'])
    plt.setp(xlabels, ha='right', fontsize=6)
    plt.setp(ylabels, ha='right', fontsize=6)
    ax.axhline(0, linewidth=0.6, ls='-', color=cchart['axsx'])

    # ax.axhline(unpyl, linewidth=0.6, ls='--', color=cchart['texto'])
    # ax.text(5, unpyl + 100, currency(unpyl, 0), fontsize=6, ha="left", color=cchart['texto'])
    # ax.text(5, unpyl - 100, 'UnP&l', fontsize=6, ha="left", color=cchart['texto'])
    ax.fill_between(x + width, 0, data['series']['Profit'], color='LightSteelBlue', alpha=0.35)

    ax.spines[['top', 'right']].set_visible(False)
    ax.set_ylabel('dolar ($)', fontsize=6)
    ax.set_xticks(x + width, data['label'], fontsize=6)
    ax.set_yticks(ix)
    fg.legend(loc='outside upper right', fontsize=6)

    ax.spines['bottom'].set_color(cchart['axsx'])
    ax.spines['left'].set_color(cchart['axsy'])
    ax.set_xlabel('', fontsize=6, color=cchart['axsx'])
    ax.tick_params(axis='x', colors=cchart['axsx'])
    ax.tick_params(axis='y', colors=cchart['axsy'])


def performa_portafolio(fg: object, cv: object, data, dlabl, titulo):

    ccol = ['red']

    if not data.empty:

        fg.clear()
        fg.suptitle(titulo, color=cchart['titulo'], fontsize='medium')
        ax = fg.add_subplot()
        av = ax.twinx()
        ax.set_box_aspect(dlabl['aspect'])
        p_legend, ix = list(), list(dlabl)
        #
        # plot index referencia data[labl[0]]
        # Plot activo data[labl[1]]
        ax.plot(data.index, data[dlabl[ix[0]]], color=cchart['plot5'], linewidth=1)
        ax.plot(data.index, data[ix[1]], color=cchart['plot2'], linewidth=1)

        xmax = max(data[dlabl[ix[0]]].max(), data[ix[1]].max())
        xmin = min(data[dlabl[ix[0]]].min(), data[ix[1]].min())
        ylm = [xmin, xmax]
        #
        # Set de Eje X
        ax.set_facecolor(cchart['fondo'])
        xlabels = ax.get_xticklabels()
        plt.setp(xlabels, ha='right', rotation=20, fontsize=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
        ax.tick_params(axis='x', colors=cchart['axsx'])

        ax.spines['bottom'].set_color(cchart['axsx'])
        ax.spines['left'].set_color(cchart['axsy'])
        ax.set_xlabel('', fontsize='x-small', color=cchart['axsx'])

        ax.grid(True, color=cchart['axsx'], linewidth=0.3)

        ax.spines.right.set_visible(False)
        ax.spines.top.set_visible(False)
        #
        # Set de 1er Eje Y
        ylabels = ax.get_yticklabels()
        ax.set_ylabel('Perfoman', fontsize=6, color=cchart['axsy'])
        ax.yaxis.set_major_formatter(porcentaje)
        plt.setp(ylabels, ha='right', fontsize=6)
        ax.tick_params(axis='y', colors=cchart['axsy'])
        ax.set_ylim(ylm)
        #
        # Set de 2do Eje Y
        av.spines['left'].set_color(cchart['axsy'])
        ax.axhline(0, linewidth=0.6, ls='--', color=cchart['texto'])

        """
        @  construcción de 2do eje, para mostrar profit
        """
        columna = 'value'
        facecolors = [cchart['plot1'] if y > 0 else cchart['plot3'] for y in data[columna]]
        edgecolors = facecolors

        av.set_ylabel(' Dolar US', fontsize='x-small', color=cchart['plot1'])
        av.tick_params(axis='y', labelcolor=cchart['plot1'])
        av.yaxis.set_major_formatter(currency)
        #
        # legend
        p_legend, ix = list(), list(dlabl)
        p_legend.append(mpatches.Patch(color=cchart['plot5'], label=dlabl[ix[0]]))
        p_legend.append(mpatches.Patch(color=cchart['plot2'], label=dlabl[ix[1]]))
        if 'Value' in ix:
            colors = [cchart['plot1']]
            p_legend.append(mpatches.Patch(color=cchart['plot1'], label=dlabl[ix[2]], alpha=0.4))
            gmin = data[columna].min()
            gmax = data[columna].max()

        if 'Costo' in ix:
            colors.append(cchart['plot3'])
            p_legend.append(mpatches.Patch(color=cchart['plot3'], label=dlabl[ix[3]], alpha=0.4))
            xmin = data[columna].min()
            xmax = data[columna].max()
        #
        # plot ambas regiones Value y Costo
        if len(colors) == 1:
            av.plot(data.index, data[columna], color=colors[0], alpha=0.8, linewidth=1)
            av.fill_between(data.index, data[columna], where=data[columna] > 0, facecolor=colors[1], alpha=.3)

        if len(colors) == 2:
            av.plot(data.index, data[columna], color=colors[0], alpha=0.3, linewidth=1)
            av.fill_between(data.index, data[columna], data['costo_base'],
                            where=data[columna] > data['costo_base'], facecolor=colors[0], alpha=.3)

            av.plot(data.index, data['costo_base'], color=colors[1], alpha=0.3, linewidth=1)
            av.fill_between(data.index, data['costo_base'], where=data['costo_base'] > 0, facecolor=colors[1], alpha=.3)


        fg.legend(handles=p_legend, loc=dlabl['legend'], fontsize=5)
        vlm = [min(ylm[0], gmin, xmin), max(ylm[1], gmax, xmax)]
        av.set_ylim(vlm)

        tlabels = av.get_yticklabels()
        plt.setp(tlabels, ha='left', fontsize=6, color=cchart['plot1'])
        av.tick_params(axis='y', colors=cchart['plot1'])
        av.spines['right'].set_color(cchart['plot1'])
        av.spines.right.set_visible(True)
        av.axhline(0, linewidth=0.6, ls='--', color=cchart['plot1'])


def chart_trazaplan(fg: object, cv: object, traz, gcolor):
    """
    @param fg: figura cava sobre la se hara el plot
    @param cv: objeto cava
    @param traz:  dict de unload trazaplan
    @param gcolor:
    @return:  Chat de capital invertido vs plan trazado
    """

    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    ax.set_box_aspect(0.30)

    if traz:

        meta, tinv, tvis, efec, tdiv = list(), list(), list(), list(), list()
        rmax, imax = 0, 0
        for key in traz:
            if key['costobase'] != 0:
                meta.append(str(key['meta']) + " año")
                efec.append(key['efectividad'])
                tinv.append(float(key['tinversion']))
                tvis.append(key['vision'])
                tdiv.append(key['trendimiento'])
                rmax = max(rmax, key['trendimiento'])
                imax = max(imax, key['tinversion'])

        imax = float(imax) * 1.05
        datos = ({'Alcanzado': tinv})
        ddato = ({'Dividendo': tdiv})

        x = np.arange(len(meta))
        width, multiplier, i = 0.25, 1, 1

        for attribute, measurement in datos.items():
            offset = width * multiplier
            rects = ax.bar(x + offset, measurement, width, label=attribute)

        ax.plot(x + offset, tvis, linestyle=':', linewidth=1, label='Trazado', color=cchart['axsy'])
        for i in x[1:]:
            xcol = 'cyan' if efec[i] > 0 else 'red'
            ax.text(x[i] - offset, tinv[i] + offset, '{:>+4.1%}'.format(efec[i]), fontsize=5, va="center", color=xcol)

        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(True, color=cchart['axsx'], linewidth=0.3)
        ax.set_ylabel('dolar ($)', fontsize=6, color=cchart['texto'])
        ax.set_xticks(x + width, meta, fontsize=6)
        fg.legend(loc='outside upper right', fontsize=6)
        fg.suptitle('Capital (Trazado/Alcanzado) vs Rendimiento Total',
                    fontsize='smaller', color=cchart['titulo'])

        ax.set_facecolor(gcolor)
        ylabels = ax.get_yticklabels()
        plt.setp(ax.get_xticklabels(), ha='right', fontsize=6, color=cchart['axsy'], rotation=30)
        plt.setp(ax.get_yticklabels(), ha='right', fontsize=6, color=cchart['axsy'])

        ax.spines.left.set_visible(True)
        ax.spines['left'].set_color(cchart['axsy'])
        ax.tick_params(axis='x', colors=cchart['axsy'])
        ax.tick_params(axis='y', colors=cchart['axsy'])
        ax.set(ylim=(0, imax))
        ax.yaxis.set_major_formatter(currency)
        """
        @  construcción de 2do eje, para mostrar % rendimiento de capital + dividendos
        """
        for attribute, measurement in ddato.items():
            offset = width * multiplier
            rects = av.bar(x + offset, measurement, width / 2, label=attribute, color=cchart['2eje'])

        av.set_ylabel('Rendimiento (Cap+Div)', fontsize=6, color=cchart['2eje'])
        av.tick_params(axis='y', labelcolor=cchart['2eje'])
        av.yaxis.set_major_formatter(porcentaje)
        av.set(ylim=(0, 0.6))

        tlabels = av.get_yticklabels()
        plt.setp(tlabels, ha='left', fontsize=6, color=cchart['2eje'])
        av.tick_params(axis='y', colors=cchart['2eje'])
        av.spines['right'].set_color(cchart['2eje'])
        av.spines.right.set_visible(True)


def chart_extracto(fg: object, cv: object, fontsize=6, dextract=None, columnas=None):

    fg.clear()
    ax = fg.add_subplot()
    ax.set_facecolor(cchart['fondo'])
    ax.set_box_aspect(0.35)

    xdf = pd.DataFrame(dextract, columns=columnas)
    xdf['extracto'] = pd.to_datetime(xdf['extracto'])

    (ln0,) = ax.plot(xdf['extracto'], xdf['costobase'], label='Base de inversión', linestyle='-.',
                                                        linewidth=1, color=cchart['plot1'])

    (ln1,) = ax.plot(xdf['extracto'], xdf['navcierre'], label='Valor market', linestyle='-',
                                                        linewidth=1, color=cchart['plot3'])

    fg.legend(loc='outside upper right', fontsize=6)
    fg.suptitle('Extractos (Renta Variable)', fontsize='medium', color=cchart['titulo'])

    ax.set_xlabel('', fontsize=6, color=cchart['titulo'])
    ax.set_ylabel('dolar ($)', fontsize='x-small', color=cchart['axsy'])
    ax.spines[['top', 'right']].set_visible(False)

    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(6, 12)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    for label in ax.get_xticklabels(which='major'):
        label.set(rotation=30, ha='right', fontsize=6)
    ax.grid(True, color=cchart['axsx'], linewidth=0.3)

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha='right', fontsize='x-small', color=cchart['axsx'])
    plt.setp(ylabels, ha='right', fontsize='x-small', color=cchart['axsy'])
    ymax = float(max(xdf['costobase'])) * 1.3
    ax.set(ylim=[0, ymax])
    ax.yaxis.set_major_formatter(currency)
    ax.tick_params(axis='y', colors=cchart['axsy'])
    ax.tick_params(axis='x', colors=cchart['axsx'])



def char_estrategia(fg: object, cv: object, xaspect=0.30, strategy=None):

    fg.clear()
    ax = fg.add_subplot()
    ax.set_facecolor(cchart['fondo'])
    ax.set_box_aspect(xaspect)

    data, cbar, otro = dict(), list(), 0
    """
        Construccion de dict() para grafico 
    """
    ix = [0, 'Peso', 'Dividendo', 'Objetivo', 'Empresa', 'Estrategia']
    for key in strategy:
        for vehiculo in strategy[key]:

            for estrategia in strategy[key][vehiculo]:
                cbase, adiv = 0, 0
                for activo in strategy[key][vehiculo][estrategia]:
                    keys = list(activo.keys())
                    cbase += activo[keys[0]]
                    adiv += activo[keys[ix.index('Dividendo')]]

                jkey = estrategia if estrategia not in {'Exchange', 'Trading'} else '** ' + estrategia
                cbar.append('tab:green' if estrategia not in {'Exchange', 'Trading'} else 'tab:orange')
                otro += cbase if estrategia not in {'Exchange', 'Trading'} else 0
                data[jkey] = cbase

    group_data = list(data.values())
    group_names = list(data.keys())
    group_mean = np.mean(group_data)
    group_suma = sum(items for items in group_data)

    ax.barh(group_names, group_data, color=cbar)
    ax.spines[:].set_visible(False)
    ax.spines.bottom.set_color(cchart['axsx'])
    ax.spines.bottom.set_visible(True)

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha='right', fontsize=6, color=cchart['axsx'])
    plt.setp(ylabels, ha='right', fontsize=6, color=cchart['texto'])

    ax.set_ylabel('Estrategia', fontsize=6, color=cchart['axsy'])
    ax.set_xlabel('Total Inversión (USD)', fontsize=6, color=cchart['texto'])
    fg.suptitle('Estrategia vs Riesgo', fontsize='medium', color=cchart['titulo'])

    ax.axvline(group_mean, ls=':', color=cchart['texto'])

    gmin = min(group_data)
    gmax = max(group_data)
    xsti = [0, 2e3, 5e3, 7e3, 9e3]

    ptra = '{:>4.1%}'.format(1 - otro/group_suma)
    pres = '{:>4.1%}'.format(otro / group_suma)

    n = len(cbar) - 1
    for group in [2, n]:
        xc = cbar[n] if group == n else cbar[0]
        ax.text(xsti[3], group, ptra if group == n else pres, fontsize=6, va="center", color=xc)

    ax.set(xlim=[gmin, gmax])
    ax.xaxis.set_major_formatter(currency)
    ax.tick_params(axis='x', colors=cchart['axsx'])
    ax.set_xticks(xsti)


def char_performan_estrategia(fg: object, cv: object, fontsize=6, dextract=None, columnas=None):

    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    ax.set_facecolor(cchart['fondo'])
    ax.set_box_aspect(0.40)

    df = pd.DataFrame(dextract, columns=columnas)
    df['extracto'] = pd.to_datetime(df['extracto'])
    df['Ingresos'] = df['crecimiento'] + df['dividendos'] + df['idevengo']
    df['Costos'] = df['fee'] + df['comisiones'] + df['tax'] + df['imargen'] + df['perdidas']
    df['año'] = df['extracto'].dt.year

    resum = df.groupby('año').agg({'Ingresos': 'sum', 'Costos': 'sum'}).reset_index()
    lyear = list(resum['año'])
    resum = resum.set_index('año')
    resum['margen'] = (resum['Ingresos'] - resum['Costos']) / resum['Ingresos']
    m_margen = np.mean(resum['margen'])

    x = np.arange(len(lyear))
    width = 0.25  # the width of the bars
    multiplier = 1
    cbar = ('green', 'red', 'orange')

    p_legend = list()

    for keys, measurement in resum.items():
        offset = width * multiplier
        if keys == 'Ingresos':
            # rects = ax.bar(x + offset, measurement, width, label=keys)
            rects = ax.bar(x + offset, measurement, width, color=cchart['plot4'])
            p_legend.append(mpatches.Patch(color=cchart['plot4'], label=keys))

        if keys == 'Costos':
            # rects = ax.bar(x + offset, measurement, width / 2, label=keys, color=cchart['2eje'])
            rects = ax.bar(x + offset, measurement, width / 2, color=cchart['2eje'])
            p_legend.append(mpatches.Patch(color=cchart['2eje'], label=keys))

    p_legend.append(mpatches.Patch(color=cchart['plot1'], label='Margen Neto'))

    ax.set_ylabel('dolar($)', fontsize='x-small', color=cchart['axsy'])
    ax.set_xlabel('', fontsize='x-small', color=cchart['axsx'])
    ax.spines['top'].set_visible(False)
    ax.grid(True, color=cchart['axsx'], linewidth=0.3)


    fg.legend(loc='outside upper right', handles=p_legend, fontsize=6)
    fg.suptitle('Ingresos y Costes de Operación (Margen)', fontsize='medium', color=cchart['titulo'])

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha='right', fontsize=6, color=cchart['axsx'], rotation=30)
    plt.setp(ylabels, ha='right', fontsize=6, color=cchart['axsy'])

    ax.set_xticks(x + width, lyear)
    ax.yaxis.set_major_formatter(currency)
    ax.tick_params(axis='x', colors=cchart['axsx'])
    """
    @  construcción de 2do eje, para mostrar costos
    """
    av.plot(x + width, resum['margen'], color=cchart['plot1'], linewidth=0.6)

    tlabels = av.get_yticklabels()
    plt.setp(tlabels, ha='left', fontsize=6, color=cchart['plot3'])
    av.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
    av.set_ylabel('Margen Neto', color=cchart['plot1'], fontsize=6)

    av.set(ylim=(0, 1))
    av.tick_params(axis='y', colors=cchart['plot3'])

    av.spines['right'].set_color(cchart['plot3'])
    av.spines.right.set_visible(True)
    av.axhline(m_margen, linewidth=0.6, ls='--', color=cchart['plot3'])
    av.text(x[0], m_margen * 1.15, 'Promedio', fontsize=5, va="center", color=cchart['plot3'])

    cv.draw()


def char_acumulativo(fontsize=8, dextract=None, color='lime'):
    global axs

    df = pd.DataFrame(dextract, columns=ix)

    fmax = 48 if len(dextract) > 48 else len(dextract) - 1
    endd = df['extracto'].iloc[0]
    stad = df['extracto'].iloc[fmax]
    ends = endd.strftime('%Y-%m-%d')
    stas = stad.strftime('%Y-%m-%d')
    print('pase....')
    sp500 = yf.download('^GSPC', start=stas, end=ends, interval='M')['Close']
    print('salida  SP500=', sp500)
    ldat, lcos, lix, ling = list(), list(), list(), list()
    k = fmax
    for i in sp500.index:
        print()
        ldat.append(float(df['navcierre'].iloc[k] - df['costobase'].iloc[k]))
        ling.append(float(df['crecimiento'].iloc[k] + df['dividendos'].iloc[k] + df['idevengo'].iloc[k]))
        lix.append(i)
        k += -1

    inver = pd.Series(ldat, index=lix)
    iing = pd.Series(ling, index=lix)
    r_sp500 = (1 + sp500.pct_change()).cumprod() - 1
    r_inver = (1 + inver.pct_change()).cumprod() - 1

    lcolor = 'tab:gray'
    xlabels = axs.get_xticklabels()
    ylabels = axs.get_yticklabels()
    axs.set_ylabel('Value ($)', color=lcolor, fontsize='x-small')
    axs.stackplot(lix, iing,  labels='Ingresos', alpha=0.2)
    axs.stackplot(lix, inver, labels='Gap NAV', alpha=0.2)

    plt.setp(xlabels, horizontalalignment='right', fontsize='x-small')
    plt.setp(ylabels, horizontalalignment='right', fontsize='x-small')

    axs.set_box_aspect(0.30)
    axs.set_facecolor(color)
    axs.spines[['top', 'bottom']].set_visible(False)
    axs.tick_params(axis='y', labelcolor=lcolor)
    fg0.legend(loc='outside lower right', fontsize='x-small')
    axs.set_title('Rendimiento de inversions (^GSPC)', fontsize='medium', color='blue')
    axs.set_xlabel('', fontsize=fontsize, color='blue')

    ymin = min(ldat)
    ymax = max(ldat)
    amax = max(abs(ymin), abs(ymax))
    axs.yaxis.set_major_formatter(currency)
    axs.set(ylim=[ymin, amax])

    axs.xaxis.set_major_locator(mdates.MonthLocator(bymonth=6))
    axs.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    axs.axhline(0, color='gray', linewidth=0.5, linestyle='--')
    axs.grid(False)

    lcolor = 'tab:gray'
    axt = axs.twinx()  # instantiate a second axes that shares the same x-axis
    axt.set_box_aspect(0.30)
    axt.tick_params(axis='y', labelcolor=lcolor)
    axt.spines[['top']].set_visible(False)

    tlabels = axt.get_yticklabels()
    axt.set_ylabel('Acumlativo (%)', fontsize='x-small', color='blue')
    plt.setp(tlabels, horizontalalignment='left', fontsize='x-small')
    axt.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))

    (ln0,) = axt.plot(r_sp500, label='S&P 500', linestyle='--')
    (ln1,) = axt.plot(r_inver, label='Portafolio', linestyle='dotted')


def setup_fear_greed(fg: object, cv: object):
    """
    With custom locator and formatter.
    Note that the extreme values are swapped.
    """
    def xy_color(score=None):
        color = 'red' if score > 60 else 'green'
        angle = math.radians(((100 - score) / 100) * 180)
        x, y = math.cos(angle), math.sin(angle)
        return x, y, color

    def fear_vix(fear=None):
        hoy = datetime.now().date()
        BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
        START_DATE = hoy.strftime("%Y-%m-%d")
        ua = UserAgent()

        headers = {
            'User-Agent': ua.random,
        }

        r = requests.get(BASE_URL + START_DATE, headers=headers)
        data = r.json()
        wfear = data['fear_and_greed']['score'] if is_none(fear) else fear
        vix = data['market_volatility_vix']['score']
        return wfear, vix

    def char_plot(ax=None, x=None, y=None, score=None, color=None, titulo=None):
        face = 'Gold' if (score > 45) and (score < 60) else 'GreenYellow' if score < 45 else 'OrangeRed'
        acolor = 'GreenYellow' if face == 'Gold' else 'Gold'
        ax.set_facecolor(face)

        ax.arrow(0, 0, x, y, head_width=0.2, head_length=1.0, fc=acolor, ec='black', alpha=0.5)

        ax.text(0, -0.25, titulo, ha='center', va='center', fontsize=10, color='white')

        ax.text(0, 0.30, '{:.0f}'.format(score), ha='center', va='center', fontsize=28, color=acolor)

        ax.text(0.15, 0.25, ix[0], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=66)
        ax.text(0.27, 0.60, ix[1], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=40)
        ax.text(0.50, 0.75, ix[2], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=0)
        ax.text(0.72, 0.60, ix[3], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=-40)
        ax.text(0.85, 0.23, ix[4], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=-66)

    # Crear el gráfico
    fg.clear()
    tr = PolarAxes.PolarTransform()
    ix = ['MIEDO\nEXTREMO', 'MIEDO', 'NEUTRO', 'AVARICIA', 'AVARICIA\nEXTREMA']

    pi = np.pi
    angle_ticks = [(0.00, r"$0$"),
                   (0.20 * pi, r"$\frac{1}{5}\pi$"),
                   (0.40 * pi, r"$\frac{2}{5}\pi$"),
                   (0.60 * pi, r"$\frac{3}{5}\pi$"),
                   (0.80 * pi, r"$\frac{4}{5}\pi$")]

    grid_loc01 = FixedLocator([v for v, s in angle_ticks])
    tick_for01 = DictFormatter(dict(angle_ticks))

    grid_loc02 = MaxNLocator(1)
    grid_help01 = floating_axes.GridHelperCurveLinear(tr, extremes=(pi, 0.00, 2, 1),
                                                      grid_locator1=grid_loc01, grid_locator2=grid_loc02,
                                                      tick_formatter1=tick_for01, tick_formatter2=None)

    fg.suptitle('CNN Fear and Greed Index', color='cyan', fontsize='medium')
    ax = fg.add_subplot(121, axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
    ay = fg.add_subplot(122, axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
    ax.grid()
    ay.grid()

    (fear, vix) = fear_vix()
    (xf, yf, color) = xy_color(fear)
    char_plot(ax=ax, x=xf, y=yf, score=fear, color=color, titulo='Feeling')

    (xv, yv, color) = xy_color(vix)
    char_plot(ax=ay, x=xv, y=yv, score=vix, color=color, titulo='Volatility')

    return


def chart_rendimiento_dividendos(fg: object, cv: object, datos=None, dlabl=None, asset=None):
    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    ax.set_box_aspect(asset['aspect'])

    p_legend, p_zonas = list(), list()
    p_legend.append(mpatches.Patch(color=cchart['plot4'], label=dlabl['symbol'], alpha=0.4))
    p_zonas.append(mpatches.Patch(color=cchart['plot3'], label=dlabl['sell']))
    p_zonas.append(mpatches.Patch(color=cchart['plot1'], label=dlabl['buy']))

    fg.legend(handles=p_zonas, loc=dlabl['legend'], fontsize=6)
    fg.suptitle('Precio vs Rendimiento Dividendo ', fontsize='medium', color=cchart['titulo'])
    activo = asset['ticket'] + ': ' + asset['name']
    # f_legend = ax.legend(handles=p_legend, loc='upper left', fontsize=6)
    # ax.add_artist(f_legend)

    forward = asset['forward']
    d_index = datos.index

    describe = datos.describe()
    p_min = datos["Close"].min()
    ax.plot(d_index, datos['Close'], alpha=.23, color=cchart['plot4'], lw=2)
    ax.fill_between(d_index, p_min, datos['Close'], alpha=0.7)
    ax.set_title(activo)

    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(True, color=cchart['axsx'], linewidth=0.3)
    ax.set_ylabel('Precio promedio ($)', fontsize=6, color=cchart['texto'])

    ax.set_facecolor(cchart['fondo'])
    ylabels = ax.get_yticklabels()
    plt.setp(ax.get_xticklabels(), ha='right', fontsize=6, color=cchart['axsy'], rotation=30)
    plt.setp(ax.get_yticklabels(), ha='right', fontsize=6, color=cchart['axsy'])

    ax.spines.left.set_visible(True)
    ax.spines['left'].set_color(cchart['texto'])
    ax.tick_params(axis='x', colors=cchart['axsy'])
    ax.tick_params(axis='y', colors=cchart['texto'])
    ax.set(ylim=(describe['Close']['min'] * .90, describe['Close']['max'] * 1.1))
    ax.yaxis.set_major_formatter(currency)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    """
     @  construcción de 2do eje, para mostrar % rendimiento de capital + dividendos
    """
    off = .001
    y = describe['Rendimiento']['mean'] + describe['Rendimiento']['std']
    x = describe['Rendimiento']['mean'] - describe['Rendimiento']['std']
    m = describe['Rendimiento']['mean']
    av.scatter(d_index, datos['Rendimiento'],  marker='o', color=cchart['2eje'])
    av.fill_between(d_index, datos['Rendimiento'].values, m, where=(m < datos['Rendimiento']),
                    facecolor=cchart['plot1'], alpha=.4,  interpolate=True)
    av.fill_between(d_index, datos['Rendimiento'].values, m, where=(m > datos['Rendimiento']),
                    facecolor=cchart['plot3'], alpha=.4,  interpolate=True)

    av.axhline(y, linewidth=0.6, ls='--', color=cchart['plot1'])
    av.text(d_index[2], y + off, '{:>+4.1%} Infravalorado el activo'.format(y), fontsize=6, color=cchart['texto'])
    av.axhline(m, linewidth=0.6, ls='--', color=cchart['texto'])
    av.axhline(x, linewidth=0.6, ls='--', color=cchart['plot3'])
    av.text(d_index[2], x - off, '{:>+4.1%} Sobrevalorado el activo'.format(x), fontsize=6, color=cchart['texto'])
    av.text(d_index[-1], forward, '{:>+4.1%} forward'.format(forward), fontsize=6, ha='right', color=cchart['texto'])

    av.set_ylabel('Rendimiento Dividendo', fontsize=6, color=cchart['2eje'])
    av.tick_params(axis='y', labelcolor=cchart['2eje'])
    av.yaxis.set_major_formatter(porcentaje)
    #
    # calcula limites para el eje de rendimiento, considera el max entre forward, limites
    # infravalorado y sobrevalorado
    l_max = max(describe['Rendimiento']['max'], y)
    l_min = min(describe['Rendimiento']['min'], x)
    av.set(ylim=(l_min * .95, l_max * 1.05))

    tlabels = av.get_yticklabels()
    plt.setp(tlabels, ha='left', fontsize=6, color=cchart['2eje'])
    av.tick_params(axis='y', colors=cchart['2eje'])
    av.spines['right'].set_color(cchart['2eje'])
    av.spines.right.set_visible(True)


def char_performance_sector(fg: object, cv: object, datos=None, dlabl=None, asset=None):

    fg.clear()
    ax = fg.add_subplot()
    av = ax.twinx()
    ax.set_facecolor(cchart['fondo'])
    ax.set_box_aspect(dlabl['aspect'])

    vs = 'Perf Quart'
    x = np.arange(len(datos['Name']))
    width = 0.60  # the width of the bars
    multiplier = 1
    cbar = ('green', 'red', 'orange')
    xmax = max(datos['Perf Year'].max(), datos[vs].max())
    xmin = min(datos['Perf Year'].min(), datos[vs].min())
    lm = (xmin, xmax)

    p_legend = list()

    for keys, measurement in datos.items():
        offset = width * multiplier
        if keys == 'Perf Year':
            rects = ax.bar(x + offset, measurement, width, color=cchart['plot4'], alpha=0.35)
            p_legend.append(mpatches.Patch(color=cchart['plot4'], label=keys))

        if keys == 'Perf Quart':
            rects = ax.bar(x + offset, measurement, width * .45, color=cchart['2eje'])
            p_legend.append(mpatches.Patch(color=cchart['2eje'], label=keys))


    p_legend.append(mpatches.Patch(color=cchart['plot1'], label='weight Portafolio'))
    fg.legend( loc=dlabl['legend'], handles=p_legend, fontsize=6)
    fg.suptitle('Performance por Sector vs Portafolio', fontsize='medium', color=cchart['titulo'])
    #
    # set eje X
    xlabels = ax.get_xticklabels()
    plt.setp(xlabels, ha='right', fontsize=6, color=cchart['axsx'], rotation=25)
    ax.set_xlabel('', fontsize='x-small', color=cchart['axsx'])

    ax.spines.left.set_visible(True)
    av.spines['left'].set_color(cchart['axsy'])

    ax.set_xticks(x + width, datos['Name'])
    ax.grid(True, color=cchart['axsx'], linewidth=0.3)
    ax.set_ylim([xmin, xmax])

    #
    # set 1er eje Y
    ylabels = ax.get_yticklabels()
    plt.setp(ylabels, ha='right', fontsize=6, color=cchart['axsy'])
    ax.set_ylabel('Rendimiento', fontsize=6, color=cchart['axsy'])

    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
    ax.tick_params(axis='y', colors=cchart['axsx'])
    """
    @  construcción de 2do eje, para mostrar costos
    """
    av.plot(x + width, datos['Peso'], color=cchart['plot1'], linewidth=0.9,  ls='--')

    tlabels = av.get_yticklabels()
    plt.setp(tlabels, ha='left', fontsize=6, color=cchart['plot1'])
    av.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:2.0%}"))
    av.set_ylabel('% Inversión', color=cchart['plot1'], fontsize=6)

    p_peso = datos['Peso'].mean()
    av.set_ylim([xmin, xmax])
    av.tick_params(axis='y', colors=cchart['plot1'])
    # av.axhline(p_peso, linewidth=0.6, ls='--', color=cchart['plot3'])
    # av.text(x[0], p_peso * 1.15, 'Peso Promedio', fontsize=5, va="center", color=cchart['plot3'])

    # av.spines['right'].set_color(cchart['plot3'])
    av.spines.right.set_visible(True)
    # cv.draw()




