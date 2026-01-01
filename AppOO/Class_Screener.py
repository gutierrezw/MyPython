from Modulos_Mysql import MarketScreen, BDsystem
from Modulos_Utilitarios import style_app, is_null, is_none, mask_numero
from Modulos_python import tk, ttk, W, S, N, E, VERTICAL, HORIZONTAL, io, ImageTk, Image, messagebox, datetime


class Screener(tk.Frame):
    def __init__(self, master=None, account=None, colors=None):
        super().__init__(master)
        self.root = ttk.Frame(master, padding=(1, 1, 1, 1), style='B.TFrame')
        self.account = account
        self.colors = colors
        self.config(bg="black")
        self.s_country = None
        self.s_sector = None
        self.s_tipo = 'Dividends'
        self.s_beta = None
        self.s_market = None
        self.s_entry = None
        self.tree = None
        self.panel = None
        self.options = None
        self.wi20 = None
        self.root.pack(side=tk.LEFT)
        self.market = None
        self.counter = 0
        self.ix = []
        self.ctree = ['Symbol', 'Name', 'Status', 'Country', 'Dividends', 'Dividends_Yield',
                      'Market_Cap', 'Sector', 'Beta', 'Volume', 'Last_Sale', 'ExDividend'
        ]


        # Accesos MySql ----------------------------------------------------------------------------------------------
        self.ScMarket = MarketScreen()
        
        self.start()    
    
    
    # Start Screener 
    def start(self):
        # carga de datos e insert treeview
        self.market, self.ix = self.ScMarket.select(account=self.account, tipo=self.s_tipo,
                                                    country=self.s_country, sector=self.s_sector,
                                                    name=self.s_entry, symbol=self.s_entry)

        self.widgets_screener()
        self.update_screener()


    def widgets_screener(self):

        def item_selected(event):
            for selected_item in self.tree.selection():
                item = self.tree.item(selected_item)
                record = item['values']
                if not is_none(record[0]):
                    ticket = record[0].strip()
                    name = record[1]
                    # evaluar_fila(vehiculo='Stock', empresa=name, ticket=ticket)

        def sort_treeview(tree, col, reverse):
            xlis = [(tree.set(k, col), k) for k in tree.get_children('')]
            xlis.sort(reverse=reverse)

            # Reordenar los elementos en el treeview
            for index, (val, k) in enumerate(xlis):
                tree.move(k, '', index)

            tree.heading(col, text=col, command=lambda: sort_treeview(tree, col, not reverse))
            i = 0
            for item in tree.get_children():
                xtag = "even" if i % 2 == 0 else "odd"
                tree.item(item, tags=(xtag,))
                i += 1

        def get_select(*args):
            self.s_tipo = tipo.get()
            self.s_beta = beta.get()
            self.s_entry = entry.get()
            self.s_market = mkt_c.get()

            self.s_beta = self.s_beta if not is_null(self.s_beta) else None
            self.s_entry = self.s_entry if not is_null(self.s_entry) else None
            self.s_market = self.s_market if not is_null(self.s_market) else None

        def update_window(tipo):

            if tipo == 'reset':
                self.s_country = None
                self.s_sector = None
                self.s_tipo = 'Dividends'
                self.s_beta = None
                self.s_market = None
                self.s_entry = None

            self.after(1, self.update_screener)

        def country_select(event):
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    self.s_country = event.widget.get(indice)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def sector_select(event):
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    self.s_sector = event.widget.get(indice)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def filtra_x_beta(s_beta):
            b_range = [-5, 0.5, 1.5, 5]
            if not is_none(s_beta):
                i = 0 if s_beta == 'Low' else 1 if s_beta == 'Medium' else 2
                for item in self.tree.get_children():
                    item_values = self.tree.item(item, "values")
                    if b_range[i] <= float(item_values[4]) < b_range[i + 1]:
                        self.tree.delete(item)

        try:

            self.win = ttk.Frame(self.root, padding=(5, 5, 5, 5), style='B.TFrame')
            self.panel = ttk.Frame(self.win, padding=(5, 5, 5, 5), style='B.TFrame')
            self.options = ttk.Frame(self.win, padding=(5, 5, 5, 5), style='C.TFrame')
            self.win.pack(fill=tk.BOTH)
            self.panel.pack(side=tk.LEFT)
            self.options.pack(side=tk.RIGHT)

            self.tree = ttk.Treeview(self.panel, columns=self.ctree, height=27, style='B.TFrame')
            v_scroll = ttk.Scrollbar(self.panel, orient=VERTICAL, command=self.tree.yview)
            # h_scroll = ttk.Scrollbar(self.panel, orient=HORIZONTAL, command=self.tree.xview)
            # self.tree.configure(yscroll=v_scroll.set, xscroll=h_scroll.set, style='Treeview.Heading')
            self.tree.configure(yscroll=v_scroll.set, style='Treeview.Heading')
            self.tree.bind('<<TreeviewSelect>>', item_selected)

            imagen_tk = BDsystem.select_image(idd=201, size=(32, 32))
            self.tree.heading("#0", image=imagen_tk)
            self.tree.heading(self.ctree[0], text=self.ctree[0].replace('_', ' '), anchor=tk.W,
                            command=lambda: sort_treeview(self.tree, self.ctree[0], False))
            self.tree.heading(self.ctree[1], text=self.ctree[1].replace('_', ' '), anchor=tk.W,
                            command=lambda: sort_treeview(self.tree, self.ctree[1], False))
            self.tree.heading(self.ctree[2], text=self.ctree[2].replace('_', ' '), anchor=tk.W,
                            command=lambda: sort_treeview(self.tree, self.ctree[2], False))
            self.tree.heading(self.ctree[3], text=self.ctree[3].replace('_', ' '), anchor=tk.W,
                            command=lambda: sort_treeview(self.tree, self.ctree[3], False))
            self.tree.heading(self.ctree[4], text=self.ctree[4].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[4], False))
            self.tree.heading(self.ctree[5], text=self.ctree[5].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[5], False))
            self.tree.heading(self.ctree[6], text=self.ctree[6].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[6], False))
            self.tree.heading(self.ctree[7], text=self.ctree[7].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[7], False))
            self.tree.heading(self.ctree[8], text=self.ctree[8].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[8], False))
            self.tree.heading(self.ctree[9], text=self.ctree[9].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[9], False))
            self.tree.heading(self.ctree[10], text=self.ctree[10].replace('_', ' '), anchor=tk.E,
                            command=lambda: sort_treeview(self.tree, self.ctree[10], False))
            self.tree.heading(self.ctree[11], text=self.ctree[11].replace('_', ' '), anchor=tk.W,
                            command=lambda: sort_treeview(self.tree, self.ctree[11], False))

            self.tree.column("#0", width=50, minwidth=50, stretch=tk.NO)
            self.tree.column(self.ctree[0], width=60, minwidth=60, stretch=tk.NO)
            self.tree.column(self.ctree[1], width=200, minwidth=200, stretch=tk.NO)
            self.tree.column(self.ctree[2], width=40, minwidth=40, stretch=tk.NO)
            self.tree.column(self.ctree[3], width=100, minwidth=100, stretch=tk.NO)
            self.tree.column(self.ctree[4], width=60, minwidth=60, stretch=tk.NO)
            self.tree.column(self.ctree[5], width=90, minwidth=90, stretch=tk.NO)
            self.tree.column(self.ctree[6], width=90, minwidth=90, stretch=tk.NO)
            self.tree.column(self.ctree[7], width=90, minwidth=90, stretch=tk.NO)
            self.tree.column(self.ctree[8], width=50, minwidth=50, stretch=tk.NO)
            self.tree.column(self.ctree[9], width=60, minwidth=60, stretch=tk.NO)
            self.tree.column(self.ctree[10], width=60, minwidth=60, stretch=tk.NO)
            self.tree.column(self.ctree[11], width=90, minwidth=90, stretch=tk.NO)
            
            # define carractristicas del treeview()
            self.tree.tag_configure("even", background="black", foreground='white')
            self.tree.tag_configure("odd", background="black", foreground='white')
            self.tree.grid(column=0, row=6, columnspan=2, rowspan=4, sticky=(N, S, E, W))
            # h_scroll.grid(column=0, row=10, columnspan=2, sticky=E + W)
            v_scroll.grid(column=3, row=6, rowspan=4, sticky=N + S)

            # set position of all above objects by pack panel
            imagen_tk = BDsystem.select_image(idd=200, size=(32, 32))

            entry = ttk.Entry(self.panel, width=58, justify="left", font=("Arial", 22), style='C.TButton')
            search = tk.Button(self.panel, image=imagen_tk, bg=self.colors['bgcolor'], relief=tk.FLAT,
                                command=lambda: self.update_screener)
            search.imagen = imagen_tk
            entry.grid(column=1, row=0, columnspan=3, pady=5)
            search.grid(column=0, row=0, sticky=E, pady=5)
            entry.bind("<KeyRelease>", get_select)

            self.insert_treeview()

            # Windows 2 (right)
            self.wi20 = ttk.Frame(self.options, padding=(5, 5, 5, 5), style='C.TFrame')
            self.wi20.grid(column=0, row=19, padx=0, pady=10, sticky=(N, S, E, W))
            apply = tk.Button(self.wi20, text='Apply', width=6, bg=self.colors['bgcolor'],
                            command=lambda: update_window('apply'))
            reset = tk.Button(self.wi20, text='Reset', width=6, bg=self.colors['bgcolor'],
                            command=lambda: update_window('reset'))

            # filtro tipo de activo rnb1
            tipo = tk.StringVar()
            tipo.set(self.s_tipo)
            tipo.trace("w", get_select)
            tp1 = ttk.Label(self.options, text='TIPO DE ACTIVO ::', style='C.TLabel')
            tp2 = ttk.Radiobutton(self.options, text="Stock Dividends", variable=tipo,
                                value="Dividends", style='C.TRadiobutton')
            tp3 = ttk.Radiobutton(self.options, text="Stock Trend", variable=tipo,
                                value="Trend", style='C.TRadiobutton')
            tp4 = ttk.Radiobutton(self.options, text="ETF's Funds", variable=tipo,
                                value="ETF", style='C.TRadiobutton')

            tp1.grid(column=0, row=0, sticky=W, pady=1)
            tp2.grid(column=0, row=1, sticky=W, padx=10)
            tp3.grid(column=0, row=2, sticky=W, padx=10)
            tp4.grid(column=0, row=3, sticky=W, padx=10)

            # filtro Beta de activo rnb2
            beta = tk.StringVar()
            beta.set(self.s_beta)
            beta.trace("w", get_select)
            bt1 = ttk.Label(self.options, text='BETA ::', style='C.TLabel')
            bt2 = ttk.Radiobutton(self.options, text="Low (<0.5)", variable=beta,
                                value='Low', style='C.TRadiobutton')
            bt3 = ttk.Radiobutton(self.options, text="Medium (0.5-1.5)", variable=beta,
                                value='Medium', style='C.TRadiobutton')
            bt4 = ttk.Radiobutton(self.options, text="High (>1.5)", variable=beta,
                                value='High', style='C.TRadiobutton')

            bt1.grid(column=0, row=4, sticky=W, pady=10)
            bt2.grid(column=0, row=5, sticky=W, padx=10)
            bt3.grid(column=0, row=6, sticky=W, padx=10)
            bt4.grid(column=0, row=7, sticky=W, padx=10)


            # filtro Market CAP de activo rnb3
            mkt_c = tk.StringVar()
            mkt_c.set(self.s_market)
            mkt_c.trace("w", get_select)
            mt1 = ttk.Label(self.options, text='MARKET CAP ::', style='C.TLabel')
            mt2 = ttk.Radiobutton(self.options, text="Mega (>$200B)", variable=mkt_c,
                                value="Mega", style='C.TRadiobutton')
            mt3 = ttk.Radiobutton(self.options, text="Large ($10B-$200B)", variable=mkt_c,
                                value="Large", style='C.TRadiobutton')
            mt4 = ttk.Radiobutton(self.options, text="Medium ($2B-$10B)", variable=mkt_c,
                                value="Medium", style='C.TRadiobutton')
            mt5 = ttk.Radiobutton(self.options, text="Small ($300M-$2B)", variable=mkt_c,
                                value="Small", style='C.TRadiobutton')
            mt6 = ttk.Radiobutton(self.options, text="Micro ($50M-$300M)", variable=mkt_c,
                                value="Micro", style='C.TRadiobutton')
            mt7 = ttk.Radiobutton(self.options, text="Nano (<$50M)", variable=mkt_c,
                                value="Nano", style='C.TRadiobutton')

            mt1.grid(column=0, row=8, sticky=W, pady=10)
            mt2.grid(column=0, row=9, sticky=W, padx=10)
            mt3.grid(column=0, row=10, sticky=W, padx=10)
            mt4.grid(column=0, row=11, sticky=W, padx=10)
            mt5.grid(column=0, row=12, sticky=W, padx=10)
            mt6.grid(column=0, row=13, sticky=W, padx=10)
            mt7.grid(column=0, row=14, sticky=W, padx=10)


            # filtro sector rnb4
            st1 = ttk.Label(self.options, text='SECTOR ::', style='C.TLabel')
            sector = tk.Listbox(self.options, width=24, height=5)
            sector.bind('<<ListboxSelect>>', sector_select)
            s_scroll = ttk.Scrollbar(self.options, orient=tk.VERTICAL, command=sector.yview)
            sector.config(yscrollcommand=s_scroll.set)
            st1.grid(column=0, row=15, sticky=W, pady=10)
            sector.grid(column=0, row=16, sticky=W, padx=10)
            s_scroll.grid(column=1, row=16, sticky=(W, N + S))

            d_sector, d_country = self.sector_country()
            sector.insert(tk.END, 'None')
            for keys in d_sector:
                sector.insert(tk.END, keys)

            # filtro country rnb5
            ct1 = ttk.Label(self.options, text='COUNTRY ::', style='C.TLabel')
            country = tk.Listbox(self.options, width=24, height=5)
            country.bind('<<ListboxSelect>>', country_select)
            c_scroll = ttk.Scrollbar(self.options, orient=tk.VERTICAL, command=country.yview)
            country.config(yscrollcommand=c_scroll.set)

            country.insert(tk.END, 'None')
            for keys in d_country:
                country.insert(tk.END, keys)

            ct1.grid(column=0, row=17, sticky=W, pady=10)
            country.grid(column=0, row=18, sticky=W, padx=10)
            c_scroll.grid(column=1, row=18, sticky=(W, N + S))

            apply.grid(column=0, row=19, sticky=E, padx=20, pady=20)
            reset.grid(column=1, row=19, sticky=E, columnspa=2, pady=20)
        except EncodingWarning as e:
            print("widgets_screener(): {}".format(e))


    def update_screener(self):
       
        self.filtra_seleccion()

        d_sector, d_country = self.sector_country()

        self.after(9000000, self.update_screener)


    def sector_country(self) -> list:
        s_datos, c_datos = list(), list()
        for keys in self.market:
            if not is_null(keys[self.ix.index('sector')]):
                if keys[self.ix.index('sector')] not in s_datos:
                    s_datos.append(keys[self.ix.index('sector')])

            if not is_none(keys[self.ix.index('country')]):
                if keys[self.ix.index('country')] not in c_datos:
                    c_datos.append(keys[self.ix.index('country')])

        return s_datos, c_datos

    # carga datos en treeview()
    def insert_treeview(self):
        self.counter, ix = 0, self.ix

        for keys in self.market:
            beta = 0 if is_none(keys[ix.index('beta')]) else keys[ix.index('beta')]
            r_div = 0 if is_none(keys[ix.index('dividendRate')]) else keys[ix.index('dividendRate')]
            u_div = 0 if is_none(keys[ix.index('lastDividendValue')]) else keys[ix.index('lastDividendValue')]
            d_yield = 0 if is_none(keys[ix.index('dividendYield')]) else keys[ix.index('dividendYield')]
            mkt_cap = 0 if is_none(keys[ix.index('marketCap')]) else keys[ix.index('marketCap')]
            volume = 0 if is_none(keys[ix.index('volume')]) else keys[ix.index('volume')]
            country = ' ' if is_none(keys[ix.index('country')]) else keys[ix.index('country')]
            sector = ' ' if is_none(keys[ix.index('sector')]) else keys[ix.index('sector')]
            shortName = ' ' if is_none(keys[ix.index('shortName')]) else keys[ix.index('shortName')]
            categoriaActivo = ' ' if is_none(keys[ix.index('categoriaActivo')]) else keys[ix.index('categoriaActivo')]

            # xtag = "even" if i % 2 == 0 else "old"
            self.tree.insert("", tk.END,  values=(
                            '{:<10}'.format(keys[ix.index('symbol')]),
                            '{:<20}'.format(shortName),
                            '{:^5}'.format(categoriaActivo),
                            '{:<20}'.format(country),
                            '{:>10.2f}'.format(r_div),
                            '{:>10.2%}'.format(d_yield),
                            '{:>10}'.format(mask_numero(mkt_cap)),
                            '{:<20}'.format(sector),
                            '{:>7.2f}'.format(beta),
                            '{:>8}'.format(mask_numero(volume)),
                            # '{:>7.2f}'.format(keys[ix.index('lastPrice')]),
                            '{:>7.2f}'.format(0),
                            '{:%y-%b-%d}'.format(keys[ix.index('exDividendDate')]) if keys[ix.index('exDividendDate')] else '-'
            ))
            # ), tags=(xtag,))
            self.counter += 1

    # elimina datos de treeview()
    def delete_items_treeview(self):
        for item_id in self.tree.get_children(''):
            self.tree.delete(item_id)

    # controla que se muestren los datos seleccionados en el screener
    def filtra_seleccion(self):

       
        (self.market, self.ix) = self.ScMarket.select(account=self.account, tipo=self.s_tipo,
                                                      country=self.s_country, sector=self.s_sector,
                                                      name=self.s_entry, symbol=self.s_entry)

        self.delete_items_treeview()
        self.insert_treeview()
        # print(f'update({len(self.market)}) tipo={self.s_tipo}, country={self.s_country}, sector={self.s_sector}',
        #       f'name={self.s_entry}, symbol={self.s_entry}')

        if not is_none(self.s_beta):
            pass 

        if not is_none(self.s_market):
            pass



if __name__ == '__main__':
    win = tk.Tk()
    dw = 1290
    dh = 700
    df = 1297
    style = style_app(main=win)
    dpn = ttk.Frame(win, style="C.TFrame", width=dw, height=dh)
    dpn.grid(padx=5, pady=5)

    max_dw = dpn.winfo_screenwidth()
    max_dh = dpn.winfo_screenheight()
    bgcolor = 'DarkCyan'
    cchart = {'texto': 'white', 'titulo': 'cyan', 'fondo': bgcolor, 'axsy': 'black',
                   'axsx': 'black', '2eje': 'orange', 'plot1': 'green', 'plot2': 'orange',
                   'plot3': 'red', 'plot4': 'yellow', 'plot5': 'DodgerBlue'}
    colors = {'bgcolor': bgcolor,
              'fgcolor': 'white',
              'cgcolor': 'black',
              'dw': dw,
              'dh': dh,
              'df': df,
              'max_dw': max_dw,
              'max_dh': max_dh}
    colors.update({'cchart': cchart})

    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")

    frame_screener = Screener(master=dpn, account='U4214563', colors=colors)
    frame_screener.pack()
    win.mainloop()
