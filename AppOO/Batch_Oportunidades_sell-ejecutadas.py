from Modulos_Mysql import PlanInversion, IPerformance, RepositorioOportunidadesBuySell
from Modulos_python import datetime, timedelta, pd, os, csv, json
from Class_DataFrame import get_yfinance
from Class_DashBot import Chatbot
from Modulos_Utilitarios import symbol_indicadores, limpiar_nan


# crea info()
def datos_yfinance(symbol, vehiculo, read, ix):
    activos, pdatos = get_yfinance(ticket=symbol, vehiculo=vehiculo)
    d_index = pdatos.index.tz_localize(None)

    date = read[ix.index("fechahora")].date()
    fecha_limite = pd.to_datetime(date)
    datos = pdatos[d_index <= fecha_limite].copy()

    indicadores, info = {}, {}
    if not datos.empty:
        indicadores = symbol_indicadores(symbol=symbol, datos=datos)

    update = False
    info.update(
        {
            symbol: {
                "activos": activos,  # almacena yf.Ticker.info()
                "datos": datos,  # almacena yf.history()
                "datos_tecnicos": indicadores,  # almacena datos técnicos
                "update": update,
            }
        }
    )  # True: si contiene dividends

    return indicadores


def tipo_sell(indicadores, read, ix):

    stock = read[ix.index("stock")] - read[ix.index("cantidad")]
    sell = -read[ix.index("cantidad")]
    opt = sell / stock
    costo = read[ix.index("basico")] * stock
    profi = read[ix.index("gprealizadas")]
    costAcum = (read[ix.index("preciotrans")] - read[ix.index("mtmgp")]) * sell
    roi = profi / costAcum
    p_stock = stock - sell
    avgcost = 0 if p_stock == 0 else (costo - costAcum) / p_stock
    tipo = None
    struct = {}

    if read[ix.index("stock")] == 0.0:
        tipo = "100%"
    elif read[ix.index("stock")] > 0.0:
        if opt <= 0.25:
            tipo = " 25%"
        elif 0.25 > opt <= 0.33:
            tipo = " 33%"
        elif opt > 0.33:
            tipo = "100%"

    if tipo is not None:

        datosTenicos = json.dumps(indicadores) if indicadores else {}
        struct.update({"symbol": read[ix.index("simbolo")]})
        struct.update({"option": tipo})
        struct.update({"profit": profi})
        struct.update({"cantidad lotes": 1})
        struct.update({"cantidad sell": sell})
        struct.update({"last": read[ix.index("preciotrans")]})
        struct.update({"fecha": read[ix.index("fechahora")].date()})
        struct.update({"costoCum": costAcum})
        struct.update({"roi": roi})
        struct.update({"costobase": costo})
        struct.update({"position": stock})
        struct.update({"disponible": sell})
        struct.update({"pos avgCost": avgcost})
        struct.update({"pos position": p_stock})
        struct.update({"pos costobase": avgcost * p_stock})
        struct.update({"datos_tecnicos": datosTenicos})
        struct.update({"Recomendado": 1})
        struct.update({"Comentarios": "hitorial de venta directa"})

    return struct


def read_csv(file):
    vacio = pd.DataFrame()
    path = os.getcwd()
    path += f"\\tmp\\{file}"
    df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
    if df.empty:
        return vacio

    df.columns = df.columns.str.strip()
    df.reset_index(drop=True, inplace=True)
    df["Opcion"] = df["Opcion"].astype(str).str.strip()
    df = df.dropna(how="all", axis=1)

    # Filtrar recomendaciones válidas
    df_recom = df[(df["%Roi"] > -0.10) & (df["Profit"] > 1) & (df["Profit"] < 16)]
    return df_recom if not df_recom.empty else vacio


def oportunidades(file, update=False):
    df_sell = read_csv(file=file)

    items = 0
    if not df_sell.empty and update:
        for _, row in df_sell.iterrows():
            # inserta Opornunidad de venta
            insert = ROportunidades.insertar_sell(
                row=row, tipo="sell", subtipo="gain", origen="modelo_sellv01", tolerancia_roi=0.50
            )
            items += 1
            print(f"Insert {insert} {items}")
    else:
        print(df_sell)
    print(f"Registros insert...: {items}")
    print("=" * 60)


def app(account, insert):
    def write_file(archivo=None, accion="detalle", struct=None):

        if (accion == "header") and (archivo == "sell"):
            writer.writerow(
                [
                    "Symbol",
                    "Opcion",
                    "Profit",
                    "NroLotes",
                    "CantidadSell",
                    "PriceMarket",
                    "Fecha",
                    "CostoCum",
                    "%Roi",
                    "CostoBase",
                    "Position",
                    "Disponible",
                    "PosAvgCost",
                    "PosPosition",
                    "PosCostobase",
                    "Datostecnicos",
                    "Recomendado",
                    "Comentarios",
                ]
            )

        elif (accion == "detalle") and (archivo == "sell"):
            writer.writerow(
                [
                    struct["symbol"],
                    struct["option"],
                    struct["profit"],
                    struct["cantidad lotes"],
                    struct["cantidad sell"],
                    struct["last"],
                    struct["fecha"],
                    struct["costoCum"],
                    struct["roi"],
                    struct["costobase"],
                    struct["position"],
                    struct["disponible"],
                    struct["pos avgCost"],
                    struct["pos position"],
                    struct["pos costobase"],
                    struct["datos_tecnicos"],
                    struct["Recomendado"],
                    struct["Comentarios"],
                ]
            )

    hoy = datetime.now()
    desde = datetime(hoy.year, 1, 1)
    dias = hoy - desde
    hasta = hoy - timedelta(dias.days)

    book, ix = ROportunidades.select_booktrading(accion="desde_hasta", account=account, fecha=hasta, hasta=hoy)

    tipo, items, path = "sell", 0, os.getcwd()
    arch = f"csv_historialDatosIA_{tipo}.csv"
    path += "\\tmp\\" + arch

    with open(path, mode="w", newline="") as file:
        writer = csv.writer(file)
        write_file(archivo=tipo, accion="header")

        for i, read in enumerate(book):
            fecha_favilda = read[ix.index("fechahora")].date() >= hasta.date()
            if fecha_favilda and read[ix.index("codigo")] == "C" and read[ix.index("gprealizadas")] > 0:

                # carga info()
                indicadores = datos_yfinance(
                    symbol=read[ix.index("simbolo")], vehiculo=read[ix.index("categoria")], read=read, ix=ix
                )
                struct = tipo_sell(indicadores=indicadores, read=read, ix=ix)
                if struct:
                    write_file(archivo=tipo, accion="detalle", struct=struct)
                    items += 1

    print("=" * 60)
    print(f"Archivo............: {arch}")
    print(f"Registros grabados.: {items}")
    print("=" * 60)
    oportunidades(file=arch, update=insert)


if __name__ == "__main__":
    Performa = IPerformance()
    PInversion = PlanInversion()
    ROportunidades = RepositorioOportunidadesBuySell()

    # app(account='B0000001', insert=False)
    app(account="U4214563", insert=True)
