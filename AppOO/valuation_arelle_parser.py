# ================================================
# valuation_arelle_parser.py
# Capa: acceso directo a Arelle
# ================================================

# valuation_arelle_parser.py
# ----------------------------------------------
# Nueva versión limpia del loader iXBRL + XBRL
# ----------------------------------------------

from arelle import Cntlr
from arelle import ModelXbrl
from zipfile import ZipFile
from pathlib import Path


# ----------------------------------------------
# Cargador universal usando Arelle
# ----------------------------------------------
def load_xbrl_with_arelle(path, instance=None):
    """
    Carga cualquier formato soportado:
        - .htm / .html  → Inline XBRL
        - .xml / .xbrl → instancia clásica
        - .zip         → paquetes SEC
    Retorna: modelXbrl (Arelle)
    """
    path = str(path)
    p = Path(path)

    # Crear el controlador
    cntlr = Cntlr.Cntlr(logFileName=None)

    # Detectar extensión
    ext = p.suffix.lower()

    # Resolver instancia principal (htm/xml/zip)
    if ext in [".htm", ".html", ".xml", ".xbrl"]:
        open_file = path

    elif ext == ".zip":
        with ZipFile(path, "r") as z:
            candidates = [
                f
                for f in z.namelist()
                if f.lower().endswith((".xml", ".xbrl"))
                and "cal" not in f.lower()
                and "pre" not in f.lower()
                and "def" not in f.lower()
                and "lab" not in f.lower()
            ]

            if not candidates:
                raise Exception(f"No se encontró instancia en ZIP: {path}")

            if instance:
                open_file = f"{path}::{instance}"
            else:
                open_file = f"{path}::{candidates[0]}"

    else:
        raise Exception(f"Tipo no soportado: {path}")

    # 🔥 CARGA REAL QUE FUNCIONA EN TU VERSION DE ARELLE
    try:
        model = cntlr.modelManager.load(open_file)
    except Exception as e:
        raise Exception(f"Arelle no pudo cargar {open_file}: {e}")

    if model is None:
        raise Exception(f"Arelle devolvió model=None: {open_file}")

    return model


# ----------------------------------------------
# Extraer hechos
# ----------------------------------------------
def extract_facts(model):
    """
    Devuelve un diccionario:
        { 'us-gaap:NetIncomeLoss' : [fact1, fact2, ...] }
    """
    facts = {}

    for fact in model.facts:
        if fact.qname is None:
            continue

        name = f"{fact.qname.prefix}:{fact.qname.localName}"

        if name not in facts:
            facts[name] = []

        facts[name].append(fact)

    return facts


# ----------------------------------------------
# Extraer contextos
# ----------------------------------------------
def extract_contexts(model):
    """
    Devuelve diccionario:
        { contextID : { 'start':..., 'end':..., 'instant':... } }
    """
    ctx = {}

    for cid, c in model.contexts.items():
        if c is None:
            continue

        info = {}

        if c.isInstantPeriod:
            info["instant"] = c.instantDate

        if c.isStartEndPeriod:
            info["start"] = c.startDatetime
            info["end"] = c.endDatetime

        ctx[cid] = info

    return ctx


# ----------------------------------------------
# Extraer unidades
# ----------------------------------------------
def extract_units(model):
    """
    Devuelve unidades:
       { unitID : 'USD', 'shares', 'pure', ... }
    """
    units = {}

    for uid, u in model.units.items():
        if u is None:
            continue

        measures = [m.localName for m in u.measures[0]]
        if measures:
            units[uid] = measures[0]

    return units
