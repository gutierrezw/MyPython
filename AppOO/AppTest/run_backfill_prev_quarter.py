"""
run_backfill_prev_quarter.py
Script one-time: descarga el filing 13F-HR del trimestre ANTERIOR para los fondos
que tienen posiciones en símbolos de cartera.

Objetivo: dar baseline histórico para que al reprocessar los filings actuales,
la comparación de shares genere BUY/SELL/HOLD reales en vez de todo "NEW".

Flujo:
  1. Obtener fund_ids/CIKs de fondos con posiciones en cartera
  2. Para cada CIK: bajar 2do 13F-HR más reciente de EDGAR
  3. Insertar en fund_filings (processed=0) si no existe ya
  4. Resetear processed=0 para los filings actuales de esos fondos
  5. Borrar fund_holdings de esos fondos (para que el reprocess sea limpio)
  6. Correr sync_13f_holdings → prev quarter = NEW, current = BUY/SELL/HOLD real

Correr desde AppTest/:  python run_backfill_prev_quarter.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import requests, time, logging
from Modulos_Mysql import MarketScreen
from AppValuations.edgar_13f import (
    _sec_get, _find_holdings_xml, sync_13f_holdings,
    _EDGAR_SUBMISSIONS_URL, _EDGAR_ARCHIVES_URL, _13F_SAVE_DIR,
)

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s")
_logger = logging.getLogger("backfill_prev_quarter")

ACCOUNT = "U4214563"   # cuenta stock


def _fmt_accession(acc_no_dashes: str) -> str:
    """000110465926014835 → 0001104659-26-014835 (formato EDGAR)."""
    a = acc_no_dashes.zfill(18)
    return f"{a[:10]}-{a[10:12]}-{a[12:]}"


def _get_prev_13f_filing(cik: str, skip_accession: str) -> tuple | None:
    """Retorna (accession, filing_date, filename_xml) del 13F-HR ANTERIOR al skip_accession."""
    r = _sec_get(_EDGAR_SUBMISSIONS_URL.format(cik=int(cik)))
    if not r:
        return None
    skip_edgar = _fmt_accession(skip_accession)
    try:
        recent = r.json().get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accs = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        found_skip = False
        for form, acc, fd in zip(forms, accs, dates):
            if form != "13F-HR":
                continue
            if acc == skip_edgar:
                found_skip = True
                continue
            if found_skip:
                # Este es el filing anterior al que ya tenemos
                xml_name = _find_holdings_xml(cik, acc)
                if xml_name:
                    return acc, fd, xml_name
    except Exception as e:
        _logger.warning(f"_get_prev_13f_filing [{cik}]: {e}")
    return None


def main():
    market = MarketScreen()
    conn = market._conectar(tabla="select.market")
    cursor = conn.cursor()

    # --- 1. Obtener CIKs + accession actuales de fondos con posiciones en cartera ----
    print("Obteniendo fondos con posiciones en cartera...")
    cursor.execute("""
        SELECT DISTINCT f.cik, f.fund_name, ff.accession, ff.filename AS current_xml
        FROM funds f
        INNER JOIN fund_holdings fh ON fh.fund_id = f.id
        INNER JOIN market m ON fh.symbol = m.symbol AND m.encartera = 'Y'
        INNER JOIN fund_filings ff ON ff.cik = f.cik
        WHERE f.cik IS NOT NULL AND f.cik != 0
        ORDER BY f.cik
    """)
    rows = cursor.fetchall()
    conn.close()

    # Deduplicar: un CIK puede aparecer muchas veces (una por símbolo/holding)
    seen = {}
    for cik, fund_name, accession, current_xml in rows:
        if cik not in seen:
            seen[cik] = {"fund_name": fund_name, "accession": accession, "current_xml": current_xml}

    total = len(seen)
    print(f"Total CIKs a procesar: {total:,}")

    # --- 2. Descargar filing del trimestre anterior ----------------------------------
    downloaded, skipped, failed, already_have = 0, 0, 0, 0
    pending_save = []

    for i, (cik, info) in enumerate(seen.items()):
        if i % 100 == 0:
            print(f"  [{i}/{total}] descargados={downloaded} skipped={skipped} failed={failed}")

        prev = _get_prev_13f_filing(cik, info["accession"])
        if not prev:
            skipped += 1
            continue

        prev_accession, prev_date, xml_name = prev
        prev_acc_clean = prev_accession.replace("-", "")

        # Verificar si ya está en BD
        conn2 = market._conectar(tabla="select.market")
        c2 = conn2.cursor()
        c2.execute("SELECT 1 FROM fund_filings WHERE filename = %s", (xml_name,))
        exists = c2.fetchone()
        conn2.close()

        if exists:
            already_have += 1
            continue

        # Descargar XML
        xml_url = _EDGAR_ARCHIVES_URL.format(cik=int(cik), acc_no_dashes=prev_acc_clean, filename=xml_name)
        r = _sec_get(xml_url)
        if not r:
            failed += 1
            continue

        os.makedirs(_13F_SAVE_DIR, exist_ok=True)
        dest = os.path.join(_13F_SAVE_DIR, xml_name)
        if not os.path.exists(dest):
            with open(dest, "wb") as f:
                f.write(r.content)

        pending_save.append((xml_name, str(cik), info["fund_name"], prev_date, prev_acc_clean))
        downloaded += 1

        if len(pending_save) >= 200:
            market.bulk_save_fund_filings(pending_save)
            pending_save.clear()

        time.sleep(0.12)   # respetar rate limit EDGAR (~8 req/s)

    if pending_save:
        market.bulk_save_fund_filings(pending_save)

    print(f"\n=== Descarga completada ===")
    print(f"  Descargados : {downloaded:,}")
    print(f"  Ya en BD    : {already_have:,}")
    print(f"  Sin prev    : {skipped:,}")
    print(f"  Fallidos    : {failed:,}")

    if downloaded == 0:
        print("Nada nuevo descargado — abortando reprocess.")
        return

    # --- 3. Resetear processed=0 para filings actuales de esos fondos ---------------
    print("\nReseteando processed=0 para filings actuales de los fondos afectados...")
    cik_list = list(seen.keys())
    conn3 = market._conectar(tabla="update.market")
    c3 = conn3.cursor()

    for batch_start in range(0, len(cik_list), 500):
        batch = cik_list[batch_start:batch_start + 500]
        placeholders = ",".join(["%s"] * len(batch))
        c3.execute(
            f"UPDATE fund_filings SET processed = 0 WHERE cik IN ({placeholders})",
            batch,
        )
    conn3.commit()
    conn3.close()
    print(f"  Filings reseteados para {len(cik_list):,} CIKs")

    # --- 4. Borrar fund_holdings de esos fondos (reprocess limpio) ------------------
    print("\nBorrando fund_holdings previos de fondos afectados...")
    conn4 = market._conectar(tabla="update.market")
    c4 = conn4.cursor()

    # Obtener fund_ids de los CIKs afectados
    for batch_start in range(0, len(cik_list), 500):
        batch = cik_list[batch_start:batch_start + 500]
        placeholders = ",".join(["%s"] * len(batch))
        c4.execute(
            f"DELETE fh FROM fund_holdings fh "
            f"INNER JOIN funds f ON fh.fund_id = f.id "
            f"WHERE f.cik IN ({placeholders})",
            batch,
        )
    conn4.commit()
    deleted_rows = c4.rowcount
    conn4.close()
    print(f"  Borradas ~{deleted_rows:,} filas de fund_holdings")

    # --- 5. Reprocess sync_13f_holdings (prev quarter = NEW, current = real) --------
    print("\nEjecutando sync_13f_holdings (procesa prev quarter primero por ORDER filing_date ASC)...")
    result = sync_13f_holdings(ACCOUNT)
    print(f"  sync_13f_holdings: {result}")
    print("\nListo. Ahora corre sync_13f_scores para recalcular inst_score.")


if __name__ == "__main__":
    main()
