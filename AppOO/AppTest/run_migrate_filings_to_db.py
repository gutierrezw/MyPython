"""
Migración one-time: transfiere 13f_metadata.json y 13f_holdings_processed.json
a la tabla fund_filings en BD. Ejecutar una sola vez.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen
from Modulos_Utilitarios import read_json_tmp

market = MarketScreen()

print("=" * 70)
print("Migración: JSON 13F → tabla fund_filings")
print("=" * 70)

# Cargar JSONs
metadata  = read_json_tmp("13f_metadata.json")
processed_data = read_json_tmp("13f_holdings_processed.json")
processed_set  = set(processed_data.get("files", []))

print(f"\nMetadata entries : {len(metadata):,}")
print(f"Processed entries: {len(processed_set):,}")

# Verificar estado actual de BD
conn = market._conectar(tabla="select.market")
cur  = conn.cursor()
cur.execute("SELECT COUNT(*) FROM fund_filings")
ya_en_bd = cur.fetchone()[0]
cur.close()
conn.close()
print(f"fund_filings BD  : {ya_en_bd:,} filas actuales")

# Construir registros
records = []
sin_cik = 0
for filename, meta in metadata.items():
    cik       = meta.get("cik")
    fund_name = meta.get("fund_name", "")
    filing_date = meta.get("filing_date", "")
    if not cik or not filing_date:
        sin_cik += 1
        continue
    # accession extraída del filename: {cik}_{accno}_{xmlfile}
    parts     = filename.split("_", 2)
    accession = parts[1] if len(parts) >= 2 else ""
    processed = 1 if filename in processed_set else 0
    records.append((filename, cik, fund_name, filing_date, accession, processed))

print(f"\nRegistros a insertar : {len(records):,}")
print(f"Sin CIK/fecha (skip) : {sin_cik:,}")

if not records:
    print("\nNada que migrar.")
    sys.exit(0)

# Insertar con processed incluido
conn = market._conectar(tabla="update.market")
cur  = conn.cursor()
inserted = 0
batch_size = 500
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    cur.executemany(
        "INSERT IGNORE INTO fund_filings "
        "(filename, cik, fund_name, filing_date, accession, processed) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        batch,
    )
    conn.commit()
    inserted += cur.rowcount
    print(f"  [{i + len(batch):,}/{len(records):,}] insertados={inserted:,}")

cur.close()
conn.close()

print(f"\nMigración completa — {inserted:,} filas insertadas en fund_filings")
print("Los JSONs temporales pueden eliminarse cuando confirmes que todo funciona.")
