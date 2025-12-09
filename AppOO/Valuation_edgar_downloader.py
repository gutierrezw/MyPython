# valuation_edgar_downloader.py
"""
Módulo para descargar filings de la SEC desde EDGAR.
Funciones principales:
- get_cik_from_ticker(ticker): Obtiene el CIK a partir del ticker.
- get_filings_metadata(cik): Obtiene metadata de filings desde submissions.json.
- download_filing_file(cik, accession, filename, save_dir): Descarga un archivo específico del filing.
- is_foreign_filer(form_list): Detecta si una empresa presenta formularios extranjeros (20-F, 6-K).
"""

from Modulos_python import os, time, json, requests, datetime, timezone

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
FOREIGN_FORMS = ["20-F"]  # Solo 20-F (anuales). 6-K son eventos, no financials.


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
# busca y descarga archivos ZIP asociados
# =====================================================
def download_zip_files(cik: str, ticker: str, accession: str, save_dir: str):
    """
    Descarga automáticamente cualquier archivo ZIP asociado al filing.
    Retorna una lista con los ZIP descargados.
    """
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/index.json"
    zip_files_downloaded = []

    try:
        r = requests.get(index_url, headers=HEADERS)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"⚠️ No se pudo leer index.json para {accession}: {e}")
        return []

    items = data.get("directory", {}).get("item", [])
    zip_files = [it["name"] for it in items if it["name"].lower().endswith(".zip")]

    for zfile in zip_files:
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{zfile}"
        local_path = os.path.join(save_dir, zfile)

        if not os.path.exists(local_path):
            try:
                rz = requests.get(url, headers=HEADERS)
                if rz.status_code == 404:
                    continue
                rz.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(rz.content)

                # print(f"📦 ZIP descargado: {ticker} - {zfile}")
                time.sleep(0.5)

            except Exception as e:
                print(f"❌ Error descargando ZIP {ticker} - {zfile}: {e}")
                continue

        zip_files_downloaded.append({"zip_file": zfile, "path": local_path})

    return zip_files_downloaded


# =====================================================
# Función principal
# =====================================================
def download_filing(ticker=None, display=False):

    if ticker is None:
        print("=" * 70)
        ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
        print("=" * 70)
        print(f"📊 Buscando los últimos filings para {ticker}...\n")

    # Buscar CIK
    cik = get_cik_from_ticker(ticker)
    if not cik:
        if display:
            print(f"❌ No se encontró CIK para {ticker}.")
        return

    # Obtener metadata
    filings = get_filings_metadata(cik)
    if not filings:
        if display:
            print("⚠️ No se pudo obtener metadata de filings.")
        return False

    form_types = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    filenames = filings.get("primaryDocument", [])

    # Determinar si es doméstica o extranjera
    if is_foreign_filer(form_types):
        target_forms = FOREIGN_FORMS
        company_type = "foreign"
        if display:
            print("🌍 Empresa extranjera detectada (formularios 20-F / 6-K).\n")
    else:
        target_forms = DOMESTIC_FORMS
        company_type = "domestic"
        if display:
            print("🏛️ Empresa doméstica detectada (formularios 10-K / 10-Q).\n")

    # Crear directorios
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_EDGAR_Files")
    dirs = {
        form: os.path.join(ticker_dir, f"{form.replace('-', '')}_Filings")
        for form in target_forms
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    # Clasificar por tipo
    categorized = {f: [] for f in target_forms}
    for form, date, acc, file in zip(form_types, filing_dates, accessions, filenames):
        if form in target_forms:
            categorized[form].append((date, acc, file))

    # Limitar cantidad
    limits = {"10-K": 5, "10-Q": 3, "20-F": 3}
    for f in target_forms:
        categorized[f] = sorted(categorized[f], reverse=True)[: limits.get(f, 3)]

    # Descargar
    downloaded_files = []
    for form, entries in categorized.items():
        if not entries:
            continue
        if display:
            print(f"📁 Preparando descarga: {len(entries)} × {form}\n")
        for date, acc, file in entries:
            # 1. Descargar documento principal
            download_filing_file(cik, acc, file, dirs[form])

            # 2. Descargar ZIPs
            zip_entries = download_zip_files(cik, ticker, acc, dirs[form])

            # 3. Registrar el documento principal
            downloaded_files.append(
                {
                    "form": form,
                    "date": date,
                    "accession": acc,
                    "file": file,
                    "path": os.path.join(dirs[form], file),
                    "is_zip": False,
                }
            )

            # 4. Registrar cada ZIP
            for z in zip_entries:
                downloaded_files.append(
                    {
                        "form": form,
                        "date": date,
                        "accession": acc,
                        "file": z["zip_file"],
                        "path": z["path"],
                        "is_zip": True,
                    }
                )

    # Guardar JSON resumen
    metadata_path = os.path.join(ticker_dir, "metadata.json")
    metadata = {
        "ticker": ticker,
        "cik": cik,
        "company_type": company_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directories": dirs,
        "downloaded_files": downloaded_files,
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    if display:
        print("\n=== ✅ Descarga completada ===")
        print(f"Ticker: {ticker} | CIK: {cik}")
        print(f"📂 Metadata guardada en: {metadata_path}")
        print(f"Fecha de ejecución: {datetime.now(timezone.utc).isoformat()}")

    return True


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":
    download_filing(display=True)
