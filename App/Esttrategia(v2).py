import csv
from tkinter import filedialog

from api_chart import *

global tree, extract


def cagar_csv_extracto():
    try:
        ruta = filedialog.askopenfilename(title="Activity Statement", filetypes=(("Archivos CSV", "*.csv"),))
        extracto, ilog = dict(), False
        if ruta:
            if ruta.endswith('.csv'):
                with (open(ruta, newline='') as csvfile):

                    spamreader = csv.reader(csvfile, delimiter=',')

                    for row in spamreader:

                        if ('Statement' in row) and ('Data' in row):
                            pass
                        elif 'Period' in row:
                            f_inicio, f_fin = row[-1].split(' - ')
                            f_fin = f_fin.strip()

                            f_obj = datetime.strptime(f_fin, "%B %d, %Y")
                            fecha = f_obj.strftime("%Y-%m-%d")
                            extracto.update({'periodo': fecha})

                        elif ('Title' in row) and ('Activity Statement' in row):
                            ilog = true

                        if ('Cash Report' in row) and ('Data' in row) and ('Commissions' in row):
                            ix = ('Cash Report', 'Header', 'Currency Summary', 'Currency', 'Total',
                                  'Securities', 'Futures', 'Paxos')
                            extracto.update({'comisiones': row[ix.index('Securities')]})

                        if ('Dividends' in row) and ('Data' in row) and ('Total' in row):
                            ix = ('Dividends', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')
                            extracto.update({'dividendos': row[ix.index('Amount')]})

                        if ('Withholding Tax' in row) and ('Data' in row) and ('Total' in row):
                            ix = ('Withholding Tax', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount', 'Code')
                            extracto.update({'tax': row[ix.index('Amount')]})

                        if ('Fees' in row) and ('Data' in row) and ('Total' in row):
                            ix = ('Fees', 'Header', 'Subtitle', 'Currency', 'Account', 'Date', 'Description', 'Amount')
                            extracto.update({'fee': row[ix.index('Amount')]})

                        if ('Deposits & Withdrawals' in row) and ('Data' in row) and ('USD' in row):
                            ix = ('Deposits & Withdrawals', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')

                            extracto.update({'depositos': 0})
                            extracto.update({'retiradas': 0})
                            extracto.update({'transferencias': 0})

                            if 'Electronic Fund Transfer' in row[ix.index('Description')]:
                                extracto.update({'depositos': row[ix.index('Amount')]})
                            if 'Disbursement' in row[ix.index('Description')]:
                                extracto.update({'retiradas': row[ix.index('Amount')]})
                            if 'Internal Transfer' in row[ix.index('Description')]:
                                extracto.update({'transferencias': row[ix.index('Amount')]})

                        if ('Interest' in row) and ('Data' in row) and ('USD' in row):
                            ix = ('Interest', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')

                            if 'Debit' in row[ix.index('Description')]:
                                extracto.update({'margen': row[ix.index('Amount')]})
                            if 'Managed Securities' in row[ix.index('Description')]:
                                extracto.update({'devengo': row[ix.index('Amount')]})

                        if ('Open Positions' in row) and ('Total' in row) and ('Stocks' in row) and ('USD' in row):
                            ix = ('Open Positions', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency',
                                  'Symbol', 'Quantity', 'Mult', 'Cost Price', 'Cost Basis',
                                  'Close Price', 'Value', 'Unrealized P/L', 'Code')
                            extracto.update({'costobase': row[ix.index('Cost Basis')]})
                            extracto.update({'value': row[ix.index('Value')]})
                            ilog = True

                        if ('Realized & Unrealized Performance Summary' in row) and ('Data' in row) and ('Total' in row):
                            ix = ('Realized & Unrealized Performance Summary', 'Header', 'Asset Category', 'Symbol',
                                  'Cost Adj.', 'Realized S/T Profit', 'Realized S/T Loss', 'Realized L/T Profit',
                                  'Realized L/T Loss', 'Realized Total', 'Unrealized S/T Profit', 'Unrealized S/T Loss',
                                  'Unrealized L/T Profit', 'Unrealized L/T Loss', 'Unrealized Total', 'Total', 'Code')

                            extracto.update({'crecimiento': float(row[ix.index('Realized S/T Profit')]) +
                                                            float(row[ix.index('Realized L/T Profit')])
                                             })
                            extracto.update({'perdidas': float(row[ix.index('Realized S/T Loss')]) +
                                                         float(row[ix.index('Realized L/T Loss')])
                                             })
        #
        # valida que CSv es 'Activity Statement'
        if not ilog:
            return {}, ilog
        else:
            return extracto, ilog

    except Exception as error:
        print("[Error:: get_stock_info()]: {}".format(error))
        return {}, None

        return extracto, ilog


def extractos():
    extracto = select_extracto(account=apilocal['account'], extract='select*')
    datos, y_datos, f_datos = pd.DataFrame(extracto), pd.DataFrame(), pd.DataFrame()

    datos['extracto'] = pd.to_datetime(datos['extracto'])
    datos.set_index('extracto', inplace=True)

    datos['ingresos'] = datos['crecimiento'] + datos['dividendos'] + datos['idevengo']
    datos['costos'] = datos['perdidas'] + datos['fee'] + datos['comisiones'] + datos['tax'] + datos['imargen']
    datos['beneficios'] = datos['ingresos'] - datos['costos']

    y_datos['depositos'] = datos['depositos'].resample('YE').sum()
    y_datos['crecimiento'] = datos['crecimiento'].resample('YE').sum()
    y_datos['perdidas'] = datos['perdidas'].resample('YE').sum()
    y_datos['ingresos'] = datos['ingresos'].resample('YE').sum()
    y_datos['costos'] = datos['costos'].resample('YE').sum()
    y_datos['beneficios'] = datos['beneficios'].resample('YE').sum()
    y_datos['margen'] = y_datos['beneficios'] / y_datos['ingresos']

    f_datos['depositos'] = datos['depositos'].resample('YE-JUL').sum()
    f_datos['crecimiento'] = datos['crecimiento'].resample('YE-JUL').sum()
    f_datos['perdidas'] = datos['perdidas'].resample('YE-JUL').sum()
    f_datos['ingresos'] = datos['ingresos'].resample('YE-JUL').sum()
    f_datos['costos'] = datos['costos'].resample('YE-JUL').sum()
    f_datos['beneficios'] = datos['beneficios'].resample('YE-JUL').sum()
    f_datos['margen'] = f_datos['beneficios'] / f_datos['ingresos']
    f_index = f_datos.index
    # f_datos = f_datos.drop(index=f_index[0])

    # print(y_datos.index)
    # print(y_datos)

    xlist = list(f_datos.index)
    years = [timestamp.year for timestamp in list(f_datos.index)]
    print(datos.info())
    print(f_datos.info())


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    style = ttk.Style(win)
    style.configure('TFrame',   font=('Courier', 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    # f_extracto, ilog = cagar_csv_extracto()
    # print(f_extracto)

    extractos()
    win.mainloop()

xestrategia = read_estrategia()