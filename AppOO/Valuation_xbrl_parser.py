# xbrl_parser.py
"""
Parsing iXBRL + agregado TTM + heurísticas REIT.

Contiene:
- detect_scale_from_text_and_units(): detecta thousands/millions
- extract_xbrl_metrics(): lee Inline XBRL y extrae métricas clave
- aggregate_xbrl_metrics(): arma TTM (NetIncome, OCF, CapEx, Dividends, FFO, AFFO)
- detect_reit_enhanced(): identifica REIT por FFO/AFFO o metadata
"""

import re
import warnings
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from Valuation_utils import safe_parse_number

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# ============================================================
# 🔍 Detectar escala (thousands / millions)
# ============================================================
def detect_scale_from_text_and_units(file_path: Path):
    """
    Lee el texto del filing y busca frases típicas:
    - "in thousands"
    - "in millions"

    También inspecciona tags <unit>.
    Retorna multiplier: 1, 1000, 1_000_000
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return 1

    # Palabras típicas en encabezados
    if "in thousands" in text or "amounts in thousands" in text:
        return 1_000
    if "in millions" in text or "amounts in millions" in text:
        return 1_000_000

    # Buscar en definiciones de units del XBRL
    try:
        soup = BeautifulSoup(text, "lxml")
    except:
        soup = BeautifulSoup(text, "html.parser")

    for unit in soup.find_all(re.compile(r"xbrli:unit|unit")):
        uid = (unit.get("id") or "").lower()
        if "thousand" in uid:
            return 1_000
        if "million" in uid:
            return 1_000_000

        # interior del tag
        t = unit.text.lower()
        if "thousand" in t:
            return 1_000
        if "million" in t:
            return 1_000_000

    return 1


# ============================================================
# 📄 Extraer métricas desde iXBRL
# ============================================================
def extract_xbrl_metrics(file_path: Path, multiplier: int = 1):
    """
    Extrae principales métricas financieras desde un archivo .htm/.xml iXBRL.

    Keys retornadas:
      Revenues
      NetIncome
      OperatingCashFlow
      CapitalExpenditures
      SharesOutstanding
      DividendsPaid
      FFO
      AFFO
      raw_elements: { tag_name: [list entries] }
      contexts
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
        "contexts": {},
    }

    if not file_path.exists():
        return res

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return res

    try:
        soup = BeautifulSoup(text, "lxml")
    except Exception:
        soup = BeautifulSoup(text, "html.parser")

    # ---------- contexts (periods / instant dates) ----------
    for ctx in soup.find_all(re.compile(r"xbrli:context|context")):
        cid = ctx.get("id")
        if not cid:
            continue

        start = ctx.find(re.compile(r"xbrli:startdate|startdate"))
        end = ctx.find(re.compile(r"xbrli:enddate|enddate"))
        instant = ctx.find(re.compile(r"xbrli:instant|instant"))

        if start and end:
            res["contexts"][cid] = {
                "type": "duration",
                "start": start.text.strip(),
                "end": end.text.strip(),
            }
        elif instant:
            res["contexts"][cid] = {
                "type": "instant",
                "date": instant.text.strip(),
            }

    # ---------- Helper para buscar un tag por name ----------
    def find_first_numeric(names):
        for nm in names:
            # Buscar tags ix:nonfraction / ix:nonnumeric con name="xxx"
            tag = soup.find(lambda t: (
                t.name
                and t.get("name") == nm
                and t.text
                and t.text.strip() not in ("", "-", "—")
            ))

            if not tag:
                # fallback genérico
                tags = soup.find_all(attrs={"name": nm})
                tag = tags[0] if tags else None

            if tag and tag.text:
                val = safe_parse_number(tag.text.strip())
                if val is not None:
                    return val * multiplier
        return None

    # ---------- Candidatos para cada métrica ----------
    candidates = {
        "Revenues": [
            "us-gaap:Revenues",
            "us-gaap:SalesRevenueNet",
            "Revenues",
        ],
        "NetIncome": [
            "us-gaap:NetIncomeLoss",
            "us-gaap:ProfitLoss",
            "NetIncomeLoss",
        ],
        "OperatingCashFlow": [
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivities",
        ],
        "CapitalExpenditures": [
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquirePropertyPlantAndEquipment",
        ],
        "SharesOutstanding": [
            "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
            "us-gaap:CommonStockSharesOutstanding",
            "CommonStockSharesOutstanding",
        ],
        "DividendsPaid": [
            "us-gaap:PaymentsOfDividends",
            "us-gaap:DividendsPaid",
            "DividendsPaid",
        ],
        "FFO": [
            "us-gaap:FundsFromOperations",
            "us-gaap:FundsFromOperationsBasic",
            "FundsFromOperations",
        ],
        "AFFO": [
            "us-gaap:AdjustedFundsFromOperations",
            "AdjustedFundsFromOperations",
        ],
    }

    # ---------- Extraer métricas principales ----------
    for key, names in candidates.items():
        res[key] = find_first_numeric(names)

    # ---------- Extraer raw_elements (todos los elementos con name=) ----------
    raw = {}
    for tag in soup.find_all():
        name_attr = tag.get("name")
        if not name_attr:
            continue

        entry = {
            "text": tag.text.strip(),
            "context": tag.get("contextref") or tag.get("contextRef"),
            "unit": tag.get("unitref") or tag.get("unitRef"),
            "scale": tag.get("scale"),
            "decimals": tag.get("decimals"),
        }
        raw.setdefault(name_attr, []).append(entry)

    res["raw_elements"] = raw
    return res


# ============================================================
# 📈 Agregado TTM a partir de los últimos 4 filings
# ============================================================
def aggregate_xbrl_metrics(file_paths):
    """
    file_paths: lista de Path ordenados (más reciente primero)

    Retorna:
    {
        files_used: [...]
        per_file: [...]
        ttm: {
            NetIncome_TTM,
            OperatingCashFlow_TTM,
            CapitalExpenditures_TTM,
            DividendsPaid_TTM,
            FFO_TTM,
            AFFO_TTM
        }
        shares: valor más reciente
        raw_series: series completas
    }
    """

    per_file = []

    # ---------- Procesar cada archivo ----------
    for p in file_paths:
        try:
            mult = detect_scale_from_text_and_units(p)
            parsed = extract_xbrl_metrics(p, mult)
            per_file.append({
                "path": p,
                "dt": datetime.fromtimestamp(p.stat().st_mtime),
                "parsed": parsed,
                "multiplier": mult
            })
        except Exception:
            continue

    if not per_file:
        return {
            "files_used": [],
            "per_file": [],
            "ttm": {},
            "shares": None,
            "raw_series": {}
        }

    # Orden más reciente primero
    per_file = sorted(per_file, key=lambda x: x["dt"], reverse=True)

    # Series a acumular
    keys = [
        "NetIncome", "OperatingCashFlow", "CapitalExpenditures",
        "DividendsPaid", "FFO", "AFFO"
    ]

    series = {k: [] for k in keys}
    shares_list = []

    for entry in per_file:
        parsed = entry["parsed"]

        for k in keys:
            val = parsed.get(k)
            if isinstance(val, (int, float)):
                series[k].append({
                    "value": val,
                    "path": entry["path"],
                    "dt": entry["dt"]
                })

        shares_val = parsed.get("SharesOutstanding")
        if isinstance(shares_val, (int, float)):
            shares_list.append({
                "value": shares_val,
                "path": entry["path"],
                "dt": entry["dt"]
            })

    # ---------- Sumar últimas 4 ----------
    def sum_top_k(k, count=4):
        vals = [it["value"] for it in series.get(k, [])[:count]]
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


# ============================================================
# 🏢 Detección REIT mejorada
# ============================================================
def detect_reit_enhanced(parsed_agg: dict, ticker: str = None):
    """
    Detecta REIT si:
    1) Existe FFO/AFFO → REIT casi seguro
    2) raw_elements contienen tags con 'ffo'/'fundsfromoperations'
    3) Perfil de Yahoo menciona REIT (industry/summary)
    """

    # 1) TTM directo
    ttm = parsed_agg.get("ttm", {})
    if ttm.get("FFO_TTM") or ttm.get("AFFO_TTM"):
        return True

    # 2) Revisar raw elements
    try:
        for entry in parsed_agg.get("per_file", []):
            raw = entry["parsed"].get("raw_elements", {})
            for name in raw.keys():
                ln = name.lower()
                if ("ffo" in ln or "fundsfromoperations" in ln
                        or "affo" in ln or "adjustedfundsfromoperations" in ln):
                    return True
    except Exception:
        pass

    # 3) Fallback: descripción Yahoo Finance
    if ticker:
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            for k in ("industry", "sector", "longBusinessSummary"):
                v = info.get(k)
                if v and "reit" in v.lower():
                    return True
        except Exception:
            pass

    return False
