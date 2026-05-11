import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_python import pd, datetime
from Modulos_Mysql import PlanInversion, RepositorioOportunidadesBuySell, IPerformance, DiariaCNV


def construir_nuevo(account, repo, perf):
    book, ix = repo.select_booktrading(accion="cartera", account=account, idivisa="ARS")
    performa, iy = perf.select_performa_inversion(account=account, vehiculo="BBVA.ARS", accion="all")

    if not book or not performa:
        return []

    datos = pd.DataFrame(book, columns=ix)
    datos = datos.drop(
        columns=[
            "id",
            "sec",
            "split",
            "updateStamp",
            "categoria",
            "idtrans",
            "divisa",
            "cuenta",
            "sell",
            "activa",
            "simbolo",
            "preciocierre",
            "preciotrans",
            "mtmgp",
            "stock",
        ]
    )

    idatos = pd.DataFrame(performa, columns=iy)
    idatos = idatos.drop(
        columns=["id", "idcuenta", "vehiculo", "referencia", "p_referencia", "p_vehiculo", "timestamp"]
    )
    idatos["dividendos"] = idatos["dividends"]
    idatos["navcierre"] = idatos["value"]
    idatos["costobase"] = idatos["costo_base"]
    idatos["Date"] = pd.to_datetime(idatos["fechaclose"])
    idatos.set_index("Date", inplace=True)
    idatos = idatos.drop(columns=["fechaclose", "dividends", "value", "costo_base"])

    idatos.index = pd.to_datetime(idatos.index)
    m_idatos = idatos.groupby(idatos.index.to_period("M")).last()
    m_idatos.index = m_idatos.index.strftime("%Y-%m")

    datos["depositos"] = datos.apply(
        lambda r: (r["producto"] / r["factor_cambio"] if r["codigo"] == "O" else 0), axis=1
    )
    datos["retiros"] = datos.apply(
        lambda r: (r["basico"] * r["cantidad"] / r["factor_cambio"] if r["codigo"] == "C" else 0), axis=1
    )
    datos["perdidas"] = datos.apply(
        lambda r: (-r["gprealizadas"] / r["factor_cambio"] if r["gprealizadas"] < 0 else 0), axis=1
    )
    datos["crecimiento"] = datos.apply(
        lambda r: (r["gprealizadas"] / r["factor_cambio"] if r["gprealizadas"] >= 0 else 0), axis=1
    )
    datos["costos"] = datos["perdidas"] + datos["tarifacomision"]
    datos["costo_base"] = datos["depositos"] - datos["retiros"]
    datos["beneficios"] = datos["crecimiento"] - datos["costos"]
    datos["comisiones"] = datos["tarifacomision"]
    datos["idevengo"] = 0.0
    datos["imargen"] = 0.0
    datos["tax"] = 0.0
    datos["fee"] = 0.0
    datos["Date"] = pd.to_datetime(datos["fechahora"])

    datos = datos.drop(columns=["fechahora", "producto", "tarifacomision", "basico", "cantidad"])
    datos.set_index("Date", inplace=True)
    datos.index = datos.index.strftime("%Y-%m")
    m_datos = datos.groupby(datos.index).sum()

    resumen = pd.merge(m_datos, m_idatos, on="Date", how="left")
    resumen = resumen.infer_objects(copy=False).fillna(0)
    resumen.index = pd.to_datetime(resumen.index)
    resumen.index = resumen.index + pd.offsets.MonthEnd(0)
    resumen.fillna(0, inplace=True)

    anterior = 0.0
    resultado = []
    for row in resumen.itertuples():
        values = {
            "extracto": row.Index.date(),
            "depositos": row.depositos,
            "retiros": row.retiros,
            "navcierre": row.navcierre,
            "cierreanterior": anterior,
            "costobase": row.costobase,
            "crecimiento": row.crecimiento,
            "perdidas": row.perdidas,
        }
        anterior = row.navcierre
        resultado.append(values)

    return resultado


def main():
    pla = PlanInversion()
    repo = RepositorioOportunidadesBuySell()
    perf = IPerformance()
    cnv = DiariaCNV()

    cuentas = {
        "BBVA.ARS": cnv.get_sesion_by_vehiculo("BBVA.ARS")["idcuenta"],
        "SANT.ARS": cnv.get_sesion_by_vehiculo("SANT.ARS")["idcuenta"],
    }

    for label, account in cuentas.items():
        print(f"\n{'='*100}")
        print(f"  {label} ({account})")
        print(f"{'='*100}")

        extractos = pla.select_extracto(account=account, extract="select*")
        ext_map = {r["extracto"].strftime("%Y-%m"): r for r in (extractos or [])}

        nuevo = construir_nuevo(account, repo, perf)
        nuevo_map = {r["extracto"].strftime("%Y-%m"): r for r in nuevo}

        meses = sorted(set(list(ext_map.keys()) + list(nuevo_map.keys())))

        print(
            f"  {'Mes':<9} {'Nav_BD':>10} {'Nav_New':>10} {'ΔNav':>10}   {'CB_BD':>10} {'CB_New':>10} {'ΔCB':>10}   {'Dep':>8} {'Ret':>8} {'Crec':>8}"
        )
        print(f"  {'-'*9} {'-'*10} {'-'*10} {'-'*10}   {'-'*10} {'-'*10} {'-'*10}   {'-'*8} {'-'*8} {'-'*8}")

        for mes in meses:
            ext = ext_map.get(mes)
            nvo = nuevo_map.get(mes)

            nav_bd = ext["navcierre"] if ext else None
            cb_bd = ext["costobase"] if ext else None
            nav_new = nvo["navcierre"] if nvo else None
            cb_new = nvo["costobase"] if nvo else None
            dep = nvo["depositos"] if nvo else None
            ret = nvo["retiros"] if nvo else None
            crec = nvo["crecimiento"] if nvo else None

            d_nav = (nav_new - nav_bd) if (nav_bd is not None and nav_new is not None) else None
            d_cb = (cb_new - cb_bd) if (cb_bd is not None and cb_new is not None) else None

            def fmt(v, w=10):
                return f"{v:>{w}.2f}" if v is not None else f"{'---':>{w}}"

            def fmts(v, w=10):
                return f"{v:>+{w}.2f}" if v is not None else f"{'n/a':>{w}}"

            print(
                f"  {mes:<9} {fmt(nav_bd)} {fmt(nav_new)} {fmts(d_nav)}   "
                f"{fmt(cb_bd)} {fmt(cb_new)} {fmts(d_cb)}   "
                f"{fmt(dep, 8)} {fmt(ret, 8)} {fmt(crec, 8)}"
            )


if __name__ == "__main__":
    main()
