"""
Verifica CIKs de la tabla funds contra EDGAR.
Modo 1 (default): solo reporta mismatches → genera reporte CSV para revisión manual
Modo 2 (--apply):  aplica correcciones del CSV aprobado

Uso:
  python AppTest/run_fix_fund_ciks.py           # genera reporte
  python AppTest/run_fix_fund_ciks.py --apply   # aplica correcciones
"""
import sys
import os
import csv
import time
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../AppValuations"))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Modulos_python import requests, json, re
from Modulos_Mysql import MarketScreen
from edgar_13f import (
    _sec_get, _get_latest_13f_accession, _find_holdings_xml,
    _load_13f_metadata, _save_13f_metadata,
    _13F_SAVE_DIR, _EDGAR_ARCHIVES_URL, _EDGAR_SUBMISSIONS_URL,
)

_HEADERS     = {"User-Agent": "AppOO research@appoo.com"}
_EFTS        = "https://efts.sec.gov/LATEST/search-index"
_REPORT_FILE = os.path.join(os.path.dirname(__file__), "fund_cik_mismatches.csv")


def _edgar_name(cik: str) -> str | None:
    r = _sec_get(_EDGAR_SUBMISSIONS_URL.format(cik=int(cik)))
    if r:
        return r.json().get("name", "").strip()
    return None


def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[,\.&/\-]", " ", name)
    name = re.sub(r"\b(inc|llc|lp|ltd|corp|co|the|group|management|advisors?|associates?|fund)\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _names_match(db_name: str, edgar_name: str) -> bool:
    a = _normalize(db_name)
    b = _normalize(edgar_name)
    if not a or not b:
        return True
    words_a = set(a.split())
    words_b = set(b.split())
    common = words_a & words_b
    return len(common) >= 2 or b in a or a in b


def _search_correct_cik(fund_name: str) -> tuple[str, str] | tuple[None, None]:
    """Busca CIK correcto en EDGAR. Retorna (cik, edgar_name) o (None, None)."""
    try:
        r = requests.get(
            _EFTS,
            params={"entity": fund_name, "forms": "13F-HR",
                    "dateRange": "custom", "startdt": "2025-07-01"},
            headers=_HEADERS, timeout=15,
        )
        hits = r.json().get("hits", {}).get("hits", [])
        for hit in hits[:3]:
            ciks = hit.get("_source", {}).get("ciks", [])
            if ciks:
                edgar_n = _edgar_name(ciks[0])
                time.sleep(0.1)
                if edgar_n and _names_match(fund_name, edgar_n):
                    return ciks[0], edgar_n
    except Exception as e:
        print(f"  _search_correct_cik({fund_name}): {e}")
    return None, None


def _download_xml(fund_name: str, cik: str, metadata: dict) -> bool:
    result = _get_latest_13f_accession(cik)
    if not result:
        return False
    accession, filing_date = result
    xml_file = _find_holdings_xml(cik, accession)
    if not xml_file:
        return False
    local_name = f"{cik}_{accession.replace('-', '')}_{xml_file}"
    local_path = os.path.join(_13F_SAVE_DIR, local_name)
    url = _EDGAR_ARCHIVES_URL.format(
        cik=int(cik), acc_no_dashes=accession.replace("-", ""), filename=xml_file,
    )
    r = _sec_get(url, timeout=60)
    if not r:
        return False
    with open(local_path, "wb") as f:
        f.write(r.content)
    metadata[local_name] = {"cik": cik, "fund_name": fund_name, "filing_date": filing_date}
    return True


def modo_reporte(top_n: int = 703):
    """Verifica todos los CIKs y genera CSV con mismatches para revisión manual."""
    market = MarketScreen()
    funds  = market.load_top_funds_with_cik(top_n)

    mismatches = []
    verified = 0
    errors = 0

    print(f"Verificando {len(funds)} fondos contra EDGAR (solo lectura)...")
    print("-" * 70)

    for i, (fund_name, cik) in enumerate(funds, 1):
        time.sleep(0.15)
        try:
            edgar_n = _edgar_name(cik)
            if not edgar_n:
                errors += 1
                continue

            if _names_match(fund_name, edgar_n):
                verified += 1
                if i % 100 == 0:
                    print(f"  [{i}/{len(funds)}] ok={verified} mismatches={len(mismatches)}")
                continue

            # Mismatch — buscar CIK correcto
            print(f"\n[{i}] MISMATCH: '{fund_name}'")
            print(f"       CIK actual {cik} → EDGAR: '{edgar_n}'")

            new_cik, new_edgar_n = _search_correct_cik(fund_name)
            time.sleep(0.3)

            print(f"       CIK sugerido: {new_cik or 'NO ENCONTRADO'} ({new_edgar_n or '-'})")

            mismatches.append({
                "fund_name"    : fund_name,
                "cik_actual"   : cik,
                "edgar_name_actual": edgar_n,
                "cik_sugerido" : new_cik or "",
                "edgar_name_sugerido": new_edgar_n or "",
                "aplicar"      : "S" if new_cik else "N",  # editar manualmente si querés cambiar
            })

        except Exception as e:
            print(f"  [{i}] ERROR {fund_name}: {e}")
            errors += 1

    # Guardar CSV
    with open(_REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "fund_name", "cik_actual", "edgar_name_actual",
            "cik_sugerido", "edgar_name_sugerido", "aplicar"
        ])
        writer.writeheader()
        writer.writerows(mismatches)

    print("\n" + "=" * 70)
    print(f"  verificados OK : {verified}")
    print(f"  mismatches     : {len(mismatches)}")
    print(f"  errores API    : {errors}")
    print(f"\nReporte guardado en: {_REPORT_FILE}")
    print("Revisá el CSV, ajustá la columna 'aplicar' (S/N) y ejecutá:")
    print("  python AppTest/run_fix_fund_ciks.py --apply")


def modo_aplicar():
    """Lee el CSV aprobado y aplica las correcciones marcadas con aplicar=S."""
    if not os.path.exists(_REPORT_FILE):
        print(f"ERROR: No existe {_REPORT_FILE}. Ejecutá primero sin --apply.")
        return

    market   = MarketScreen()
    metadata = _load_13f_metadata()
    os.makedirs(_13F_SAVE_DIR, exist_ok=True)

    with open(_REPORT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    to_apply = [r for r in rows if r.get("aplicar", "").strip().upper() == "S" and r.get("cik_sugerido")]
    print(f"Aplicando {len(to_apply)} correcciones de {len(rows)} en reporte...")
    print("-" * 70)

    corrected = 0
    failed = 0

    for row in to_apply:
        fund_name = row["fund_name"]
        old_cik   = row["cik_actual"]
        new_cik   = row["cik_sugerido"]
        print(f"\n  {fund_name}")
        print(f"    CIK: {old_cik} → {new_cik}")

        # Actualizar BD
        market.update_fund_cik(fund_name, new_cik)

        # Borrar XML viejo
        old_keys = [k for k, v in metadata.items() if v.get("cik") == old_cik and v.get("fund_name") == fund_name]
        for key in old_keys:
            old_path = os.path.join(_13F_SAVE_DIR, key)
            if os.path.exists(old_path):
                os.remove(old_path)
            del metadata[key]

        # Descargar XML nuevo
        time.sleep(0.5)
        ok = _download_xml(fund_name, new_cik, metadata)
        print(f"    XML nuevo: {'OK' if ok else 'FALLO'}")
        if ok:
            corrected += 1
        else:
            failed += 1

    _save_13f_metadata(metadata)
    print("\n" + "=" * 70)
    print(f"  corregidos: {corrected}  fallidos: {failed}")
    print("Listo. Re-corré sync_13f_holdings para actualizar fund_holdings.")


if __name__ == "__main__":
    if "--apply" in sys.argv:
        modo_aplicar()
    else:
        modo_reporte()
