"""
test_sc13dg_parser.py
Analiza TODOS los SC 13D/G de SEC EDGAR donde CCI es el sujeto.
Muestra: filers únicos, distribución 13D/G, pct declarado, solapamiento con 13F.
"""

import sys
import os
import re
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

HEADERS = {"User-Agent": "InversionesWildaga Research (research@test.com)"}
SUBJECT_NAME = "Crown Castle"
MAX_FILINGS = 50  # tope para no saturar EDGAR


# ── helpers ─────────────────────────────────────────────────────────────────


def _get(url, **kw):
    """GET con rate-limit 0.5 s."""
    time.sleep(0.5)
    return requests.get(url, headers=HEADERS, timeout=20, **kw)


def buscar_filings_efts(nombre: str, desde: str = "2020-01-01") -> list[dict]:
    """
    Busca SC 13D/G en EDGAR full-text search donde el sujeto es `nombre`.
    Devuelve lista de dicts: {accession, form, date, cik_filer}.
    """
    print(f"\n{'='*60}")
    print(f"EDGAR full-text search: SC 13D/G sobre '{nombre}' desde {desde}")
    print(f"{'='*60}")

    url = (
        "https://efts.sec.gov/LATEST/search-index?"
        f"q=%22{nombre.replace(' ', '+')}%22"
        f"&forms=SC+13G,SC+13D,SC+13G%2FA,SC+13D%2FA"
        f"&dateRange=custom&startdt={desde}&enddt=2026-12-31"
        f"&hits.hits._source=file_date,form_type,entity_name,ciks"
        f"&hits.hits.total=true&hits.hits.max=100"
    )
    r = _get(url)
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    total_hits = data.get("hits", {}).get("total", {})
    print(f"  Total hits EDGAR: {total_hits}")

    filings = []
    for h in hits[:MAX_FILINGS]:
        src = h.get("_source", {})
        raw_id = h.get("_id", "")
        # _id puede ser "0001086364-24-008417:filename.txt" o solo accession
        accession = raw_id.split(":")[0] if ":" in raw_id else raw_id
        ciks = src.get("ciks", [])
        filings.append(
            {
                "accession": accession,
                "form": src.get("form_type", ""),
                "date": src.get("file_date", ""),
                "cik_filer": ciks[0] if ciks else None,
            }
        )

    print(f"  Filings parseados: {len(filings)}")
    return filings


def obtener_sgml_header(accession: str, cik_filer: str) -> str:
    """Descarga sólo los primeros 8 KB del .txt del filing (el SGML header)."""
    if not cik_filer:
        return ""
    acc_clean = accession.replace("-", "")
    cik_int = int(cik_filer.lstrip("0") or "0")
    txt_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accession}.txt"
    try:
        r = _get(txt_url, stream=True)
        content = b""
        for chunk in r.iter_content(4096):
            content += chunk
            if len(content) >= 8192:
                break
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        return ""


def parsear_sgml_header(texto: str) -> dict:
    """Extrae filer_name, filer_cik, subject_company, form_type, filed_date del SGML."""
    datos = {}

    m = re.search(r"CONFORMED SUBMISSION TYPE:\s*(.+)", texto)
    if m:
        datos["form_type"] = m.group(1).strip()

    m = re.search(r"FILED AS OF DATE:\s*(\d+)", texto)
    if m:
        raw = m.group(1)
        datos["filed_date"] = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"

    m = re.search(r"SUBJECT COMPANY:\s*\n.*?COMPANY CONFORMED NAME:\s*(.+)", texto, re.S)
    if m:
        datos["subject_company"] = m.group(1).strip().split("\n")[0].strip()

    m = re.search(r"FILED BY:\s*\n.*?COMPANY CONFORMED NAME:\s*(.+)", texto, re.S)
    if m:
        datos["filer_name"] = m.group(1).strip().split("\n")[0].strip()

    m = re.search(r"FILED BY:\s*\n.*?CENTRAL INDEX KEY:\s*(\d+)", texto, re.S)
    if m:
        datos["filer_cik"] = m.group(1).strip()

    return datos


def parsear_pct(texto: str) -> float | None:
    """Extrae pct_class del cuerpo del filing (primeros 50 KB)."""
    texto_limpio = re.sub(r"<[^>]+>", " ", texto)
    texto_limpio = re.sub(r"&nbsp;|&amp;|&lt;|&gt;", " ", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio)

    for pat in [
        r"(?:Percent of Class|percent of the class)[^\d]*([\d\.]+)\s*%",
        r"([\d]+\.[\d]+)\s*%\s*(?:of the|of outstanding)",
    ]:
        m = re.search(pat, texto_limpio, re.I)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def obtener_doc_completo(accession: str, cik_filer: str, primary_doc: str = None) -> str:
    """Descarga hasta 50 KB del documento principal para extraer pct_class."""
    if not cik_filer:
        return ""
    acc_clean = accession.replace("-", "")
    cik_int = int(cik_filer.lstrip("0") or "0")

    # Intentar index JSON para hallar primary doc
    if not primary_doc:
        idx_url = f"https://data.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accession}-index.json"
        try:
            r = _get(idx_url)
            if r.status_code == 200:
                items = r.json().get("directory", {}).get("item", [])
                for item in items:
                    name = item.get("name", "")
                    if name.endswith((".htm", ".html", ".txt")) and "index" not in name.lower():
                        primary_doc = name
                        break
        except Exception:
            pass

    if primary_doc:
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{primary_doc}"
        try:
            r = _get(doc_url, stream=True)
            content = b""
            for chunk in r.iter_content(8192):
                content += chunk
                if len(content) >= 50000:
                    break
            return content.decode("utf-8", errors="ignore")
        except Exception:
            pass

    # Fallback: txt completo (primeros 50 KB)
    txt_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accession}.txt"
    try:
        r = _get(txt_url, stream=True)
        content = b""
        for chunk in r.iter_content(8192):
            content += chunk
            if len(content) >= 50000:
                break
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""


# ── main ────────────────────────────────────────────────────────────────────


def main():
    filings = buscar_filings_efts(SUBJECT_NAME, desde="2020-01-01")

    if not filings:
        print("Sin filings encontrados.")
        return

    # ── Fase 1: leer SGML header de cada filing ──────────────────────────
    print(f"\n{'='*60}")
    print(f"FASE 1 — Leyendo SGML headers ({len(filings)} filings)...")
    print(f"{'='*60}")

    registros = []
    for i, f in enumerate(filings):
        acc = f["accession"]
        cik_f = f["cik_filer"]
        sgml = obtener_sgml_header(acc, cik_f)
        header = parsear_sgml_header(sgml) if sgml else {}

        rec = {
            "accession": acc,
            "form": header.get("form_type") or f["form"],
            "date": header.get("filed_date") or f["date"],
            "filer_name": header.get("filer_name", "(sin nombre)"),
            "filer_cik": header.get("filer_cik") or cik_f,
            "subject_company": header.get("subject_company", ""),
            "pct_class": None,
        }
        print(f"  [{i+1:02d}] {rec['date']} | {rec['form']:<10} | {rec['filer_name'][:40]}")
        registros.append(rec)

    # ── Fase 2: extraer pct_class de los más recientes por filer ─────────
    print(f"\n{'='*60}")
    print("FASE 2 — Extrayendo pct_class (más reciente por filer)...")
    print(f"{'='*60}")

    # Agrupar por filer_cik, tomar el más reciente
    ultimo_por_filer: dict[str, dict] = {}
    for rec in registros:
        cik = rec["filer_cik"] or rec["filer_name"]
        if cik not in ultimo_por_filer or rec["date"] > ultimo_por_filer[cik]["date"]:
            ultimo_por_filer[cik] = rec

    filers_activos = list(ultimo_por_filer.values())

    for rec in filers_activos:
        texto = obtener_doc_completo(rec["accession"], rec["filer_cik"])
        pct = parsear_pct(texto) if texto else None
        rec["pct_class"] = pct
        pct_str = f"{pct:.2f}%" if pct else "N/A"
        print(f"  {rec['filer_name'][:40]:<40} {pct_str}")

    # ── Análisis final ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("ANÁLISIS CONSOLIDADO")
    print(f"{'='*60}")

    # Distribución de form types
    from collections import Counter

    form_dist = Counter(r["form"] for r in registros)
    print("\n  Distribución de form types:")
    for ftype, cnt in sorted(form_dist.items()):
        print(f"    {ftype:<12}: {cnt} filings")

    # Filers únicos
    print(f"\n  Filers únicos (posición más reciente):")
    print(f"  {'Filer':<45} {'Form':<10} {'Fecha':<12} {'Pct':>7}")
    print(f"  {'-'*45} {'-'*10} {'-'*12} {'-'*7}")
    filers_con_pct = sorted(filers_activos, key=lambda x: (x["pct_class"] or 0), reverse=True)
    for rec in filers_con_pct:
        pct_str = f"{rec['pct_class']:.2f}%" if rec["pct_class"] else "N/A"
        print(f"  {rec['filer_name'][:45]:<45} {rec['form']:<10} {rec['date']:<12} {pct_str:>7}")

    # Totales
    total_pct = sum(r["pct_class"] for r in filers_activos if r["pct_class"])
    con_pct = sum(1 for r in filers_activos if r["pct_class"])
    print(f"\n  Total filers únicos     : {len(filers_activos)}")
    print(f"  Con pct_class extraído  : {con_pct}/{len(filers_activos)}")
    print(f"  Suma pct declarado      : {total_pct:.2f}%  (holders >5%)")
    print(f"  → Nuestro fh_count cubre: todos los holders 13F")
    print(f"  → SC 13D/G cubre        : solo los que superan 5% del float")

    # Solapamiento esperado con 13F
    print(f"\n  Diagnóstico solapamiento SC 13D/G vs 13F:")
    print(f"  • SC 13G: holders PASIVOS >5% (fondos índice, ETFs)")
    print(f"  • SC 13D: holders ACTIVOS >5% (activistas, intención de influir)")
    print(f"  • 13F   : TODOS los holders institucionales (sin umbral %)")
    print(f"  • Los filers de SC 13D/G SIEMPRE aparecen en 13F (misma posición)")
    print(f"  • Tabla separada sc13dg_holdings: señal de concentración y activismo")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
