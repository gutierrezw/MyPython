from Library_python import (
    datetime,
    timedelta,
    os,
    ttk,
    Path,
)

def style_app(main=None) -> object:
    """
    @param main:  windonw principal de la aplicación
    @return: configura colores y style de la aplicación
    """
    style = ttk.Style(main)

    # TFrame
    style.configure(
        "TFrame", font=("Courier", 8), foreground="white", background="black"
    )
    style.map(
        "TFrame",
        background=[("selected", "lightblue")],  # Fondo de selección
        foreground=[("selected", "black")],
    )  # Texto de selección

    style.configure(
        "B.TFrame", font=("Courier", 8), foreground="black", background="black"
    )
    style.configure(
        "C.TFrame", font=("Courier", 8), foreground="white", background="DarkCyan"
    )
    style.configure(
        "W.TFrame", font=("Courier", 8), foreground="black", background="white"
    )
    style.configure("R.TFrame", font=("Courier", 8), background="red")

    # Button
    style.configure("W.TButton", foreground="white")
    style.configure("B.TButton", foreground="black")
    style.configure("C.TButton", background="DarkCyan", foreground="black")

    # TNoteBook
    style.configure("TNotebook", background="DarkCyan", borderwidth=1)
    style.configure("TNotebook.Tab", background="DarkCyan", foreground="black")

    style.configure(
        "Custom.TNotebook.Tab", background="lightblue", font=("Arial", 10, "bold")
    )

    # TLabel
    style.configure(
        "TLabel", font=("Courier", 8), foreground="white", background="black"
    )
    style.configure(
        "C.TLabel", font=("Courier", 8), foreground="white", background="DarkCyan"
    )
    style.configure(
        "Br.TLabel", font=("Courier", 8), foreground="black", background="red3"
    )
    style.configure(
        "Bg.TLabel", font=("Courier", 8), foreground="black", background="green2"
    )
    style.configure(
        "Wr.TLabel", font=("Courier", 8), foreground="White", background="firebrick4"
    )
    style.configure(
        "Wg.TLabel", font=("Courier", 8), foreground="White", background="dark green"
    )
    # (C.TScrollbar)
    style.configure(
        "C.TScrollbar",
        troughcolor="gray",
        background="DarkCyan",
        arrowcolor="black",
        relief="flat",
        gripcount=10,
    )

    # (Treeview)
    style.configure(
        "Treeview",
        background="Black",
        foreground="white",
        fieldbackground="black",
        font=("Courier", 8),
    )

    style.map(
        "Treeview",
        background=[("selected", "lightblue")],
        foreground=[("selected", "black")],
    )

    # B.Heading
    style.configure(
        "B.Heading", font=("Arial", 10, "bold"), background="blue", foreground="white"
    )

    # R.Heading
    style.configure(
        "R.Heading", font=("Arial", 10, "bold"), background="red", foreground="white"
    )
    # G.Heading
    style.configure(
        "G.Heading", font=("Arial", 10, "bold"), background="green", foreground="white"
    )

    # (TRadiobutton)
    style.configure(
        "C.TRadiobutton", background="DarkCyan", foreground="black", font=("Courier", 8)
    )

    # (TCheckbutton)
    # style.configure("T.TCheckbutton", font=("Helvetica", 10), foreground="gray")
    style.configure("T.TCheckbutton", foreground="gray")
    style.map(
        "T.TCheckbutton",
        background=[("selected", "green"), ("!selected", "red")],
        foreground=[("selected", "white"), ("!selected", "white")],
    )
    style.configure(
        "TScrollbar",
        background="gray",
        troughcolor="black",
        arrowcolor="blue",
        gripcount=5,
        width=5,
    )

    return style


def spaces(s):
    blancos = " " * s
    return blancos

# Elimina archivos
def delete_file(ruta=None, patron=None, display=True):
    """Elimina varios archivos que coincidan con un patrón en un directorio."""

    s_archivo = None
    ruta_directorio = Path(ruta)

    # Elimina patron del directorio
    if patron is not None:
        for s_archivo in ruta_directorio.glob(patron):
            try:
                s_archivo.unlink()
            except Exception as e:
                if display:
                    print(f"delete_file(): {e}")

    else:
        try:
            s_archivo = Path(ruta)
            s_archivo.unlink()
        except Exception as e:
            if display:
                print(f"delete_file(): {e}")


# establece cache -- para yfinance
def define_FileCache(name=None):
    ipath = os.getcwd()
    if name is not None:
        cache = ipath + f"\\tmp\\{name}"
    elif name is None:
        temp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cache = ipath + "\\tmp\\cache_{temp}"
    return cache


if __name__ == "__main__":
    print("rutinas-----")
