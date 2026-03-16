import sys
import os
import json
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from Class_InstitucionalScore import _13F_SAVE_DIR, _13F_METADATA_FILE, _save_13f_metadata
from Class_InstitucionalScore import _get_latest_13f_accession
from Modulos_Mysql import MarketScreen

print("=" * 70)
print("rebuild_13f_metadata — reconstruye metadata.json desde archivos existentes")
print("=" * 70)

market = MarketScreen()
xml_files = [f for f in os.listdir(_13F_SAVE_DIR) if f.endswith(".xml")]
print(f"  XMLs encontrados: {len(xml_files)}")

# Cargar metadata existente para no sobreescribir entradas ya correctas
try:
    with open(_13F_METADATA_FILE, "r") as f:
        metadata = json.load(f)
    print(f"  metadata.json existente: {len(metadata)} entradas")
except Exception:
    metadata = {}
    print("  metadata.json no existe — creando desde cero")

# Construir mapa cik → fund_name desde la DB
conn = market._conectar(tabla="select.market")
cursor = conn.cursor()
cursor.execute("SELECT cik, fund_name FROM funds WHERE cik IS NOT NULL")
cik_to_fund = {row[0]: row[1] for row in cursor.fetchall()}
cursor.close()
conn.close()
print(f"  fondos con CIK en DB: {len(cik_to_fund)}")

found, skipped = 0, 0
for xml_file in xml_files:
    if xml_file in metadata:
        skipped += 1
        continue

    # Nombre formato: {cik}_{accession_nodashes}_{xml_filename}
    parts = xml_file.split("_", 2)
    if len(parts) < 2:
        skipped += 1
        continue

    cik = parts[0]
    accession_nodashes = parts[1]
    fund_name = cik_to_fund.get(cik, f"CIK:{cik}")

    # Reconstruir filing_date desde la accession (año embebido: pos 10-11)
    # accession format: XXXXXXXXXX + YY + NNNNNN  → año 20YY
    filing_date = None
    if len(accession_nodashes) >= 12:
        year_str = accession_nodashes[10:12]
        filing_date = f"20{year_str}-01-01"  # aproximado — mes/día desconocidos sin query

    metadata[xml_file] = {
        "cik": cik,
        "fund_name": fund_name,
        "filing_date": filing_date,
    }
    found += 1

_save_13f_metadata(metadata)

print("=" * 70)
print(f"  entradas nuevas    : {found}")
print(f"  ya existían        : {skipped}")
print(f"  total en metadata  : {len(metadata)}")
print("Listo.")
