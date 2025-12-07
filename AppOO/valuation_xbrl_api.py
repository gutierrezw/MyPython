# ================================================
# valuation_xbrl_api.py (FIXED VERSION)
# Capa: API estándar para el motor
# ================================================

import os
import zipfile

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
