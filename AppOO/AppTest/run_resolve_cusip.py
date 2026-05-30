"""
Diagnostico y fix EDGAR CUSIP resolver.
Usa la API correcta: efts.sec.gov con parametro q (no entity).
Correr: python AppTest/run_resolve_cusip.py
"""

import re
import time
import requests

_HEADERS = {"User-Agent": "AppOO research@appoo.com"}
_CUSIP_RE = re.compile(r"CUSIP[:\s#]*([A-Z0-9]{9})", re.I)


def _get_cik_by_ticker(ticker):
    """Busca CIK en el JSON de tickers de EDGAR."""
    try:
        r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=_HEADERS, timeout=15)
        data = r.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return int(entry["cik_str"])
    except Exception as e:
        print(f"  _get_cik_by_ticker({ticker}): {e}")
    return None


def _resolve_cusip_new(symbol, short_name):
    """Resuelve CUSIP via CIK lookup → submissions → filing header."""
    # Estrategia 1: CIK por ticker
    cik = _get_cik_by_ticker(symbol)
    if cik:
        print(f"  CIK por ticker: {cik}")
    else:
        # Estrategia 2: full-text search por nombre
        try:
            r = requests.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{short_name}"',
                    "forms": "10-K,20-F,40-F",
                    "dateRange": "custom",
                    "startdt": "2022-01-01",
                },
                headers=_HEADERS,
                timeout=15,
            )
            hits = r.json().get("hits", {}).get("hits", [])
            print(f"  full-text hits={len(hits)}")
            for hit in hits[:2]:
                src = hit.get("_source", {})
                ciks = src.get("ciks", [])
                entity = src.get("entity_name", "")
                print(f"    entity={entity!r} ciks={ciks}")
                if ciks:
                    cik = int(ciks[0])
                    break
        except Exception as e:
            print(f"  full-text search error: {e}")

    if not cik:
        return None

    # Obtener filings via submissions API
    try:
        sub_url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        r = requests.get(sub_url, headers=_HEADERS, timeout=15)
        subs = r.json()
        filings = subs.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accns = filings.get("accessionNumber", [])

        for form, accn in zip(forms, accns):
            if form not in ("10-K", "20-F", "40-F"):
                continue
            acc_clean = accn.replace("-", "")
            hdr_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{accn}.hdr.sgml"
            r2 = requests.get(hdr_url, headers=_HEADERS, timeout=10)
            if r2.ok:
                m = _CUSIP_RE.search(r2.text)
                if m:
                    return m.group(1).upper()
                # sin CUSIP en header → buscar en doc principal
                docs = filings.get("primaryDocument", [])
                idx = list(accns).index(accn)
                if idx < len(docs):
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{docs[idx]}"
                    r3 = requests.get(doc_url, headers=_HEADERS, stream=True, timeout=20)
                    if r3.ok:
                        raw = b""
                        for chunk in r3.iter_content(8192):
                            raw += chunk
                            if len(raw) >= 65536:
                                break
                        r3.close()
                        m = _CUSIP_RE.search(raw.decode("utf-8", errors="ignore"))
                        if m:
                            return m.group(1).upper()
            time.sleep(0.3)
            break  # solo probar el más reciente

    except Exception as e:
        print(f"  submissions error: {e}")

    return None


TARGETS = [
    ("BABA", "Alibaba Group Holding Limited"),
    ("BTG", "B2Gold Corp"),
    ("PHYS", "Sprott Physical Gold Trust"),
    ("VST", "Vistra Corp"),
]

print(f"{'Symbol':<8} {'ShortName':<35} CUSIP")
print("-" * 65)
for sym, name in TARGETS:
    print(f"\n>>> {sym} / {name}")
    cusip = _resolve_cusip_new(sym, name)
    print(f"  RESULTADO: {cusip if cusip else '❌ no encontrado'}")
