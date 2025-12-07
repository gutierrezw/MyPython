# ================================================
# valuation_arelle_engine.py (DB READY VERSION)
# Output estructurado para base de datos
# ================================================

import os
import json
import zipfile
import time
import requests
import numpy as np
from datetime import datetime
from pathlib import Path

from valuation_xbrl_api import load_filing, build_ttm, analyze_dividend_history
from valuation_ddm import DividendDiscountModel


def is_reit(ttm: dict):
    """
    Detecta si la empresa es un REIT basándose en:
    1. Si reporta FFO o AFFO directamente en filings
    2. Si tiene GainsOnRealEstateSales significativos
    """
    # Si reporta FFO/AFFO nativo, definitivamente es REIT
    if ttm.get("FFO") is not None or ttm.get("AFFO") is not None:
        return True

    # Si tiene gains significativos en RE sales, probablemente REIT
    gains = ttm.get("GainsOnRealEstateSales")
    if gains and abs(gains) > 1000000:  # Más de $1M
        return True

    return False


def get_ticker_dir(BASE_DIR: Path, ticker: str) -> Path:
    return BASE_DIR / f"{ticker.upper()}_EDGAR_Files"


def load_metadata(ticker_dir: Path):
    meta_path = ticker_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No existe metadata.json en: {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


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


def build_file_list(BASE_DIR: Path, ticker: str, display_logs=False):
    ticker_dir = get_ticker_dir(BASE_DIR, ticker)
    meta = load_metadata(ticker_dir)

    items_10k = []
    items_10q = []

    for entry in meta.get("downloaded_files", []):
        date_str = entry.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = entry.get("path")
        if not path or not os.path.exists(path):
            continue

        form = entry.get("form", "")
        low = path.lower()

        if entry.get("is_zip"):
            insts = extract_instances_from_zip(path)
            for inst in insts:
                if form == "10-K":
                    items_10k.append((dt, path, inst))
                else:
                    items_10q.append((dt, path, inst))
            continue

        if low.endswith(".htm"):
            if form == "10-K":
                items_10k.append((dt, path, None))
            else:
                items_10q.append((dt, path, None))
            continue

        if low.endswith(".xml"):
            if form == "10-K":
                items_10k.append((dt, path, None))
            else:
                items_10q.append((dt, path, None))
            continue

    items_10k.sort(key=lambda x: x[0], reverse=True)
    items_10q.sort(key=lambda x: x[0], reverse=True)

    out = []
    if items_10k:
        out.append((items_10k[0][1], items_10k[0][2]))

    for dt, p, inst in items_10q[:3]:
        out.append((p, inst))

    if display_logs:
        print("\n📄 Archivos a procesar:")
        for p, inst in out:
            print(f" - {Path(p).name}")

    return out


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

                try:
                    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                except:
                    pass

                try:
                    return data["quoteSummary"]["result"][0]["price"][
                        "regularMarketPrice"
                    ]["raw"]
                except:
                    pass

            except:
                time.sleep(0.5 + attempt)

    return None


def compute_reit_metrics(ttm: dict):
    """
    Calcula FFO y AFFO según fórmula NAREIT.
    ⚠️ Solo aplica a REITs - para empresas normales devuelve None
    """
    # ✅ Solo calcular para REITs
    if not is_reit(ttm):
        return {
            "FFO": None,
            "AFFO": None,
            "is_reit": False,
        }

    net_income = ttm.get("NetIncome")
    depreciation = ttm.get("Depreciation") or 0
    gains_on_sales = ttm.get("GainsOnRealEstateSales") or 0
    capex = ttm.get("CapEx") or 0

    ffo = None
    if net_income is not None:
        ffo = net_income + depreciation - gains_on_sales

    affo = None
    if ffo is not None and capex != 0:
        maintenance_capex = abs(capex) * 0.20
        affo = ffo - maintenance_capex

    return {
        "FFO": ffo,
        "AFFO": affo,
        "is_reit": True,
    }


def compute_valuations(ttm: dict, price: float):
    net_income = ttm.get("NetIncome")
    ocf = ttm.get("OperatingCF")
    capex = ttm.get("CapEx")
    dividends = ttm.get("DividendsPaid")
    shares = ttm.get("Shares")
    revenues = ttm.get("Revenues")

    reit_metrics = compute_reit_metrics(ttm)
    ffo = reit_metrics["FFO"]
    affo = reit_metrics["AFFO"]

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    # Métricas por acción
    eps = net_income / shares if (net_income and shares) else None
    ocf_per_share = ocf / shares if (ocf and shares) else None
    fcf_per_share = fcf / shares if (fcf and shares) else None
    revenue_per_share = revenues / shares if (revenues and shares) else None
    dividend_per_share = dividends / shares if (dividends and shares) else None
    ffo_per_share = ffo / shares if (ffo and shares) else None
    affo_per_share = affo / shares if (affo and shares) else None

    # Ratios de valuación
    pe_ratio = price / eps if eps else None
    p_fcf = price / fcf_per_share if fcf_per_share else None
    p_s = price / revenue_per_share if revenue_per_share else None
    p_ffo = price / ffo_per_share if ffo_per_share else None
    p_affo = price / affo_per_share if affo_per_share else None

    div_yield = (dividend_per_share / price * 100) if dividend_per_share else None
    payout_ratio = (
        (dividends / net_income * 100) if (dividends and net_income) else None
    )

    # ✅ Convertir NaN a None para JSON/DB
    def clean_value(v):
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    return {
        "Price": clean_value(price),
        "Shares": clean_value(shares),
        # Totales
        "NetIncome_Total": clean_value(net_income),
        "OperatingCF_Total": clean_value(ocf),
        "CapEx_Total": clean_value(capex),
        "FCF_Total": clean_value(fcf),
        "Dividends_Total": clean_value(dividends),
        "Revenues_Total": clean_value(revenues),
        "FFO_Total": clean_value(ffo),
        "AFFO_Total": clean_value(affo),
        # Por acción
        "EPS": clean_value(eps),
        "OCF_Per_Share": clean_value(ocf_per_share),
        "FCF_Per_Share": clean_value(fcf_per_share),
        "Revenue_Per_Share": clean_value(revenue_per_share),
        "Dividend_Per_Share": clean_value(dividend_per_share),
        "FFO_Per_Share": clean_value(ffo_per_share),
        "AFFO_Per_Share": clean_value(affo_per_share),
        # Ratios de valuación
        "PE_Ratio": clean_value(pe_ratio),
        "P_FCF": clean_value(p_fcf),
        "P_S": clean_value(p_s),
        "P_FFO": clean_value(p_ffo),
        "P_AFFO": clean_value(p_affo),
        "Dividend_Yield_Percent": clean_value(div_yield),
        "Payout_Ratio_Percent": clean_value(payout_ratio),
        # Balance Sheet
        "Total_Assets": clean_value(ttm.get("TotalAssets")),
        "Total_Equity": clean_value(ttm.get("TotalEquity")),
    }


def run_ddm_analysis(dividend_per_share, price, required_return=0.10):
    """Ejecuta múltiples escenarios de DDM"""
    if not dividend_per_share or dividend_per_share <= 0:
        return None

    ddm = DividendDiscountModel(dividend_per_share, required_return)

    results = {}

    # Gordon Growth - Múltiples escenarios
    for growth in [0.02, 0.03, 0.04, 0.05]:
        if growth < required_return:
            result = ddm.gordon_growth(growth)
            iv = result.get("intrinsic_value")
            if iv:
                mos = ddm.margin_of_safety(iv, price)
                results[f"Gordon_{int(growth*100)}pct"] = {
                    "model": "Gordon Growth Model",
                    "growth_rate": growth,
                    "intrinsic_value": iv,
                    "margin_of_safety_percent": mos["margin_of_safety_%"],
                    "recommendation": mos["recommendation"],
                }

    # Two-Stage DDM
    result = ddm.two_stage(
        high_growth_rate=0.07, high_growth_years=5, stable_growth_rate=0.03
    )
    iv = result.get("intrinsic_value")
    if iv:
        mos = ddm.margin_of_safety(iv, price)
        results["TwoStage_7pct_5y"] = {
            "model": "Two-Stage DDM",
            "high_growth_rate": 0.07,
            "high_growth_years": 5,
            "stable_growth_rate": 0.03,
            "intrinsic_value": iv,
            "margin_of_safety_percent": mos["margin_of_safety_%"],
            "recommendation": mos["recommendation"],
        }

    # Three-Stage DDM
    result = ddm.three_stage(
        high_growth_rate=0.08,
        high_growth_years=3,
        transition_years=4,
        stable_growth_rate=0.03,
    )
    iv = result.get("intrinsic_value")
    if iv:
        mos = ddm.margin_of_safety(iv, price)
        results["ThreeStage_8pct_3y"] = {
            "model": "Three-Stage DDM",
            "high_growth_rate": 0.08,
            "high_growth_years": 3,
            "transition_years": 4,
            "stable_growth_rate": 0.03,
            "intrinsic_value": iv,
            "margin_of_safety_percent": mos["margin_of_safety_%"],
            "recommendation": mos["recommendation"],
        }

    return results


def run_valuation(file_list, ticker, price):
    """
    ✅ RETORNA DICCIONARIO COMPLETO - LISTO PARA DB
    """
    filings = []

    for path, instance in file_list:
        try:
            model = load_filing(path, instance)
            filings.append(model)
        except Exception as e:
            print(f"[ERROR] al cargar filing {path}: {e}")

    if not filings:
        return {"error": "No se cargó ningún filing."}

    ttm = build_ttm(filings)
    vals = compute_valuations(ttm, price)

    # Ejecutar análisis DDM
    ddm_results = None
    if vals.get("Dividend_Per_Share"):
        ddm_results = run_ddm_analysis(vals["Dividend_Per_Share"], price)
        analyze_divideds = analyze_dividend_history(ticker)

    # ✅ ESTRUCTURA PARA DB
    return {
        "metadata": {
            "ticker": ticker,
            "analysis_date": datetime.now().isoformat(),
            "price_date": datetime.now().date().isoformat(),
            "files_processed": [Path(p).name for p, _ in file_list],
        },
        "market_data": {
            "current_price": vals["Price"],
            "shares_outstanding": vals["Shares"],
        },
        "fundamentals": {
            "income_statement": {
                "net_income": vals["NetIncome_Total"],
                "revenues": vals["Revenues_Total"],
                "operating_cash_flow": vals["OperatingCF_Total"],
            },
            "cash_flow": {
                "operating_cf": vals["OperatingCF_Total"],
                "capex": vals["CapEx_Total"],
                "free_cash_flow": vals["FCF_Total"],
                "dividends_paid": vals["Dividends_Total"],
            },
            "balance_sheet": {
                "total_assets": vals["Total_Assets"],
                "total_equity": vals["Total_Equity"],
            },
        },
        "reit_metrics": {
            "ffo_total": vals["FFO_Total"],
            "affo_total": vals["AFFO_Total"],
            "ffo_per_share": vals["FFO_Per_Share"],
            "affo_per_share": vals["AFFO_Per_Share"],
            "is_reit": is_reit(ttm),
        },
        "per_share_metrics": {
            "eps": vals["EPS"],
            "revenue_per_share": vals["Revenue_Per_Share"],
            "dividend_per_share": vals["Dividend_Per_Share"],
            "ocf_per_share": vals["OCF_Per_Share"],
            "fcf_per_share": vals["FCF_Per_Share"],
            "ffo_per_share": vals["FFO_Per_Share"],
            "affo_per_share": vals["AFFO_Per_Share"],
        },
        "valuation_ratios": {
            "pe_ratio": vals["PE_Ratio"],
            "p_s_ratio": vals["P_S"],
            "p_fcf_ratio": vals["P_FCF"],
            "p_ffo_ratio": vals["P_FFO"],
            "p_affo_ratio": vals["P_AFFO"],
            "dividend_yield_percent": vals["Dividend_Yield_Percent"],
            "payout_ratio_percent": vals["Payout_Ratio_Percent"],
        },
        "ddm_valuation": ddm_results,
        "dividend_analysis": analyze_divideds,
        "raw_ttm_data": ttm,  # Por si querés guardar los datos crudos también
    }


def print_summary(result):
    """
    ✅ FUNCIÓN OPCIONAL - Imprime resumen legible
    """
    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return

    meta = result["metadata"]
    market = result["market_data"]
    per_share = result["per_share_metrics"]
    ratios = result["valuation_ratios"]
    reit = result["reit_metrics"]
    ddm = result.get("ddm_valuation")

    print("\n" + "=" * 70)
    print(f"📊 ANÁLISIS DE VALORACIÓN - {meta['ticker']}")
    print(f"📅 Fecha: {meta['analysis_date'][:10]}")
    print("=" * 70)

    print(f"\n💰 Precio Actual: ${market['current_price']:.2f}")
    print(f"📈 Shares: {market['shares_outstanding']:,.0f}")

    # ✅ Solo mostrar métricas REIT si es REIT
    if reit.get("is_reit") and reit["ffo_per_share"]:
        print("\n🏢 MÉTRICAS REIT:")
        print(f"  FFO/share: ${reit['ffo_per_share']:.2f}")
        if ratios["p_ffo_ratio"]:
            print(f"  P/FFO: {ratios['p_ffo_ratio']:.2f}x")
        if reit["affo_per_share"]:
            print(f"  AFFO/share: ${reit['affo_per_share']:.2f}")

    print("\n📉 FUNDAMENTALES:")
    if per_share["eps"]:
        print(f"  EPS: ${per_share['eps']:.2f}")
    if per_share["dividend_per_share"]:
        print(f"  Dividend/share: ${per_share['dividend_per_share']:.2f}")
    if ratios["dividend_yield_percent"]:
        print(f"  Dividend Yield: {ratios['dividend_yield_percent']:.2f}%")
    if ratios["pe_ratio"]:
        print(f"  P/E: {ratios['pe_ratio']:.2f}x")

    if ddm:
        print("\n💎 VALORACIÓN DDM:")
        for key, data in ddm.items():
            print(f"\n  {key.replace('_', ' ')}:")
            print(f"    Valor Intrínseco: ${data['intrinsic_value']:.2f}")
            print(f"    Margen: {data['margin_of_safety_percent']:+.1f}%")
            print(f"    📌 {data['recommendation']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")

    ticker = input("💼 Ingrese el ticker: ").strip().upper()
    price = get_yf_price(ticker)

    if not price:
        print("❌ No se pudo obtener el precio de Yahoo Finance")
        price = float(input("Ingrese el precio manualmente: "))

    file_list = build_file_list(BASE_DIR, ticker, display_logs=False)

    # print(f"\n⚙️  Analizando {ticker}...")
    result = run_valuation(file_list, ticker, price)

    # Resumen en pantalla
    # print_summary(result)

    # ✅ DICCIONARIO IDENTADO LISTO PARA DB
    print("\n" + "=" * 70)
    print("💾 ESTRUCTURA DE DATOS (lista para DB):")
    print("=" * 70)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Crear carpeta valuations si no existe
    valuations_dir = BASE_DIR / f"{ticker.upper()}_EDGAR_Files" / "valuations"
    valuations_dir.mkdir(parents=True, exist_ok=True)

    # Guardar archivo
    filename = f"{ticker}_valuation_{datetime.now().strftime('%Y%m%d')}.json"
    output_file = valuations_dir / filename

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"✅ Guardado en: {output_file}")
