from Modulos_Utilitarios import *
from Modulos_python import *

from pprint import pprint
from Class_Ibrks import IBClient

# Create a new session of the IB Web API.
ib_client = IBClient(
    username="guti2004",
    account="4214563",
    is_server_running=True
)


#pprint('portfolio_account_ledger()')
#ledger = ib_client.portfolio_account_ledger(account_id='U4214563')
#pprint(ledger)
# pprint('--------------------------------------')

if __name__ == "__main__":
    root = tk.Tk()
    dw = 1290
    dh = 700
    df = 1297
    bgcolor = 'DarkCyan'
    fgcolor = 'white'
    cgcolor = 'black'
    max_dw = root.winfo_screenwidth()
    max_dh = root.winfo_screenheight()
    dimension = "%dx%d+0+0" % (max_dw, max_dh)

    rns = tk.Toplevel()
    title = "Grain Capital"
    dimension = "%dx%d+%d+%d" % (max_dw - 10, 220, 0, 775)
    rns.geometry(dimension)
    rns.resizable(False, False)
    rns.attributes('-toolwindow', 1)
    rns.focus()
    rns.title(title)
    rns.config(bg=cgcolor)

    style = ttk.Style()
    style.configure("R.TFrame", background="red", foreground="red")
    style.configure("R.TLabel", background="grey", foreground="white")

    win1 = ttk.Frame(rns, padding=(1, 1, 1, 1), style='B.TFrame')
    win2 = ttk.Frame(rns, padding=(1, 1, 1, 1), style='B.TFrame')
    win3 = ttk.Frame(rns, padding=(1, 1, 1, 1), style='R.TFrame', width=500, height=300)
    win1.grid(column=0, row=0)
    win2.grid(column=1, row=0)
    win3.grid(column=3, row=0)

    fg = Figure(figsize=(3.00, 2.4), dpi=110, layout="tight")
    fg.set_facecolor(fgcolor)
    cv = FigureCanvasTkAgg(fg, master=win2)
    cv.draw()
    cv.get_tk_widget().pack()


    lb0 = tk.Label(win3, text='Opciones de venta', font=('Arial', 13), bg=cgcolor, fg='cyan')
    lb1 = ttk.Label(win3, text='cantidad', style='B.TLabel')
    lb2 = ttk.Label(win3, text='LMT', style='B.TLabel')
    lb3 = ttk.Label(win3, text='Precio', style='B.TLabel')
    lb4 = ttk.Label(win3, text='DAY', style='B.TLabel')
    lb6 = ttk.Button(win3, text='SELL',  style='TButton')
    lb6.grid(column=0, row=5)
    lb0.grid(column=0, row=0, columnspan=4)
    lb2.grid(column=0, row=3)
    lb3.grid(column=2, row=3)
    lb4.grid(column=4, row=3)
    # ib_client.create_session()
    root.mainloop()