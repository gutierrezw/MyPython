import json

import pandas as pd
from api_chart import *
from bd_conect import *
from globales import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def rendimiento_dividends(fg: object, cv: object, activo: object, symbol=None, plot="no", period="5y") -> dict:
    try:
        if not is_none(symbol):
            if type(activo) != "yfinance.ticker.Ticker":
                activo, datos = get_yfinance(ticket=symbol, vehiculo="Stock")

            ix_name = "shortName" if "shortName" in activo.info else "longName"
            empresa = activo.info[ix_name]

            y_datos, value = pd.DataFrame(), "E"
            if "Dividends" not in datos:
                return y_datos, value

            m_div = datos[datos["Dividends"] != 0]
            m_index = m_div.index

            if not m_div.empty:
                forward_div = activo.info["dividendRate"]
                pd.options.mode.copy_on_write = True
                x_none, pdatos = get_yfinance(ticket=symbol, vehiculo="hist")

                # datos.insert(datos.shape[1], 'Close', 0)
                datos.index = datos.index.tz_localize(None)
                d_index = datos.index

                # filtra los meses de pago de dividendos y calcula su rendimiento
                m_datos = datos[datos["Dividends"] != 0]
                m_datos["Rendimiento"] = m_datos["Dividends"] / m_datos["Close"]
                m_index = m_datos.index

                # replantea el dividendo anual y su rendimiento
                y_datos = pd.DataFrame(columns=["Close", "Dividends", "Rendimiento"])
                y_datos["Close"] = m_datos["Close"].resample("YE").mean()
                y_datos["Dividends"] = m_datos["Dividends"].resample("YE").sum()
                y_datos["Rendimiento"] = m_datos["Rendimiento"].resample("YE").sum()

                y_index = y_datos.index
                if len(d_index) > 0:
                    y_datos.loc[y_index[-1], "Rendimiento"] = forward_div / datos.loc[d_index[-1], "Close"]
                    y_datos.loc[y_index[-1], "Close"] = datos.loc[d_index[-1], "Close"]
                    forward_yield = y_datos.loc[y_index[-1], "Rendimiento"]

                    if plot == "yes":
                        dlabl = {
                            "symbol": symbol,
                            "buy": "Zona buy",
                            "sell": "Zona sell",
                            "legend": "outside upper left",
                        }
                        asset = {"ticket": symbol, "forward": forward_yield, "name": empresa, "aspect": 0.40}
                        chart_rendimiento_dividendos(fg, cv, datos=y_datos, dlabl=dlabl, asset=asset)

                    m = y_datos.describe()["Rendimiento"]["mean"]
                    i = y_datos[y_datos["Rendimiento"] > m]["Rendimiento"].mean()
                    s = y_datos[y_datos["Rendimiento"] < m]["Rendimiento"].mean()

                    dforward = y_datos.loc[y_index[-1], "Rendimiento"]
                    value = ("I" if dforward > m else "S" if dforward < m else "N",)

    except EncodingWarning as error:
        print("rendimiento_dividends()]: {}".format(error))
    return y_datos, value


if __name__ == "__main__":
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (dw, dh)
    win.geometry(dimension)
    win.config(bg="black")
    style = ttk.Style(win)
    style.configure("TFrame", font=("Courier", 8), foreground="white", background="black")
    dpn = ttk.Frame(win, style="TFrame", width=df, height=700)
    dpn.grid(pady=50)

    gcolor = "black"
    fg = Figure(figsize=(8.0, 6.0), dpi=110, layout="tight")
    fg.set_facecolor(gcolor)
    cv = FigureCanvasTkAgg(fg, master=dpn)
    cv.draw()
    cv.get_tk_widget().pack()

    datos, value = rendimiento_dividends(fg=fg, cv=cv, activo=None, plot="yes", period="5y", symbol="HASI")
    x = datos.to_json(orient="split")
    d = json.loads(x)
    w = pd.DataFrame(data=d["data"], columns=d["columns"], index=d["index"])
    w.index = pd.to_datetime(w.index, unit="ms")
    print(value, datos)

    win.mainloop()
