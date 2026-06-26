# Yahoo Finance REST Loader (Sin `yfinance`)

Este documento describe cómo construir un **loader de mercado completo
(\~5000 empresas en \~30s)** usando directamente la **API REST interna
de Yahoo Finance**.

Objetivo: - Descargar miles de empresas rápidamente - Obtener precios +
fundamentales - Mapear a una tabla `Market` - Evitar la lentitud de
`yfinance.Ticker.info`

------------------------------------------------------------------------

# Arquitectura

Lista de tickers → Batch de 250 símbolos → Requests paralelos (quote
API) → Normalizador de atributos → Base de datos (Market)

5000 empresas ≈ 20 requests

Con paralelismo → **20‑30 segundos**.

------------------------------------------------------------------------

# Endpoint 1 --- Quote (precio y métricas rápidas)

https://query1.finance.yahoo.com/v7/finance/quote

Ejemplo:

https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL,MSFT,NVDA

Campos importantes:

symbol → ticker\
shortName → shortName\
regularMarketPrice → lastPrice\
regularMarketPreviousClose → previous_close\
regularMarketOpen → open\
regularMarketVolume → volume\
marketCap → marketCap\
currency → currency\
averageDailyVolume3Month → averageVolume\
fiftyTwoWeekHigh → fiftyTwoWeekHigh\
fiftyTwoWeekLow → fiftyTwoWeekLow\
trailingPE → trailingPE\
forwardPE → forwardPE\
epsTrailingTwelveMonths → trailingEps\
beta → beta

------------------------------------------------------------------------

# Endpoint 2 --- Fundamentals

https://query2.finance.yahoo.com/v10/finance/quoteSummary/{TICKER}

Modules:

price,summaryDetail,defaultKeyStatistics,financialData,assetProfile

Ejemplo:

https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=price,summaryDetail,defaultKeyStatistics,financialData,assetProfile

------------------------------------------------------------------------

# Python Loader (alta velocidad)

``` python
import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

def fetch_batch(symbols):

    params = {"symbols": ",".join(symbols)}

    r = requests.get(BASE_URL, params=params, timeout=10)

    data = r.json()["quoteResponse"]["result"]

    results = []

    for s in data:

        results.append({
            "symbol": s.get("symbol"),
            "shortName": s.get("shortName"),
            "lastPrice": s.get("regularMarketPrice"),
            "previous_close": s.get("regularMarketPreviousClose"),
            "open": s.get("regularMarketOpen"),
            "volume": s.get("regularMarketVolume"),
            "marketCap": s.get("marketCap"),
            "currency": s.get("currency"),
            "fiftyTwoWeekHigh": s.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": s.get("fiftyTwoWeekLow"),
            "averageVolume": s.get("averageDailyVolume3Month"),
            "trailingPE": s.get("trailingPE"),
            "forwardPE": s.get("forwardPE"),
            "beta": s.get("beta"),
            "trailingEps": s.get("epsTrailingTwelveMonths"),
        })

    return results


def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


def load_market(tickers):

    batches = list(chunk(tickers, 250))

    all_data = []

    with ThreadPoolExecutor(max_workers=10) as ex:

        results = ex.map(fetch_batch, batches)

        for r in results:
            all_data.extend(r)

    return all_data
```

------------------------------------------------------------------------

# Estrategia recomendada (screener)

1)  Descargar mercado completo con quote API\
2)  Aplicar filtros iniciales\
3)  Pedir fundamentales solo a empresas filtradas

Esto reduce **95% del tráfico**.

------------------------------------------------------------------------

# Rendimiento esperado

yfinance tradicional → 20‑40 min\
REST paralela → 20‑30 s

------------------------------------------------------------------------

Fin del documento
