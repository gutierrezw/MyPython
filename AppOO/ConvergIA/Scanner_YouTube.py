from Modulos_python import feedparser, anthropic, logging, json, re, yf, time, os
from Modulos_Mysql import MarketScreen
from Modulos_Utilitarios import read_json_tmp, write_json_tmp

_logger = logging.getLogger("YouTubeScanner")
_MODEL = "claude-haiku-4-5-20251001"
_CANDIDATES_FILE = "youtube_candidates.json"
_MAX_VIDEOS = 10

_CANALES_FALLBACK = {
    "DanyPerezTrader": "UCDhxeQwPPUdIdwu0W9ud_Jg",
    "Invierteygana": "UC29Uya07F0sVo6j7kKDXJnQ",
    "MapadeMercados": "UClAt-9bKF4jyNMU9WmiNpKA",
    "elinformek": "UCJQQVLyM6wtPleV4wFBK06g",
    "Renta4BancoESP": "UCLITO_RoijmgfYWi_kmiONA",
    "ElClubDeInversion": "UCtWEGc5ws4HvMvCW-hVY-Gw",
}

_RSS_BASE = "https://www.youtube.com/feeds/videos.xml?channel_id="

_FINANCE_KEYWORDS = re.compile(
    r"\b(accion|acción|bolsa|mercado|inversion|inversión|dividendo|análisis|analisis|"
    r"stock|ticker|comprar|vender|portafolio|cartera|nasdaq|sp500|s&p|nyse|etf|fondo|"
    r"crypto|bitcoin|btc|eth|trading|trader|fondos|rentabilidad|valoracion|valoración|"
    r"recomend|sector|empresa)\b",
    re.IGNORECASE,
)


def _load_canales() -> dict:
    """Carga canales activos desde BD. Fallback al dict hardcodeado si falla."""
    try:
        rows = MarketScreen().load_youtube_canales()
        if rows:
            return {canal: data["channel_id"] for canal, data in rows.items()}
    except Exception as e:
        _logger.warning(f"_load_canales: BD no disponible, usando fallback — {e}")
    return _CANALES_FALLBACK


def _fetch_videos(canales: dict, seen_ids: set) -> tuple:
    videos = []
    all_ids = set()
    for canal, channel_id in canales.items():
        url = f"{_RSS_BASE}{channel_id}"
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:_MAX_VIDEOS]:
                video_id = entry.get("id", "")
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                if not title or not video_id:
                    continue
                all_ids.add(video_id)
                if video_id in seen_ids:
                    continue
                videos.append(
                    {"id": video_id, "canal": canal, "channel_id": channel_id, "title": title, "summary": summary[:800]}
                )
        except Exception as e:
            _logger.warning(f"_fetch_videos [{canal}]: {e}")
    return videos, all_ids


def _filter_financial(videos: list) -> list:
    return [v for v in videos if _FINANCE_KEYWORDS.search(v["title"]) or _FINANCE_KEYWORDS.search(v["summary"])]


def _resolve_names(nombres: list) -> tuple:
    """Convierte lista de nombres → ({ticker: confidence}, {ticker: market_cap}, {ticker: company_name}, {ticker: website})."""
    candidates = {}
    market_caps = {}
    company_names = {}
    websites = {}
    for nombre in nombres:
        try:
            quotes = yf.Search(nombre, max_results=1).quotes
            if not quotes:
                continue
            top = quotes[0]
            if top.get("quoteType") != "EQUITY":
                continue
            ticker = top.get("symbol", "").upper()
            if not ticker:
                continue
            candidates[ticker] = 0.90
            market_caps[ticker] = int(top.get("regularMarketCap") or top.get("marketCap") or 0)
            company_names[ticker] = nombre
            try:
                websites[ticker] = yf.Ticker(ticker).info.get("website") or ""
            except Exception:
                websites[ticker] = ""
        except Exception as e:
            _logger.warning(f"_resolve_names [{nombre}]: {e}")
        time.sleep(0.3)
    return candidates, market_caps, company_names, websites


def _classify(videos: list, api_key: str) -> tuple:
    if not videos or not api_key:
        return {}, {}, {}, {}

    lines = []
    for v in videos:
        lines.append(f"[{v['canal']}] {v['title']}")
        if v.get("summary"):
            lines.append(f"  Descripción: {v['summary']}")

    prompt = (
        "You are a financial analyst reading Spanish-language investment YouTube videos.\n"
        "Extract the names of companies that are ANALYZED in these videos (not just mentioned in passing).\n"
        'Return ONLY a JSON array of company names in English: ["Company Name 1", "Company Name 2"].\n'
        "Do NOT include indexes, ETFs, banks mentioned as analysts (Goldman Sachs, JP Morgan), or central banks.\n"
        "If no companies are analyzed, return [].\n\nVideos:\n" + "\n".join(lines)
    )
    try:
        msg = anthropic.Anthropic(api_key=api_key).messages.create(
            model=_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        start, end = text.find("["), text.rfind("]") + 1
        if start >= 0 and end > start:
            nombres = [n for n in json.loads(text[start:end]) if isinstance(n, str)]
            _logger.warning(f"_classify: Claude extrajo {len(nombres)} nombres: {nombres}")
            return _resolve_names(nombres)
    except Exception as e:
        _logger.error(f"_classify: {e}")
    return {}, {}, {}, {}


def _backfill_incomplete(market: MarketScreen, limit: int = 5) -> int:
    """Completa campos nulos en candidatos existentes. Máx `limit` por ejecución para no saturar yfinance."""
    symbols = market.load_youtube_candidatos_incomplete(limit)
    updated = 0
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            market.update_youtube_candidato_fields(
                sym,
                website=info.get("website") or None,
                sector=info.get("sector") or None,
                market_cap=int(info.get("marketCap") or 0) or None,
                company_name=info.get("shortName") or info.get("longName") or None,
                country=info.get("country") or None,
                last_price=float(price) if price else None,
            )
            updated += 1
        except Exception as e:
            _logger.warning(f"_backfill_incomplete [{sym}]: {e}")
        time.sleep(0.5)
    return updated


def _validate(candidates: dict, market_caps: dict, account: str) -> dict:
    try:
        existing = set(MarketScreen().load_symbols(account).keys())
    except Exception as e:
        _logger.warning(f"_validate: BD no disponible, omitiendo filtro existentes — {e}")
        existing = set()
    return {
        ticker: {"confidence": round(conf, 2), "market_cap": market_caps.get(ticker, 0)}
        for ticker, conf in candidates.items()
        if len(ticker) <= 10
    }


def _update_canal_stats(videos_nuevos: list, candidates_raw: dict, validated: dict) -> None:
    """Incrementa detecciones/validados por canal en youtube_canales."""
    try:
        market = MarketScreen()
        detecciones_por_canal: dict = {}
        validados_por_canal: dict = {}
        for v in videos_nuevos:
            cid = v["channel_id"]
            detecciones_por_canal.setdefault(cid, 0)
        for ticker in candidates_raw:
            for v in videos_nuevos:
                if ticker in v["title"] or ticker in v["summary"]:
                    detecciones_por_canal[v["channel_id"]] = detecciones_por_canal.get(v["channel_id"], 0) + 1
                    break
        for ticker in validated:
            for v in videos_nuevos:
                if ticker in v["title"] or ticker in v["summary"]:
                    validados_por_canal[v["channel_id"]] = validados_por_canal.get(v["channel_id"], 0) + 1
                    break
        for channel_id in {v["channel_id"] for v in videos_nuevos}:
            market.update_youtube_canal_stats(
                channel_id,
                detecciones_por_canal.get(channel_id, 0),
                validados_por_canal.get(channel_id, 0),
            )
    except Exception as e:
        _logger.warning(f"_update_canal_stats: {e}")


def scan_youtube(account: str, api_key: str = None) -> dict:
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    canales = _load_canales()
    stored = read_json_tmp(_CANDIDATES_FILE)
    seen_ids = set(stored.get("seen_ids", []))
    existing_candidates = stored.get("candidates", {})

    videos, all_ids = _fetch_videos(canales, seen_ids)
    filtered = _filter_financial(videos)
    candidates_raw, market_caps, company_names, websites = _classify(filtered, key)
    validated = _validate(candidates_raw, market_caps, account)

    market = MarketScreen()
    for ticker, data in validated.items():
        nombre = company_names.get(ticker, ticker).lower()
        canal_origen = next(
            (v["canal"] for v in videos if nombre in v["title"].lower() or nombre in v["summary"].lower()),
            "unknown",
        )
        market.upsert_youtube_candidato(
            ticker,
            data["confidence"],
            data.get("market_cap", 0),
            canal_origen,
            company_names.get(ticker, ""),
            websites.get(ticker, ""),
        )

    rechazados = market.cleanup_youtube_candidatos()
    if rechazados:
        _logger.warning(f"scan_youtube: cleanup — {rechazados} candidatos expirados rechazados")

    _update_canal_stats(videos, candidates_raw, validated)

    # seen_ids = solo lo que está HOY en el RSS (máx 15×canales)
    # IDs viejos que ya salieron del RSS nunca van a volver — no tiene sentido acumularlos
    new_seen = all_ids if (not filtered or key) else seen_ids

    write_json_tmp(
        _CANDIDATES_FILE,
        {
            "seen_ids": list(new_seen),
            "last_scan": {
                "videos_nuevos": len(videos),
                "videos_skip": len(all_ids) - len(videos),
                "filtered": len(filtered),
                "detected_raw": candidates_raw,
            },
        },
    )

    _logger.warning(
        f"scan_youtube: {len(videos)} nuevos / {len(all_ids)-len(videos)} ya vistos, "
        f"{len(filtered)} financieros, {len(candidates_raw)} detectados, {len(validated)} nuevos validados"
    )
    return {
        "videos": len(videos),
        "videos_skip": len(all_ids) - len(videos),
        "filtered": len(filtered),
        "detected": len(candidates_raw),
        "detected_raw": candidates_raw,
        "new_validated": len(validated),
        "validated": validated,
    }


def backfill_youtube_candidatos(limit: int = 5) -> int:
    """Completa campos nulos en candidatos existentes. Sin RSS ni Claude. Máx `limit` por llamada."""
    market = MarketScreen()
    return _backfill_incomplete(market, limit)
