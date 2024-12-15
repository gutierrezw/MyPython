from tkinter import Tk

from finvizfinance.group.performance import Performance
from finvizfinance.quote import finvizfinance
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from api_chart import char_performance_sector
from bd_conect import *

path = os.getcwd()
path = path + '\\tmp'


def chat_finviz(symbol=None):
    """
    @param symbol: ticket a consultar
    @return:
    """

    stock = finvizfinance(symbol)
    x = stock.ticker_charts(timeframe='daily',  charttype="advanced", out_dir=path)
    # Image(filename='tsla.jpg')
    return stock


def grupo_sector(fg, cv):
    """
    @param fg:
    @param cv:
    @return:
    """

    def get_sector_portafolio():
        xsector = {'Consumer, Non-cyclical': 'Consumer Defensive',
                   'Communications': 'Communication Services',
                   'Industrial': 'Industrials',
                   'Consumer, Cyclical': 'Consumer Cyclical',
                   'Technology': 'Technology',
                   'Energy': 'Energy',
                   'Financial': 'Financial',
                   'Basic Materials': 'Basic Materials',
                   'None': 'Financial'}

        positions = select_inversion(tipoin='Stock', ticket='all')
        d_sector, total = dict(), 0
        for pkeys in positions:
            key_sec = pkeys['sector']
            total += float(pkeys['costobase'])
            value = xsector[key_sec] if key_sec in list(xsector.keys()) else xsector['None']
            if key_sec not in list(xsector.keys()):
                print('get_sector_portafolio() - Sector no encontrado::', key_sec)

            if value not in list(d_sector.keys()):
                d_sector[value] = float(pkeys['costobase'])
            else:
                d_sector[value] += float(pkeys['costobase'])

        name = list(d_sector.keys())
        inversion = list(d_sector.values())
        s_sector = {'Name': name,
                    'Inversion': inversion,
                    'Peso': [x / total for x in inversion]}

        return s_sector

    fg_performance = Performance()
    sector = fg_performance.screener_view(group='Sector')

    d_positions = get_sector_portafolio()
    p_sector = pd.DataFrame(d_positions)

    datos = pd.merge(sector, p_sector, on='Name', how='left')
    datos.fillna(0, inplace=True)

    dlabl = {'BTC': 'BTC++index', '++ index': "++ Token's", "legend": 'outside lower right', "aspect": 0.30}
    char_performance_sector(fg, cv, datos=datos, dlabl=dlabl)




if __name__ == '__main__':
    win = Tk()
    gcolor = 'black'
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)

    win.config(bg=gcolor)
    style = ttk.Style(win)
    style.configure('TFrame',   font=('Courier', 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)
    win1 = tk.Frame(dpn, bg='black')
    win2 = tk.Frame(dpn, bg='black')
    win1.grid(column=0, row=0, padx=2)
    win2.grid(column=1, row=0, padx=2)

    fg = Figure(figsize=(5.3, 2.7), dpi=110, layout="tight")
    ax = fg.add_subplot()
    fg.set_facecolor(gcolor)
    cv = FigureCanvasTkAgg(fg, master=win2)
    cv.draw()
    cv.get_tk_widget().pack()

    # ticket = chat_finviz('HASI')
    group_sector(fg, cv)

    win.mainloop()
