# ================================================
# find_ffo_affo.py
# Buscar conceptos específicos de REITs en HASI
# ================================================

from valuation_arelle_parser import (
    load_xbrl_with_arelle,
    extract_facts,
    extract_contexts,
)
from valuation_xbrl_api import get_fact_value

FILE = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR\HASI_EDGAR_Files\10K_Filings\hasi-20241231.htm"

print("=" * 70)
print("🔍 BUSCANDO CONCEPTOS ESPECÍFICOS DE REITs EN HASI")
print("=" * 70)

model = load_xbrl_with_arelle(FILE, None)
facts_dict = extract_facts(model)
contexts = extract_contexts(model)

print(f"\n📊 Total conceptos únicos: {len(facts_dict)}")

# Palabras clave para buscar
keywords = [
    "FFO",
    "FundsFromOperations",
    "AFFO",
    "AdjustedFunds",
    "CAD",
    "DistributableIncome",
    "FAD",
    "NAREIT",
    "RealEstate",
    "OperatingIncome",
    "EBITDA",
    "Depreciation",
    "Amortization",
    "GainsLosses",
]

print("\n" + "=" * 70)
print("🎯 CONCEPTOS ENCONTRADOS (con valores numéricos)")
print("=" * 70)

matches = []

for concept_name, fact_list in facts_dict.items():
    # Buscar por keywords
    if any(kw.lower() in concept_name.lower() for kw in keywords):
        # Intentar obtener valor numérico
        for fact in fact_list:
            val = get_fact_value(fact)
            if val is not None:
                try:
                    num_val = float(val)
                    ctx = contexts.get(fact.contextID, {})
                    matches.append((concept_name, num_val, ctx))
                    break  # Solo el primero con valor
                except:
                    pass

# Ordenar por nombre
matches.sort(key=lambda x: x[0])

print(f"\n✅ Total matches: {len(matches)}\n")

for concept, value, ctx in matches:
    print(f"📌 {concept}")
    print(f"   Valor: {value:,.2f}")
    if "start" in ctx and "end" in ctx:
        print(f"   Período: {ctx['start'].date()} → {ctx['end'].date()}")
    elif "instant" in ctx:
        print(f"   Fecha: {ctx['instant'].date()}")
    print()

# Buscar todos los conceptos que contengan "hasi:" (custom taxonomy)
print("\n" + "=" * 70)
print("🏢 CONCEPTOS CUSTOM DE HASI (hasi:*)")
print("=" * 70)

hasi_concepts = [(k, v) for k, v in facts_dict.items() if k.startswith("hasi:")]
print(f"\nTotal conceptos custom: {len(hasi_concepts)}\n")

for concept, fact_list in sorted(hasi_concepts)[:30]:  # Primeros 30
    # Obtener un valor si existe
    val = None
    for fact in fact_list:
        val = get_fact_value(fact)
        if val is not None:
            break

    if val:
        try:
            print(f"{concept}: {float(val):,.2f}")
        except:
            print(f"{concept}: {str(val)[:50]}")
    else:
        print(f"{concept}: (sin valor)")

print("\n" + "=" * 70)
print("✅ BÚSQUEDA COMPLETADA")
print("=" * 70)
