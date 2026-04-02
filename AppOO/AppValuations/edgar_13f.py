import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import ET, logging, requests, time, date, timedelta
from Modulos_Mysql import MarketScreen

_logger = logging.getLogger("InstitucionalScore")
_EDGAR_HEADERS = {"User-Agent": "InversionesWildaga Research Bot (gutierrez.madrid.wilmer@example.com)"}
_EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_EDGAR_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{filename}"
_OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
_13F_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "EDGAR", "13F")
_13F_NS = {"tf": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}
_FILING_REFRESH_DAYS = 80  # umbral para re-chequear EDGAR (< 1 trimestre)


def _sec_get(url: str, timeout: int = 20) -> requests.Response | None:
    """GET al SEC con retry x3 y backoff en 503/timeout."""
    for attempt in range(3):
        if attempt > 0:
            time.sleep(5 * attempt)
        try:
            r = requests.get(url, headers=_EDGAR_HEADERS, timeout=timeout)
            if r.status_code == 503:
                continue
            r.raise_for_status()
            return r
        except requests.exceptions.Timeout:
            continue
        except Exception:
            return None
    return None


def _get_latest_13f_accession(cik: str) -> tuple | None:
    """Retorna (accession, filing_date) del último 13F-HR para el CIK dado."""
    r = _sec_get(_EDGAR_SUBMISSIONS_URL.format(cik=int(cik)))
    if not r:
        return None
    try:
        filings = r.json().get("filings", {}).get("recent", {})
        for form, acc, filing_date in zip(
            filings.get("form", []), filings.get("accessionNumber", []), filings.get("filingDate", [])
        ):
            if form == "13F-HR":
                return acc, filing_date
    except Exception as e:
        _logger.warning(f"_get_latest_13f_accession [{cik}]: {e}")
    return None


def _find_holdings_xml(cik: str, accession: str) -> str | None:
    """Busca el archivo XML de holdings (INFORMATION TABLE) en el índice del filing 13F-HR."""
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/index.json"
    r = _sec_get(url)
    if not r:
        _logger.warning(f"_find_holdings_xml [{cik}/{accession}]: sin respuesta")
        return None
    try:
        items = r.json().get("directory", {}).get("item", [])
        for item in items:
            if item.get("type", "").upper() == "INFORMATION TABLE":
                return item.get("name")
        for item in items:
            name = item.get("name", "")
            if name.lower().endswith(".xml") and "primary" not in name.lower():
                return name
    except Exception as e:
        _logger.warning(f"_find_holdings_xml [{cik}/{accession}]: {e}")
    return None


def sync_fund_filings() -> dict:
    """Descarga el último 13F-HR XML para todos los fondos con CIK en tabla funds.

    Lógica de skip (Opción B — refresh trimestral por filing_date):
    - Sin filing previo en BD       → descarga siempre.
    - filing_date < 80 días         → skip sin llamar a EDGAR (filing fresco).
    - filing_date ≥ 80 días         → consulta EDGAR; descarga solo si la accession cambió.
    Guarda en tabla fund_filings (persistente) en vez de JSON temporal.
    """
    market = MarketScreen()
    funds = market.load_all_funds_with_cik()
    os.makedirs(_13F_SAVE_DIR, exist_ok=True)
    cik_meta = market.load_fund_filings_cik_meta()
    total = len(funds)
    downloaded, skipped, failed = 0, 0, 0
    hoy = date.today()
    umbral = timedelta(days=_FILING_REFRESH_DAYS)
    pending_save = []  # acumula registros para bulk save cada 100 descargas

    for i, (fund_name, cik) in enumerate(funds, 1):
        if i % 100 == 0 or i == total:
            _logger.warning(
                f"sync_fund_filings: [{i}/{total}] descargados={downloaded} " f"skipped={skipped} fallidos={failed}"
            )

        stored = cik_meta.get(cik)

        if stored:
            try:
                filing_date_stored = date.fromisoformat(stored["filing_date"])
            except (ValueError, TypeError):
                filing_date_stored = None

            if filing_date_stored and (hoy - filing_date_stored) < umbral:
                skipped += 1
                continue  # filing fresco — no hace falta consultar EDGAR

        # Sin filing previo o vencido — consultar EDGAR
        time.sleep(0.5)
        result = _get_latest_13f_accession(cik)
        if not result:
            failed += 1
            continue

        accession, filing_date = result
        accession_no_dashes = accession.replace("-", "")

        # Si la accession coincide con la almacenada — ya tenemos el más reciente
        if stored and stored.get("accession") == accession_no_dashes:
            skipped += 1
            continue

        xml_file = _find_holdings_xml(cik, accession)
        if not xml_file:
            skipped += 1
            continue

        filename = f"{cik}_{accession_no_dashes}_{xml_file}"
        local_path = os.path.join(_13F_SAVE_DIR, filename)

        if not os.path.exists(local_path):
            url = _EDGAR_ARCHIVES_URL.format(
                cik=int(cik),
                acc_no_dashes=accession_no_dashes,
                filename=xml_file,
            )
            r = _sec_get(url, timeout=30)
            if not r:
                _logger.warning(f"sync_fund_filings [{fund_name}]: sin respuesta al descargar XML")
                failed += 1
                continue
            try:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                time.sleep(0.5)
            except Exception as e:
                _logger.warning(f"sync_fund_filings [{fund_name}]: {e}")
                failed += 1
                continue

        # Registrar en BD (XML descargado o ya existía en disco con accession nueva)
        pending_save.append((filename, cik, fund_name, filing_date, accession_no_dashes))
        downloaded += 1
        if len(pending_save) >= 100:
            market.bulk_save_fund_filings(pending_save)
            pending_save.clear()

    if pending_save:
        market.bulk_save_fund_filings(pending_save)

    return {"funds": total, "downloaded": downloaded, "skipped": skipped, "failed": failed}


def resolve_cusips_openfigi(cusips: list) -> dict:
    """Resuelve lista de CUSIPs a {cusip: ticker} via OpenFIGI batch API.
    Free tier: máx 10 items/request, 25 requests/min → 2.5s entre requests."""
    result = {}
    total = len(cusips)
    batch_size = 10
    for i in range(0, total, batch_size):
        batch = cusips[i : i + batch_size]
        if i % 500 == 0 or i + batch_size >= total:
            _logger.warning(f"  OpenFIGI: [{i}/{total}] resueltos={len(result)}")
        payload = [{"idType": "ID_CUSIP", "idValue": c} for c in batch]
        try:
            r = requests.post(_OPENFIGI_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if r.status_code == 429:
                time.sleep(60)
                r = requests.post(_OPENFIGI_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            r.raise_for_status()
            for cusip, item in zip(batch, r.json()):
                data = item.get("data", [])
                if data:
                    ticker = data[0].get("ticker")
                    if ticker:
                        result[cusip] = ticker
        except Exception as e:
            _logger.warning(f"resolve_cusips_openfigi batch {i}: {e}")
        time.sleep(2.5)
    return result


def parse_13f_xml(filepath: str) -> list:
    """Parsea un XML 13F-HR y retorna lista de {cusip, name, shares, value, option_type}.
    option_type: None=acciones directas, 'CALL'/'PUT'=opciones sobre acciones."""
    positions = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for info in root.findall("tf:infoTable", _13F_NS):
            cusip = (info.findtext("tf:cusip", namespaces=_13F_NS) or "").strip()
            name = (info.findtext("tf:nameOfIssuer", namespaces=_13F_NS) or "").strip()
            shares_elem = info.find("tf:shrsOrPrnAmt/tf:sshPrnamt", _13F_NS)
            shares = int(shares_elem.text) if shares_elem is not None and shares_elem.text else None
            value_text = info.findtext("tf:value", namespaces=_13F_NS)
            value = int(value_text) * 1000 if value_text else None
            put_call = (info.findtext("tf:putCall", namespaces=_13F_NS) or "").strip().upper()
            option_type = put_call if put_call in ("CALL", "PUT") else None
            if cusip and shares:
                positions.append(
                    {
                        "cusip": cusip,
                        "name": name,
                        "shares": shares,
                        "value": value,
                        "option_type": option_type,
                    }
                )
    except Exception as e:
        _logger.warning(f"parse_13f_xml [{filepath}]: {e}")
    return positions


def sync_13f_holdings(account: str) -> dict:
    """Parsea XMLs 13F no procesados y pobla fund_holdings.
    Usa tabla fund_filings (processed=0) en vez de JSON temporal."""
    market = MarketScreen()
    unprocessed = market.load_unprocessed_filings()
    cusip_map = market.get_cusip_map(account)

    _logger.warning(f"sync_13f_holdings: {len(unprocessed)} XMLs pendientes")

    # Paso 1: recolectar posiciones de los XMLs no procesados
    all_positions = {}
    for entry in unprocessed:
        xml_file = entry["filename"]
        cik = entry["cik"]
        fund_id = market.get_fund_id_by_cik(cik)
        if not fund_id:
            continue
        filepath = os.path.join(_13F_SAVE_DIR, xml_file)
        if not os.path.exists(filepath):
            continue
        positions = parse_13f_xml(filepath)
        all_positions[xml_file] = (fund_id, entry["filing_date"], positions)

    # Paso 2: bulk upsert fund_holdings
    _logger.warning("sync_13f_holdings: cargando estado previo de fund_holdings...")
    prev_map = market.load_fund_holdings_prev()

    records = []
    inserted_holdings = 0
    inserted_options = 0
    for xml_file, (fund_id, filing_date, positions) in all_positions.items():
        for pos in positions:
            symbol = cusip_map.get(pos["cusip"])
            if not symbol:
                continue
            opt = pos.get("option_type") or "STK"
            shares = pos["shares"]
            prev_key = (fund_id, pos["cusip"], opt)
            shares_prev = prev_map.get(prev_key)

            if shares_prev is None:
                operation, shares_delta, pct_change = "NEW", None, None
            elif shares > shares_prev:
                operation = "BUY"
                shares_delta = shares - shares_prev
                pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
            elif shares < shares_prev:
                operation = "SELL"
                shares_delta = shares - shares_prev
                pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
            else:
                operation, shares_delta, pct_change = "HOLD", 0, 0.0

            # Actualizar prev_map en memoria para que el siguiente filing del mismo fondo
            # compare contra este (permite BUY/SELL/HOLD entre trimestres consecutivos)
            prev_map[prev_key] = shares

            records.append(
                (
                    fund_id,
                    symbol,
                    shares,
                    shares_prev,
                    shares_delta,
                    pct_change,
                    operation,
                    filing_date,
                    pos["value"],
                    pos["cusip"],
                    opt,
                )
            )
            if opt != "STK":
                inserted_options += 1
            else:
                inserted_holdings += 1

    _logger.warning(
        f"sync_13f_holdings: bulk insert {len(records)} registros "
        f"({inserted_holdings} directos, {inserted_options} opciones)..."
    )
    market.bulk_upsert_fund_holdings(records)

    # Marcar como procesados en BD
    market.mark_filings_processed(list(all_positions.keys()))

    return {
        "xml_files": len(unprocessed),
        "inserted_holdings": inserted_holdings,
        "inserted_options": inserted_options,
    }
