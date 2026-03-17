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
_EDGAR_BROWSE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
_EDGAR_HEADERS = {"User-Agent": "InversionesWildaga Research Bot (gutierrez.madrid.wilmer@example.com)"}


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

            return {
                "inst_ownership_pct": inst_pct,
                "insider_ownership_pct": insider_pct,
                "inst_top_holder": top_holder[:120] if top_holder else None,
                "inst_top_holder_shares": top_shares,
                "inst_holders_count": holders_count,
                "fund_names": fund_names,
                "fund_holders": fund_holders,
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
        holders_count = data.get("inst_holders_count", 0)
        score = None
        if inst_pct is not None and holders_count > 0:
            score = round(inst_pct * 0.6 + math.log(max(holders_count, 1)) * 0.4, 4)
        return {
            "inst_ownership_pct": inst_pct,
            "insider_ownership_pct": data.get("insider_ownership_pct"),
            "inst_top_holder": data.get("inst_top_holder"),
            "inst_top_holder_shares": data.get("inst_top_holder_shares"),
            "inst_holders_count": holders_count,
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
    updated, deleted = 0, 0

    for symbol in symbols:
        if all_symbols.get(symbol) in ("T", "N"):
            continue
        raw = inst._fetch_ownership(symbol)
        if not raw:
            inst.market.delete(symbol, account)
            deleted += 1
            continue

        for name in raw.get("fund_names", []):
            fund_freq[name] = fund_freq.get(name, 0) + 1

        inst_pct = raw.get("inst_ownership_pct")
        holders_count = raw.get("inst_holders_count", 0)
        score = None
        if inst_pct is not None and holders_count > 0:
            score = round(inst_pct * 0.6 + math.log(max(holders_count, 1)) * 0.4, 4)

        campos = [
            "inst_ownership_pct", "insider_ownership_pct", "inst_top_holder",
            "inst_top_holder_shares", "inst_holders_count", "inst_score", "inst_funds",
        ]
        valores = [
            inst_pct, raw.get("insider_ownership_pct"), raw.get("inst_top_holder"),
            raw.get("inst_top_holder_shares"), holders_count, score,
            len(raw.get("fund_holders", [])),
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
        "deleted": deleted,
        "funds_discovered": len(fund_freq),
    }


def _cik_from_urn(urn: str) -> str | None:
    """Extrae CIK de los dos formatos URN que devuelve EDGAR.
    - Company: urn:tag:www.sec.gov:cik=0001086364
    - Filing:  urn:tag:sec.gov,2008:accession-number=0001086364-24-008417
    """
    urn_low = urn.lower()
    if "cik=" in urn_low:
        return urn_low.split("cik=")[1].split("&")[0].zfill(10)
    if "accession-number=" in urn_low:
        acc = urn.split("accession-number=")[1]
        return acc.split("-")[0].zfill(10)
    return None


def _search_edgar_cik(fund_name: str) -> str | None:
    """Busca CIK en EDGAR company search (Atom XML) para un fondo institucional (form 13F-HR).
    Intenta con nombre completo → 2 palabras → 1 palabra hasta encontrar resultados.
    Reintenta hasta 3 veces con backoff en caso de 503 o timeout."""
    words = [w.strip(".,;") for w in fund_name.split()]
    seen = []
    for q in [fund_name, " ".join(words[:2]), words[0]]:
        if q not in seen:
            seen.append(q)
    for query in seen:
        params = {"company": query, "CIK": "", "type": "13F-HR", "dateb": "",
                  "owner": "include", "count": "5", "action": "getcompany", "output": "atom"}
        for attempt in range(3):
            if attempt > 0:
                time.sleep(5 * attempt)
            try:
                r = requests.get(_EDGAR_BROWSE_URL, params=params, headers=_EDGAR_HEADERS, timeout=20)
                if r.status_code == 503:
                    continue
                r.raise_for_status()
                root = ET.fromstring(r.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    id_elem = entry.find("atom:id", ns)
                    if id_elem is not None:
                        cik = _cik_from_urn(id_elem.text or "")
                        if cik:
                            return cik
                break
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                _logger.warning(f"_search_edgar_cik [{fund_name}]: {e}")
                return None
    return None


def sync_13f_scores(account: str) -> dict:
    """
    Recalcula inst_score blendando yfinance (inst_ownership_pct, inst_holders_count)
    con señales 13F (fh_count, fh_buy_ratio) y actualiza market.
    Nuevas columnas requeridas en market: fh_count INT, fh_total_value BIGINT.
    """
    inst = InstitucionalScore()
    fh_stats = inst.market.load_fund_holdings_stats()
    inst_fields = inst.market.load_market_inst_fields(account)
    updated, skipped = 0, 0

    for symbol, (inst_pct, holders_count) in inst_fields.items():
        stats = fh_stats.get(symbol, {})
        fh_count = stats.get("fh_count", 0)
        fh_total_value = stats.get("fh_total_value")
        fh_buy_ratio = stats.get("fh_buy_ratio", 0.0)

        has_yf = inst_pct is not None and holders_count
        has_13f = fh_count > 0

        if not has_yf and not has_13f:
            skipped += 1
            continue

        score = round(
            (inst_pct or 0.0) * 0.40
            + math.log(max(holders_count or 0, 1)) * 0.20
            + math.log(max(fh_count, 1)) * 0.20
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
