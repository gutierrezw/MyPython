import os
import time
import json
import requests
from datetime import datetime, timezone

# =====================================================
# Configuración
# =====================================================
BASE_DIR = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR"
HEADERS = {
    "User-Agent": "InversionesWildaga Research Bot (gutierrez.madrid.wilmer@example.com)"
}
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Formularios disponibles
DOMESTIC_FORMS = ["10-K", "10-Q"]
FOREIGN_FORMS = ["20-F", "6-K"]

# =====================================================
# Funciones auxiliares
# =====================================================
def get_cik_from_ticker(ticker: str) -> str | None:
    """Busca el CIK correspondiente a un ticker."""
    try:
        r = requests.get(SEC_TICKERS_URL, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        for entry in data.values():
            if entry["ticker"].lower() == ticker.lower():
                return str(entry["cik_str"]).zfill(10)
    except Exception as e:
        print(f"❌ Error al obtener CIK: {e}")
    return None


def get_filings_metadata(cik: str) -> dict:
    """Obtiene metadatos de filings desde submissions.json."""
    url = SEC_SUBMISSIONS_URL.format(cik=int(cik))
    try:
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 404:
            # print(f"⚠️ No se encontró submissions para CIK {cik}")
            return {}
        r.raise_for_status()
        return r.json().get("filings", {}).get("recent", {})
    except Exception as e:
        print(f"❌ Error al obtener filings metadata: {e}")
        return {}


def download_filing_file(cik: str, accession: str, filename: str, save_dir: str):
    """Descarga un archivo del filing si no existe."""
    base_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{filename}"
    local_path = os.path.join(save_dir, filename)

    if os.path.exists(local_path):
        # print(f"⚠️ Ya existía: {filename}")
        return

    try:
        r = requests.get(base_url, headers=HEADERS)
        if r.status_code == 404:
            print(f"❌ No encontrado: {filename}")
            return
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        # print(f"✅ Descargado: {filename}")
        time.sleep(0.5)
    except Exception as e:
        print(f"❌ Error al descargar {filename}: {e}")


def is_foreign_filer(form_list: list[str]) -> bool:
    """Detecta si una empresa presenta formularios extranjeros (20-F, 6-K)."""
    return any(f in form_list for f in FOREIGN_FORMS)


# =====================================================
# Función principal
# =====================================================
def main():
    print("=" * 70)
    ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
    print("=" * 70)
    print(f"📊 Buscando los últimos filings para {ticker}...\n")

    # Buscar CIK
    cik = get_cik_from_ticker(ticker)
    if not cik:
        print(f"❌ No se encontró CIK para {ticker}.")
        return

    # Obtener metadata
    filings = get_filings_metadata(cik)
    if not filings:
        print("⚠️ No se pudo obtener metadata de filings.")
        return

    form_types = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    filenames = filings.get("primaryDocument", [])

    # Determinar si es doméstica o extranjera
    if is_foreign_filer(form_types):
        target_forms = FOREIGN_FORMS
        company_type = "foreign"
        print("🌍 Empresa extranjera detectada (formularios 20-F / 6-K).\n")
    else:
        target_forms = DOMESTIC_FORMS
        company_type = "domestic"
        print("🏛️ Empresa doméstica detectada (formularios 10-K / 10-Q).\n")

    # Crear directorios
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_EDGAR_Files")
    dirs = {form: os.path.join(ticker_dir, f"{form.replace('-', '')}_Filings") for form in target_forms}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    # Clasificar por tipo
    categorized = {f: [] for f in target_forms}
    for form, date, acc, file in zip(form_types, filing_dates, accessions, filenames):
        if form in target_forms:
            categorized[form].append((date, acc, file))

    # Limitar cantidad
    limits = {"10-K": 5, "10-Q": 3, "20-F": 3, "6-K": 3}
    for f in target_forms:
        categorized[f] = sorted(categorized[f], reverse=True)[:limits.get(f, 3)]

    # Descargar
    downloaded_files = []
    for form, entries in categorized.items():
        if not entries:
            continue
        # print(f"📁 Preparando descarga: {len(entries)} × {form}\n")
        for date, acc, file in entries:
            # print(f"⬇️ {form} {date} ({acc})")
            download_filing_file(cik, acc, file, dirs[form])
            downloaded_files.append({
                "form": form,
                "date": date,
                "accession": acc,
                "file": file,
                "path": os.path.join(dirs[form], file)
            })

    # Guardar JSON resumen
    metadata_path = os.path.join(ticker_dir, "metadata.json")
    metadata = {
        "ticker": ticker,
        "cik": cik,
        "company_type": company_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directories": dirs,
        "downloaded_files": downloaded_files
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    print("\n=== ✅ Descarga completada ===")
    print(f"Ticker: {ticker} | CIK: {cik}")
    print(f"📂 Metadata guardada en: {metadata_path}")
    print(f"Fecha de ejecución: {datetime.now(timezone.utc).isoformat()}")


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":
    main()
