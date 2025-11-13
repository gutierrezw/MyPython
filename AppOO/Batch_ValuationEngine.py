"""
ValuationEngineNew.py
Versión mejorada: integra metadata.json de EDGAR.

- Usa datos locales en EDGAR/<TICKER>_EDGAR_Files/
- Si existe metadata.json, toma de allí los archivos XML/XBRL
- Detecta REITs
- Calcula valor intrínseco con DDM, DCF o FFO/AFFO
- Devuelve un diccionario listo para el BuyAgent o persistencia
"""

import os
import re
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
import warnings



from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ============================================================
# 📁 CONFIGURACIÓN BASE
# ============================================================

BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")
VERBOSE = False

# ============================================================
# 🧭 FUNCIONES AUXILIARES
# ============================================================

# --- Requiere: BeautifulSoup y funciones extract_xbrl_metrics / get_yf_price existentes ---

# ---------------------------
# Util: Retorna una lista de Path de filings relevantes desde metadata.json
# ---------------------------
def get_filing_list(ticker_dir: Path):
    """
    Retorna lista de Path ordenada: todos 10-Q del año actual (si existen) + últimos 5 10-K.
    Fallback: retorna hasta 5 archivos más recientes.
    """
    metadata_path = ticker_dir / "metadata.json"
    candidates = []

    # leer metadata.downloaded_files si existe
    if metadata_path.exists():
        try:
            md = json.loads(metadata_path.read_text(encoding="utf-8"))
            for item in md.get("downloaded_files", []):
                if not isinstance(item, dict):
                    continue
                # posibles keys: path, local_path, file, local_name
                pstr = item.get("path") or item.get("local_path") or item.get("file") or item.get("local_name")
                form = (item.get("form") or "").upper()
                date = item.get("date") or item.get("downloaded_date") or item.get("timestamp")
                if not pstr:
                    continue
                p = Path(pstr)
                if not p.is_absolute():
                    p = ticker_dir / p
                if p.exists() and p.suffix.lower() in (".htm", ".html", ".xml"):
                    # normalize date
                    dt = None
                    if isinstance(date, str):
                        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                            try:
                                dt = datetime.fromisoformat(date)
                                break
                            except Exception:
                                try:
                                    dt = datetime.strptime(date, fmt)
                                    break
                                except Exception:
                                    dt = None
                    if dt is None:
                        try:
                            dt = datetime.fromtimestamp(p.stat().st_mtime)
                        except Exception:
                            dt = datetime(1900, 1, 1)
                    candidates.append({"path": p, "form": form, "dt": dt})
        except Exception as e:
            if VERBOSE:
                print("⚠️ Error leyendo metadata.json:", e)

    # fallback: scan subdirs
    if not candidates:
        for sub in ["10Q_Filings", "10K_Filings", "6K_Filings", "20F_Filings"]:
            d = ticker_dir / sub
            if d.exists():
                for ext in ("*.htm", "*.html", "*.xml"):
                    for f in d.glob(ext):
                        form = "10-Q" if "10q" in sub.lower() or re.search(r"10-?q", f.name, re.I) else \
                               "10-K" if "10k" in sub.lower() or re.search(r"10-?k", f.name, re.I) else ""
                        dt = datetime.fromtimestamp(f.stat().st_mtime)
                        candidates.append({"path": f, "form": form, "dt": dt})

    if not candidates:
        return []

    # select 10-Q for current year and last 5 10-K
    year_now = datetime.now().year
    ten_qs = [c for c in candidates if (c.get("form","").upper().startswith("10-Q") or re.search(r"10-?q", c["path"].name, re.I))]
    ten_qs_year = [c for c in ten_qs if c["dt"].year == year_now]
    ten_qs_year = sorted(ten_qs_year, key=lambda x: x["dt"], reverse=True)

    ten_ks = [c for c in candidates if (c.get("form","").upper().startswith("10-K") or re.search(r"10-?k", c["path"].name, re.I))]
    ten_ks = sorted(ten_ks, key=lambda x: x["dt"], reverse=True)[:5]

    chosen = ten_qs_year + ten_ks
    if not chosen:
        # include latest 10-Q if none in year
        if ten_qs:
            chosen = [sorted(ten_qs, key=lambda x: x["dt"], reverse=True)[0]] + ten_ks
        else:
            # fallback last 5
            chosen = sorted(candidates, key=lambda x: x["dt"], reverse=True)[:5]

    # return only Path objects
    return [c["path"] for c in chosen]

# ---------------------------
# Util: Helpers: scale detection & normalization
# ---------------------------
def detect_scale_from_text_and_units(file_path: Path):
    """
    Heurística para detectar si los números en el filing están en 'thousands' o 'millions'.
    Retorna multiplier: 1 (normal), 1_000 (thousands), 1_000_000 (millions)
    """
    text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
    # common phrases
    if "in thousands" in text or "amounts in thousands" in text or "expressed in thousands" in text:
        return 1_000
    if "in millions" in text or "amounts in millions" in text or "expressed in millions" in text:
        return 1_000_000

    # look for unit definitions <xbrli:unit id="usd"> or id containing thousand/million
    try:
        soup = BeautifulSoup(text, "lxml")
    except Exception:
        soup = BeautifulSoup(text, "html.parser")
    for unit in soup.find_all(re.compile(r"xbrli:unit|unit"), recursive=True):
        uid = unit.get("id") or ""
        if uid and ("thousand" in uid.lower() or "thou" in uid.lower()):
            return 1_000
        if uid and ("million" in uid.lower() or "mill" in uid.lower()):
            return 1_000_000
        # inner text measures
        if unit.text and ("thousand" in unit.text or "million" in unit.text):
            if "thousand" in unit.text:
                return 1_000
            if "million" in unit.text:
                return 1_000_000

    # check inline tag scale or decimals attributes presence (fallback: assume 1)
    # If tags contain scale="-3" or decimals indicates magnitude, we could infer but it's complex; fallback=1
    return 1

# ---------------------------
# Util: 
# ---------------------------
def safe_parse_number(txt):
    """Intenta convertir texto a float/int, limpiando comas y signos."""
    if txt is None:
        return None
    s = str(txt).strip()
    if s in ("", "-", "—"):
        return None
    s = s.replace("$", "").replace(",", "").replace("\u00A0", "").strip()
    # remove parentheses for negatives
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()
    try:
        if "." in s:
            v = float(s)
        else:
            v = int(s)
        return -v if neg else v
    except Exception:
        try:
            return float(s)
        except Exception:
            return None

# ---------------------------
# Util: 
# ---------------------------
def detect_reit_status_from_text(file_path: Path):
    """
    Simple text analysis on the filing: search for 'real estate investment trust' or 'REIT'
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        if "real estate investment trust" in text or "real-estate investment trust" in text or " reit " in text:
            return True
    except Exception:
        pass
    return False

# ---------------------------
# Util: recoger series temporales: intentar usar los items más recientes
# ---------------------------
def aggregate_xbrl_metrics(file_paths):
    """
    file_paths: list[Path] ordered newest -> older
    retorna dict: files_used, per_file(list), ttm (NetIncome_TTM, ...), shares, raw_series
    """
    per_file = []
    for p in file_paths:
        try:
            # detect multiplier per file
            mult = detect_scale_from_text_and_units(p)
            parsed = extract_xbrl_metrics(p, multiplier=mult)
            per_file.append({"path": p, "dt": datetime.fromtimestamp(p.stat().st_mtime), "parsed": parsed, "multiplier": mult})
        except Exception:
            continue

    if not per_file:
        return {"files_used": [], "per_file": [], "ttm": {}, "shares": None, "raw_series": {}}

    # sort newest first
    per_file = sorted(per_file, key=lambda x: x["dt"], reverse=True)

    # keys to aggregate (summing last up to 4 quarters)
    keys = ["NetIncome", "OperatingCashFlow", "CapitalExpenditures", "DividendsPaid", "FFO", "AFFO"]
    series = {k: [] for k in keys}
    shares_list = []

    for entry in per_file:
        parsed = entry["parsed"]
        for k in keys:
            v = parsed.get(k)
            if isinstance(v, (int, float)):
                series[k].append({"value": v, "path": entry["path"], "dt": entry["dt"]})
        shares_val = parsed.get("SharesOutstanding")
        if isinstance(shares_val, (int, float)):
            shares_list.append({"value": shares_val, "path": entry["path"], "dt": entry["dt"]})

    def sum_top_k(k, kcount=4):
        vals = [it["value"] for it in series.get(k, [])[:kcount] if isinstance(it["value"], (int, float))]
        return round(sum(vals), 2) if vals else None

    ttm = {f"{k}_TTM": sum_top_k(k, 4) for k in keys}

    shares = shares_list[0]["value"] if shares_list else None

    return {
        "files_used": [str(e["path"]) for e in per_file],
        "per_file": per_file,
        "ttm": ttm,
        "shares": shares,
        "raw_series": series
    }

# ---------------------------
# Util: recoger series temporales: intentar usar los items más recientes
# ---------------------------
def detect_reit_enhanced(parsed_agg: dict, ticker: str = None):
    """
    Heurística que busca FFO/AFFO en raw_elements o ttm; fallback a ticker profile.
    Retorna True/False.
    """
    # check ttm
    try:
        ttm = parsed_agg.get("ttm", {})
        if ttm.get("FFO_TTM") not in (None, 0) or ttm.get("AFFO_TTM") not in (None, 0):
            return True
    except Exception:
        pass

    # check raw elements names across per_file
    try:
        for entry in parsed_agg.get("per_file", []):
            parsed = entry.get("parsed", {})
            for name in parsed.get("raw_elements", {}).keys():
                if "fundsfromoperations" in name.lower() or "ffo" in name.lower() or "adjustedfundsfromoperations" in name.lower() or "affo" in name.lower():
                    return True
    except Exception:
        pass

    # fallback profile via yfinance
    if ticker:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            for k in ("industry", "sector", "longBusinessSummary", "shortName", "longName"):
                v = info.get(k)
                if v and isinstance(v, str):
                    lv = v.lower()
                    if "reit" in lv or "real estate" in lv:
                        return True
        except Exception:
            pass

    return False

# ---------------------------
# Extracción de métricas desde iXBRL (inline XBRL HTML/XML)
# ---------------------------
def extract_xbrl_metrics(file_path: Path, multiplier: int = 1):
    """
    Extrae métricas desde un iXBRL file (.htm/.xml) y aplica multiplier (escala).
    Retorna dict con keys:
      Revenues, NetIncome, OperatingCashFlow, CapitalExpenditures, SharesOutstanding,
      DividendsPaid, FFO, AFFO, raw_elements, contexts
    """
    res = {
        "Revenues": None,
        "NetIncome": None,
        "OperatingCashFlow": None,
        "CapitalExpenditures": None,
        "SharesOutstanding": None,
        "DividendsPaid": None,
        "FFO": None,
        "AFFO": None,
        "raw_elements": {},
        "contexts": {}
    }

    if not file_path.exists():
        return res

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        soup = BeautifulSoup(text, "lxml")
    except Exception:
        soup = BeautifulSoup(text, "html.parser")

    # contexts
    for ctx in soup.find_all(re.compile(r"xbrli:context|context")):
        cid = ctx.get("id")
        if not cid:
            continue
        start = ctx.find(re.compile(r"xbrli:startdate|startdate"))
        end = ctx.find(re.compile(r"xbrli:enddate|enddate"))
        instant = ctx.find(re.compile(r"xbrli:instant|instant"))
        if start and end:
            res["contexts"][cid] = {"type": "duration", "start": start.text.strip(), "end": end.text.strip()}
        elif instant:
            res["contexts"][cid] = {"type": "instant", "date": instant.text.strip()}

    # helper to find numeric by name list
    def find_first_numeric(names):
        for nm in names:
            # ix:nonfraction or ix:nonnumeric variants
            tag = soup.find(lambda t: (t.name and t.name.lower() in ("ix:nonfraction", "ix:nonnumeric", "ix:nonnumeric", "nonfraction", "nonfractional")) and (t.get("name") == nm))
            if not tag:
                # try search by name attribute anywhere
                tags = soup.find_all(attrs={"name": nm})
                tag = tags[0] if tags else None
            if tag and tag.text and tag.text.strip() not in ("", "-", "—"):
                val = safe_parse_number(tag.text.strip())
                if val is not None:
                    return val * multiplier
        return None

    # candidate element names
    candidates = {
        "Revenues": ["us-gaap:Revenues", "us-gaap:SalesRevenueNet", "Revenues"],
        "NetIncome": ["us-gaap:NetIncomeLoss", "us-gaap:ProfitLoss", "NetIncomeLoss"],
        "OperatingCashFlow": ["us-gaap:NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivities"],
        "CapitalExpenditures": ["us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquirePropertyPlantAndEquipment"],
        "SharesOutstanding": ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
                              "us-gaap:CommonStockSharesOutstanding", "us-gaap:SharesOutstanding", "CommonStockSharesOutstanding"],
        "DividendsPaid": ["us-gaap:PaymentsOfDividends", "us-gaap:DividendsPaid", "DividendsPaid"],
        "FFO": ["us-gaap:FundsFromOperations", "us-gaap:FundsFromOperationsBasic", "FundsFromOperations"],
        "AFFO": ["us-gaap:AdjustedFundsFromOperations", "AdjustedFundsFromOperations"]
    }

    for key, names in candidates.items():
        val = find_first_numeric(names)
        res[key] = val

    # raw elements map: name -> list of occurrences
    raw = {}
    # scan ix tags with name attr
    for tag in soup.find_all():
        name = tag.get("name")
        if not name:
            continue
        txt = tag.text.strip()
        entry = {
            "text": txt,
            "context": tag.get("contextref") or tag.get("contextRef"),
            "unit": tag.get("unitref") or tag.get("unitRef"),
            "scale": tag.get("scale"),
            "decimals": tag.get("decimals")
        }
        raw.setdefault(name, []).append(entry)
    res["raw_elements"] = raw

    return res

# ---------------------------
# Obtener precio (Yahoo simple)
# ---------------------------
def get_yf_price(ticker: str):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data["chart"]["result"][0]["meta"].get("regularMarketPrice")
    except Exception:
        return None


# ---------------------------
# Cálculos: múltiplos y valores intrínsecos
# ---------------------------
def calc_valuations(metrics: dict, price: float, is_reit: bool):
    """
    metrics: dict keys expected: NetIncome, OperatingCashFlow, CapitalExpenditures,
             SharesOutstanding, FFO, AFFO, DividendsPaid (all TTM or aggregated)
    """
    out = {}
    shares = metrics.get("SharesOutstanding")
    net_income = metrics.get("NetIncome")
    revenues = metrics.get("Revenues")
    ocf = metrics.get("OperatingCashFlow")
    capex = metrics.get("CapitalExpenditures")
    dividends_paid = metrics.get("DividendsPaid")
    ffo = metrics.get("FFO")
    affo = metrics.get("AFFO")

    # EPS
    eps = None
    if net_income and shares and shares != 0:
        eps = net_income / shares

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - capex

    try:
        out["P/E"] = round(price / eps, 3) if (price and eps and eps != 0) else None
    except Exception:
        out["P/E"] = None

    try:
        out["P/S"] = round(price / (revenues / shares), 3) if (price and revenues and shares and shares != 0) else None
    except Exception:
        out["P/S"] = None

    try:
        out["P/FCF"] = round(price / (fcf / shares), 3) if (price and fcf and shares and shares != 0) else None
    except Exception:
        out["P/FCF"] = None

    if is_reit:
        ffo_per_share = None
        affo_per_share = None
        if ffo and shares and shares != 0:
            ffo_per_share = ffo / shares
        if affo and shares and shares != 0:
            affo_per_share = affo / shares
        out["FFO_per_share"] = ffo_per_share
        out["AFFO_per_share"] = affo_per_share
        out["P/FFO"] = round(price / ffo_per_share, 3) if (price and ffo_per_share and ffo_per_share != 0) else None
        out["P/AFFO"] = round(price / affo_per_share, 3) if (price and affo_per_share and affo_per_share != 0) else None

    # DDM
    dividend_per_share = None
    if dividends_paid and shares and shares != 0:
        dividend_per_share = abs(dividends_paid) / shares
    if dividend_per_share and dividend_per_share > 0:
        g = 0.03
        r = 0.09
        out["DDM_value"] = round((dividend_per_share * (1 + g)) / (r - g), 3) if r > g else None
    else:
        out["DDM_value"] = None

    # Simple DCF on FCF per share
    if fcf and shares and shares != 0:
        fcf_per_share = fcf / shares
        growth = 0.03
        discount = 0.09
        years = 5
        pv = 0.0
        for t in range(1, years + 1):
            pv += (fcf_per_share * ((1 + growth) ** t)) / ((1 + discount) ** t)
        try:
            terminal = (fcf_per_share * ((1 + growth) ** years)) / (discount - growth)
            pv += terminal / ((1 + discount) ** years)
            out["DCF_value_per_share"] = round(pv, 3)
        except Exception:
            out["DCF_value_per_share"] = None
    else:
        out["DCF_value_per_share"] = None

    out["EPS"] = eps
    out["FCF"] = fcf
    out["SharesOutstanding"] = shares
    out["NetIncome"] = net_income
    out["Revenues"] = revenues
    out["OperatingCashFlow"] = ocf
    out["CapitalExpenditures"] = capex
    out["DividendsPaid"] = dividends_paid
    out["FFO"] = ffo
    out["AFFO"] = affo

    return out

# ---------------------------
# Clase principal
# ---------------------------
class ValuationEngine:
    def __init__(self, ticker: str, base_dir: Path = None, verbose: bool = False):
        self.ticker = ticker.upper()
        self.base_dir = base_dir or BASE_DIR
        self.ticker_dir = Path(self.base_dir) / f"{self.ticker}_EDGAR_Files"
        self.verbose = verbose

    def run(self):
        if not self.ticker_dir.exists():
            print(f"📂 No existe carpeta para {self.ticker}. Ejecuta el downloader externo primero.")
            return None

        files = get_filing_list(self.ticker_dir)
        if not files:
            print("❌ No filings encontrados.")
            return None

        if self.verbose:
            print("📄 Archivos usados (ordenados):")
            for f in files:
                print("  -", f)

        parsed_agg = aggregate_xbrl_metrics(files)

        # REIT detection: enhanced first, then fallback to text on first file
        is_reit = detect_reit_enhanced(parsed_agg, self.ticker)
        if not is_reit and files:
            # check in textual content of most recent file
            try:
                if detect_reit_status_from_text(files[0]):
                    is_reit = True
            except Exception:
                pass

        price = get_yf_price(self.ticker)

        # prepare metrics_for_calc using ttm keys
        t = parsed_agg.get("ttm", {})
        metrics_for_calc = {
            "NetIncome": t.get("NetIncome_TTM"),
            "OperatingCashFlow": t.get("OperatingCashFlow_TTM"),
            "CapitalExpenditures": t.get("CapitalExpenditures_TTM"),
            "SharesOutstanding": parsed_agg.get("shares"),
            "FFO": t.get("FFO_TTM"),
            "AFFO": t.get("AFFO_TTM"),
            "DividendsPaid": t.get("DividendsPaid_TTM"),
            # optional Revenues (not aggregated here; left None if not found)
            "Revenues": None
        }

        valuations = calc_valuations(metrics_for_calc, price, is_reit)

        result = {
            "ticker": self.ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": price,
            "is_reit": is_reit,
            "source_file": str(files[0]) if files else None,
            # include parsed agg only if verbose true
            **({"parsed_agg": parsed_agg} if self.verbose else {}),
            "valuations": valuations
        }

        print("\n=== Resultado resumido ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result

# ---------------------------
# Ejecución directa
# ---------------------------
if __name__ == "__main__":
    tk = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
    eng = ValuationEngine(tk, verbose=True)
    eng.run()