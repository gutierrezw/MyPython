# ================================================
# valuation_engine.py
# Tu motor de valoración integrado con Arelle
# ================================================

# ============================================================
# valuation_arelle_engine.py
# Motor original del usuario, pero usando Arelle internamente
# ============================================================

import os
import json
import zipfile
import time
import requests
import numpy as np
from datetime import datetime
from pathlib import Path

# 🔵 Aquí usamos TU módulo Arelle
from valuation_xbrl_api import (
    load_filing,  # carga un filing individual (Arelle)
    build_ttm,  # construye el TTM combinando los filings
)


# ============================================================
# Obtiene el directorio del ticker (Ej: HASI_EDGAR_Files)
# ============================================================
def get_ticker_dir(BASE_DIR: Path, ticker: str) -> Path:
    return BASE_DIR / f"{ticker.upper()}_EDGAR_Files"


# ============================================================
# Carga metadata.json
# ============================================================
def load_metadata(ticker_dir: Path):
    meta_path = ticker_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No existe metadata.json en: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Inspecciona ZIP → obtiene instancias XML válidas
# ============================================================
def extract_instances_from_zip(zip_path: str):
    instances = []
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                low = name.lower()
                if low.endswith(".xml") and not any(
                    k in low for k in ["cal", "pre", "def", "lab"]
                ):
                    instances.append(name)
    except Exception as e:
        print(f"⚠ Error leyendo ZIP {zip_path}: {e}")

    return instances


# ============================================================
# Genera file_list EXACTAMENTE como tu engine original
# ============================================================
def build_file_list(BASE_DIR: Path, ticker: str, display_logs=False):
    ticker_dir = get_ticker_dir(BASE_DIR, ticker)
    meta = load_metadata(ticker_dir)

    items = []

    for entry in meta.get("downloaded_files", []):
        date_str = entry.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = entry.get("path")
        if not path or not os.path.exists(path):
            continue

        low = path.lower()

        # ZIP
        if entry.get("is_zip"):
            insts = extract_instances_from_zip(path)
            for inst in insts:
                items.append((dt, path, inst))
            continue

        # HTML inline XBRL
        if low.endswith(".htm"):
            items.append((dt, path, None))
            continue

        # XML
        if low.endswith(".xml"):
            items.append((dt, path, None))
            continue

    # ordenar por fecha
    items.sort(key=lambda x: x[0], reverse=True)

    out = [(p, inst) for _, p, inst in items]

    if display_logs:
        print("\n📄 File_list final para Arelle:")
        for p, inst in out:
            print(f" - {p} :: {inst}" if inst else f" - {p}")

    return out


# ============================================================
# Yahoo Finance (tu código original)
# ============================================================
def get_yf_price(ticker: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}

    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}",
    ]

    for attempt in range(3):
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 429:
                    time.sleep(1 + attempt)
                    continue
                r.raise_for_status()
                data = r.json()

                # chart
                try:
                    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                except:
                    pass

                # quoteSummary
                try:
                    return data["quoteSummary"]["result"][0]["price"][
                        "regularMarketPrice"
                    ]["raw"]
                except:
                    pass

            except:
                time.sleep(0.5 + attempt)

    return None


# ============================================================
# Calcula valuaciones simples (tu lógica original)
# ============================================================
def compute_valuations(ttm: dict, price: float):
    ocf = ttm.get("OperatingCF")
    capex = ttm.get("CapEx")

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    return {
        "Price": price,
        "NetIncome": ttm.get("NetIncome"),
        "OperatingCF": ocf,
        "CapEx": capex,
        "FCF": fcf,
        "P/E": price / (ttm["NetIncome"] or np.nan),
        "P/FCF": price / (fcf or np.nan),
        "P/S": price / (ttm.get("Revenues") or np.nan),
        "Dividends": ttm.get("DividendsPaid"),
        "Shares": ttm.get("Shares"),
        "FFO": ttm.get("FFO"),
        "AFFO": ttm.get("AFFO"),
    }


# ============================================================
# 🚀 Pipeline principal — usando Arelle
# ============================================================
def run_valuation(file_list, price):
    """
    file_list → [(path, None), (zip, instance.xml), ...]
    price → precio Yahoo
    """

    filings = []

    # cargamos todos los filings usando Arelle
    for path, instance in file_list:
        try:
            model = load_filing(path, instance)
            filings.append(model)
        except Exception as e:
            print(f"[ERROR] al cargar filing {path}: {e}")

    if not filings:
        return {"ERROR": "No se cargó ningún filing."}

    # construir TTM usando TU función build_ttm()
    ttm = build_ttm(filings)

    # valuación con tu fórmula original
    vals = compute_valuations(ttm, price)

    return {
        "files_used": file_list,
        "ttm": ttm,
        "valuations": vals,
    }


# ============================================================
# CLI identico al tuyo
# ============================================================
if __name__ == "__main__":
    BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")

    ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
    price = get_yf_price(ticker)

    file_list = build_file_list(BASE_DIR, ticker, display_logs=True)

    result = run_valuation(file_list, price)

    print("\n📊 Resultados de valoración:")
    print(json.dumps(result, indent=4))
