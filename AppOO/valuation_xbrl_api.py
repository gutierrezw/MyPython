# ================================================
# valuation_xbrl_api.py
# Capa: API estándar para el motor
# ================================================

# valuation_xbrl_api.py
# -----------------------------------------------------
# Interfaz de alto nivel para el motor de valoración.
# Usa valuation_arelle_parser para cargar y consultar facts.
# -----------------------------------------------------

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
# Función de carga principal
# -----------------------------------------------------
def load_filing(path, instance=None):
    """
    path: ruta al archivo (htm, xml o zip)
    instance: si es ZIP, el nombre del XML que contiene la instancia
    """
    model = load_xbrl_with_arelle(path, instance)

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
# Selecciona el hecho más apropiado entre múltiples contextos
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

        # valor numérico
        try:
            val = float(f.xValue)
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
# Construye TTM a partir de los últimos 4 filings
# -----------------------------------------------------
def build_ttm(filings):
    """
    filings → lista de Filing cargados
    Retorna dict con:
        NetIncome
        OperatingCF
        CapEx
        Dividends
        Shares
        Revenues
        FFO
        AFFO
    """

    def try_names(primary, fallback=None, prefer="duration"):
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

    return {
        "NetIncome": try_names(["us-gaap:NetIncomeLoss", "us-gaap:ProfitLoss"]),
        "OperatingCF": try_names(
            ["us-gaap:NetCashProvidedByUsedInOperatingActivities"]
        ),
        "CapEx": try_names(["us-gaap:CapitalExpenditures"], prefer="duration"),
        "Dividends": try_names(["us-gaap:PaymentsOfDividends"]),
        "Shares": try_names(
            ["us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"],
            ["us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"],
            prefer="duration",
        ),
        "Revenues": try_names(["us-gaap:Revenues", "us-gaap:SalesRevenueNet"]),
        "FFO": try_names(["us-gaap:FundsFromOperations"], prefer="duration"),
        "AFFO": try_names(["us-gaap:AdjustedFundsFromOperations"], prefer="duration"),
    }
