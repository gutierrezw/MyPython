from Class_DataFrame import get_yfinance
from Modulos_Mysql import (IPerformance, RepositorioOportunidadesBuySell)
from Modulos_Utilitarios import vehiculo_parm, convierte_ticket_crypto, porcentaje
from Modulos_Comunes import detalle_book, read_csv_insert_diaria, crea_dataframe_performa_Index
from Modulos_python import *

"""
 fecha:: 2024-08-24
 nota::: modulo para reconstruir  tabla performa inversión específicamente para Stock,  se hace pasos
         1) se crea index de referencia 
         2) se obtiene de booktrading, los símbolos  y Dataframe de  las operaciones 
         3) se actualiza el acumulado porcentual de cada simbolo en performa del stock (P_vehiculo) de acuerdo
            al peso para en momento de la operación.
         4) Eliminar manualmente la tablas performa_inversion
         4) hay que cargar tabla diaria_performa antes de iniciar el paso (5) 
         6) cambiar a False switch diaria para iniciar carga performa_inversion
"""

ROp = RepositorioOportunidadesBuySell()
Inv = IPerformance()


def plot_index(wperf, fg, log=True):
    ax = fg.add_subplot()
    ax.plot(wperf.index, wperf[cum_index], label='S&P 500 Return ')

    ax.set_facecolor('black')
    titulo = 'S&P 500 Cumulative Logaritico' if log else 'S&P 500 Cumulative Return '
    fg.suptitle(titulo, fontsize='medium', color='cyan')
    fg.legend(loc='outside upper right', fontsize=6)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    ax.yaxis.set_major_formatter(porcentaje)

    ax.set_ylabel('Cumulative Return', fontsize=6)

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha='right', rotation=20, fontsize=6, color='white')
    plt.setp(ylabels, ha='right', fontsize=6, color='white')
    ax.grid(True)


def plot_asset(wperf):
    fg2.clear()
    ax = fg2.add_subplot()

    ax.plot(wperf.index, wperf[cum_index], label='Index Cumulative Return', color='orange')
    ax.plot(wperf.index, wperf['CumPort'], label='Cumulative Return ++portafolio')

    ax.set_facecolor('black')
    fg2.suptitle('Comparación de retornos acumulados', fontsize='medium', color='cyan')
    fg2.legend(loc='outside upper right', fontsize=6)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    ax.yaxis.set_major_formatter(porcentaje)
    ax.set_ylabel('Return', fontsize=6)

    xlabels = ax.get_xticklabels()
    ylabels = ax.get_yticklabels()
    plt.setp(xlabels, ha='right', rotation=20, fontsize=6, color='white')
    plt.setp(ylabels, ha='right', fontsize=6, color='white')
    ax.grid(True)


def inserta_index_performa(df=None, insert=True):
    for fecha, rows in df.iterrows():
        values = {}
        values.update({'idcuenta': account})
        values.update({'vehiculo': vehiculo})
        values.update({'idcuenta': account})
        values.update({'vehiculo': vehiculo})
        values.update({'fechaclose': fecha})
        values.update({'referencia': index_ref})
        values.update({'p_referencia': rows[rtn_index]})
        values.update({'p_vehiculo':  rows['retorno']})
        values.update({'gyp_dia': rows['gyp_dia']})
        values.update({'nr_gyp': rows['nr_gyp']})
        values.update({'value': rows['value']})
        values.update({'costo_base': rows['costo_base']})
        values.update({'dividends': rows['dividends']})

        if insert:
            Inv.insert_performa_inversion(values)


# Leer el archivo CSV y convertirlo en una lista
def read_csv_insert_diaria(path=None, insert=False):

    with open(path, mode='r', newline='') as file:
        reader = csv.reader(file)
        ix = next(reader)
        diaria = [rows for rows in reader]

        if insert:
            for read in diaria:
                values = {}
                for i, col in enumerate(ix, start=0):
                    if col == 'symbol':
                        symbol = read[i]
                    
                    elif col != 'symbol':
                        values.update({col: read[i]})

                # print(f"Insertando diaria_performance {symbol} - {values}")
                if float(values['cantidad']) > 0:
                    Inv.insert_diaria_performance(values, symbol=symbol) 

    return diaria, ix


def procesar_cuenta_desde_inicio(new_diaria=True, insert=False):
    book, ix = [], []

    #  True para construir diaria y graficar
    if new_diaria:
        book, ix = ROp.select_booktrading(accion='cartera', account=account, idivisa=divisa)
        path = detalle_book(account=account, vehiculo=vehiculo, book=book, ix=ix)

        # Leer el archivo CSV y convierte en lista
        diaria, iy = read_csv_insert_diaria(path, insert)
            
        df_performa = crea_dataframe_performa_Index(account=account,
                                                    vehiculo=vehiculo,
                                                    display=True,
                                                    diaria=diaria,
                                                    iy=iy)

    else:
        # caso que toma diaria de las tablas
        diaria, iy = Inv.select_diaria_performance(account=account)
        df_performa = crea_dataframe_performa_Index(account=account,
                                            vehiculo=vehiculo,
                                            display=True,
                                            diaria=diaria,
                                            iy=iy)

    plot_asset(df_performa)

    # inserta tabla inversion_performance desde el inicio
    if insert:
       inserta_index_performa(df_performa)


def procesar_cuenta_desde_app(new_diaria=True, insert=False):
    book, ix = [], []

    #  True para construir diaria y graficar
    if new_diaria:
        book, ix = ROp.select_booktrading(accion='diaria_app', account=account, idivisa=divisa)
        path = detalle_book(account=account, vehiculo=vehiculo, book=book, ix=ix, option='app')

        # Leer CSV e inserta después de ultima diaria
        diaria, iy = read_csv_insert_diaria(path=path, insert=False)

if __name__ == '__main__':

    win = tk.Tk()
    dimension = "%dx%d+0+0" % (900, 700)
    win.geometry(dimension)
    win.config(bg="black")

    dp1 = ttk.Frame(win, style="TFrame", width=700, height=300)
    dp1.grid(column=0, row=0)
    dp2 = ttk.Frame(win, style="TFrame", width=700, height=300)
    dp2.grid(column=0, row=1)


    fg1 = Figure(figsize=(8, 3), dpi=110, layout="tight")
    fg1.set_facecolor('black')
    cv1 = FigureCanvasTkAgg(fg1, master=dp1)
    cv1.draw()
    cv1.get_tk_widget().pack()

    fg2 = Figure(figsize=(8, 3), dpi=110, layout="tight")
    fg2.set_facecolor('black')
    cv2 = FigureCanvasTkAgg(fg2, master=dp2)
    cv2.draw()
    cv2.get_tk_widget().pack()

    # cuentas = {'Stock': {'account': 'U4214563', 'divisa': 'USD'}}
    # cuentas = {'Crypto':{'account': 'B0000001', 'divisa': 'USD'}}
    cuentas = {'BBVA.ARS':{'account': 'BBVA0001', 'divisa': 'ARS'}}
    cuentas = {'BBVA.ARS':{'account': 'SANT0001', 'divisa': 'ARS'}}

    Performa = Performance()

    for vehiculo, param in cuentas.items():
        account = param['account']
        divisa = param['divisa']    

        symbol, rtn_index, cum_index, index_ref = vehiculo_parm(vehiculo=vehiculo)
        hoy = datetime.now().date()

        procesar_cuenta_desde_inicio(new_diaria=True, insert=True)
        # procesar_cuenta_desde_app(new_diaria=True, insert=True)

    win.mainloop()


