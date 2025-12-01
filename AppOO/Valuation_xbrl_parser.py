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
import zipfile
import xml.etree.ElementTree as ET
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


def debug_list_all_tags_from_xml_string(xml_string, limit=200):
    """
    Lista tags (local-name) encontrados en el mini-XML generado desde iXBRL.
    Útil para identificar cómo una empresa etiqueta FFO, AFFO, Revenues, etc.
    """
    try:
        root = ET.fromstring(xml_string)
    except Exception as e:
        print("[debug] ERROR parsing XML:", e)
        return

    print("\n============================")
    print("TAGS ENCONTRADOS EN MINI-XML")
    print("============================")

    count = 0
    seen = set()

    for el in root.iter():
        if count >= limit:
            print("... (limit reached)")
            break

        tag = el.tag
        if "}" in tag:
            local = tag.split("}", 1)[1]
        else:
            local = tag

        if local in seen:
            continue
        seen.add(local)

        txt = (el.text or "").strip().replace("\n", " ")

        print(f"- {local}: '{txt[:80]}'")
        count += 1

    print("============================\n")


# ------------------------------------------------------
# Extrae .zip sin realizar escritura en disco
# ------------------------------------------------------
def extract_from_zip(zip_path):
    """
    Abre un ZIP XBRL y devuelve una lista de (archivo, contenido_xml)
    sin escribir nada a disco.
    """
    results = []

    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.lower().endswith(".xml"):  # solo XML relevantes
                try:
                    data = z.read(name).decode("utf-8", errors="ignore")
                    results.append((name, data))
                except Exception:
                    continue

    return results


# ------------------------------------------------------
# Detección automática y parsing
# ------------------------------------------------------
def parse_xbrl_auto(path_like):
    """
    Detección automática de XBRL:
      - HTML/iXBRL → extracción robusta de ix:nonFraction + wrap XML válido.
      - XML → parse directo.
      - ZIP → extrae xmls, prioriza instance, parsea y fusiona.
    """

    p = Path(path_like) if not isinstance(path_like, Path) else path_like
    suffix = p.suffix.lower()

    print(f"[parse_xbrl_auto] usando: {p}, tipo: {suffix}")

    # ---------------------------------------------------
    # Helper: genera cabecera con TODOS los prefijos detectados
    # ---------------------------------------------------
    def wrap_with_namespaces(mini_xml: str):
        """
        Detecta prefijos usados en el mini-XML y genera xmlns:* automático.
        Garantiza que el XML sea 100% parseable.
        """
        prefixes_needed = set()

        # buscar prefijos tipo "xbrli:" o "ix:"
        for m in re.findall(r"([A-Za-z0-9_\-]+):[A-Za-z0-9_\-]+", mini_xml):
            prefixes_needed.add(m)

        # namespaces comunes del ecosistema XBRL
        ns_map = {
            "xbrli": "http://www.xbrl.org/2003/instance",
            "link": "http://www.xbrl.org/2003/linkbase",
            "xlink": "http://www.w3.org/1999/xlink",
            "ix": "http://www.xbrl.org/2013/inlineXBRL",
            "xbrldi": "http://xbrl.org/2006/xbrldi",
            "iso4217": "http://www.xbrl.org/2003/iso4217",
            "utr": "http://www.xbrl.org/2009/utr",
            "dei": "http://xbrl.sec.gov/dei/2022-01-31",
            "us-gaap": "http://fasb.org/us-gaap/2022-01-31",
            "us-roles": "http://fasb.org/us-roles/2022-01-31",
            "srt": "http://fasb.org/srt",
            "num": "http://www.xbrl.org/dtr/type/numeric",
            "nonnum": "http://www.xbrl.org/dtr/type/non-numeric",
            "xbrldt": "http://xbrl.org/2005/xbrldt",
        }

        # construir xmlns dinámicos
        ns_parts = []
        for pref in prefixes_needed:
            if pref in ns_map:
                ns_parts.append(f'xmlns:{pref}="{ns_map[pref]}"')
            else:
                # namespace desconocido → generar un placeholder válido
                ns_parts.append(f'xmlns:{pref}="http://auto.namespace/{pref}"')

        ns_text = " ".join(ns_parts)

        wrapped = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f"<xbrl {ns_text}>\n"
            f"{mini_xml}\n"
            "</xbrl>"
        )

        print("[wrap_with_namespaces] namespaces agregados:", prefixes_needed)
        return wrapped

    # ---------------------------------------------------
    # 1) HTML / INLINE iXBRL
    # ---------------------------------------------------
    if suffix in (".htm", ".html"):

        try:
            html = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            print("[parse_xbrl_auto] ERROR leyendo HTML")
            return {}

        # --- EXTRACCIÓN INLINE ROBUSTA ---
        mini = extract_inline_xbrl_from_html(html)
        print("[parse_xbrl_auto] inline extraído? ->", bool(mini))

        if mini:
            print("[mini-inline-preview]:", mini[:400])

        if mini:
            try:
                # limpieza de entidades
                mini_clean = (
                    mini.replace("&nbsp;", " ")
                    .replace("&amp;", "&")
                    .replace("&ndash;", "-")
                    .replace("&mdash;", "-")
                )

                # NUEVO WRAP → usa namespaces dinámicos detectados
                wrapped = wrap_with_namespaces(mini_clean)

                print("[parse_xbrl_auto] XML WRAPPED generado.")
                debug_list_all_tags_from_xml_string(wrapped)

                parsed = parse_xml_string(wrapped)

                if parsed:
                    return parsed

                print("[parse_xbrl_auto] Falló parse de inline → fallback")

            except Exception as e:
                print("[parse_xbrl_auto] EXCEPTION procesando inline:", e)

        # Fallback → HTML extractor
        print("[parse_xbrl_auto] usando fallback extract_xbrl_metrics_improved()")
        try:
            return extract_xbrl_metrics_improved(p) or {}
        except Exception:
            return {}

    # ---------------------------------------------------
    # 2) XML directo
    # ---------------------------------------------------
    if suffix == ".xml":
        try:
            xml_text = p.read_text(encoding="utf-8", errors="ignore")
            return parse_xml_string(xml_text) or {}
        except Exception:
            print("[parse_xbrl_auto] ERROR leyendo XML")
            return {}

    # ---------------------------------------------------
    # 3) ZIP → múltiples XML
    # ---------------------------------------------------
    if suffix == ".zip":
        try:
            xml_entries = extract_from_zip(p)
        except Exception:
            xml_entries = []

        if not xml_entries:
            print("[parse_xbrl_auto] ZIP vacío")
            return {}

        def is_linkbase(n):
            n = n.lower()
            return any(x in n for x in ("_cal.xml", "_pre.xml", "_lab.xml", "_def.xml"))

        candidates = [x for x in xml_entries if not is_linkbase(x[0])]
        if not candidates:
            candidates = xml_entries

        merged = {}

        for name, xml_text in candidates:
            try:
                if (
                    "<context" not in xml_text.lower()
                    and "<xbrl" not in xml_text.lower()
                    and "ix:" not in xml_text.lower()
                ):
                    continue

                parsed_local = parse_xml_string(xml_text) or {}
                for k, v in parsed_local.items():
                    if v is None:
                        continue
                    if merged.get(k) is None:
                        merged[k] = v
            except:
                continue

        if not merged:
            for name, xml_text in xml_entries:
                try:
                    parsed_local = parse_xml_string(xml_text) or {}
                    for k, v in parsed_local.items():
                        if v is None:
                            continue
                        if merged.get(k) is None:
                            merged[k] = v
                except:
                    continue

        return merged

    # ---------------------------------------------------
    # 4) fallback final
    # ---------------------------------------------------
    return {}


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
        d = parse_date(c["end"]) if c.get("end") else None
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


# ------------------------------------------------------
# parse standar directamente desde ZIP
# ------------------------------------------------------
def parse_xml_string(xml_string):
    """
    Parser universal para XBRL con namespaces dinámicos (versión robusta).
    Extrae métricas GAAP + FFO/AFFO típicas de REITs.
    Evita XPath complejos: busca por local-name iterando el árbol.
    """
    out = {
        "NetIncome": None,
        "OperatingCashFlow": None,
        "CapitalExpenditures": None,
        "DividendsPaid": None,
        "SharesOutstanding": None,
        "FFO": None,
        "AFFO": None,
        "entity": {"sic": None, "registrant_name": None},
        "_extraction_audit": [],
    }

    try:
        # parse XML (ElementTree)
        root = ET.fromstring(xml_string)

        # función para obtener local-name (quita namespace si existe)
        def local_name(tag):
            if isinstance(tag, str) and "}" in tag:
                return tag.split("}", 1)[1]
            return tag

        # función que busca el primer elemento cuyo local-name está en possible_tags
        # y cuyo texto parece un número (entero o float). Devuelve texto sin limpiar.
        def find_tag_by_localname(possible_tags):
            poss = set(possible_tags)
            for el in root.iter():
                ln = local_name(el.tag)
                if ln in poss:
                    txt = el.text
                    if txt:
                        txt = txt.strip()
                        # normalizar numeros simples: quitar comas y signos de paréntesis
                        txt_norm = txt.replace(",", "").replace("\u2212", "-")
                        if txt_norm.startswith("(") and txt_norm.endswith(")"):
                            txt_norm = "-" + txt_norm[1:-1]
                        # permitir floats/ints negativos
                        if re.match(r"^-?\d+(\.\d+)?$", txt_norm):
                            # devolver como float (si contiene punto) o int
                            try:
                                if "." in txt_norm:
                                    return float(txt_norm)
                                else:
                                    return float(int(txt_norm))
                            except Exception:
                                # si falla conversión, devolver None y seguir
                                continue
            return None

        # extraer por lista de nombres esperados (sin namespace)
        out["NetIncome"] = find_tag_by_localname(
            ["NetIncomeLoss", "ProfitLoss", "NetIncome", "NetEarnings"]
        )
        out["OperatingCashFlow"] = find_tag_by_localname(
            [
                "NetCashProvidedByUsedInOperatingActivities",
                "NetCashProvidedByOperatingActivities",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ]
        )
        out["CapitalExpenditures"] = find_tag_by_localname(
            [
                "CapitalExpenditures",
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
            ]
        )
        out["DividendsPaid"] = find_tag_by_localname(
            ["PaymentsOfDividends", "DividendsPaid", "DividendsDeclared"]
        )
        out["SharesOutstanding"] = find_tag_by_localname(
            [
                "WeightedAverageNumberOfSharesOutstandingBasic",
                "WeightedAverageNumberOfSharesOutstanding",
                "CommonStockSharesOutstanding",
                "SharesOutstanding",
            ]
        )

        # REIT: FFO / AFFO (buscamos varios tag names posibles)
        out["FFO"] = find_tag_by_localname(
            [
                "FundsFromOperations",
                "FFO",
                "FundsFromOperationsBasic",
                "FundsFromOperationsContinuingOperations",
            ]
        )
        out["AFFO"] = find_tag_by_localname(
            ["AdjustedFundsFromOperations", "AFFO", "AdjustedFundsFromOperationsBasic"]
        )

        # entity / DEI: buscar codigo SIC y registrant name (texto simple)
        # SIC: buscar un elemento con local-name 'EntityCentralIndexKey' o 'EntitySIC'
        # Si no es numérico, lo dejamos como None
        sic_val = None
        registrant = None
        for el in root.iter():
            ln = local_name(el.tag)
            if ln in (
                "EntityCentralIndexKey",
                "EntityRegistrantIdentifier",
                "EntitySIC",
                "SIC",
            ):
                txt = (el.text or "").strip()
                if txt:
                    # si parece numero (ECIK es numeric-like) guardar
                    if re.match(r"^\d+$", txt):
                        sic_val = txt
                        break
            if ln in ("EntityRegistrantName", "RegistrantName", "EntityRegistrant"):
                txt = (el.text or "").strip()
                if txt:
                    registrant = txt
                    # no break: queremos dar preferencia a sic si aparece luego

        out["entity"]["sic"] = sic_val
        out["entity"]["registrant_name"] = registrant

        out["_extraction_audit"].append("parse_xml_string OK (iterative search)")

    except ET.ParseError as e:
        out["_extraction_audit"].append(f"ERROR: parse error: {e}")
    except Exception as e:
        out["_extraction_audit"].append(f"ERROR: {e}")

    return out


# ------------------------------------------------------
# Normaliza números inline
# ------------------------------------------------------
def _normalize_inline_number(s: str):
    """
    Normaliza valores numéricos de iXBRL:
      - "(1,234)"   -> "-1234"
      - "1,234.56"  -> "1234.56"
      - "−123"      -> "-123"        (minus unicode)
      - " 1 234 "   -> "1234"
      - "P5D", "Q3", "2025", fechas → se devuelven sin tocar

    Regresa:
        string normalizado o None si está vacío.
    """
    if s is None:
        return None

    t = s.strip()
    if t == "":
        return None

    # ⚠️ Si contiene letras mezcladas con números, lo dejamos como está
    # Ej: "Q3", "P5D", "September 30, 2025"
    if re.search(r"[A-Za-z]", t):
        return t

    # Reemplazos básicos
    t = t.replace("\u2212", "-")  # unicode minus
    t = t.replace(",", "")

    # (1234) → -1234
    if t.startswith("(") and t.endswith(")"):
        t = "-" + t[1:-1]

    # Si después de procesar no queda nada, devolver None
    t2 = t.strip()
    if t2 == "":
        return None

    return t2


# ------------------------------------------------------
# Extrae inline XBRL desde HTML/iXBRL
# ------------------------------------------------------
def extract_inline_xbrl_from_html(html_text: str):
    """
    Extrae hechos inline XBRL desde HTML/iXBRL y produce un mini-XML consistente,
    sin prefijos, con contextos y unidades reconstruidos correctamente.

    Esta versión:
      - NO copia <context> ni <unit> del HTML.
      - Reconstruye contextos a partir de los contextRef detectados.
      - Soporta ix:nonFraction, ix:nonNumeric, Workiva, data-*.
      - Produce XML limpio sin prefijos (lo que tu motor espera).
    """

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(html_text, "lxml")

    # -------------------------------------------
    # 1) Detectar todos los hechos inline
    # -------------------------------------------

    # candidatos
    candidates = []

    # A) ix:nonfraction / ix:nonnumeric
    candidates.extend(
        soup.find_all(
            lambda t: t.name
            and any(kw in t.name.lower() for kw in ("ix:nonfraction", "ix:nonnumeric"))
        )
    )

    # B) nombres que terminan nonfraction/nonnumeric (Workiva)
    candidates.extend(
        soup.find_all(
            lambda t: t.name
            and (
                t.name.lower().endswith("nonfraction")
                or t.name.lower().endswith("nonnumeric")
            )
        )
    )

    # C) tags con name, data-name
    candidates.extend(
        [
            t
            for t in soup.find_all(True)
            if t.has_attr("name") or t.has_attr("data-name")
        ]
    )

    # D) tags con metadata Workiva data-*
    for t in soup.find_all(True):
        for k in t.attrs:
            if k.startswith("data-") and any(x in k for x in ("fact", "name", "ix")):
                candidates.append(t)
                break

    # remover duplicados
    seen = set()
    inline_tags = []
    for t in candidates:
        ident = id(t)
        if ident in seen:
            continue
        seen.add(ident)
        inline_tags.append(t)

    # -------------------------------------------
    # 2) Procesar hechos → lista de dicts
    # -------------------------------------------
    extracted_facts = []
    context_refs = set()
    unit_refs = set()

    for tag in inline_tags:
        # nombre del hecho
        name_attr = (
            tag.get("name")
            or tag.get("data-name")
            or tag.get("data-fact-name")
            or tag.get("data-ix-name")
        )

        if not name_attr:
            name_attr = tag.get("title") or tag.get("aria-label")

        if not name_attr:
            # buscar strings tipo "us-gaap:Revenues"
            for v in tag.attrs.values():
                if isinstance(v, str) and ":" in v:
                    if re.match(r"[A-Za-z0-9_\-]+:[A-Za-z0-9_]+", v):
                        name_attr = v
                        break

        if not name_attr:
            continue

        local = name_attr.split(":")[-1].strip()

        # contextRef, unitRef
        ctx = (
            tag.get("contextref")
            or tag.get("contextRef")
            or tag.get("data-context")
            or tag.get("context")
        )
        unit = (
            tag.get("unitref")
            or tag.get("unitRef")
            or tag.get("data-unit")
            or tag.get("unit")
        )
        decimals = tag.get("decimals") or tag.get("data-decimals")

        # valor
        txt = tag.get_text(" ", strip=True)
        val = _normalize_inline_number(txt)
        if not val:
            alt = tag.get("value") or tag.get("content") or tag.get("data-value")
            if alt:
                val = _normalize_inline_number(alt)

        if not val:
            continue

        if ctx:
            context_refs.add(ctx)
        if unit:
            unit_refs.add(unit)

        extracted_facts.append(
            {
                "local": local,
                "value": val,
                "ctx": ctx,
                "unit": unit,
                "decimals": decimals,
            }
        )

    if not extracted_facts:
        return ""

    # -------------------------------------------
    # 3) Reconstruir contextos limpios
    # -------------------------------------------
    contexts_xml = []
    for c in sorted(context_refs):
        # ⚠️ No sabemos periodos reales aquí (intervalos).
        # Generamos context placeholder seguro, consistente.
        contexts_xml.append(
            f'<context id="{c}"><entity><identifier>Dummy</identifier></entity>'
            f"<period><instant>1970-01-01</instant></period></context>"
        )

    # -------------------------------------------
    # 4) Reconstruir units (solo placeholder)
    # -------------------------------------------
    units_xml = []
    for u in sorted(unit_refs):
        units_xml.append(f'<unit id="{u}"><measure>pure</measure></unit>')

    # -------------------------------------------
    # 5) Construir los hechos
    # -------------------------------------------
    facts_xml = []
    for f in extracted_facts:
        attrs = []
        if f["ctx"]:
            attrs.append(f'contextRef="{f["ctx"]}"')
        if f["unit"]:
            attrs.append(f'unitRef="{f["unit"]}"')
        if f["decimals"] is not None:
            attrs.append(f'decimals="{f["decimals"]}"')

        attr_text = (" " + " ".join(attrs)) if attrs else ""

        val = f["value"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        facts_xml.append(f"<{f['local']}{attr_text}>{val}</{f['local']}>")

    # -------------------------------------------
    # 6) Armar mini-XBRL final
    # -------------------------------------------
    mini = ["<xbrl>"]
    mini.extend(contexts_xml)
    mini.extend(units_xml)
    mini.extend(facts_xml)
    mini.append("</xbrl>")

    return "\n".join(mini)


# ------------------------------------------------------
# # Facade: aggregate_xbrl_metrics + REIT detector
# ------------------------------------------------------
def aggregate_xbrl_metrics(file_paths):
    """
    Produce parsed_agg compatible con lo que espera Valuation_engine:
    {
      "files_used": [...],
      "per_file": [...],
      "ttm": {...},
      "shares": ...,
      "raw_series": {...},
      "entity": {...}
    }
    """
    per_file = []

    for p in file_paths:
        # ----------------------------------------------
        # SOPORTE PARA FORMATOS:
        #  - path::INLINE
        #  - path::instance.xml
        #  - path normal
        # ----------------------------------------------
        if "::" in str(p):
            base_path, suffix = str(p).split("::", 1)
            base_path = Path(base_path)

            # ==========================================================
            # CASO INLINE iXBRL
            # ==========================================================
            if suffix.upper() == "INLINE":
                try:
                    with open(base_path, "r", encoding="utf-8", errors="ignore") as f:
                        html = f.read()

                    # 1) mini-inline extractor
                    xml_text = extract_inline_xbrl_from_html(html)

                    # Heurística para verificar si vale la pena intentar parsear
                    looks_like_xml = (
                        xml_text
                        and isinstance(xml_text, str)
                        and xml_text.count("<") >= 5
                        and xml_text.count(">") >= 5
                    )

                    parsed = None

                    # Intentar parse si parece XML real
                    if looks_like_xml:
                        try:
                            parsed = parse_xml_string(xml_text)
                        except Exception:
                            parsed = None

                    # 2) Fallback SIEMPRE que mini-inline falle
                    if not parsed:
                        parsed = parse_xbrl_auto(base_path)

                    per_file.append(
                        {
                            "path": f"{base_path}::INLINE",
                            "dt": datetime.fromtimestamp(base_path.stat().st_mtime),
                            "parsed": parsed or {},
                        }
                    )
                except Exception as e:
                    print(f"INLINE ERROR {base_path}: {e}")
                continue

            # ==========================================================
            # CASO ZIP::instance.xml
            # ==========================================================
            elif base_path.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(base_path, "r") as z:
                        if suffix in z.namelist():
                            xml_text = z.read(suffix).decode("utf-8", errors="ignore")
                            parsed = parse_xml_string(xml_text)
                        else:
                            parsed = {}
                except Exception as e:
                    print(f"ZIP INSTANCE ERROR {base_path}::{suffix}: {e}")
                    continue

                per_file.append(
                    {
                        "path": f"{base_path}::{suffix}",
                        "dt": datetime.fromtimestamp(base_path.stat().st_mtime),
                        "parsed": parsed,
                    }
                )
                continue  # fin ZIP

    # ----------------------------------------------------------------
    # Si no se pudo procesar nada
    # ----------------------------------------------------------------
    if not per_file:
        return {
            "files_used": [],
            "per_file": [],
            "ttm": {},
            "shares": None,
            "raw_series": {},
            "entity": {"sic": None, "registrant_name": None},
        }

    # ----------------------------------------------------------------
    # ORDENAR archivos por fecha
    # ----------------------------------------------------------------
    per_file = sorted(per_file, key=lambda x: x["dt"], reverse=True)

    # ----------------------------------------------------------------
    # SERIES A AGREGAR
    # ----------------------------------------------------------------
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

    # Procesar todos los parseados
    for entry in per_file:
        parsed = entry.get("parsed", {}) or {}

        # series numéricas para TTM
        for k in keys:
            v = parsed.get(k)
            if isinstance(v, (int, float)):
                series[k].append({"value": v, "path": entry["path"], "dt": entry["dt"]})

        # shares
        shares_val = (
            parsed.get("SharesOutstanding")
            or parsed.get("sharesoutstanding")
            or parsed.get("Shares")
        )
        if isinstance(shares_val, (int, float)):
            shares_list.append(
                {"value": shares_val, "path": entry["path"], "dt": entry["dt"]}
            )

    # ----------------------------------------------------------------
    # TTM: suma últimos 4
    # ----------------------------------------------------------------
    def sum_top_k(k, kcount=4):
        vals = [
            it["value"]
            for it in series.get(k, [])[:kcount]
            if isinstance(it["value"], (int, float))
        ]
        return round(sum(vals), 2) if vals else None

    ttm = {f"{k}_TTM": sum_top_k(k, 4) for k in keys}

    # Shares
    shares = shares_list[0]["value"] if shares_list else None

    raw_series = {k: v for k, v in series.items()}

    # ----------------------------------------------------------------
    # ENTITY INFO
    # ----------------------------------------------------------------
    entity = {"sic": None, "registrant_name": None}
    for entry in per_file:
        ent = entry.get("parsed", {}).get("entity", {}) or {}
        if ent and (ent.get("sic") or ent.get("registrant_name")):
            entity = ent
            break

    print(f"aggregate_xbrl_metrics: processed {per_file} files.")

    return {
        "files_used": [str(e["path"]) for e in per_file],
        "per_file": per_file,
        "ttm": ttm,
        "shares": shares,
        "raw_series": raw_series,
        "entity": entity,
    }


# ------------------------------------------------------
# Heuristica robusta para detectar REITs
# ------------------------------------------------------
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
