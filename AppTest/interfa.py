from estrategia import *
from bd_conect import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import yfinance as yf
import mplfinance as mpf


def order(colm):
    print('titulo=', colm)

def fila(colm):
    print('ticket=', colm)

def filtro():
    print('filtro  x')

def pagina(accion):
    if accion == '--':
        print('pagina atras')
    if accion == '++':
        print('avanza pagina')

def titulos(i=4):
    mxp[i][0] = ttk.Button(fwin0, text='titulo ' + str(0), width=11, command=lambda: order(0)).grid(row=i,  column=0)
    mxp[i][1] = ttk.Button(fwin0, text='titulo ' + str(1), width=11, command=lambda: order(1)).grid(row=i,  column=1)
    mxp[i][2] = ttk.Button(fwin0, text='titulo ' + str(2), width=11, command=lambda: order(2)).grid(row=i,  column=2)
    mxp[i][3] = ttk.Button(fwin0, text='titulo ' + str(3), width=11, command=lambda: order(3)).grid(row=i,  column=3)
    mxp[i][4] = ttk.Button(fwin0, text='titulo ' + str(4), width=11, command=lambda: order(4)).grid(row=i,  column=4)
    mxp[i][5] = ttk.Button(fwin0, text='titulo ' + str(5), width=11, command=lambda: order(5)).grid(row=i,  column=5)
    mxp[i][6] = ttk.Button(fwin0, text='titulo ' + str(6), width=11, command=lambda: order(6)).grid(row=i,  column=6)
    mxp[i][7] = ttk.Button(fwin0, text='titulo ' + str(7), width=11, command=lambda: order(7)).grid(row=i,  column=7)
    mxp[i][8] = ttk.Button(fwin0, text='titulo ' + str(8), width=11, command=lambda: order(8)).grid(row=i,  column=8)
    mxp[i][9] = ttk.Button(fwin0, text='titulo ' + str(9), width=11, command=lambda: order(9)).grid(row=i,  column=9)
    mxp[i][10] =ttk.Button(fwin0, text='titulo ' + str(10),width=11, command=lambda: order(10)).grid(row=i, column=10)
    mxp[i][11] =ttk.Button(fwin0, text='titulo ' + str(11),width=11, command=lambda: order(11)).grid(row=i, column=11)
    mxp[i][12] =ttk.Button(fwin0, text='titulo ' + str(12),width=11, command=lambda: order(12)).grid(row=i, column=12)
    mxp[i][13] =ttk.Button(fwin0, text='titulo ' + str(13),width=11, command=lambda: order(13)).grid(row=i, column=13)
    mxp[i][14] =ttk.Button(fwin0, text='titulo ' + str(14),width=11, command=lambda: order(14)).grid(row=i, column=14)
    mxp[i][15] =ttk.Button(fwin0, text='titulo ' + str(15),width=11, command=lambda: order(15)).grid(row=i, column=15)
    mxp[i][16] =ttk.Button(fwin0, text='titulo ' + str(16),width=11, command=lambda: order(16)).grid(row=i, column=16)

    mxp[37][13] = ttk.Button(fwin0, text='-- Pag', width=11, command=lambda: pagina('--')).place(y=670, x=990)
    mxp[37][14] = ttk.Button(fwin0, text='++ Pag', width=11, command=lambda: pagina('++')).place(y=670, x=1070)
    mxp[37][15] = ttk.Button(fwin0, text='Filtro',width=11, command=filtro).place(y=670, x=1150)

    return mxp

def lineas(i,j=0):
    lfg = "TLabel" if i%2 == 0 else "I.TLabel"
    if i == 6:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 7:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 8:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 9:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 10:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 11:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 12:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 13:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 14:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 15:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 16:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 17:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 18:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 19:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 20:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 21:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 22:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 23:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 24:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 25:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 26:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 27:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 28:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 29:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 30:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 31:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 32:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 33:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 34:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 35:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 36:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)
    if i == 37:
        mxp[i][j] = ttk.Button(fwin0, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        mxp[i][j].grid(row=i, column=j)



    return mxp


def stock(fwin0):
    global mxp
    mxp = [[None] * 17 for _ in range(38)]
    for i in range(0, 37):
        for j in range(17):
            if i in (0, 1, 2):
                if i == 2:
                    if j == 13:
                        Sinvertir = StringVar(fwin0, '0')
                        mxp[i][j] = ttk.Entry(fwin0, width=7, font=10, justify="right", textvariable=Sinvertir)
                        mxp[i][j].grid(row=i, column=j)
                    if j == 14:
                        mxp[i][j] = ttk.Button(fwin0, text="Inversión", style='TLabel', width=10)
                        mxp[i][j].grid(row=i, column=j)
                else:
                    mxp[i][j] = ttk.Button(fwin0, text=str(j), width=10, style='TLabel')
                    mxp[i][j].grid(row=i, column=j)
            else:
                if i == 4:
                    titulos(i)
                else:
                    if i > 4:
                        if j == 0:
                            lineas(i, j=0)
                        else:
                            lfg = "TLabel" if i == 5 else ("TLabel" if i % 2 == 0 else "I.TLabel")
                            mxp[i][j] = ttk.Button(fwin0, text=str(j), width=10, style=lfg)
                            mxp[i][j].grid(row=i, column=j)

def ctitulos(i=4):
    cxp[i][0] = ttk.Button(fwin0, text='titulo ' + str(0), width=11).grid(row=i,  column=0)
    cxp[i][1] = ttk.Button(fwin0, text='titulo ' + str(1), width=11).grid(row=i,  column=1)
    cxp[i][2] = ttk.Button(fwin0, text='titulo ' + str(2), width=11).grid(row=i,  column=2)
    cxp[i][3] = ttk.Button(fwin0, text='titulo ' + str(3), width=11).grid(row=i,  column=3)
    cxp[i][4] = ttk.Button(fwin0, text='titulo ' + str(4), width=11).grid(row=i,  column=4)
    cxp[i][5] = ttk.Button(fwin0, text='titulo ' + str(5), width=11).grid(row=i,  column=5)
    cxp[i][6] = ttk.Button(fwin0, text='titulo ' + str(6), width=11).grid(row=i,  column=6)
    cxp[i][7] = ttk.Button(fwin0, text='titulo ' + str(7), width=11).grid(row=i,  column=7)
    cxp[i][8] = ttk.Button(fwin0, text='titulo ' + str(8), width=11).grid(row=i,  column=8)
    cxp[i][9] = ttk.Button(fwin0, text='titulo ' + str(9), width=11).grid(row=i,  column=9)
    cxp[i][10] =ttk.Button(fwin0, text='titulo ' + str(10),width=11).grid(row=i, column=10)
    cxp[i][11] =ttk.Button(fwin0, text='titulo ' + str(11),width=11).grid(row=i, column=11)
    cxp[i][12] =ttk.Button(fwin0, text='titulo ' + str(12),width=11).grid(row=i, column=12)
    cxp[i][13] =ttk.Button(fwin0, text='titulo ' + str(13),width=11).grid(row=i, column=13)
    cxp[i][14] =ttk.Button(fwin0, text='titulo ' + str(14),width=11).grid(row=i, column=14)
    cxp[i][15] =ttk.Button(fwin0, text='titulo ' + str(15),width=11).grid(row=i, column=15)
    cxp[i][16] =ttk.Button(fwin0, text='titulo ' + str(16),width=11).grid(row=i, column=16)

    mxp[37][13] = ttk.Button(fwin0, text='-- Pag', width=11, command=lambda: pagina('--')).place(y=670, x=990)
    mxp[37][14] = ttk.Button(fwin0, text='++ Pag', width=11, command=lambda: pagina('++')).place(y=670, x=1070)
    mxp[37][15] = ttk.Button(fwin0, text='Filtro',width=11, command=filtro).place(y=670, x=1150)

    return cxp

def clineas(i,j=0):
    lfg = "TLabel" if i%2 == 0 else "I.TLabel"
    if i == 6:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 7:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 8:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 9:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 10:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 11:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 12:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 13:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 14:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 15:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 16:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 17:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 18:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 19:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 20:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 21:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 22:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 23:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 24:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 25:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 26:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 27:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 28:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 29:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 30:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 31:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 32:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 33:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 34:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 35:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 36:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    if i == 37:
        cxp[i][j] = ttk.Button(fwin1, text=str(i),
                               width=10, style=lfg, command=lambda: fila(i))
        cxp[i][j].grid(row=i, column=j)
    return cxp


def crypto(fwin1):
    global cxp
    cxp = [[None] * 17 for _ in range(38)]
    for i in range(0, 37):
        for j in range(17):
            if i in (0, 1, 2):
                if i == 2:
                    if j == 13:
                        Sinvertir = StringVar(fwin1, '0')
                        cxp[i][j] = ttk.Entry(fwin1, width=7, font=10, justify="right", textvariable=Sinvertir)
                        cxp[i][j].grid(row=i, column=j)
                    if j == 14:
                        cxp[i][j] = ttk.Button(fwin1, text="Inversión", style='TLabel', width=10)
                        cxp[i][j].grid(row=i, column=j)
                else:
                    cxp[i][j] = ttk.Button(fwin1, text=str(j), width=10, style='TLabel')
                    cxp[i][j].grid(row=i, column=j)
            else:
                if i == 4:
                    ctitulos(i)
                else:
                    if i > 4:
                        if j == 0:
                            clineas(i, j=0)
                        else:
                            lfg = "TLabel" if i == 5 else ("TLabel" if i % 2 == 0 else "I.TLabel")
                            cxp[i][j] = ttk.Button(fwin1, text=str(j), width=10, style=lfg)
                            cxp[i][j].grid(row=i, column=j)


def  trader(Rnb):
    trader = tk.Listbox(Rnb, bg="gray", fg="white", width=91, height=45, background='blue')
    trader.insert(tk.END, "Python.. trader", "C.. trader", "C++.. trader", "Java.. trader")
    trader.pack()


def plan(win):
    win1 = tk.Frame(win, bg="green")
    win1.grid(row=0, column=0, padx=5, pady=10)
    win2 = tk.Frame(fwin0, bg="white")
    win2.grid(row=0, column=2, padx=5, pady=10)
    win3 = tk.Frame(win, bg="red")
    win3.grid(row=1, column=0,columnspan=2, padx=5, pady=10)

    mpl = [[None] * 15 for _ in range(20)]
    styl = ttk.Style()
    styl.configure('TSeparator', background='green')
    tit = ['Visión', 'Deseada', 'Actual', 'Indicador', 'OBjetivo']
    mpl[0][0] = ttk.Button(win1, text=tit[0], width=17).grid(row=0, column=0, pady=10)
    mpl[0][1] = ttk.Button(win1, text=tit[1], width=12).grid(row=0, column=1, pady=10)
    mpl[0][2] = ttk.Button(win1, text=tit[2], width=12).grid(row=0, column=2, pady=10)
    mpl[0][3] = ttk.Button(win1, text=tit[3], width=12).grid(row=0, column=3, pady=10)
    mpl[0][4] = ttk.Button(win1, text=tit[4], width=50).grid(row=0, column=4, columnspan=3)
    mpl[0][5] = tk.Text(win1, height=5, width=42, font=('Courier', 8))
    mpl[0][5].grid(row=1, column=4, rowspan=4, columnspan=3)

    for i in range(1, 6):
        for j in range(4):
            mpl[i][j] = ttk.Button(win1, text=j, style='TLabel')
            mpl[i][j].grid(row=i, column=j)
    mpl[4][0] = ttk.Separator(win1, orient="horizontal", style='TSeparator')
    mpl[4][0].grid(row=4, column=1, ipadx=140, columnspa=3)
    mpl[5][5] = ttk.Button(fwin1, text=" divisa USD", style='TLabel').grid(row=5, column=3)

    trz = ['Meta', 'Extracto', 'Visión', 'Costobase', 'Efectividad', 'Estatus', 'Recompensa']
    mpl[6][0] = ttk.Button(win1, text=trz[0], width=17).grid(row=6, column=0, padx=4, pady=10)
    mpl[6][1] = ttk.Button(win1, text=trz[1], width=12).grid(row=6, column=1, padx=4, pady=10)
    mpl[6][2] = ttk.Button(win1, text=trz[2], width=12).grid(row=6, column=2, padx=4, pady=10)
    mpl[6][3] = ttk.Button(win1, text=trz[3], width=12).grid(row=6, column=3, padx=4, pady=10)
    mpl[6][4] = ttk.Button(win1, text=trz[4], width=12).grid(row=6, column=4, padx=4, pady=10)
    mpl[6][5] = ttk.Button(win1, text=trz[5], width=12).grid(row=6, column=5, padx=4, pady=10)
    mpl[6][6] = ttk.Button(win1, text=trz[6], width=20).grid(row=6, column=6, padx=4, pady=10)
    for i in range(7, 19):
        for j in range(7):
            mpl[i][j] = ttk.Button(win1, text=j, style='TLabel')
            mpl[i][j].grid(row=i, column=j)

    #ttk.Separator(fwin4, orient="vertical",
    #              style="red.TSeparator").grid(row=0, column=7, ipady=180, padx=10, pady=10, rowspan=19)
    #ttk.Separator(fwin4, orient="horizontal",
    #              style='TSeparator').grid(row=21, column=0, ipadx=350, columnspan=8)

    rsg = ['Riesgos', 'Solución Potencial']
    mpl[7][0] = ttk.Button(win3, text=rsg[0], width=25)
    mpl[7][0].grid(row=0, column=0)
    mpl[7][1] = ttk.Button(win3, text=rsg[1], width=100)
    mpl[7][1].grid(row=0, column=1)
    for i in range(8,14):
        mpl[i][0] = ttk.Button(win3, text='xxxxx', width=25)
        mpl[i][0].grid(row=i+1, column=0)
        mpl[i][1] = ttk.Button(win3, text='yyyyyyy', width=100)
        mpl[i][1].grid(row=i+1, column=1)


def winchar(win):
    datos = yf.download("HASI", progress=False, interval="1wk", period='1y')

    fg0 = Figure(figsize=(5.0, 2.5), dpi=110)
    fg1 = Figure(figsize=(5.0, 2.5), dpi=110)
    fg2 = Figure(figsize=(5.6, 3.5), dpi=110)
    fg3 = Figure(figsize=(5.6, 3.5), dpi=110)
    fg4 = Figure(figsize=(5.6, 3.5), dpi=110)

    pn0 = ttk.Frame(win, style="I.TFrame")
    pn1 = ttk.Frame(win, style="I.TFrame")
    pn2 = ttk.Frame(win, style="I.TFrame")
    pn3 = ttk.Frame(win, style="I.TFrame")
    pn4 = ttk.Frame(win, style="I.TFrame")

    pn0.place(x=df + 15, y=190)
    pn1.place(x=df + 15, y=470)
    pn2.pack(pady=2, padx=2, side="left")
    pn3.pack(pady=2, padx=2, side="left")
    pn4.pack(pady=2, padx=2, side="left")

    # Crear el lienzo de la figura de matplotlib
    # cv0 = FigureCanvasTkAgg(fg0, master=pn0)
    # cv0.draw()
    # cv0.get_tk_widget().pack()
    # Crear el lienzo de la figura de matplotlib
    cv1 = FigureCanvasTkAgg(fg1, master=pn1)
    cv1.draw()
    cv1.get_tk_widget().pack()
    # Crear el lienzo de la figura de matplotlib
    cv2 = FigureCanvasTkAgg(fg2, master=pn2)
    cv2.draw()
    cv2.get_tk_widget().pack()
    # Crear el lienzo de la figura de matplotlib
    cv3 = FigureCanvasTkAgg(fg3, master=pn3)
    cv3.draw()
    cv3.get_tk_widget().pack()
    # Crear el lienzo de la figura de matplotlib
    cv4 = FigureCanvasTkAgg(fg4, master=pn4)
    cv4.draw()
    cv4.get_tk_widget().pack()


def chartborde(master=None, canvas=None, fre=0, panel=None, scala=None):
    #
    # carga widgets de graficos
    #
    mc = mpf.make_marketcolors(base_mpf_style='charles', up='green', down='red', volume={'up':'blue','down':'orange'})
    st = mpf.make_mpf_style(base_mpl_style='dark_background', marketcolors=mc, y_on_right=False,
                            edgecolor='grey')

    #fg0, ax0 = mpf.plot(datos, type='candle', style=st, figsize=(5.5, 2.7), volume=True, axisoff=False,
    #                    tight_layout=False, panel_ratios=(1, .3), returnfig=True, datetime_format=' %m-%y',xrotation=60,
    #                    scale_width_adjustment=dict(ohlc=.5, lines=0.45, candle=.5), ylabel_lower='RSI')

    #cv0 = FigureCanvasTkAgg(fg0, master=pn0)
    #cv0.draw()
    #cv0.get_tk_widget().pack()
    win.update()

    #print('pase por chartborde')
    master.after(fre, lambda: chartborde(master, canvas, fre, panel, scala))



win = tk.Tk()
dw=1290
dh=750
df=1290
dimension = "%dx%d+0+0" % (dw,dh)
win.geometry(dimension)
win.title("Prueba v4.0")
win.config(bg="black")


style = ttk.Style(win)
style.configure('TFrame',    font=('Courier', 8), foreground="white", background="black")
style.configure('I.TFrame',  font=('Courier', 8), foreground="black", background="while")
style.configure('TLabel',    font=('Courier', 8), foreground="white", background="black")
style.configure('I.TLabel',  font=('Courier', 8), foreground="black", background="white")
style.configure('TEntry',    font=('Courier', 8), foreground="white", background="black")
style.configure('TNotebook', font=('Courier', 8), foreground="white", background="gray")

nb = ttk.Notebook(win, style="TNotebook", width=df,  height=700)
fwin0 = ttk.Frame(nb, style="TFrame", width=df,  height=700)
fwin1 = ttk.Frame(nb, style="TFrame", width=df,  height=700)
fwin2 = ttk.Frame(nb, style="TFrame", width=df,  height=700)
fwin3 = ttk.Frame(nb, style="TFrame", width=df,  height=700)
fwin4 = ttk.Frame(nb, style="TFrame", width=df,  height=700)

nb.add(fwin0, text='stock')
nb.add(fwin1, text='Crypto')
nb.add(fwin2, text='Estrategia')
nb.add(fwin3, text='Analisis')
nb.add(fwin4, text='Plan')
nb.pack(anchor='nw', pady=10, expand=True)
## plot
##
# Crear la figura de matplotlib
winchar(win)
#
#
global mxp
Rnb = ttk.Frame(win, style="TFrame")
#Rnb.place(x=df+10, y=10)
##
## hojas de Notebook
##
stock(fwin0)
crypto(fwin1)
trader(Rnb)
plan(fwin4)
#after(2000, lambda: chartborde(master=win, canvas=cv1, fre=2000, panel=pn0, scala='1wk'))
#chartborde(master=win, canvas=cv1, fre=2000, panel=pn1, scala='1wk')
#win.after(9000, lambda: chartborde(master=win, canvas=cv2, fre=9000, panel=pn2, scala='1wk'))
#win.after(9000, lambda: chartborde(master=win, canvas=cv3, fre=9000, panel=pn3, scala='1wk'))
#win.after(9000, lambda: chartborde(master=win, canvas=cv4, fre=9000, panel=pn4, scala='1wk'))


win.mainloop()