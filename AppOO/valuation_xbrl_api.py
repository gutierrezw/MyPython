# ================================================
# valuation_xbrl_api.py (FIXED VERSION)
# Capa: API estándar para el motor
# ================================================

import os
import sys
import json
import zipfile
import yfinance as yf
import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from valuation_arelle_parser import (
    load_xbrl_with_arelle,
    extract_facts,
    extract_contexts,
    extract_units,
)


# -----------------------------------------------------
# Filing (representa un filing cargado con Arelle)
# -----------------------------------------------------
@dataclass
class Filing:
    path: str
    model: object
    facts: dict
    contexts: dict
    units: dict

    def get_facts(self, name):
        """Retorna la lista de hechos tal como vienen de Arelle."""
        return self.facts.get(name, [])


# -----------------------------------------------------
# dividend_history.py
# Análisis histórico de dividendos usando yfinance
# -----------------------------------------------------
def analyze_dividend_history(ticker, years=10, display_log=False):
    """
    Analiza histórico de dividendos y calcula CAGR
    """
    if display_log:
        print("=" * 70)
        print(f"📊 ANÁLISIS DE DIVIDENDOS - {ticker}")
        print("=" * 70)

    # Descargar datos
    stock = yf.Ticker(ticker)
    dividends = stock.dividends

    if dividends.empty:
        print(f"\n❌ No hay datos de dividendos para {ticker}")
        return None

    # Agrupar por año
    dividends_annual = dividends.groupby(dividends.index.year).sum()

    # Limitar a últimos N años
    dividends_annual = dividends_annual.tail(years)

    if display_log:
        print(f"\n💰 DIVIDENDOS ANUALES (últimos {years} años):")
        print("-" * 70)

        for year, amount in dividends_annual.items():
            print(f"  {year}: ${amount:.4f}")

    # Calcular CAGR (Compound Annual Growth Rate)
    if len(dividends_annual) >= 2:
        start_div = dividends_annual.iloc[0]
        end_div = dividends_annual.iloc[-1]
        years_diff = len(dividends_annual) - 1

        if start_div > 0:
            cagr = ((end_div / start_div) ** (1 / years_diff)) - 1

            if display_log:
                print(f"\n📈 CRECIMIENTO:")
                print("-" * 70)
                print(
                    f"  Dividendo inicial ({dividends_annual.index[0]}): ${start_div:.4f}"
                )
                print(
                    f"  Dividendo final ({dividends_annual.index[-1]}): ${end_div:.4f}"
                )
                print(f"  Período: {years_diff} años")
                print(f"  CAGR: {cagr*100:.2f}% anual")

                # Proyección simple
                print(f"\n🔮 PROYECCIÓN (si mantiene CAGR {cagr*100:.2f}%):")
                print("-" * 70)

        current_year = datetime.now().year
        sescenario, message = "", ""
        for i in range(1, 6):
            future_div = end_div * ((1 + cagr) ** i)
            print(f"  {current_year + i}: ${future_div:.4f}")

            # Recomendación DDM
            if display_log:
                print(f"\n💡 RECOMENDACIÓN PARA DDM:")
                print("-" * 70)

            if cagr < 0:
                message = f"  ⚠️  Dividendos han DECRECIDO {abs(cagr)*100:.2f}%/año"
                escenario = f"  💭 Usar escenario conservador: 0-2%"
            elif cagr < 0.03:
                message = f"  📊 Crecimiento bajo: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario conservador: 2-3%"
            elif cagr < 0.06:
                message = f"  ✅ Crecimiento moderado: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario moderado: 3-5%"
            else:
                message = f"  🚀 Crecimiento alto: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario optimista: 5-7%"

            return {
                "ticker": ticker,
                "annual_dividends": dividends_annual.to_dict(),
                "cagr": cagr,
                "message": message,
                "escenario": escenario,
                "start_year": int(dividends_annual.index[0]),
                "end_year": int(dividends_annual.index[-1]),
                "start_dividend": float(start_div),
                "end_dividend": float(end_div),
            }

    return None


def compare_tickers(tickers, years=10, display_log=False):
    """
    Compara histórico de dividendos de múltiples tickers
    """
    if display_log:
        print("\n" + "=" * 70)
        print("📊 COMPARACIÓN DE CRECIMIENTO DE DIVIDENDOS")
        print("=" * 70)

    results = []

    for ticker in tickers:
        result = analyze_dividend_history(ticker, years)
        if result:
            results.append(result)

    # Tabla comparativa
    if results:
        if display_log:
            print("\n" + "=" * 70)
            print("📋 RESUMEN COMPARATIVO:")
            print("=" * 70)
            print(
                f"{'Ticker':<10} {'CAGR':<10} {'Div Actual':<15} {'Recomendación DDM':<20}"
            )
            print("-" * 70)

        for r in results:
            cagr_pct = r["cagr"] * 100
            if r["cagr"] < 0.03:
                rec = "2-3% (conservador)"
            elif r["cagr"] < 0.06:
                rec = "3-5% (moderado)"
            else:
                rec = "5-7% (optimista)"

            if display_log:
                print(
                    f"{r['ticker']:<10} {cagr_pct:>6.2f}%    ${r['end_dividend']:<12.4f}  {rec:<20}"
                )

    return results


def Analyze_options(ticker=None, years=10, input_mode=False):

    # Si pasan ticker como argumento
    if len(ticker) == 1:
        ticker = ticker.upper()
        results = analyze_dividend_history(ticker, years=10)
    else:
        # input("📊 Ingrese tickers separados por coma (ej: KHC,HASI,O): ")
        tickers = [t.strip() for t in ticker.split(",")]
        results = compare_tickers(tickers, years=10)

    return results


# -----------------------------------------------------
# ✅ FIX: Obtener valor del fact (múltiples métodos)
# -----------------------------------------------------
def get_fact_value(fact):
    """
    Intenta obtener el valor de un fact usando diferentes métodos.
    Inline XBRL puede tener el valor en diferentes atributos.
    """
    # Método 1: xValue
    if hasattr(fact, "xValue") and fact.xValue is not None:
        return fact.xValue

    # Método 2: value
    if hasattr(fact, "value") and fact.value is not None:
        try:
            return float(str(fact.value).replace(",", ""))
        except:
            return fact.value

    # Método 3: text
    if hasattr(fact, "text") and fact.text:
        try:
            return float(str(fact.text).replace(",", ""))
        except:
            return fact.text

    return None


# -----------------------------------------------------
# ✅ Usa metadata.json para retornar los filings:
# -----------------------------------------------------
def get_zip_files(ticker_dir, display_logs=False):
    """
    Usa metadata.json para retornar los filings relevantes:
    - ZIP → con lista de INSTANCE FILES internos
    - HTM → se marca como INLINE XBRL
    - XML sueltos → se toman directamente

    Retorna lista: [ (path, instance_list), ... ] ordenados por fecha.
    """

    metadata_path = os.path.join(ticker_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        if display_logs:
            print("⚠ No existe metadata.json")
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    files = []
    for item in meta.get("downloaded_files", []):
        date_str = item.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = item.get("path")
        if not path or not os.path.exists(path):
            continue

        if item.get("is_zip", False):
            # inspeccionar ZIP
            inst = []
            try:
                with zipfile.ZipFile(path, "r") as z:
                    for name in z.namelist():
                        low = name.lower()
                        if low.endswith(".xml") and not any(
                            k in low for k in ["cal", "pre", "def", "lab"]
                        ):
                            inst.append(name)
            except:
                pass

            files.append((dt, path, inst))

        else:
            # HTM inline XBRL
            if path.lower().endswith(".htm"):
                files.append((dt, path, ["INLINE"]))
            # XML suelto
            elif path.lower().endswith(".xml"):
                files.append((dt, path, [path]))

    # ordenar por fecha
    files.sort(key=lambda x: x[0], reverse=True)

    # devolver (path, instance_list)
    return [(p, inst) for _, p, inst in files]


# -----------------------------------------------------
# Función de carga principal
# -----------------------------------------------------
def load_filing(path, instance=None):
    """
    path: ruta al archivo (htm, xml o zip)
    instance: si es ZIP, el nombre del XML que contiene la instancia
    """
    model = load_xbrl_with_arelle(path, instance, display_logs=False)

    facts = extract_facts(model)
    contexts = extract_contexts(model)
    units = extract_units(model)

    return Filing(
        path=str(path),
        model=model,
        facts=facts,
        contexts=contexts,
        units=units,
    )


# -----------------------------------------------------
# ✅ FIX: Selecciona el hecho más apropiado
# -----------------------------------------------------
def select_best_fact(facts, contexts, prefer="duration"):
    """
    Dado un conjunto de facts del mismo nombre:
      - elige INSTANT o DURATION según preferencia
      - elige el más reciente
      - devuelve el valor como float
    """

    if not facts:
        return None

    candidates = []

    for f in facts:
        ctx_id = f.contextID
        ctx = contexts.get(ctx_id)
        if ctx is None:
            continue

        # seleccionar instant o duration
        if prefer == "instant" and "instant" not in ctx:
            continue
        if prefer == "duration" and ("start" not in ctx or "end" not in ctx):
            continue

        # obtener fecha de referencia
        if "instant" in ctx:
            refdate = ctx["instant"]
        else:
            refdate = ctx["end"]

        # A veces Arelle devuelve strings en vez de datetime
        if isinstance(refdate, str):
            try:
                refdate = datetime.fromisoformat(refdate)
            except:
                continue

        # ✅ FIX: Usar get_fact_value()
        val = get_fact_value(f)
        if val is None:
            continue

        try:
            val = float(val)
        except:
            continue

        candidates.append((refdate, val))

    if not candidates:
        return None

    # ordenar por fecha descendente
    candidates.sort(key=lambda x: x[0], reverse=True)

    # devolver valor más reciente
    return candidates[0][1]


# -----------------------------------------------------
# Interfaz simple para el motor: get_fact()
# -----------------------------------------------------
def get_fact(filing, name, prefer="duration"):
    """
    name = "us-gaap:NetIncomeLoss"
    prefer = "duration" | "instant"
    """
    facts = filing.get_facts(name)
    return select_best_fact(facts, filing.contexts, prefer)


# -----------------------------------------------------
# ✅ FIX: Build TTM con los conceptos correctos
# -----------------------------------------------------
def build_ttm(filings):
    """
    filings → lista de Filing cargados
    Retorna dict con métricas clave para valoración
    """

    def try_names(primary, fallback=None, prefer="duration"):
        """Busca el primer fact disponible en la lista de nombres"""
        for name in primary:
            for f in filings:
                v = get_fact(f, name, prefer)
                if v is not None:
                    return v

        if fallback:
            for name in fallback:
                for f in filings:
                    v = get_fact(f, name, prefer)
                    if v is not None:
                        return v

        return None

    # ✅ CONCEPTOS ACTUALIZADOS BASADOS EN EL DIAGNÓSTICO
    return {
        # Net Income - HASI usa ProfitLoss
        "NetIncome": try_names(
            ["us-gaap:ProfitLoss", "us-gaap:NetIncomeLoss"], prefer="duration"
        ),
        "Depreciation": try_names(
            [
                "us-gaap:DepreciationDepletionAndAmortization",
                "us-gaap:Depreciation",
                "us-gaap:DepreciationAndAmortization",
            ],
            prefer="duration",
        ),
        "GainsOnRealEstateSales": try_names(
            [
                "us-gaap:ProceedsFromSaleOfRealEstateHeldforinvestment",
                "us-gaap:GainLossOnSaleOfProperties",
                "us-gaap:GainLossOnSaleOfPropertyPlantEquipment",
            ],
            prefer="duration",
        ),
        # Operating Cash Flow
        "OperatingCF": try_names(
            [
                "us-gaap:NetCashProvidedByUsedInOperatingActivities",
                "us-gaap:CashProvidedByUsedInOperatingActivities",
            ],
            prefer="duration",
        ),
        # CapEx
        "CapEx": try_names(
            [
                "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
                "us-gaap:CapitalExpenditures",
            ],
            prefer="duration",
        ),
        # Dividendos - HASI usa DividendsCommonStockCash
        "DividendsPaid": try_names(
            [
                "us-gaap:DividendsCommonStockCash",
                "us-gaap:PaymentsOfDividends",
                "us-gaap:PaymentsOfDividendsCommonStock",
            ],
            prefer="duration",
        ),
        # Shares Outstanding
        "Shares": try_names(
            [
                "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
                "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
                "dei:EntityCommonStockSharesOutstanding",
            ],
            prefer="instant",
        ),
        # Revenue
        "Revenues": try_names(
            [
                "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",  # ✅ KHC usa este
                "us-gaap:Revenues",
                "us-gaap:SalesRevenueNet",
                "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            ],
            prefer="duration",
        ),
        # FFO (Funds From Operations) - para REITs
        "FFO": try_names(
            ["us-gaap:FundsFromOperations", "hasi:FundsFromOperations"],
            prefer="duration",
        ),
        # AFFO (Adjusted FFO) - para REITs
        "AFFO": try_names(
            ["us-gaap:AdjustedFundsFromOperations", "hasi:AdjustedFundsFromOperations"],
            prefer="duration",
        ),
        # Assets y Equity para análisis adicional
        "TotalAssets": try_names(["us-gaap:Assets"], prefer="instant"),
        "TotalEquity": try_names(
            ["us-gaap:StockholdersEquity", "us-gaap:Equity"], prefer="instant"
        ),
    }
