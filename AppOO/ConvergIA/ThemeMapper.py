from Modulos_python import logging
from Modulos_Mysql import MarketScreen

_logger = logging.getLogger("Sentimiento")


def load_sentiment(account: str) -> dict:
    """Retorna {symbol: sentimiento} con la lectura más reciente de BD."""
    return MarketScreen().load_latest_sentiment(account)


def load_analysis(account: str) -> dict:
    """Retorna {symbol: {interpretacion, patron}} con el análisis de hoy de BD."""
    return MarketScreen().load_sentiment_analysis(account)


def voto_sentimiento(symbol: str, sentiment: dict, analysis: dict = None) -> int:
    """Voto −1/0/+1 de sentimiento general de noticias.

    Reglas por patrón:
      acumulacion  → +1 siempre
      distribucion → −1 siempre
      neutro       →  0 siempre
      inflexion    → +1 si sentimiento >= 0, 0 si sentimiento < 0 (abstención, no penaliza)
      sin datos    →  None (excluido del denominador de Consenso)
    """
    if not analysis and not sentiment:
        return None
    if analysis and symbol in analysis:
        patron = analysis[symbol].get("patron", "neutro")
        sent = sentiment.get(symbol, 0)
        if patron == "acumulacion":
            return 1
        if patron == "distribucion":
            return -1
        if patron == "neutro":
            return 0
        if patron == "inflexion":
            return 1 if sent >= 0 else 0
        return 0
    val = sentiment.get(symbol)
    return val if val is not None else None


# alias de compatibilidad — Class_Screener usa este nombre
voto_tech_alignment = voto_sentimiento
