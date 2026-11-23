"""
Valoración de acciones: el único lugar que decide "barata o cara" y los 5 ejes del radar.

Funciones puras, sin BD: reciben la fila de `market` como dict y los pares del universo ya agrupados.
Diseño y motivos en Doc/plan-valoracion.md (§ 2, § 2.1 y § 3).
"""

from Modulos_python import bisect, datetime, json, math, pd


BANDA_VAL = 0.10
MIN_PARES = 10
MIN_ANIOS_DIVIDENDO = 3
PAYOUT_SANO = 0.6
ANIOS_CONTINUIDAD = 5
COHERENCIA_DIVIDENDO = (0.5, 2.0)
VENTANA_DIVIDENDO_DIAS = 350
DIVIDENDO_VIGENTE_DIAS = 400
SECTORES_SIN_PAYOUT = ("Real Estate",)
INDUSTRIAS_SIN_PAYOUT = ("Asset Management", "Oil & Gas Midstream")

_METRICAS = (
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "revenueGrowth",
    "returnOnEquity",
    "returnOnAssets",
    "operatingMargins",
    "deuda_cap",
    "fcf_cap",
    "yield",
)


def valoracion(row, pares=None):
    """Decide si la acción está barata o cara contra su referencia. Primer método que aplica:

    1. `dividendo`: tiene >= 3 años completos de traza → yield de 12 meses contra la media de esos años.
    2. `pb_industria`: banco o aseguradora → P/B contra la mediana de su industria (o sector).
    3. `pe_forward` / `pe_trailing`: P/E contra la mediana de su sector en la misma base, nunca mezcladas. Forward
       si Yahoo lo da; trailing si no hay forward. Un forward <= 0 (pérdida esperada) se abstiene.

    Si a un método le faltan pares (< MIN_PARES) se pasa al siguiente. Sin método, el voto se abstiene.
    `categoria` es el signo de la comparación de dividendo, sin banda; 'N' si la traza dice que no paga; None = el
    llamador conserva la vigente.
    `trampa`: el dividendo actual no lo cubre ni la ganancia esperada ni el flujo de caja → el voto no pasa de 0.
    `cobertura` es la mejor de esas pruebas (la parte del dividendo que se lleva). `motivos` explica por qué la
    valoración se abstuvo o quedó limitada.
    """
    res = {
        "metodo": None,
        "desvio": None,
        "voto": None,
        "categoria": None,
        "media": None,
        "banda_alta": None,
        "banda_baja": None,
        "trampa": False,
        "cobertura": None,
        "motivos": [],
    }
    sector = row.get("sector") or ""
    industria = row.get("industry") or ""
    trailing = _num(row.get("trailingAnnualDividendRate"))
    tasa = _num(row.get("dividendRate"))
    precio = _num(row.get("lastPrice"))
    serie = _leer_traza(row.get("trazaDividends"))
    if _paga_dividendo(serie, tasa) is False:
        res["categoria"] = "N"

    if serie and len(serie) - 1 >= MIN_ANIOS_DIVIDENDO:
        div12 = serie[-1][0] * serie[-1][2] if serie[-1][0] else None
        media = sum(r[2] for r in serie[:-1]) / (len(serie) - 1)
        if div12 and not _dividendo_coherente(div12, tasa, serie[-2][1]):
            res["motivos"].append("dividendo incoherente")
        elif div12 and media > 0:
            yfwd = div12 / precio if precio and precio > 0 else serie[-1][2]
            if yfwd > 0:
                res.update(
                    metodo="dividendo",
                    desvio=(yfwd - media) / media,
                    categoria="I" if yfwd > media else "S",
                    media=media,
                    banda_alta=media * (1 + BANDA_VAL),
                    banda_baja=media * (1 - BANDA_VAL),
                )

    if res["metodo"] is None and pares:
        pb = _num(row.get("priceToBook"))
        es_banco = sector == "Financial Services" and (
            industria.startswith("Banks") or industria.startswith("Insurance -")
        )
        if es_banco and pb and pb > 0:
            med = _mediana_grupo(pares, "priceToBook", sector, industria, ("industry", "sector"))
            if med:
                res.update(metodo="pb_industria", desvio=(med - pb) / med, media=med)
        if res["metodo"] is None:
            fpe = _num(row.get("forwardPE"))
            if fpe is not None and fpe <= 0:
                res["motivos"].append("pérdida esperada")
            else:
                for metodo, base in (("pe_forward", "forwardPE"), ("pe_trailing", "trailingPE")):
                    pe = _num(row.get(base))
                    med = _mediana_grupo(pares, base, sector, industria, ("sector",)) if pe and pe > 0 else None
                    if med:
                        res.update(metodo=metodo, desvio=(med - pe) / med, media=med)
                        break

    div = tasa if tasa is not None else (trailing if _misma_moneda(row) else None)
    if div and div > 0 and not _payout_exento(sector, industria):
        pruebas = _pruebas_cobertura(row, div, precio)
        if pruebas:
            res["cobertura"] = min(pruebas)
            res["trampa"] = res["cobertura"] > 1
            if res["trampa"]:
                res["motivos"].append("trampa")
            elif (_num(row.get("payoutRatio")) or 0) > 1:
                res["motivos"].append("payout cubierto")

    if res["desvio"] is not None:
        d = res["desvio"]
        res["voto"] = 1 if d > BANDA_VAL else (-1 if d < -BANDA_VAL else 0)
        if res["trampa"]:
            res["voto"] = min(res["voto"], 0)
    return res


def serie_rendimiento_anual(m_datos, precio):
    """Serie anual del rendimiento por dividendo: es lo que se guarda en `market.trazaDividends`.

    El primer año se descarta si es parcial (menos pagos que la mediana de los años completos que le siguen).
    La última fila es siempre el año en curso: lo pagado hasta hoy y el rendimiento de 12 meses `div12m / precio`,
    los dos del historial — el trailing de Yahoo viene en la moneda del balance en emisores extranjeros y por
    acción ordinaria en algunos ADR. Los 12 meses se anclan al último pago para no contar 13 pagos mensuales ni
    5 trimestrales; si el último pago tiene más de DIVIDENDO_VIGENTE_DIAS, el dividendo ya no está vigente (0).
    Si este año todavía no pagó, la fila se agrega en vez de pisar el año anterior. Los años sin pago entre el último
    pago y el año anterior entran con 0: sin ellos quien dejó de pagar en 2023 tendría la traza 2019..2023 y 2026.
    """
    columnas = ["Close", "Dividends", "Rendimiento"]
    m = m_datos[m_datos["Dividends"] != 0].copy()
    if m.empty:
        return pd.DataFrame(columns=columnas)
    if m.index.tz is not None:
        m.index = m.index.tz_localize(None)
    m["Rendimiento"] = m["Dividends"] / m["Close"]
    anual = m.resample("YE")
    y_datos = pd.DataFrame(
        {
            "Close": anual["Close"].mean(),
            "Dividends": anual["Dividends"].sum(),
            "Rendimiento": anual["Rendimiento"].sum(),
        }
    )
    pagos = anual["Dividends"].count()

    hoy = pd.Timestamp(datetime.now())
    previos = [i for i in y_datos.index if i.year < hoy.year]
    if len(previos) > MIN_ANIOS_DIVIDENDO and pagos.loc[previos[0]] < _mediana(sorted(pagos.loc[previos[1:]])):
        y_datos = y_datos.drop(previos[0])
    anios = pd.date_range(y_datos.index[0], pd.Timestamp(year=hoy.year - 1, month=12, day=31), freq="YE")
    y_datos = y_datos.reindex(y_datos.index.union(anios))
    y_datos[["Dividends", "Rendimiento"]] = y_datos[["Dividends", "Rendimiento"]].fillna(0.0)

    ultimo = m.index[-1]
    div12 = 0.0
    if ultimo > hoy - pd.Timedelta(days=DIVIDENDO_VIGENTE_DIAS):
        div12 = float(m.loc[m.index > ultimo - pd.Timedelta(days=VENTANA_DIVIDENDO_DIAS), "Dividends"].sum())
    precio = _num(precio) or 0.0
    fin = pd.Timestamp(year=hoy.year, month=12, day=31)
    pagado = float(y_datos.loc[fin, "Dividends"]) if fin in y_datos.index else 0.0
    rend = div12 / precio if precio > 0 else float("nan")
    y_datos.loc[fin, columnas] = [precio if precio > 0 else float("nan"), pagado, rend]
    return y_datos.sort_index()


def valoracion_historial(info, datos):
    """Serie anual y valoración desde el historial de yfinance, al precio del último cierre. Es el único armado de la
    categoría I/S/N (cartera y ex-cartera) y de la banda de los dos gráficos de rendimiento por dividendo."""
    precio = float(datos["Close"].iloc[-1]) if not datos.empty else None
    y_datos = serie_rendimiento_anual(datos, precio)
    return y_datos, valoracion(dict(info, lastPrice=precio, trazaDividends=y_datos))


def dividendo_maduro(traza):
    """True si paga dividendo hace al menos MIN_ANIOS_DIVIDENDO años completos y sigue pagando (`_sigue_pagando`);
    None sin traza."""
    filas = _leer_traza(traza)
    if not filas:
        return None
    if len(filas) - 1 < MIN_ANIOS_DIVIDENDO:
        return False
    return _sigue_pagando(filas)


def pares_por_grupo(filas):
    """{metrica: {(nivel, nombre): valores ordenados}} por sector e industria. Se arma una vez por pasada."""
    pares = {m: {} for m in _METRICAS}
    for row in filas:
        grupos = [(n, row.get(n)) for n in ("sector", "industry") if row.get(n)]
        for metrica, valor in _metricas(row).items():
            if valor is None:
                continue
            for grupo in grupos:
                pares[metrica].setdefault(grupo, []).append(valor)
    for por_grupo in pares.values():
        for lista in por_grupo.values():
            lista.sort()
    return pares


def ejes_radar(row, val, pares):
    """Los 5 ejes de 0 a 1. Un componente sin dato no entra; un eje sin componentes queda None (no 0)."""
    def pct(metrica):
        if met.get(metrica) is None:
            return None
        return _percentil(pares, metrica, met[metrica], sector, industria, niveles)

    sector = row.get("sector") or ""
    industria = row.get("industry") or ""
    niveles = ("industry", "sector") if sector == "Financial Services" else ("sector",)
    met = _metricas(row)
    val = val or valoracion(row, pares)
    deuda = pct("deuda_cap")
    return {
        "valor": None if val["desvio"] is None else min(1.0, max(0.0, 0.5 + val["desvio"])),
        "futuro": pct("revenueGrowth"),
        "pasado": _promedio([pct("returnOnEquity"), pct("returnOnAssets"), pct("operatingMargins")]),
        "salud": _promedio([None if deuda is None else 1 - deuda, pct("fcf_cap")]),
        "dividendo": _eje_dividendo(row, pct("yield"), val["cobertura"]),
    }


def _eje_dividendo(row, nivel, cobertura):
    serie = _leer_traza(row.get("trazaDividends"))
    paga = _paga_dividendo(serie, _num(row.get("dividendRate")))
    if paga is None:
        return None
    if not paga:
        return 0.0
    sostenibilidad = None
    if cobertura is not None:
        sostenibilidad = max(0.0, min(1.0, (1 - cobertura) / (1 - PAYOUT_SANO)))
    continuidad = None
    if len(serie) > 1:
        anios = 0
        for r in reversed(serie[:-1]):
            if r[1] <= 0:
                break
            anios += 1
        continuidad = min(1.0, anios / ANIOS_CONTINUIDAD)
    return _promedio([nivel, sostenibilidad, continuidad])


def _metricas(row):
    def cociente(num, den):
        n, d = _num(row.get(num)), _num(row.get(den))
        return n / d if n is not None and d and d > 0 else None

    def positivo(campo):
        v = _num(row.get(campo))
        return v if v and v > 0 else None

    misma = _misma_moneda(row)
    rinde = cociente("dividendRate", "lastPrice")
    return {
        "trailingPE": positivo("trailingPE"),
        "forwardPE": positivo("forwardPE"),
        "priceToBook": positivo("priceToBook"),
        "revenueGrowth": _num(row.get("revenueGrowth")),
        "returnOnEquity": _num(row.get("returnOnEquity")),
        "returnOnAssets": _num(row.get("returnOnAssets")),
        "operatingMargins": _num(row.get("operatingMargins")),
        "deuda_cap": cociente("totalDebt", "marketCap") if misma else None,
        "fcf_cap": cociente("freeCashflow", "marketCap") if misma else None,
        "yield": rinde if rinde and rinde > 0 else None,
    }


def _dividendo_coherente(div12, tasa, anterior):
    """False si el dividendo de 12 meses no se parece ni al actual (`dividendRate`) ni al del año anterior de la
    traza. Una traza vieja guarda en la última fila el trailing de Yahoo: moneda local o acción ordinaria."""
    lo, hi = COHERENCIA_DIVIDENDO
    cocientes = [div12 / ref for ref in (tasa, anterior) if ref and ref > 0]
    return not cocientes or any(lo <= q <= hi for q in cocientes)


def _sigue_pagando(filas):
    """Dividendo de 12 meses, o pagos este año o el anterior: a varios ADR japoneses y coreanos (HMC, MUFG, KT) el
    historial de yfinance no les trae los pagos del año en curso."""
    return bool(filas) and (filas[-1][2] > 0 or filas[-1][1] > 0 or (len(filas) > 1 and filas[-2][1] > 0))


def _paga_dividendo(filas, tasa):
    """True paga, False no paga, None sin dato o si el historial y `dividendRate` se contradicen. El trailing de Yahoo
    no decide: viene en 0 para empresas que pagan (BDX, ERIC)."""
    if filas is None:
        return None
    if _sigue_pagando(filas):
        return True
    return None if tasa and tasa > 0 else False


def _pruebas_cobertura(row, div, precio):
    """Parte del dividendo que se lleva la ganancia esperada y el flujo de caja (> 1 = no lo cubre). Un denominador
    <= 0 no cubre nada. El FCF está en la moneda del balance: solo se compara si coincide con la de cotización."""
    pruebas = []
    eps = _num(row.get("forwardEps"))
    if eps is not None:
        pruebas.append(div / eps if eps > 0 else math.inf)
    fcf = _num(row.get("freeCashflow"))
    cap = _num(row.get("marketCap"))
    if fcf is not None and cap and cap > 0 and precio and precio > 0 and _misma_moneda(row):
        pruebas.append(div / precio * cap / fcf if fcf > 0 else math.inf)
    return pruebas


def _misma_moneda(row):
    balance, cotiza = row.get("financialCurrency"), row.get("currency")
    return not balance or not cotiza or balance == cotiza


def _mediana_grupo(pares, metrica, sector, industria, niveles):
    for nivel in niveles:
        lista = pares.get(metrica, {}).get((nivel, sector if nivel == "sector" else industria))
        if lista and len(lista) >= MIN_PARES:
            return _mediana(lista)
    return None


def _percentil(pares, metrica, valor, sector, industria, niveles):
    for nivel in niveles:
        lista = pares.get(metrica, {}).get((nivel, sector if nivel == "sector" else industria))
        if lista and len(lista) >= MIN_PARES:
            lo = bisect.bisect_left(lista, valor)
            hi = bisect.bisect_right(lista, valor)
            return (lo + (hi - lo) / 2) / len(lista)
    return None


def _payout_exento(sector, industria):
    return sector in SECTORES_SIN_PAYOUT or industria in INDUSTRIAS_SIN_PAYOUT


def _leer_traza(traza):
    """Filas [Close, Dividends, Rendimiento] en orden cronológico; la última es el año en curso."""
    if traza is None:
        return None
    try:
        if isinstance(traza, pd.DataFrame):
            filas = traza.sort_index()[["Close", "Dividends", "Rendimiento"]].values.tolist()
        else:
            if isinstance(traza, (bytes, bytearray)):
                traza = traza.decode("utf-8")
            d = json.loads(traza)
            pos = [d["columns"].index(c) for c in ("Close", "Dividends", "Rendimiento")]
            filas = [[f[p] for p in pos] for _, f in sorted(zip(d["index"], d["data"]), key=lambda x: x[0])]
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    return [[_num(f[0]), _num(f[1]) or 0.0, _num(f[2]) or 0.0] for f in filas]


def _mediana(valores):
    n = len(valores)
    if not n:
        return None
    return valores[n // 2] if n % 2 else (valores[n // 2 - 1] + valores[n // 2]) / 2


def _promedio(valores):
    vals = [v for v in valores if v is not None]
    return sum(vals) / len(vals) if vals else None


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None
