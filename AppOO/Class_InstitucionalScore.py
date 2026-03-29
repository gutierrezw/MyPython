import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppValuations"))

from Modulos_python import (
    yf,
    logging,
    math,
    requests,
    time,
)
from Modulos_Mysql import MarketScreen


_logger = logging.getLogger("InstitucionalScore")
_EDGAR_HEADERS = {"User-Agent": "InversionesWildaga Research Bot (gutierrez.madrid.wilmer@example.com)"}
_EDGAR_IDX_URLS = [
    "https://www.sec.gov/Archives/edgar/full-index/2026/QTR1/company.idx",
    "https://www.sec.gov/Archives/edgar/full-index/2025/QTR4/company.idx",
]


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

            analyst_rec   = info.get("recommendationKey")
            analyst_mean  = _safe_float(info.get("recommendationMean"))
            analyst_count = info.get("numberOfAnalystOpinions")

            return {
                "inst_ownership_pct": inst_pct,
                "insider_ownership_pct": insider_pct,
                "inst_top_holder": top_holder[:120] if top_holder else None,
                "inst_top_holder_shares": top_shares,
                "inst_funds": holders_count,
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
    Enriquece tabla Market con señales de ownership vía yfinance.
    Procesa todos los símbolos activos de market (excluye categoría T).
    Solo actualiza market — el descubrimiento de fondos lo hace sync_edgar_funds.
    """
    inst = InstitucionalScore()
    all_symbols = inst.market.load_symbols(account)
    symbols = list(all_symbols.keys())
    updated = 0

    for symbol in symbols:
        if all_symbols.get(symbol) in ("T", "X") or "-" in symbol:
            continue
        raw = inst._fetch_ownership(symbol)
        if not raw:
            continue

        inst_pct = raw.get("inst_ownership_pct")
        score = round(inst_pct, 4) if inst_pct is not None else None

        campos = [
            "inst_ownership_pct", "insider_ownership_pct", "inst_top_holder",
            "inst_top_holder_shares", "inst_score", "inst_funds",
            "analyst_rec", "analyst_mean", "analyst_count",
        ]
        valores = [
            inst_pct, raw.get("insider_ownership_pct"), raw.get("inst_top_holder"),
            raw.get("inst_top_holder_shares"), score, raw.get("inst_funds"),
            raw.get("analyst_rec"), raw.get("analyst_mean"), raw.get("analyst_count"),
        ]
        ok = inst.market.update(upd=campos, val=valores, symbol=symbol, account=account)
        if ok:
            updated += 1

    return {"symbols_processed": len(symbols), "updated": updated}


def _parse_edgar_13f_funds() -> list:
    """Descarga company.idx de EDGAR y retorna lista de (fund_name, cik)
    para todos los filers 13F-HR. Un solo download (~5MB)."""
    seen_ciks = set()
    funds = []
    for url in _EDGAR_IDX_URLS:
        try:
            r = requests.get(url, headers=_EDGAR_HEADERS, timeout=60)
            if not r.ok:
                continue
            for line in r.text.splitlines():
                if "13F-HR" not in line:
                    continue
                idx = line.find("13F-HR")
                if idx < 2:
                    continue
                company_name = line[:idx].strip()
                rest = line[idx + len("13F-HR"):].strip().split()
                if not rest:
                    continue
                cik = rest[0].strip().zfill(10)
                if not cik.isdigit() or not company_name or cik in seen_ciks:
                    continue
                seen_ciks.add(cik)
                funds.append((company_name[:200], cik))
            _logger.warning(f"_parse_edgar_13f_funds: {len(funds)} filers 13F-HR desde {url}")
        except Exception as e:
            _logger.warning(f"_parse_edgar_13f_funds [{url}]: {e}")
    return funds


def sync_edgar_funds() -> dict:
    """Carga todos los filers 13F-HR de EDGAR en la tabla funds.
    INSERT IGNORE — no pisa registros existentes.
    Fuente autoritativa de CIK y nombre oficial de cada fondo."""
    inst = InstitucionalScore()
    _logger.warning("sync_edgar_funds: descargando índice EDGAR...")
    funds = _parse_edgar_13f_funds()
    if not funds:
        _logger.warning("sync_edgar_funds: índice vacío, abortando")
        return {"total": 0, "inserted": 0}
    _logger.warning(f"sync_edgar_funds: {len(funds)} filers encontrados, insertando en BD...")
    inserted = inst.market.bulk_insert_edgar_funds(funds)
    _logger.warning(f"sync_edgar_funds: {inserted} nuevos fondos insertados")
    return {"total": len(funds), "inserted": inserted}


def sync_13f_scores(account: str) -> dict:
    """
    Recalcula inst_score blendando fh_ownership_pct propio (40%)
    con fh_count 13F (40%) y fh_buy_ratio (20%) y actualiza market.

    fh_ownership_pct = fh_total_shares / floatShares  (o sharesOutstanding si no hay float)
    Fuente 100% propia — no depende de inst_ownership_pct de Yahoo.
    """
    inst = InstitucionalScore()
    fh_stats = inst.market.load_fund_holdings_stats()
    inst_fields = inst.market.load_market_inst_fields(account)
    updated, skipped = 0, 0

    for symbol, mkt in inst_fields.items():
        stats = fh_stats.get(symbol, {})
        fh_count        = stats.get("fh_count", 0)
        fh_total_value  = stats.get("fh_total_value")
        fh_buy_ratio    = stats.get("fh_buy_ratio", 0.0)
        fh_total_shares = stats.get("fh_total_shares", 0)

        float_shares = mkt.get("floatShares") or mkt.get("sharesOutstanding")
        fh_ownership_pct = (
            round(fh_total_shares / float_shares, 4)
            if float_shares and fh_total_shares
            else None
        )

        has_ownership = fh_ownership_pct is not None
        has_13f = fh_count > 0

        if not has_ownership and not has_13f:
            skipped += 1
            continue

        score = round(
            (fh_ownership_pct or 0.0) * 0.40
            + math.log(max(fh_count, 1)) * 0.40
            + fh_buy_ratio * 0.20,
            4,
        )
        fh_sell_ratio      = stats.get("fh_sell_ratio")
        fh_call_shares     = stats.get("fh_call_shares")
        fh_put_shares      = stats.get("fh_put_shares")
        new_entrants       = stats.get("new_entrants")
        full_exits         = stats.get("full_exits")
        delta_call_shares  = stats.get("delta_call_shares")
        delta_put_shares   = stats.get("delta_put_shares")
        ok = inst.market.update(
            upd=["inst_score", "fh_count", "fh_total_value", "fh_buy_ratio", "fh_sell_ratio",
                 "fh_call_shares", "fh_put_shares", "new_entrants", "full_exits",
                 "delta_call_shares", "delta_put_shares", "inst_ownership_pct"],
            val=[score, fh_count if fh_count else None, fh_total_value,
                 fh_buy_ratio if fh_buy_ratio else None,
                 fh_sell_ratio if fh_sell_ratio else None,
                 fh_call_shares, fh_put_shares,
                 new_entrants if new_entrants else None,
                 full_exits if full_exits else None,
                 delta_call_shares, delta_put_shares,
                 fh_ownership_pct],
            symbol=symbol,
            account=account,
        )
        if ok:
            updated += 1

    return {"symbols": len(inst_fields), "updated": updated, "skipped": skipped}
