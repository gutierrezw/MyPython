import os
from tkinter import Tk

from rutinas import *

itrue = True


def the_gui():
    dversion = os.path.basename(__file__).replace(".py", "")

    def on_closing() -> None:
        """
        @return:
        """
        global itrue
        if tk.messagebox.askokcancel(dversion, "¿Estás seguro de que deseas salir?"):
            itrue = False
            frame_strat.destroy()
            frame_stock.destroy()
            frame_plan.destroy()
            win.destroy()

    win = Tk()
    dw = win.winfo_screenwidth()
    dh = win.winfo_screenheight()
    dw = 1200
    dh = 700
    dimension = "%dx%d+0+0" % (dw, dh)
    win.title(dversion)
    win.config(bg="black")

    # style = style_app(main=win)
    nb = ttk.Notebook(win, style="TNotebook", width=dw, height=dh)
    fwin0 = ttk.Frame(nb, style="TFrame", width=dw, height=dh)
    fwin1 = ttk.Frame(nb, style="TFrame", width=dw, height=dh)
    fwin2 = ttk.Frame(nb, style="TFrame", width=dw, height=dh)
    fwin3 = ttk.Frame(nb, style="TFrame", width=dw, height=dh)

    nb.add(fwin0, text='VisionBoard    ')
    nb.add(fwin1, text='Agenda         ')
    nb.add(fwin2, text='Localidades    ')
    nb.add(fwin3, text='Setup          ')

    nb.pack(anchor='nw', pady=10, expand=True)

    rnb = ttk.Frame(win, style="TFrame")
    rnb.pack()


    win.mainloop()


if __name__ == '__main__':
    the_gui()
