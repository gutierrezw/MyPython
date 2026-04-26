
def style_app(main=None) -> object:
    """
    @param main:  windonw principal de la aplicación
    @return: configura colores y style de la aplicación
    """
    style = ttk.Style(main)
    style.configure('T.TButton', foreground="white", background="black")
    style.configure('TFrame', font=('Courier', 8), foreground="white", background="black")
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
