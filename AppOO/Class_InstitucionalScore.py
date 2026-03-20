import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppValuations"))

from Modulos_python import (
    ET,
    yf,
    logging,
    math,
    requests,
    time,
)
from Modulos_Mysql import MarketScreen


_logger = logging.getLogger("InstitucionalScore")
_EDGAR_EFTS_URL  = "https://efts.sec.gov/LATEST/search-index"
_EDGAR_SUBS_URL  = "https://data.sec.gov/submissions/CIK{cik}.json"
_EDGAR_HEADERS   = {"User-Agent": "InversionesWildaga Research Bot (gutierrez.madrid.wilmer@example.com)"}


def _safe_float(val):
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


class InstitucionalScore:
    """
    Enriquece la tabla Market con señales de flujo institucional.
    Fuente: yf.Ticker().institutional_holders + info — no interfiere con CacheHut
    porque institutional_holders no pasa por get_yfinance().
    """

    def __init__(self):
        self.market = MarketScreen()

    def _fetch_ownership(self, symbol) -> dict:
        """Obtiene datos institucionales vía yf.Ticker() directo."""
        time.sleep(0.5)
        try:
            ticker = yf.Ticker(symbol.replace("^", "-"))
            info = ticker.info
            holders = ticker.institutional_holders

            inst_pct = _safe_float(info.get("heldPercentInstitutions"))
            insider_pct = _safe_float(info.get("heldPercentInsiders"))
            raw_count = info.get("institutionsCount")
            holders_df_count = len(holders) if holders is not None and not holders.empty else 0
            holders_count = int(raw_count) if raw_count is not None else holders_df_count
            top_holder = str(holders.iloc[0]["Holder"]) if holders_count > 0 else None
            top_shares = int(holders.iloc[0]["Shares"]) if holders_count > 0 else None
            fund_names = list(holders["Holder"].dropna()) if holders_count > 0 else []
            fund_holders = []
            if holders_count > 0:
                for _, row in holders.iterrows():
                    name = str(row.get("Holder", ""))
                    sh = row.get("Shares")
                    rd = row.get("Date Reported")
                    if name and sh is not None:
                        fund_holders.append((name, int(sh), rd))

            analyst_rec   = info.get("recommendationKey")
            analyst_mean  = _safe_float(info.get("recommendationMean"))
            analyst_count = info.get("numberOfAnalystOpinions")

            return {
                "inst_ownership_pct": inst_pct,
                "insider_ownership_pct": insider_pct,
                "inst_top_holder": top_holder[:120] if top_holder else None,
                "inst_top_holder_shares": top_shares,
                "fund_names": fund_names,
                "fund_holders": fund_holders,
                "analyst_rec": analyst_rec[:20] if analyst_rec else None,
                "analyst_mean": analyst_mean,
                "analyst_count": int(analyst_count) if analyst_count else None,
            }
        except Exception as e:
            _logger.warning(f"_fetch_ownership [{symbol}]: {e}")
            return {}

    def score_company(self, symbol) -> dict:
        """Retorna métricas institucionales + inst_score para un símbolo."""
        data = self._fetch_ownership(symbol)
        if not data:
            return {}
        inst_pct = data.get("inst_ownership_pct")
        score = round(inst_pct, 4) if inst_pct is not None else None
        return {
            "inst_ownership_pct": inst_pct,
            "insider_ownership_pct": data.get("insider_ownership_pct"),
            "inst_top_holder": data.get("inst_top_holder"),
            "inst_top_holder_shares": data.get("inst_top_holder_shares"),
            "inst_score": score,
        }


def sync_institutional(account) -> dict:
    """
    Descubre fondos institucionales y enriquece tabla Market con señales de ownership.
    Procesa TODOS los símbolos activos de market.
    Un único pass por símbolo: fund discovery + inst_* update.
    """
    inst = InstitucionalScore()
    all_symbols = inst.market.load_symbols(account)
    symbols = list(all_symbols.keys())
    fund_freq = {}
    updated = 0

    for symbol in symbols:
        if all_symbols.get(symbol) == "T":
            continue
        raw = inst._fetch_ownership(symbol)
        if not raw:
            continue

        for name in raw.get("fund_names", []):
            fund_freq[name] = fund_freq.get(name, 0) + 1

        inst_pct = raw.get("inst_ownership_pct")
        score = round(inst_pct, 4) if inst_pct is not None else None

        campos = [
            "inst_ownership_pct", "insider_ownership_pct", "inst_top_holder",
            "inst_top_holder_shares", "inst_score", "inst_funds",
            "analyst_rec", "analyst_mean", "analyst_count",
        ]
        valores = [
            inst_pct, raw.get("insider_ownership_pct"), raw.get("inst_top_holder"),
            raw.get("inst_top_holder_shares"), score,
            len(raw.get("fund_holders", [])),
            raw.get("analyst_rec"), raw.get("analyst_mean"), raw.get("analyst_count"),
        ]
        ok = inst.market.update(upd=campos, val=valores, symbol=symbol, account=account)
        if ok:
            updated += 1

        for name, shares, report_date in raw.get("fund_holders", []):
            inst.market.upsert_fund_holding(name, symbol, shares, report_date)

    for fund_name, freq in fund_freq.items():
        inst.market.upsert_fund(fund_name, freq)

    return {
        "symbols_processed": len(symbols),
        "updated": updated,
        "funds_discovered": len(fund_freq),
    }


def _normalize_name(name: str) -> str:
    """Normaliza nombre para comparación: minúsculas, sin puntuación ni stop words."""
    import re as _re
    name = name.lower()
    name = _re.sub(r"[,\.&/\-]", " ", name)
    name = _re.sub(r"\b(inc|llc|lp|ltd|corp|co|the|group|management|advisors?|associates?|fund|capital)\b", "", name)
    return _re.sub(r"\s+", " ", name).strip()


def _names_match(a: str, b: str) -> bool:
    """True si los nombres comparten al menos 2 palabras clave o uno contiene al otro."""
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return True
    wa, wb = set(na.split()), set(nb.split())
    return len(wa & wb) >= 2 or nb in na or na in nb


def _search_edgar_cik(fund_name: str) -> str | None:
    """Busca el CIK correcto en EDGAR para un fondo institucional.
    Estrategia: EFTS entity search para 13F-HR → valida nombre contra submissions API.
    Solo retorna CIK si el nombre de EDGAR coincide con el nombre del fondo."""
    try:
        r = requests.get(
            _EDGAR_EFTS_URL,
            params={"entity": fund_name, "forms": "13F-HR",
                    "dateRange": "custom", "startdt": "2025-01-01"},
            headers=_EDGAR_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
        for hit in hits[:5]:
            ciks = hit.get("_source", {}).get("ciks", [])
            if not ciks:
                continue
            cik = str(ciks[0]).zfill(10)
            # Verificar nombre real del CIK contra el nombre del fondo
            time.sleep(0.1)
            r2 = requests.get(_EDGAR_SUBS_URL.format(cik=cik), headers=_EDGAR_HEADERS, timeout=10)
            if not r2.ok:
                continue
            edgar_name = r2.json().get("name", "")
            if _names_match(fund_name, edgar_name):
                return cik
    except Exception as e:
        _logger.warning(f"_search_edgar_cik [{fund_name}]: {e}")
    return None


def sync_13f_scores(account: str) -> dict:
    """
    Recalcula inst_score blendando yfinance (inst_ownership_pct 40%)
    con señales 13F (fh_count 40%, fh_buy_ratio 20%) y actualiza market.
    """
    inst = InstitucionalScore()
    fh_stats = inst.market.load_fund_holdings_stats()
    inst_fields = inst.market.load_market_inst_fields(account)
    updated, skipped = 0, 0

    for symbol, inst_pct in inst_fields.items():
        stats = fh_stats.get(symbol, {})
        fh_count = stats.get("fh_count", 0)
        fh_total_value = stats.get("fh_total_value")
        fh_buy_ratio = stats.get("fh_buy_ratio", 0.0)

        has_yf = inst_pct is not None
        has_13f = fh_count > 0

        if not has_yf and not has_13f:
            skipped += 1
            continue

        score = round(
            (inst_pct or 0.0) * 0.40
            + math.log(max(fh_count, 1)) * 0.40
            + fh_buy_ratio * 0.20,
            4,
        )
        ok = inst.market.update(
            upd=["inst_score", "fh_count", "fh_total_value"],
            val=[score, fh_count if fh_count else None, fh_total_value],
            symbol=symbol,
            account=account,
        )
        if ok:
            updated += 1

    return {"symbols": len(inst_fields), "updated": updated, "skipped": skipped}


def sync_fund_ciks() -> dict:
    """Busca CIK en EDGAR para todos los fondos sin CIK en tabla funds."""
    inst = InstitucionalScore()
    funds = inst.market.load_funds_without_cik()
    total = len(funds)
    found, failed = 0, 0
    for fund_name in funds:
        time.sleep(1.0)
        cik = _search_edgar_cik(fund_name)
        if cik:
            inst.market.update_fund_cik(fund_name, cik)
            found += 1
        else:
            failed += 1
    return {"total": total, "found": found, "failed": failed}
