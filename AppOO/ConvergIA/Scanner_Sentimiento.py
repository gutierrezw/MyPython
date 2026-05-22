import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import anthropic, logging, json, yf, datetime
from Modulos_Mysql import MarketScreen

_logger = logging.getLogger("TechScanner")
_MODEL = "claude-haiku-4-5-20251001"
_BATCH_SIZE = 10
_MAX_HEADLINES = 5


def _fetch_headlines(symbols: list) -> dict:
    result = {}
    for sym in symbols:
        try:
            news = yf.Ticker(sym).news or []
            titles = []
            for item in news[:_MAX_HEADLINES]:
                content = item.get("content") or item
                title = content.get("title") or item.get("title", "")
                if title:
                    titles.append(title)
            if titles:
                result[sym] = titles
        except Exception as e:
            _logger.warning(f"_fetch_headlines [{sym}]: {e}")
    return result


def _classify_batch(headlines_map: dict, api_key: str) -> dict:
    if not headlines_map or not api_key:
        return {}
    lines = []
    for sym, titles in headlines_map.items():
        lines.append(f"{sym}:")
        for t in titles:
            lines.append(f"  - {t}")
    prompt = (
        "Classify the sentiment of these stock news headlines per symbol.\n"
        'Return ONLY a JSON object: {"SYMBOL": sentiment} '
        "where sentiment is 1 (positive), 0 (neutral), or -1 (negative).\n"
        "Omit symbols with no clear signal.\n\n" + "\n".join(lines)
    )
    try:
        msg = anthropic.Anthropic(api_key=api_key).messages.create(
            model=_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            raw = json.loads(text[start:end])
            return {k: int(v) for k, v in raw.items() if int(v) in (-1, 0, 1)}
    except Exception as e:
        _logger.error(f"_classify_batch: {e}")
    return {}


def scan_sentimiento(account: str, api_key: str = None, fuente: str = "yahoo") -> dict:
    key = api_key or ""
    market = MarketScreen()
    cartera = market.load_cartera_inst(account)
    symbols = [row["symbol"] for row in cartera if row.get("symbol")]

    headlines_map = _fetch_headlines(symbols)
    sentiment = {}

    for i in range(0, len(headlines_map), _BATCH_SIZE):
        batch_keys = list(headlines_map.keys())[i : i + _BATCH_SIZE]
        batch = {k: headlines_map[k] for k in batch_keys}
        result = _classify_batch(batch, key)
        sentiment.update(result)

    if sentiment:
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = [(sym, fecha_hora, val, len(headlines_map.get(sym, [])), fuente) for sym, val in sentiment.items()]
        market.bulk_save_sentiment(records)

    _logger.warning(
        f"scan_sentimiento: {len(symbols)} símbolos, {len(headlines_map)} con noticias, "
        f"{len(sentiment)} clasificados"
    )
    return {"symbols": len(symbols), "with_news": len(headlines_map), "classified": len(sentiment)}
