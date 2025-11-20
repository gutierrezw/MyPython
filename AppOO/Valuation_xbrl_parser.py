# xbrl_parser.py
"""
Parsing iXBRL + agregado TTM + heurísticas REIT.

Contiene:
- detect_scale_from_text_and_units_improved(): detecta thousands/millions
- extract_xbrl_metrics_improved(): lee Inline XBRL y extrae métricas clave
- aggregate_xbrl_metrics(): arma TTM (NetIncome, OCF, CapEx, Dividends, FFO, AFFO)
- detect_reit_enhanced(): identifica REIT por FFO/AFFO o metadata
"""

import re
import warnings
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from Valuation_utils import (
    safe_parse_number,
    _normalize_number_text,
    _find_number_in_adjacent_cells,
)


# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def _normalize_number_text(txt: str):
    if not txt:
        return None
    t = txt.replace(",", "").replace("(", "-").replace(")", "").strip()
    try:
        return float(t)
    except:
        return None


def _extract_entity_info_from_soup(soup):
    out = {"sic": None, "registrant_name": None}
    try:
        sic_tag = soup.find("dei:EntityFilerCategory") or soup.find(
            "entityfilercategory"
        )
        if sic_tag:
            out["sic"] = sic_tag.get_text(strip=True)
    except:
        pass
    try:
        nm = soup.find("dei:EntityRegistrantName") or soup.find("entityregistrantname")
        if nm:
            out["registrant_name"] = nm.get_text(strip=True)
    except:
        pass
    return out


def detect_scale_from_text_and_units_improved(file_path):
    """
    Corrige el problema de detectar erroneamente 'billions'.
    - Solo aplica scale si la frase aparece en un CONTEXTO FINANCIERO.
    - Si encuentra 'millions' => 1e6
    - Si encuentra 'thousands' => 1e3
    - 'billions' está PROHIBIDO salvo que venga directamente en unitRef.
    """

    text = Path(file_path).read_text(encoding="utf-8", errors="ignore").lower()

    # 1) chequeo unitRef (el único realmente confiable)
    # Si aparece un unitRef claro, se usa eso y no se analiza texto.
    if "unitref" in text or "unitref=" in text:
        # buscar usd, usdPerShare, etc.
        return 1  # unitRef ya contiene la escala correcta, NO multiplicamos

    # 2) detectar "millions" en encabezados contables
    if re.search(r"(in|amounts in|dollars in)\s+millions", text[:5000]):
        return 1_000_000

    # 3) detectar "thousands" en encabezados contables
    if re.search(r"(in|amounts in|dollars in)\s+thousands", text[:5000]):
        return 1_000

    # ❗ 4) 'billions' está DESACTIVADO
    # porque aparece en párrafos narrativos y causa desastre.
    # if re.search(r"(in|amounts in|dollars in)\s+billions", text[:5000]):
    #     return 1_000_000_000

    # 5) default
    return 1


def _find_number_in_adjacent_cells(tr, keywords):
    """
    Original fallback method: looks for keyword in row, take right-adjacent numeric.
    """
    t = tr.get_text(" ", strip=True).lower()
    if not any(kw in t for kw in keywords):
        return None

    cells = tr.find_all(["td", "th"])
    for td in cells:
        text = td.get_text(" ", strip=True).lower()
        if any(kw in text for kw in keywords):
            idx = cells.index(td)
            for nxt in cells[idx + 1 :]:
                v = _normalize_number_text(nxt.get_text(" ", strip=True))
                if v is not None:
                    return v
    return None


def _extract_row_numbers_simple(row):
    """
    Extra fallback: extract numbers from a table row by scanning all cells.
    """
    nums = []
    for td in row.find_all(["td", "th"]):
        v = _normalize_number_text(td.get_text(" ", strip=True))
        if v is not None:
            nums.append(v)
    return nums if nums else None


# ------------------------------------------------------
# Extrae todos los <context>
# ------------------------------------------------------
def _parse_xbrl_contexts(soup):
    """
    Extrae contextRef con periodType, fechas y retorna dict:
    ctx_id -> {type, start, end}
    """
    contexts = {}
    for ctx in soup.find_all(["context"]):
        cid = ctx.get("id")
        if not cid:
            continue

        period = ctx.find("period")
        if not period:
            continue

        start = period.find("startdate")
        end = period.find("enddate")
        instant = period.find("instant")

        if instant:
            contexts[cid] = {
                "type": "instant",
                "start": None,
                "end": instant.get_text(strip=True),
            }
        elif start and end:
            contexts[cid] = {
                "type": "duration",
                "start": start.get_text(strip=True),
                "end": end.get_text(strip=True),
            }

    return contexts


# ------------------------------------------------------
# preferir contextos duration
# ------------------------------------------------------
def _select_best_context(contexts, want_type="duration"):
    """
    want_type: "duration" o "instant"
    Devuelve el contextRef más reciente que coincida.
    """

    if not contexts:
        return None

    # filtrar por tipo
    filtered = {cid: c for cid, c in contexts.items() if c["type"] == want_type}
    if not filtered:
        return None

    # ordenar por fecha de fin más reciente
    def parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except:
            return None

    sortable = []
    for cid, c in filtered.items():
        d = parse_date(c["end"])
        if d:
            sortable.append((d, cid))

    if not sortable:
        return None

    sortable.sort(reverse=True)  # más reciente primero
    return sortable[0][1]  # contextRef id


# ------------------------------------------------------
# Extracts available XBRL contexts
# ------------------------------------------------------
def _extract_contexts_from_xbrl(soup):
    """
    Extracts available XBRL contexts (id only).
    We don't use period or start/end yet — only validate tags.
    """
    contexts = {}
    for ctx in soup.find_all(["xbrli:context", "context"]):
        cid = ctx.get("id")
        if cid:
            contexts[cid] = {"id": cid}
    return contexts


# ------------------------------------------------------
# Limpia y normaliza desde un <ix:nonFraction> o <ix:nonNumeric>
# ------------------------------------------------------
def _extract_single_xbrl_tag(tag, key, mult):
    """
    Limpia y normaliza desde un <ix:nonFraction> o <ix:nonNumeric>
    """
    raw = tag.get_text(" ", strip=True)
    val = _normalize_number_text(raw)
    if val is None:
        return None

    return round(val * mult, 2)


# ------------------------------------------------------
# MAIN EXTRACTION FUNCTION
# ------------------------------------------------------
def extract_xbrl_metrics_improved(file_path: Path):
    """
    XBRL extraction with:
    1) Multi-namespace tag scanning
    2) Entity info
    3) HTML FFO/AFFO/Revenues row-matching (advanced fallback)
    4) Original _find_number_in_adjacent_cells fallback
    5) Extra fallback scanning entire row if needed
    """
    mult = detect_scale_from_text_and_units_improved(file_path)

    text = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        soup = BeautifulSoup(text, "lxml")
    except:
        soup = BeautifulSoup(text, "html.parser")

    res = {
        "Revenues": None,
        "NetIncome": None,
        "OperatingCashFlow": None,
        "CapitalExpenditures": None,
        "SharesOutstanding": None,
        "DividendsPaid": None,
        "FFO": None,
        "AFFO": None,
        "FFO_per_share": None,
        "AFFO_per_share": None,
        "raw_elements": {},
        "contexts": {},
        "entity": {"sic": None, "registrant_name": None},
        "_extraction_audit": [],
    }

    # --------------------------------------------------
    # Load XBRL contexts
    # --------------------------------------------------
    try:
        res["contexts"] = _parse_xbrl_contexts(soup)

        # Selección de contextos por tipo
        best_duration_ctx = _select_best_context(res["contexts"], "duration")
        best_instant_ctx = _select_best_context(res["contexts"], "instant")

        res["_extraction_audit"].append(
            {
                "source": "context_selection",
                "selected": {
                    "duration_ctx": best_duration_ctx,
                    "instant_ctx": best_instant_ctx,
                    "valid_ids": set(res["contexts"].keys()),
                },
            }
        )

    except Exception as e:
        res["_extraction_audit"].append(
            {"source": "context_selection_error", "error": str(e)}
        )

    # --------------------------------------------------
    # 1) Entity info
    # --------------------------------------------------
    try:
        ent = _extract_entity_info_from_soup(soup)
        if ent:
            res["entity"].update(ent)
            res["_extraction_audit"].append({"source": "entity_tag", "entity": ent})
    except:
        pass

    # --------------------------------------------------
    # 2) Candidate tag names (wide)
    # --------------------------------------------------
    candidates = {
        "Revenues": [
            "us-gaap:revenue",
            "us-gaap:revenues",
            "us-gaap:salesrevenuenet",
            "net_sales",
            "netsales",
            "sales",
            "revenues",
            "cci:revenues",
            "khc:netsales",
        ],
        "NetIncome": [
            "us-gaap:netincomeloss",
            "us-gaap:profitloss",
            "netincome",
            "profitloss",
        ],
        "OperatingCashFlow": [
            "us-gaap:netcashprovidedbyusedinoperatingactivities",
            "netcashprovidedbyusedinoperatingactivities",
        ],
        "CapitalExpenditures": [
            "us-gaap:paymentstoacquirepropertyplantandequipment",
            "capitalexpenditures",
            "capex",
        ],
        "SharesOutstanding": [
            "us-gaap:weightedaveragenumberofdilutedsharesoutstanding",
            "us-gaap:commonstocksharesoutstanding",
            "sharesoutstanding",
        ],
        "DividendsPaid": [
            "us-gaap:paymentsofdividends",
            "us-gaap:dividendspaid",
            "dividendspaid",
        ],
        "FFO": [
            "fundsfromoperations",
            "us-gaap:fundsfromoperations",
            "ffo",
            "cci:fundsfromoperations",
        ],
        "AFFO": [
            "adjustedfundsfromoperations",
            "affo",
            "us-gaap:adjustedfundsfromoperations",
        ],
    }

    # --------------------------------------------------
    # 3) Scan REAL ixbrl elements (ix:nonFraction / ix:nonNumeric)
    # --------------------------------------------------
    for tag in soup.find_all():
        name = tag.get("name") or tag.get("name".lower())
        if not name:
            continue

        ctx = tag.get("contextref") or tag.get("contextRef")
        if not ctx:
            continue

        # Filtrar por el contextRef adecuado
        # duration → Revenues, NetIncome, OCF, CapEx, DividendsPaid, FFO, AFFO
        # instant  → SharesOutstanding
        key_group_duration = {
            "Revenues",
            "NetIncome",
            "OperatingCashFlow",
            "CapitalExpenditures",
            "DividendsPaid",
            "FFO",
            "AFFO",
        }
        key_group_instant = {"SharesOutstanding"}

        # Detect key group before extracting
        target_key = None
        lname = name.lower()
        for k, name_list in candidates.items():
            if any(nm in lname for nm in name_list):
                target_key = k
                break

        if not target_key:
            continue

        # validar contextRef correcto
        if target_key in key_group_duration and ctx != best_duration_ctx:
            continue
        if target_key in key_group_instant and ctx != best_instant_ctx:
            continue

        # si pasa el filtro → extraer
        val = _extract_single_xbrl_tag(tag, target_key, mult)
        if val is not None:
            res[target_key] = val
            res["_extraction_audit"].append(
                {
                    "source": "xbrl_filtered",
                    "key": target_key,
                    "ctx": ctx,
                    "raw": tag.get_text(strip=True),
                }
            )

    # --------------------------------------------------
    # 3.1 ADVANCED FALLBACK HTML ROW-MATCHING
    # --------------------------------------------------
    html_kw = {
        "FFO": ["funds from operations", "fundsfromoperations", "ffo"],
        "AFFO": ["affo", "adjusted funds from operations"],
        "Revenues": ["revenues", "net sales", "sales"],
    }

    for tbl in soup.find_all("table"):
        for tr in tbl.find_all("tr"):
            row_text = tr.get_text(" ", strip=True).lower()

            # FFO
            if res["FFO"] is None and any(kw in row_text for kw in html_kw["FFO"]):
                nums = _extract_row_numbers_simple(tr)
                if nums:
                    res["FFO"] = round(nums[-1] * mult, 2)
                    res["_extraction_audit"].append(
                        {
                            "key": "FFO",
                            "method": "html_advanced",
                            "row": row_text[:120],
                            "mult": mult,
                        }
                    )

            # AFFO
            if res["AFFO"] is None and any(kw in row_text for kw in html_kw["AFFO"]):
                nums = _extract_row_numbers_simple(tr)
                if nums:
                    res["AFFO"] = round(nums[-1] * mult, 2)
                    res["_extraction_audit"].append(
                        {
                            "key": "AFFO",
                            "method": "html_advanced",
                            "row": row_text[:120],
                            "mult": mult,
                        }
                    )

            # Revenues
            if res["Revenues"] is None and any(
                kw in row_text for kw in html_kw["Revenues"]
            ):
                nums = _extract_row_numbers_simple(tr)
                if nums:
                    res["Revenues"] = round(nums[-1] * mult, 2)
                    res["_extraction_audit"].append(
                        {
                            "key": "Revenues",
                            "method": "html_advanced",
                            "row": row_text[:120],
                            "mult": mult,
                        }
                    )

    # --------------------------------------------------
    # 4) ORIGINAL FALLBACK _find_number_in_adjacent_cells
    # --------------------------------------------------
    table_keywords = {
        "FFO": ["funds from operations", "fundsfromoperations", "ffo"],
        "AFFO": ["affo", "adjusted funds from operations"],
        "Revenues": ["revenues", "net sales", "sales"],
    }

    for tbl in soup.find_all("table"):
        for tr in tbl.find_all("tr"):
            for key in ["FFO", "AFFO", "Revenues"]:
                if res[key] is None:
                    val = _find_number_in_adjacent_cells(tr, table_keywords[key])
                    if val is not None:
                        res[key] = round(val * mult, 2)
                        res["_extraction_audit"].append(
                            {
                                "key": key,
                                "method": "html_basic_adjacent",
                                "row": tr.get_text(" ", strip=True)[:120],
                                "mult": mult,
                            }
                        )

    # --------------------------------------------------
    # 5) If FFO/AFFO numbers exist but per-share missing
    # --------------------------------------------------
    try:
        if (
            res["FFO"] is not None
            and res["FFO_per_share"] is None
            and res["SharesOutstanding"]
        ):
            res["FFO_per_share"] = round(res["FFO"] / res["SharesOutstanding"], 6)
        if (
            res["AFFO"] is not None
            and res["AFFO_per_share"] is None
            and res["SharesOutstanding"]
        ):
            res["AFFO_per_share"] = round(res["AFFO"] / res["SharesOutstanding"], 6)
    except:
        pass

    return res


# ============================================================
# Facade: aggregate_xbrl_metrics + REIT detector
# ============================================================
def aggregate_xbrl_metrics(file_paths):
    """
    Produce parsed_agg compatible con lo que espera Valuation_engine:
    {
      "files_used": [str(paths...)],
      "per_file": [ {"path": Path, "dt": datetime, "parsed": {...} }, ... ],
      "ttm": { "NetIncome_TTM": ..., "OperatingCashFlow_TTM": ..., "FFO_TTM": ..., ... },
      "shares": <first shares found or None>,
      "raw_series": { ... },
      "entity": {"sic":..., "registrant_name":...}
    }
    """
    per_file = []
    for p in file_paths:
        try:
            parsed = extract_xbrl_metrics_improved(
                Path(p) if not isinstance(p, Path) else p
            )
            print(f" path {p}")
            print(f" audit: {parsed["_extraction_audit"]}")

            per_file.append(
                {
                    "path": p,
                    "dt": datetime.fromtimestamp(Path(p).stat().st_mtime),
                    "parsed": parsed,
                }
            )
        except Exception as e:
            # keep going if one file fails
            continue

    if not per_file:
        return {
            "files_used": [],
            "per_file": [],
            "ttm": {},
            "shares": None,
            "raw_series": {},
            "entity": {"sic": None, "registrant_name": None},
        }

    # order by date desc
    per_file = sorted(per_file, key=lambda x: x["dt"], reverse=True)

    # keys we aggregate for TTM (same names as in parsed)
    keys = [
        "NetIncome",
        "OperatingCashFlow",
        "CapitalExpenditures",
        "DividendsPaid",
        "FFO",
        "AFFO",
    ]
    series = {k: [] for k in keys}
    shares_list = []

    for entry in per_file:
        parsed = entry.get("parsed", {}) or {}
        for k in keys:
            v = parsed.get(k)
            if isinstance(v, (int, float)):
                series[k].append({"value": v, "path": entry["path"], "dt": entry["dt"]})
        shares_val = (
            parsed.get("SharesOutstanding")
            or parsed.get("sharesoutstanding")
            or parsed.get("Shares")
        )
        if isinstance(shares_val, (int, float)):
            shares_list.append(
                {"value": shares_val, "path": entry["path"], "dt": entry["dt"]}
            )

    def sum_top_k(k, kcount=4):
        vals = [
            it["value"]
            for it in series.get(k, [])[:kcount]
            if isinstance(it["value"], (int, float))
        ]
        return round(sum(vals), 2) if vals else None

    # ttm keys with suffix
    ttm = {f"{k}_TTM": sum_top_k(k, 4) for k in keys}
    shares = shares_list[0]["value"] if shares_list else None

    raw_series = {k: v for k, v in series.items()}

    # entity: take first non-empty entity info from per_file parsed
    entity = {"sic": None, "registrant_name": None}
    for entry in per_file:
        ent = entry.get("parsed", {}).get("entity", {}) or {}
        if ent and (ent.get("sic") or ent.get("registrant_name")):
            entity = ent
            break

    return {
        "files_used": [str(e["path"]) for e in per_file],
        "per_file": per_file,
        "ttm": ttm,
        "shares": shares,
        "raw_series": raw_series,
        "entity": entity,
    }


def detect_reit_enhanced(parsed_agg: dict, ticker: str = None):
    """
    Robust REIT detection:
    1) If FFO_TTM or AFFO_TTM exists => True
    2) If entity.sic == '6798' => True
    3) Look for indicators across per_file raw_elements and text snippets:
       - names containing 'ffo' or 'fundsfromoperations'
       - raw element texts containing 'funds from operations' or 'affo'
       - presence of keywords 'real estate investment trust' in parsed text rows
       If >=2 independent indicators => True
    """
    # 1) TTM direct check
    try:
        ttm = parsed_agg.get("ttm", {}) or {}
        if ttm.get("FFO_TTM") not in (None, 0) or ttm.get("AFFO_TTM") not in (None, 0):
            return True
    except Exception:
        pass

    # 2) SIC code check
    try:
        entity = parsed_agg.get("entity", {}) or {}
        sic = str(entity.get("sic") or "").strip()
        if sic:
            m = re.search(r"\d{2,4}", sic)
            if m and m.group(0) == "6798":
                return True
    except Exception:
        pass

    # 3) indicators count
    indicators = 0
    try:
        for entry in parsed_agg.get("per_file", []):
            parsed = entry.get("parsed", {}) or {}
            # raw element names
            for name in parsed.get("raw_elements", {}).keys():
                ln = name.lower()
                if "ffo" in ln or "fundsfromoperations" in ln:
                    indicators += 1
                    break
            # raw element texts
            for vlist in parsed.get("raw_elements", {}).values():
                for v in vlist:
                    txt = (v.get("text") or "").lower()
                    if (
                        "funds from operations" in txt
                        or "fundsfromoperations" in txt
                        or "affo" in txt
                    ):
                        indicators += 1
                        break
            # text snippet / row context: check common phrases
            # we don't have a big snippet stored, but raw_elements texts cover much
            # exit early if enough indicators
            if indicators >= 2:
                return True
    except Exception:
        pass

    return False
