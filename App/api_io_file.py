import csv
from tkinter import filedialog

from globales import *
from rutinas import is_none


def get_imagen(ix=None, ancho=None, largo=None):
    """
    @param ix:
    @param ancho:
    @param largo:
    @return:
    """

    imagen0, xlis = select_objeto(codigo=ix)
    imagen = Image.open(io.BytesIO(imagen0))

    if not is_none(ancho) and not is_none(largo):
        imagen = imagen.resize((ancho, largo), Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)
        return imagen_tk, xlis

    return imagen, xlis


def get_extractos_csv(account=None, ruta=None):
    """
    @param account: id de cuenta de inversión
    @param ruta:  ruta donde se encuentra los archivos
    @return:  retorna dict() con atributos de del extracto
    """
    extracto, ilog = dict(), False
    with (open(ruta, newline='') as csvfile):

        spamreader = csv.reader(csvfile, delimiter=',')

        for row in spamreader:

            if ('Statement' in row) and ('Data' in row):
                if 'Period' in row:
                    f_inicio, f_fin = row[-1].split(' - ')
                    f_fin = f_fin.strip()

                    f_obj = datetime.strptime(f_fin, "%B %d, %Y")
                    fecha = f_obj.strftime("%Y-%m-%d")
                    extracto.update({'extracto': datetime.strptime(fecha, "%Y-%m-%d")})

                if ('Title' in row) and ('Activity Statement' in row):
                    ilog = True

            if ('Cash Report' in row) and ('Data' in row) and ('Commissions' in row):
                ix = ('Cash Report', 'Header', 'Currency Summary', 'Currency', 'Total',
                      'Securities', 'Futures', 'Paxos')
                extracto.update({'comisiones': abs(float(row[ix.index('Securities')]))})

            if ('Dividends' in row) and ('Data' in row) and ('Total' in row):
                ix = ('Dividends', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')
                extracto.update({'dividendos': row[ix.index('Amount')]})

            if ('Withholding Tax' in row) and ('Data' in row) and ('Total' in row):
                ix = (
                    'Withholding Tax', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount', 'Code')
                extracto.update({'tax': abs(float(row[ix.index('Amount')]))})

            if ('Fees' in row) and ('Data' in row) and ('Total' in row):
                ix = ('Fees', 'Header', 'Subtitle', 'Currency', 'Account', 'Date', 'Description', 'Amount')
                extracto.update({'fee': abs(float(row[ix.index('Amount')]))})

            if ('Deposits & Withdrawals' in row) and ('Data' in row) and ('USD' in row):
                ix = (
                    'Deposits & Withdrawals', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')

                extracto.update({'depositos': 0})
                extracto.update({'retiros': 0})


                if 'Electronic Fund Transfer' in row[ix.index('Description')]:
                    extracto.update({'depositos': row[ix.index('Amount')]})
                if 'Disbursement' in row[ix.index('Description')]:
                    extracto.update({'retiros': row[ix.index('Amount')]})

            if ('Interest' in row) and ('Data' in row) and ('USD' in row):
                ix = ('Interest', 'Header', 'Currency', 'Account', 'Date', 'Description', 'Amount')

                if 'Debit' in row[ix.index('Description')]:
                    extracto.update({'imargen': abs(float(row[ix.index('Amount')]))})
                if 'Managed Securities' in row[ix.index('Description')]:
                    extracto.update({'idevengo': row[ix.index('Amount')]})

            if ('Open Positions' in row) and ('Total' in row) and ('Stocks' in row) and ('USD' in row):
                ix = ('Open Positions', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency',
                      'Symbol', 'Quantity', 'Mult', 'Cost Price', 'Cost Basis',
                      'Close Price', 'Value', 'Unrealized P/L', 'Code')
                extracto.update({'costobase': row[ix.index('Cost Basis')]})
                extracto.update({'navcierre': row[ix.index('Value')]})
                ilog = True

            if ('Realized & Unrealized Performance Summary' in row) and ('Data' in row) and (
                    'Total (All Assets)' in row):
                #ix = ('Realized & Unrealized Performance Summary', 'Header', 'Asset Category', 'Symbol',
                #      'Cost Adj.', 'Realized S/T Profit', 'Realized S/T Loss', 'Realized L/T Profit',
                #      'Realized L/T Loss', 'Realized Total', 'Unrealized S/T Profit', 'Unrealized S/T Loss',
                #      'Unrealized L/T Profit', 'Unrealized L/T Loss', 'Unrealized Total', 'Total', 'Code')

                ix = ('Realized & Unrealized Performance Summary', 'Data', 'Total', '',
                      'Cost Adj.', 'Realized S/T Profit', 'Realized S/T Loss', 'Realized L/T Profit',
                      'Realized L/T Loss', 'Realized Total', 'Unrealized S/T Profit', 'Unrealized S/T Loss',
                      'Unrealized L/T Profit', 'Unrealized L/T Loss', 'Unrealized Total', 'Total', 'Code')

                extracto.update({'crecimiento': float(row[ix.index('Realized S/T Profit')]) +
                                                float(row[ix.index('Realized L/T Profit')])
                                 })
                extracto.update({'perdidas': abs(float(row[ix.index('Realized S/T Loss')])) +
                                             abs(float(row[ix.index('Realized L/T Loss')]))
                                 })

    return extracto, ilog


def cagar_archivo(account=None, titulo=None, tipo='csv'):
    """
    @param account: id de cuenta de inversión
    @param titulo:  titulo de ventada para selección de archivo
    @param tipo: tipo de archivo CSV, TXT, XLS
    @return: interfaz  para seleccionar tipo de archivo
    """
    try:
        ruta = filedialog.askopenfilename(title=titulo, filetypes=(("Archivos " + tipo.upper(), "*." + tipo),))
        ilog = False
        if ruta:
            if ruta.endswith('.' + tipo):
                extracto, ilog = get_extractos_csv(account, ruta)
        #
        # valida que CSv es 'Activity Statement'
        if not ilog:
            return {}, ilog
        else:
            return extracto, ilog

    except Exception as error:
        print("[Error::  cagar_archivo()]: {}".format(error))
        return {}, None


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    style = ttk.Style(win)
    style.configure('TFrame',   font=('Courier', 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    boton_cargar = tk.Button(dpn, text="Cargar Archivo", command=cargar_archivo)
    boton_cargar.pack(pady=20)

    win.mainloop()
