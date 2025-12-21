# ================================================
# valuation_arelle_parser.py (SIMPLIFIED VERSION)
# Capa: acceso directo a Arelle
# ================================================
from Modulos_python import Path, ZipFile

from zipfile import ZipFile
from pathlib import Path
from arelle import Cntlr, ModelManager, FileSource


def load_xbrl_with_arelle(path, instance=None, display_logs=False):
    """
    Loader universal para Inline XBRL, XML y ZIP.
    Versión simplificada que funciona con cualquier versión de Arelle.
    """
    path = str(path)
    p = Path(path)

    # Controlador sin GUI
    cntlr = Cntlr.Cntlr(logFileName=None)

    ext = p.suffix.lower()

    # --- Resolver archivo a abrir ---
    if ext in [".htm", ".html"]:
        file_to_open = path

    elif ext in [".xml", ".xbrl"]:
        file_to_open = path

    elif ext == ".zip":
        if instance:
            file_to_open = f"{path}::{instance}"
        else:
            with ZipFile(path, "r") as z:
                candidates = [
                    f
                    for f in z.namelist()
                    if f.lower().endswith((".xml", ".xbrl"))
                    and not any(k in f.lower() for k in ["cal", "pre", "def", "lab"])
                ]
                if not candidates:
                    raise Exception(f"No instancia XML dentro del ZIP: {path}")
                file_to_open = f"{path}::{candidates[0]}"
    else:
        raise Exception(f"Tipo no soportado: {path}")

    # ✅ MÉTODO SIMPLE: usar ModelManager.load() directamente
    model_manager = cntlr.modelManager

    # Cargar el modelo
    model_xbrl = model_manager.load(file_to_open)

    if model_xbrl is None:
        raise Exception(f"No se pudo cargar el filing: {file_to_open}")

    if display_logs:
        print(f"✅ Arelle cargó exitosamente: {p.name}")
        print(f"   Total facts: {len(model_xbrl.facts)}")

    return model_xbrl


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
            info["instant"] = c.instantDatetime

        if c.isStartEndPeriod:
            info["start"] = c.startDatetime
            info["end"] = c.endDatetime

        ctx[cid] = info

    return ctx


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
