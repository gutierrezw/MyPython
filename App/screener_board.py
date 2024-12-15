from api_chart import *


global tree, market, ix, s_country, s_sector, s_tipo, s_beta, s_market, s_entry
s_country, s_sector,  s_tipo, s_beta, s_market, s_entry = None, None, 'Dividends', None, None, None
market, ix = select_market(account=apilocal['account'], tipo=s_tipo)


class screener_board(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)
        self.widgets_screener()
        self.update_screener()
        self.config(bg="black")


    def widgets_screener(self):
        global tree, market, ix, gcolor, s_country, s_sector

        def item_selected(event):
            for selected_item in tree.selection():
                item = tree.item(selected_item)
                record = item['values']
                if not is_none(record[0]):
                    ticket = record[0].strip()
                    name = record[1]
                    evaluar_fila(vehiculo='Stock', empresa=name, ticket=ticket)

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
            global s_tipo, s_beta, s_market, s_entry
            s_tipo = tipo.get()
            s_beta = beta.get()
            s_entry = entry.get()
            s_market = mkt_c.get()

            s_beta = s_beta if not is_null(s_beta) else None
            s_entry = s_entry if not is_null(s_entry) else None
            s_market = s_market if not is_null(s_market) else None

        def update_window(tipo):
            global s_country, s_sector, s_tipo, s_beta, s_market, s_entry

            if tipo == 'reset':
                s_country, s_sector, s_tipo, s_beta, s_market, s_entry = None, None, 'Dividends', None, None, None
            self.after(1, self.update_screener)

        def country_select(event):
            global s_country
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    s_country = event.widget.get(indice)

                return s_country
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def sector_select(event):
            global s_sector
            try:
                seleccion = event.widget.curselection()
                if seleccion:
                    indice = seleccion[0]
                    s_sector = event.widget.get(indice)

                return s_sector
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def filtra_x_beta(s_beta):
            b_range = [-5, 0.5, 1.5, 5]
            if not is_none(s_beta):
                i = 0 if s_beta == 'Low' else 1 if s_beta == 'Medium' else 2
                for item in tree.get_children():
                    item_values = tree.item(item, "values")
                    if b_range[i] <= float(item_values[4]) < b_range[i + 1]:
                        tree.delete(item)

        gcolor = {'win1': 'Black', 'win2': 'DarkCyan'}
        ctree = ['Symbol', 'Name', 'Status', 'Country', 'Beta', 'Volume', 'Last_Sale',
                 'Dividends', 'Dividends_Yield', 'Market_Cap', 'Sector', 'Date exDividend']

        style_all(main=self)

        win1 = ttk.Frame(self, padding=(10, 40, 12, 12), style='TFrame')
        win2 = ttk.Frame(self, padding=(10, 40, 12, 12), style='W.TFrame')

        tree = ttk.Treeview(win1, columns=ctree,  height=26, style='Treeview')
        v_scroll = ttk.Scrollbar(win1, orient=VERTICAL, command=tree.yview)
        h_scroll = ttk.Scrollbar(win1, orient=HORIZONTAL, command=tree.xview)
        tree.configure(yscroll=v_scroll.set, xscroll=h_scroll.set,  style='Treeview.Heading')
        tree.bind('<<TreeviewSelect>>', item_selected)

        imagen0, xlis = select_objeto(codigo=201)
        imagen = Image.open(io.BytesIO(imagen0))
        imagen = imagen.resize((16, 16), Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)

        tree.heading("#0", image=imagen_tk)
        tree.heading(ctree[0], text=ctree[0].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[0], False))
        tree.heading(ctree[1], text=ctree[1].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[1], False))
        tree.heading(ctree[2], text=ctree[2].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[2], False))
        tree.heading(ctree[3], text=ctree[3].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[3], False))
        tree.heading(ctree[4], text=ctree[4].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[4], False))
        tree.heading(ctree[5], text=ctree[5].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[5], False))
        tree.heading(ctree[6], text=ctree[6].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[6], False))
        tree.heading(ctree[7], text=ctree[7].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[7], False))
        tree.heading(ctree[8], text=ctree[8].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[8], False))
        tree.heading(ctree[9], text=ctree[9].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[9], False))
        tree.heading(ctree[10], text=ctree[10].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[10], False))
        tree.heading(ctree[11], text=ctree[11].replace('_', ' '), anchor=tk.W,
                         command=lambda: sort_treeview(tree, ctree[11], False))
        # tree.heading(ctree[12], text=ctree[12].replace('_', ' '), anchor=tk.W)

        tree.column("#0", width=50, minwidth=50, stretch=tk.NO)
        tree.column(ctree[0], width=60, minwidth=60, stretch=tk.NO)
        tree.column(ctree[1], width=200, minwidth=200, stretch=tk.NO)
        tree.column(ctree[2], width=40, minwidth=40, stretch=tk.NO)
        tree.column(ctree[3], width=100, minwidth=100, stretch=tk.NO)
        tree.column(ctree[4], width=40, minwidth=40, stretch=tk.NO)
        tree.column(ctree[5], width=60, minwidth=60, stretch=tk.NO)
        tree.column(ctree[6], width=60, minwidth=60, stretch=tk.NO)
        tree.column(ctree[7], width=60, minwidth=60, stretch=tk.NO)
        tree.column(ctree[8], width=60, minwidth=60, stretch=tk.NO)
        tree.column(ctree[9], width=80, minwidth=80, stretch=tk.NO)
        tree.column(ctree[10], width=120, minwidth=120, stretch=tk.NO)
        tree.column(ctree[11], width=80, minwidth=80, stretch=tk.NO)
        # tree.column(ctree[12], width=100, minwidth=100, stretch=tk.NO)
        tree.tag_configure("even", background="black", foreground='white')
        tree.tag_configure("odd", background="Salmon", foreground='white')

        imagen0, xlis = select_objeto(codigo=200)
        imagen = Image.open(io.BytesIO(imagen0))
        imagen = imagen.resize((32, 32), Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)

        entry = ttk.Entry(win1, width=58, justify="left", font=("Arial", 22))
        search = ttk.Button(win1, image=imagen_tk, command=lambda: update_window('entry'), style='TButton')
        search.imagen = imagen_tk

        apply = ttk.Button(win2, text='Apply', width=7, command=lambda: update_window('apply'), style='W.TButton')
        reset = ttk.Button(win2, text='Reset', width=7, command=lambda: update_window('reset'), style='W.TButton')
        #
        # filtro tipo de activo rnb1
        #
        tipo = tk.StringVar()
        tipo.set(s_tipo)
        tipo.trace("w", get_select)
        tp1 = ttk.Label(win2, text='TIPO DE ACTIVO ::', style='W.TLabel')
        tp2 = ttk.Radiobutton(win2, text="Stock Dividends", variable=tipo, value="Dividends", style='W.TRadiobutton')
        tp3 = ttk.Radiobutton(win2, text="Stock Trend", variable=tipo, value="Trend", style='W.TRadiobutton')
        tp4 = ttk.Radiobutton(win2, text="ETF's Funds", variable=tipo, value="ETF", style='W.TRadiobutton')
        #
        # filtro Beta de activo rnb2
        #
        beta = tk.StringVar()
        beta.set(s_beta)
        beta.trace("w", get_select)
        bt1 = ttk.Label(win2, text='BETA ::', style='W.TLabel')
        bt2 = ttk.Radiobutton(win2, text="Low (<0.5)", variable=beta, value='Low', style='W.TRadiobutton')
        bt3 = ttk.Radiobutton(win2, text="Medium (0.5-1.5)", variable=beta, value='Medium', style='W.TRadiobutton')
        bt4 = ttk.Radiobutton(win2, text="High (>1.5)", variable=beta, value='High', style='W.TRadiobutton')
        #
        # filtro Market CAP de activo rnb3
        #
        mkt_c = tk.StringVar()
        mkt_c.set(s_market)
        mkt_c.trace("w", get_select)
        mt1 = ttk.Label(win2, text='MARKET CAP ::', style='W.TLabel')
        mt2 = ttk.Radiobutton(win2, text="Mega (>$200B)", variable=mkt_c, value="Mega", style='W.TRadiobutton')
        mt3 = ttk.Radiobutton(win2, text="Large ($10B-$200B)", variable=mkt_c, value="Large", style='W.TRadiobutton')
        mt4 = ttk.Radiobutton(win2, text="Medium ($2B-$10B)", variable=mkt_c, value="Medium", style='W.TRadiobutton')
        mt5 = ttk.Radiobutton(win2, text="Small ($300M-$2B)", variable=mkt_c, value="Small", style='W.TRadiobutton')
        mt6 = ttk.Radiobutton(win2, text="Micro ($50M-$300M)", variable=mkt_c, value="Micro", style='W.TRadiobutton')
        mt7 = ttk.Radiobutton(win2, text="Nano (<$50M)", variable=mkt_c, value="Nano", style='W.TRadiobutton')
        #
        # filtro sector rnb4
        #
        st1 = ttk.Label(win2, text='SECTOR ::', style='W.TLabel')
        sector = tk.Listbox(win2, width=22, height=5)
        sector.bind('<<ListboxSelect>>', sector_select)
        s_scroll = ttk.Scrollbar(win2, orient=tk.VERTICAL, command=sector.yview)
        sector.config(yscrollcommand=s_scroll.set)

        d_sector, d_country = sector_country(market, ix)
        sector.insert(tk.END, 'None')
        for keys in d_sector:
            sector.insert(tk.END, keys)
        #
        # filtro country rnb5
        #
        ct1 = ttk.Label(win2, text='COUNTRY ::', style='W.TLabel')
        country = tk.Listbox(win2, width=22, height=5)
        country.bind('<<ListboxSelect>>', country_select)
        c_scroll = ttk.Scrollbar(win2, orient=tk.VERTICAL, command=country.yview)
        country.config(yscrollcommand=c_scroll.set)

        country.insert(tk.END, 'None')
        for keys in d_country:
            country.insert(tk.END, keys)
        #
        # set position of all above objects by grid  win1
        win1.grid(column=0, row=0, sticky=(N, S, E, W))
        entry.grid(column=0, row=0, columnspan=3, pady=5)
        search.grid(column=1, row=0, sticky=E, pady=5)

        entry.bind("<KeyRelease>", get_select)

        tree.grid(column=0, row=6, columnspan=2, rowspan=4, sticky=(N, S, E, W))
        h_scroll.grid(column=0, row=10, columnspan=2, sticky=E + W)
        v_scroll.grid(column=3, row=6, rowspan=4, sticky=N + S)

        # set position of all above objects by grid  win2
        win2.grid(column=1, row=0, sticky=(N, S, E, W))
        tp1.grid(column=0, row=0, sticky=W, pady=1)
        tp2.grid(column=0, row=1, sticky=W, padx=10)
        tp3.grid(column=0, row=2, sticky=W, padx=10)
        tp4.grid(column=0, row=3, sticky=W, padx=10)

        bt1.grid(column=0, row=4, sticky=W, pady=10)
        bt2.grid(column=0, row=5, sticky=W, padx=10)
        bt3.grid(column=0, row=6, sticky=W, padx=10)
        bt4.grid(column=0, row=7, sticky=W, padx=10)

        mt1.grid(column=0, row=8, sticky=W, pady=10)
        mt2.grid(column=0, row=9, sticky=W, padx=10)
        mt3.grid(column=0, row=10, sticky=W, padx=10)
        mt4.grid(column=0, row=11, sticky=W, padx=10)
        mt5.grid(column=0, row=12, sticky=W, padx=10)
        mt6.grid(column=0, row=13, sticky=W, padx=10)
        mt7.grid(column=0, row=14, sticky=W, padx=10)

        st1.grid(column=0, row=15, sticky=W, pady=10)
        sector.grid(column=0, row=16, sticky=W, padx=10)
        s_scroll.grid(column=1, row=16, sticky=N + S, padx=10)

        ct1.grid(column=0, row=17, sticky=W, pady=10)
        country.grid(column=0, row=18, sticky=W, padx=10)
        c_scroll.grid(column=1, row=18, sticky=N + S, padx=10)

        apply.grid(column=0, row=19, sticky=E, pady=20)
        reset.grid(column=1, row=19, columnspan=2, pady=20)

        insert_treeview(tree, market, ix)
        return tree


    def update_screener(self):
        global tree, market, s_country, s_sector
        print(' update_screener()', 'sector=', s_sector, 'country=', s_country, 'tipo=', s_tipo,
              'beta=', s_beta, 'market=', s_market, 'entry=', s_entry)

        market, ix = select_market(account=apilocal['account'], tipo=s_tipo, country=s_country,
                                   sector=s_sector, name=s_entry, symbol=s_entry)

        #if  is_none(s_entry):
        #    market = filtra_seleccion(market, s_beta, s_market)

        d_sector, d_country = sector_country(market, ix)

        self.after(1, self.widgets_screener)
        return tree, market


def filtra_seleccion(market, s_beta, s_market) -> list:

    if not is_none(s_beta):
        pass
        # for keys in market:

    if not is_none(s_market):
        pass


def sector_country(market, ix) -> list:
    s_datos, c_datos = list(), list()
    for keys in market:
        if not is_null(keys[ix.index('sector')]):
            if keys[ix.index('sector')] not in s_datos:
                s_datos.append(keys[ix.index('sector')])

        if not is_none(keys[ix.index('country')]):
            if keys[ix.index('country')] not in c_datos:
                c_datos.append(keys[ix.index('country')])

    return s_datos, c_datos


def insert_treeview(tree, market, ix):
    i = 0
    for keys in market:
        beta = 0 if is_none(keys[ix.index('beta')]) else keys[ix.index('beta')]
        r_div = 0 if is_none(keys[ix.index('dividendRate')]) else keys[ix.index('dividendRate')]
        u_div = 0 if is_none(keys[ix.index('lastDividendValue')]) else keys[ix.index('lastDividendValue')]
        d_yield = 0 if is_none(keys[ix.index('dividendYield')]) else keys[ix.index('dividendYield')]
        mkt_cap = 0 if is_none(keys[ix.index('marketCap')]) else keys[ix.index('marketCap')]
        volume = 0 if is_none(keys[ix.index('volume')]) else keys[ix.index('volume')]

        if i % 2 == 0:
            tree.insert("", tk.END, values=('{:<10}'.format(keys[ix.index('symbol')]),
                                            '{:<20}'.format(keys[ix.index('shortName')]),
                                            '{:^5}'.format(keys[ix.index('categoriaActivo')]),
                                            '{:<20}'.format(keys[ix.index('country')]),
                                            '{:>7.2f}'.format(beta),
                                            '{:>8}'.format(mask_numero(volume)),
                                            '{:>7.2f}'.format(keys[ix.index('lastPrice')]),
                                            '{:>10.4f}'.format(r_div),
                                            '{:>10.2%}'.format(d_yield),
                                            '{:>10}'.format(mask_numero(mkt_cap)),
                                            '{:<20}'.format(keys[ix.index('sector')]),
                                            '{:%y-%b-%d}'.format(keys[ix.index('exDividendDate')])
                                            ), tags=("even",))
        else:
            tree.insert("", tk.END, values=('{:<10}'.format(keys[ix.index('symbol')]),
                                            '{:<20}'.format(keys[ix.index('shortName')]),
                                            '{:^5}'.format(keys[ix.index('categoriaActivo')]),
                                            '{:<20}'.format(keys[ix.index('country')]),
                                            '{:>7.2f}'.format(beta),
                                            '{:>8}'.format(mask_numero(volume)),
                                            '{:>7.2f}'.format(keys[ix.index('lastPrice')]),
                                            '{:>10.4f}'.format(r_div),
                                            '{:>10.2%}'.format(d_yield),
                                            '{:>10}'.format(mask_numero(mkt_cap)),
                                            '{:<20}'.format(keys[ix.index('sector')]),
                                            '{:%y-%b-%d}'.format(keys[ix.index('exDividendDate')])
                                            ), tags=("odd",))
        i += 1

    return tree


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")

    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=40)

    frame_screener = screener_board(master=dpn)
    frame_screener.pack()
    frame_screener.mainloop()
    win.mainloop()
