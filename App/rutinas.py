import calendar
import random
import time
from _datetime import *
from decimal import *
from tkinter import ttk

import pandas as pd
import yfinance as yf
from dateutil.relativedelta import relativedelta


def is_null(s):
    """ Valida si el parametro contingent valor Null o espacios """

    if s.isspace() or s == '':
        rc = True
    else:
        rc = False
    return rc


def is_none(s) -> bool:
    """ Valida si el parametro contingent valor None """
    if s is None:
        rc = True
    else:
        rc = False
    return rc


def is_datetime(s):
    try:
        datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
        return True
    except ValueError:
        return False


def is_numeric(s) -> bool:
    """ Valida si es numerico  string """
    try:
        if is_none(s):
            return False
        else:
            float(s)
            return True
    except ValueError:
        return False


def is_vacio(s) -> bool:
    """
    @param s: dict o list
    @return:  Valida si 's' es vacio
    """
    sset = True
    try:
        if type(s) is dict:
            if s == {}:
                sset = False
            else:
                if 'Stock' in s or 'Crypto' in s:
                    sset = False

        if type(s) is list:
            if s == []:
                sset = False

    except ValueError:
        return sset


def is_magnitud(x) -> int:
    """
    @param x: numero decimal
    @return: obtiene magnitud de numero
    """
    try:
        i = 0
        if is_numeric(x):
            n = int(x)
            for i in range(0, 100):
                if n % 10 == 0:
                    if int(n / 10) == 0:
                        return i - 1

                n = int(n / 10)

    except ValueError:
        return -1


def entry_numeric(p):
    """ Data entry de campo numerico decimal"""
    if p == "" or p.replace(".", "", 1).isdigit():
        return True
    else:
        return False


def str_float(s):
    try:
        str(s)
        if s == ' ':
            return 0
    except ValueError:
        return s


def is_entero(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def list_ticket(positions) -> list:
    i = 0
    conid_list = []
    for key in positions:
        conid_list.append(str(positions[i]['conid']))
        i += 1
    return conid_list


def sort_positions(struct, orden) -> dict:
    i = 0
    keys = orden[0]
    como = orden[1]
    if como == 'ASC':
        for i in range(len(struct)-1):
            for j in range(i+1, len(struct)):
                if struct[i][keys] > struct[j][keys]:
                    sortposition = struct[i]
                    struct[i] = struct[j]
                    struct[j] = sortposition
            i += 1
    else:
        for i in range(len(struct)-1):
            for j in range(i+1, len(struct)):
                if struct[i][keys] < struct[j][keys]:
                    sortposition = struct[i]
                    struct[i] = struct[j]
                    struct[j] = sortposition
            i += 1

    return struct


def time_string():
    return time.strftime('%H:%M:%S')


def ultimo_dia_mes(year, mes):
    num_dias = calendar.monthrange(year, mes)[1]
    ultima_fecha = f"{year}-{mes:02d}-{num_dias:02d}"
    return ultima_fecha


def validar_fecha(fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
        return True, fecha
    except ValueError:
        return False, None


def valida_meses_consecutivos(inicio=None, fin=None):
    """
    @param inicio:  fecha inicial
    @param fin: fecha final
    @return: retorna TRUE si los meses son consecutivos entre inicio y fin
    """
    if isinstance(inicio, date):
        s_inicio = inicio.strftime("%Y-%m")

    if isinstance(fin, datetime):
        s_fin = fin.strftime("%Y-%m")

    f_inicio = datetime.strptime(s_inicio, "%Y-%m")
    f_fin = datetime.strptime(s_fin, "%Y-%m")
    diferencia = relativedelta(dt1=f_fin, dt2=f_inicio, months=1)

    return f_fin == f_inicio + diferencia


def proximo_extracto(extract):
    mes = extract.month + 1 if extract.month < 12 else 1
    year = extract.year + 1 if mes == 1 else extract.year
    fecha = ultimo_dia_mes(year, mes)
    return fecha


def peso_inversion(positions, invertir, peso) -> float:
    tabla: dict = {'Gprc':   {'25%': 0.5, '50%': 1, '75%': 2.5, '100%': 3},
                   'GGyp':   {'25%': 0.5, '50%': 1, '75%': 2.5, '100%': 3},
                   'ema144': {'menorq': 0.5, 'mayorq': 1.0},
                   'ema55':  {'menorq': 1.0, 'mayorq': 0.5},
                   'peso': {'menorq': 2.0, 'mayorq': 0.5}
                   }

    def convertir(dato):
        num = 0
        if not dato.isalpha() and not isNumeric(dato):
            x = dato.replace("%", '')
            num = float(x) / 100
        else:
            num = 0.10
        return num

    valor = 0.00
    """
    @ valora ganancias del precio medio
    @ respecto al precio objetivo
    """
    if positions['Obje'] > 0:
        dprc: float = (positions['avgCost'] - positions['prcmd']) / positions['avgCost']
        keys = tabla['Gprc']
        for i in keys:
            if convertir(i) >= dprc:
                valor += keys[i]
                break
            else:
                if convertir(i) == 1:
                    valor += keys[i]

        """
        @ valora delta de Gyp proyectado
        @ respecto a las Gyp  objetivo
        """
        if positions['GyPo'] > 0:
            keys = tabla['GGyp']
            dpyg = (positions['GyPp'] - positions['GyPo']) / invertir
            for i in keys:
                if convertir(i) >= dpyg:
                    valor += keys[i]
                    break
                else:
                    if convertir(i) == 1:
                        valor += keys[i]
        """
        @ valora peso del activo para que no
        @ exceda el 10% de la cartera
        """
        if peso > 0:
            keys = tabla['peso']
            if peso <= 0.10:
                valor += keys['menorq']
            else:
                valor += keys['mayorq']

    valor = valor / 8
    return valor


def buscar_string(string, items) -> bool:
    encontro = False
    for i in range(len(string)):
        if items in string:
            encontro = True
            break
    return encontro


def buscar_ticker(positions, ticket) -> float:
    """
    @param positions: estructura de portafolio
    @param ticket:  activo a buscar en positions
    @return:  logico de encontrado o NO y la información encontrada
    """
    found = False
    keys = dict()
    for keys in positions:
        ix = 'contractDesc' if 'contractDesc' in keys else 'ticket'
        if keys[ix] == ticket:
            found = True
            break
    return found, keys


def convierte_ticket_crypto(s: str) -> str:
    ticket = s
    ticket = ticket.replace("USDT", "-USD")
    ticket = ticket.replace(" CRYPTO", "-USD")
    return ticket


def valida_yahoo(ticket) -> list:
    """

    @param ticket:
    @return:
    """
    found = False
    pdf = list()
    try:
        hoy = datetime.now()
        estamp = hoy + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        pdf = yf.download(ticket, start=hoy, end=estamp)
        if pdf.empty:
            found = True
    except NameError as error:
        print("[yahoo error]: {}".format(error))

    return found, pdf


def currency(y=None, pos=None):
    """The two arguments are the value and tick position"""
    x = y if y >= 0 else -y

    if x >= 1e6:
        s = '${:1.1f}M'.format(y*1e-6)
    else:
        if x < 1e3:
            if x > 1:
                s = '${:3.1f}'.format(y)
            else:
                s = '${:3.3f}'.format(y)
        else:
            s = '${:1.1f}K'.format(y*1e-3)

    return s


def porcentaje(y, pos=1):
    """The two arguments are the value porcentaje"""
    x = y if y >= 0 else -y

    if x >= 1e3:
        s = '{:4.0%}'.format(y)
    else:
        if x < 1e2:
            s = '{:3.2%}'.format(y)
        else:
            s = '{:2.1%}'.format(y)

    return s


def numero_randon(amplitud: int, fecha=None) -> int:
    """ Calcula numero aleatorio dada la amplitud deseada """
    nro_aleatorio: int = 0
    try:
        if is_none(fecha):
            timestamp = int(time.time())

        else:
            fecha = fecha.replace(',', '')
            dfecha = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
            timestamp = dfecha.timestamp()

        random.seed(timestamp)
        nro_aleatorio = random.randint(1, amplitud)

    except EncodingWarning as error:
        print("[Random error]: {}".format(error))

    return nro_aleatorio


def donde_invertir(positions_i, p_invertir) -> Decimal:
    """
    @param positions_i:  ticket del activo a calcular
    @param p_invertir: importe de a invertir en el ticket
    @return:
    """
    nstok, prcmd, gypp, nposi, vix_vp, vix_gp, indx = 0, 0, 0, 0, 0, 0, 0
    indx = dict(ixGp=0, ixVp=0)
    if (p_invertir > 0) and (positions_i['mktPrice'] > 0) and (positions_i['avgCost'] > 0):
        stock = Decimal(positions_i['position'])
        nstok = p_invertir / positions_i['mktPrice']
        obje = positions_i['objetivo']
        pdiv = positions_i['dividendo'] / stock
        gypo = positions_i['gypo']
        xfee = Decimal(0.35)
        if nstok > 0:
            nposi = stock + nstok
            prcmd = (positions_i['costobase'] + positions_i['mktPrice'] * nstok + xfee) / nposi
            gypp = (obje - prcmd + pdiv) * nposi
            vix_vp = (prcmd - positions_i['avgCost'])/positions_i['avgCost']
            vix_gp = (gypp - gypo) / gypo
            indx = dict(ixGp=vix_gp, ixVp=vix_vp)
    return nstok, prcmd, gypp, indx


def display_red_green(campo=None, i=None) -> str:
    if not is_none(i):
        if i % 2 != 0:
            cbg = "Wr.TLabel" if campo < 0 else "Wg.TLabel"

        if i % 2 == 0:
            cbg = "Br.TLabel" if campo < 0 else "Bg.TLabel"

    if is_none(i):
        cbg = "Wr.TLabel" if campo < 0 else "Wg.TLabel"

    return cbg


def display_azul(campo, i) -> str:
    if campo < 0.10:
        iibg = "Cb.TLabel" if i == 5 else ("Cb.TLabel" if i % 2 == 0 else "Cw.TLabel")
    else:
        iibg = "Sy.TLabel" if i == 5 else ("Sy.TLabel" if i % 2 == 0 else "Cw.TLabel")

    return iibg


def win_atrib(r):
    altura = r.winfo_reqheight()
    anchura = r.winfo_reqwidth()
    altura_pantalla = r.winfo_screenheight()
    anchura_pantalla = r.winfo_screenwidth()
    print(f"Altura: {altura}\nAnchura: {anchura}\nAltura de pantalla: {altura_pantalla}\nAnchura"
          f" de pantalla: {anchura_pantalla}")


def vehiculo_parm(vehiculo=None) -> str:
    """
    @param vehiculo:
    @return:
    """
    if vehiculo in ('Crypto', 'token'):
        symbol = "BTC-USD"
        rtn_index = 'Return BTC'
        cum_index = 'Cum BTC'
        index_ref = 'BTC++index'

    if vehiculo == 'Stock':
        symbol = '^GSPC'
        rtn_index = 'Return SPX'
        cum_index = 'Cum SPX'
        index_ref = 'SPX++index'

    return symbol, rtn_index, cum_index, index_ref


def retrocesos_fib(low=None, high=None, ema09=None, ema21=None, datos=None, desde=None) -> dict:
    """
    @param low:
    @param high:
    @param ema09:
    @param ema21:
    @param datos:
    @param desde:
    @return:
    """

    fib = [0, 0.236, 0.382, 0.50, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0]
    t_alcista, t_bajista, long = dict(), dict(), True
    rango = high - low
    for ix, valor in enumerate(fib):
        key = '{:> 3.1%}'.format(valor)
        t_alcista.update({key: low + valor * rango})

        if high - valor * rango > 0:
            fib_ant = high - valor * rango
            t_bajista.update({key: fib_ant})
        else:
            t_bajista.update({key: fib_ant})

    if ema09 <= ema21:
        zone_fib0 = dict(y1=t_alcista[' 0.0%'], y2=t_alcista[' 23.6%'], color='red', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib1 = dict(y1=t_alcista[' 23.6%'], y2=t_alcista[' 38.2%'], color='green', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib2 = dict(y1=t_alcista[' 38.2%'], y2=t_alcista[' 61.8%'], color='lime', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib3 = dict(y1=t_alcista[' 61.8%'], y2=t_alcista[' 78.6%'], color='cyan', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib4 = dict(y1=t_alcista[' 78.6%'], y2=t_alcista[' 100.0%'], color='gray', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib5 = dict(y1=t_alcista[' 100.0%'], y2=t_alcista[' 127.2%'], color='blue', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
    else:
        long = False
        zone_fib0 = dict(y1=t_bajista[' 0.0%'], y2=t_bajista[' 23.6%'], color='red', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib1 = dict(y1=t_bajista[' 23.6%'], y2=t_bajista[' 38.2%'], color='green', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib2 = dict(y1=t_bajista[' 38.2%'], y2=t_bajista[' 61.8%'], color='lime', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib3 = dict(y1=t_bajista[' 61.8%'], y2=t_bajista[' 78.6%'], color='cyan', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib4 = dict(y1=t_bajista[' 78.6%'], y2=t_bajista[' 100.0%'], color='gray', alpha=0.2,
                         interpolate=True, where=(datos['EMA009'].index > desde))
        zone_fib5 = dict(y1=t_bajista[' 100.0%'], y2=t_bajista[' 127.2%'], color='blue', alpha=0.3,
                         interpolate=True, where=(datos['EMA009'].index > desde))

    return long, t_alcista, t_bajista, zone_fib0, zone_fib1, zone_fib2, zone_fib3, zone_fib4, zone_fib5


def nivel_fib(ax, l_ix, t_alcista, t_bajista, long):
    if long:
        t_fib = t_alcista
    else:
        t_fib = t_bajista
    i = 0
    for key, valor in t_fib.items():
        if i != 0 and long:
            ax.text(l_ix, valor, key, fontsize=5, ha="center", color='white')

        if i != 6 and not long:
            ax.text(l_ix, valor, key, fontsize=5, ha="center", color='white')

        i += 1
    return ax


def numero_fib(n=None) -> int:
    """
    @param n:  numero de entrada
    @return: obtiene numero fibonacci inmediato inferior al input
    """
    fib = [0, 1, 2]
    for i in range(3, 15):
        fib.append(fib[i - 2] + fib[i - 1])
        if fib[i] > n:
            break
    return fib[i - 1]


def style_app(main=None) -> object:
    """
    @param main:  windonw principal de la aplicación
    @return: configura colores y style de la aplicación
    """
    style = ttk.Style(main)
    style.configure('T.TButton', foreground="white", background="black")
    style.configure('TFrame', font=('Courier', 8), foreground="white", background="black")
    style.configure('C.TFrame', font=('Courier', 8), foreground="white", background="DarkCyan")
    style.configure('C.TLabel', font=('Courier', 8), foreground="white", background="DarkCyan")
    style.configure('TLabel', font=('Courier', 8), foreground="white", background="black")
    style.configure('I.TFrame', font=('Courier', 8), foreground="black", background="white")
    style.configure('Ig.TFrame', font=('Courier', 12), foreground="SpringGreen3", background="white")
    style.configure('I.TLabel', font=('Courier', 8), foreground="black", background="white")
    style.configure('G.TLabel', font=('Courier', 8), foreground="white", background="green")
    style.configure('Gb.TLabel', font=('Courier', 8), foreground="green", background="black")
    style.configure('R.TLabel', font=('Courier', 8), foreground="white", background="red")
    style.configure('B.TFrame', font=('Courier', 8), foreground="blue", background="white")
    style.configure('Wb.TFrame', font=('Courier', 8), foreground="white", background="blue")
    style.configure('Cw.TLabel', font=('Courier', 8), foreground="black", background="white")
    style.configure('Cb.TLabel', font=('Courier', 8), foreground="yellow", background="black")
    style.configure('Wc.TLabel', font=('Courier', 8), foreground="white", background="CadetBlue")
    style.configure('Cy.TLabel', font=('Courier', 8), foreground="yellow", background="CadetBlue")
    style.configure('Sy.TLabel', font=('Courier', 8), foreground="yellow", background="NavajoWhite3")
    style.configure('Ws.TLabel', font=('Courier', 8), foreground="yellow", background="NavajoWhite3")
    style.configure('By.TLabel', font=('Courier', 8), foreground="yellow", background="blue")
    style.configure('G.TSeparator', font=('Courier', 8), foreground="green", background="black")
    style.configure('Br.TLabel', font=('Courier', 8), foreground="black", background="red3")
    style.configure('Bg.TLabel', font=('Courier', 8), foreground="black", background="green2")
    style.configure('Wr.TLabel', font=('Courier', 8), foreground="White", background="firebrick4")
    style.configure('Wg.TLabel', font=('Courier', 8), foreground="White", background="dark green")
    #
    # (C.TScrollbar)
    #
    style.configure("C.TScrollbar",
                    troughcolor="gray",
                    background="blue",
                    arrowcolor="white",
                    relief="flat",
                    gripcount=10)
    style.configure("C.TScrollbar",
                    troughcolor="gray",
                    background="blue",
                    arrowcolor="white",
                    relief="flat",
                    gripcount=10)
    #
    # (C.Treeview)
    #
    style.configure("C.Treeview",
                    background="black",
                    foreground="white",
                    fieldbackground="black",
                    font=("Helvetica", 9))
    style.map("C.Treeview",
              background=[('selected', 'DarkCyan')],
              foreground=[('selected', 'white')])

    return style


def style_all(main=None) -> object:
    """
     @param main:  windonw principal de la aplicación
     @return: configura colores y style  de la aplicación
     """
    style = ttk.Style(main)

    style.configure('TFrame',
                    foreground="white",
                    background="black")
    style.configure('W.TFrame',
                    foreground="black",
                    background="DarkCyan")

    style.configure('W.TLabel',
                    foreground="black",
                    background="DarkCyan")
    style.configure('W.TButton',
                    foreground="black",
                    background="DarkCyan")

    style.configure("W.TRadiobutton",
                    background="DarkCyan",
                    foreground="black",
                    indicatorcolor="red",
                    indicatordiameter=10,
                    indicatormargin=-2,
                    padding=2)

    style.configure('Treeview',
                    foreground="white",
                    background="black",
                    fieldbackground="black")

    style.configure("Treeview.Heading",
                    background="DarkCyan",
                    foreground="black",
                    relief="flat")

    style.configure("W.TRadiobutton",
                    background="DarkCyan",
                    foreground="black",
                    indicatorcolor="red",
                    indicatordiameter=10,
                    indicatormargin=-2,
                    padding=2)


def mask_numero(numero):
    if abs(numero) >= 1_000_000_000_000:
        return f'{numero / 1_000_000_000_000:.1f}T'
    elif abs(numero) >= 1_000_000_000:
        return f'{numero / 1_000_000_000:.1f}B'
    elif abs(numero) >= 1_000_000:
        return f'{numero / 1_000_000:.1f}M'
    elif abs(numero) >= 1_000:
        return f'{numero / 1_000:.1f}K'
    else:
        return str(numero)


if __name__ == '__main__':
    print('rutinas-----')
    print(is_magnitud(1000))