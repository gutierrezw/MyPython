import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import anthropic, logging, json, date
from Modulos_Mysql import MarketScreen

_logger = logging.getLogger("Sentimiento")
_MODEL = "claude-haiku-4-5-20251001"
_DIAS_HISTORIAL = 7
_PATRONES_VALIDOS = {"acumulacion", "distribucion", "neutro", "inflexion"}


def _build_prompt(symbol: str, historial: list) -> str:
    lines = [
        f"{r['fecha_hora'].strftime('%Y-%m-%d %H:%M')}  {r['sentimiento']:+d}  ({r['headlines_count']} headlines)"
        for r in historial
    ]
    return (
        f"Analyze the sentiment history for stock {symbol} over the last {_DIAS_HISTORIAL} days:\n"
        + "\n".join(lines)
        + "\n\nRespond with a JSON object with two keys:\n"
        '  "patron": one of ["acumulacion", "distribucion", "neutro", "inflexion"]\n'
        '  "interpretacion": one sentence in Spanish explaining the pattern and its implication.\n'
        "acumulacion = sustained positive signal. distribucion = sustained negative. "
        "inflexion = clear change of direction. neutro = no clear signal.\n"
        "Return ONLY the JSON object."
    )


def interpretar_sentimiento(account: str, api_key: str = None) -> dict:
    """Lee historial de sentimiento de cartera y genera interpretación diaria con Claude Haiku.
    Persiste en market_sentiment_analysis. Retorna {symbol: patron}."""
    key = api_key or ""
    if not key:
        return {}

    market = MarketScreen()
    cartera = market.load_cartera_inst(account)
    symbols = [row["symbol"] for row in cartera if row.get("symbol")]
    hoy = date.today()
    resultados = {}

    for sym in symbols:
        historial = market.load_sentiment_history(sym, days=_DIAS_HISTORIAL)
        if len(historial) < 2:
            continue
        try:
            prompt = _build_prompt(sym, historial)
            msg = anthropic.Anthropic(api_key=key).messages.create(
                model=_MODEL,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                patron = data.get("patron", "neutro")
                if patron not in _PATRONES_VALIDOS:
                    patron = "neutro"
                interpretacion = data.get("interpretacion", "")
                market.save_sentiment_analysis(sym, hoy, interpretacion, patron)
                resultados[sym] = patron
        except Exception as e:
            _logger.error(f"interpretar_sentimiento [{sym}]: {e}")

    _logger.warning(f"interpretar_sentimiento: {len(resultados)}/{len(symbols)} interpretados")
    return resultados
