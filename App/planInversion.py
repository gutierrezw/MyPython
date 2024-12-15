from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from api_chart import chart_trazaplan
from bd_conect import *
from rutinas import *

global mpl


class plan_inversion(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_plan()
        self.update_plan()
        self.config(bg="black")

    def widgets_plan(self):
        global mpl, fg, cv, ax, gcolor
        mpl = [[None] * 10 for _ in range(35)]

        win1 = tk.Frame(self, bg='black')
        win2 = tk.Frame(self, bg='black')
        win3 = tk.Frame(self, bg='black')
        win10 = tk.Frame(win1, bg='black')
        win11 = tk.Frame(win1, bg='black')
        win20 = tk.Frame(win2, bg='black', relief='groove', bd=2)
        win21 = tk.Frame(win2, bg='black')
        win30 = tk.Frame(win3, bg='black')
        win31 = tk.Frame(win3, bg='black')

        win1.grid(row=0, column=0, padx=5, pady=10)
        win2.grid(row=0, column=2, padx=2, pady=10)
        win3.grid(row=1, column=0, padx=5, pady=10, columnspan=3)

        win10.grid(row=0, column=0, pady=10)
        win11.grid(row=1, column=0, pady=10)
        win20.grid(row=0, column=0, pady=10)
        win21.grid(row=1, column=0, pady=10)
        win30.grid(row=0, column=0)
        win31.grid(row=0, column=1)

        tit = ['Visión', 'Deseada', 'Actual', 'Indicador', 'Objetivo']
        mpl[0][0] = ttk.Button(win10, text=tit[0], width=17, style='TButton', state='disabled')
        mpl[0][1] = ttk.Button(win10, text=tit[1], width=15, style='TButton', state='disabled')
        mpl[0][2] = ttk.Button(win10, text=tit[2], width=15, style='TButton', state='disabled')
        mpl[0][3] = ttk.Button(win10, text=tit[3], width=15, style='TButton', state='disabled')
        mpl[0][4] = ttk.Button(win10, text=tit[4], width=50, style='TButton', state='disabled')
        mpl[0][5] = tk.Text(win10, height=5, width=42, font=('Courier', 8))

        mpl[0][0].grid(row=0, column=0, pady=10)
        mpl[0][1].grid(row=0, column=1, pady=10)
        mpl[0][2].grid(row=0, column=2, pady=10)
        mpl[0][3].grid(row=0, column=3, pady=10)
        mpl[0][4].grid(row=0, column=4, columnspan=4)
        mpl[0][5].grid(row=1, column=4, rowspan=4, columnspan=4)

        for i in range(1, 7):
            for j in range(0, 4):
                mpl[i][j] = ttk.Button(win10, text=" ", width=14, style='TLabel')
                mpl[i][j].grid(row=i, column=j)

        mpl[4][0] = ttk.Separator(win10, orient="horizontal", style='G.TSeparator')
        mpl[5][5] = ttk.Button(win10, text=" divisa USD", style='Cb.TLabel')
        mpl[5][6] = ttk.Button(win10, text=" Ingresos pasivos", style='Cb.TLabel')

        mpl[4][0].grid(row=4, column=1, ipadx=140, columnspa=3)
        mpl[5][5].grid(row=5, column=3)
        mpl[5][6].grid(row=5, column=4, pady=5)

        trz = ['Meta', 'Extracto', 'Visión', 'Inversiones', 'Div/año', 'Efectividad', 'Estatus', 'Recompensa']
        mpl[6][0] = ttk.Button(win11, text=trz[0], width=11, state='disabled')
        mpl[6][1] = ttk.Button(win11, text=trz[1], width=11, state='disabled')
        mpl[6][2] = ttk.Button(win11, text=trz[2], width=12, state='disabled')
        mpl[6][3] = ttk.Button(win11, text=trz[3], width=12, state='disabled')
        mpl[6][4] = ttk.Button(win11, text=trz[4], width=12, state='disabled')
        mpl[6][5] = ttk.Button(win11, text=trz[5], width=12, state='disabled')
        mpl[6][6] = ttk.Button(win11, text=trz[6], width=12, state='disabled')
        mpl[6][7] = ttk.Button(win11, text=trz[7], width=20, state='disabled')

        mpl[6][0].grid(row=6, column=0, padx=2, pady=10)
        mpl[6][1].grid(row=6, column=1, padx=2, pady=10)
        mpl[6][2].grid(row=6, column=2, padx=2, pady=10)
        mpl[6][3].grid(row=6, column=3, padx=2, pady=10)
        mpl[6][4].grid(row=6, column=4, padx=2, pady=10)
        mpl[6][5].grid(row=6, column=5, padx=2, pady=10)
        mpl[6][6].grid(row=6, column=6, padx=2, pady=10)
        mpl[6][7].grid(row=6, column=7, padx=2, pady=10)
        for i in range(7, 18):
            for j in range(8):
                if j in (0, 1, 2, 7):
                    mpl[i][j] = ttk.Button(win11, text=" ", style='TLabel')
                else:
                    mpl[i][j] = ttk.Button(win11, text=" ", style='Cb.TLabel')

                mpl[i][j].grid(row=i, column=j)

        gcolor = 'black'
        fg = Figure(figsize=(4.9, 2.2), dpi=110, layout="tight")
        ax = fg.add_subplot()
        fg.set_facecolor(gcolor)
        cv = FigureCanvasTkAgg(fg, master=win20)
        cv.draw()
        cv.get_tk_widget().pack()

        rsg = ['Riesgos', 'Solución Potencial']
        mpl[14][8] = ttk.Button(win21, text=rsg[0], width=29, style='TButton', state='disabled')
        mpl[14][9] = ttk.Button(win21, text=rsg[1], width=59, style='TButton', state='disabled')

        mpl[14][8].grid(row=0, column=0)
        mpl[14][9].grid(row=0, column=1)

        for i in range(15, 22):
            mpl[i][8] = ttk.Button(win21, text=' ', width=25, style='TLabel')
            mpl[i][9] = ttk.Button(win21, text=' ', width=52, style='Cb.TLabel')

            mpl[i][8].grid(row=i + 1, column=0)
            mpl[i][9].grid(row=i + 1, column=1)

        prc = ['Precio a pagar', 'Tiempo/Energia', 'Económicos', 'Personales']
        mpl[23][0] = tk.Button(win30, text=prc[0],  width=20, height=4, state='disabled', font=9)
        mpl[23][1] = ttk.Button(win31, text=prc[1], width=59, style='TButton', state='disabled')
        mpl[23][2] = ttk.Button(win31, text=prc[2], width=59, style='TButton', state='disabled')
        mpl[23][3] = ttk.Button(win31, text=prc[3], width=59, style='TButton', state='disabled')

        mpl[23][0].grid(row=1, column=0, pady=10)
        mpl[23][1].grid(row=0, column=1, padx=1)
        mpl[23][2].grid(row=0, column=2, padx=1)
        mpl[23][3].grid(row=0, column=3, padx=1)

        k = 1
        for i in range(24, 30):
            mpl[i][1] = ttk.Button(win31, text=' ', width=50, style='Cb.TLabel')
            mpl[i][2] = ttk.Button(win31, text=' ', width=50, style='Cb.TLabel')
            mpl[i][3] = ttk.Button(win31, text=' ', width=50, style='Cb.TLabel')

            mpl[i][1].grid(row=i + 1, column=1)
            mpl[i][2].grid(row=i + 1, column=2)
            mpl[i][3].grid(row=i + 1, column=3)
            k += 1

        self.after(apilocal['elapse plan'], self.update_plan)
        return self.widgets_plan

    def update_plan(self):
        global mpl, traz
        datsess = select_sesion("select")
        plan = select_plan(datsess['idcuenta'])
        traz = select_trazaplan(datsess['idcuenta'])
        vari = select_variablesplan(datsess['idcuenta'])

        if plan:
            i = 1
            deseada, actual = 0, 0
            for key in plan:
                mpl[i][0].config(text='{:>10}'.format(key['vision']))
                mpl[i][1].config(text='{:>12.0f}'.format(key['deseada']))
                mpl[i][2].config(text='{:>12.0f}'.format(key['actual']))
                deseada += key['deseada']
                actual += key['actual']
                if i == 1:
                    mpl[i][3].config(text='{:>12.1%}'.format(key['objetivo']))
                    mpl[5][6].config(text='{:>8.0f} de Ingresos ({:>5.2%} visión actual)'.format(
                        key['indicador'], key['objetivo']))
                else:
                    mpl[i][3].config(text='{:>12.1%}'.format(key['indicador']))

                if key['proyecto'] != ' ':
                    mpl[0][5].insert(tk.END, str(i) + ") " + key['proyecto'] + "\n")
                i += 1
            mpl[5][1].config(text='{:>12n}'.format(deseada))
            mpl[5][2].config(text='{:>12n}'.format(actual))

            if traz:
                i = 7
                for tkey in traz:
                    mpl[i][0].config(text='{:>7n} Año'.format(tkey['meta']))
                    mpl[i][1].config(text='{:%Y-%B}'.format(tkey['extracto']))
                    mpl[i][2].config(text='{:>12n}'.format(tkey['vision']))
                    if tkey['costobase'] > 0:
                        mpl[i][3].config(text='{:>11.0f}'.format(tkey['tinversion']))
                        mpl[i][4].config(text='{:>10.0f}'.format(tkey['dividendo']))
                        mpl[i][5].config(text='{:>+11.1%}'.format(tkey['efectividad']))
                        mpl[i][6].config(text='{:<11}'.format(tkey['status']))
                        mpl[i][7].config(text='{:<17}'.format(tkey['recompensa']))
                    i += 1

            if vari:
                i = 15
                for tkey in vari:
                    if tkey['tipo'] == 'riesgos':
                        if not is_none(mpl[i][8]) and i < 19:
                            mpl[i][8].config(text='{:<25}'.format(tkey['ditem']))
                            mpl[i][9].config(text='{:<50}'.format(tkey['observaciones']))
                            i += 1

                i, j, k = 24, 24, 24
                for tkey in vari:
                    if tkey['tipo'] == 'esfuerzo':
                        if not is_none(mpl[i][1]) and i < 30:
                            mpl[i][1].config(text='{:<50}'.format(tkey['ditem']))
                            i += 1
                    if tkey['tipo'] == 'economico':
                        if not is_none(mpl[j][2]) and j < 30:
                            mpl[j][2].config(text='{:<50}'.format(tkey['ditem']))
                            j += 1
                    if tkey['tipo'] == 'personal':
                        if not is_none(mpl[k][3]) and k < 30:
                            mpl[k][3].config(text='{:<50}'.format(tkey['ditem']))
                            k += 1

        self.after(apilocal['elapse plan'], self.update_plan)
        chart_trazaplan(fg, cv, traz, gcolor)
        return self.update_plan


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    style = ttk.Style(win)
    style.configure('TFrame',   font=('Courier', 8), foreground="white", background="black")
    style.configure('TLabel',   font=('Courier', 8), foreground="white", background="black")
    style.configure('T.TButton', foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    frame_plan = plan_inversion(master=dpn)
    frame_plan.pack()
    frame_plan.mainloop()
