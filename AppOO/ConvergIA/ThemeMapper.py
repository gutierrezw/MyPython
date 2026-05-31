from Modulos_python import logging
from Modulos_Mysql import MarketScreen

_logger = logging.getLogger("Sentimiento")

_PATRON_VOTO = {
    "acumulacion": 1,
    "inflexion": 1,
    "neutro": 0,
    "distribucion": -1,
}


def load_sentiment(account: str) -> dict:
    """Retorna {symbol: sentimiento} con la lectura más reciente de BD."""
    return MarketScreen().load_latest_sentiment(account)


def load_analysis(account: str) -> dict:
    """Retorna {symbol: {interpretacion, patron}} con el análisis de hoy de BD."""
    return MarketScreen().load_sentiment_analysis(account)


def voto_tech_alignment(symbol: str, sentiment: dict, analysis: dict = None) -> int:
    """Voto −1/0/+1 combinando sentimiento reciente y patrón diario.
    Si hay análisis disponible, el patrón tiene prioridad sobre la lectura puntual."""
    if analysis and symbol in analysis:
        return _PATRON_VOTO.get(analysis[symbol].get("patron", "neutro"), 0)
    return sentiment.get(symbol, 0)
