#!/usr/bin/env python
"""
Script temporal para diagnosticar conceptos IFRS de VALE
"""

import sys
from pathlib import Path

# Agregar path
sys.path.insert(0, str(Path(__file__).parent))

from valuation_arelle_parser import load_xbrl_with_arelle, extract_facts

# Cargar el 20-F de VALE
vale_file = "EDGAR/VALE_EDGAR_Files/20F_Filings/valeform20f_2024.htm"
print(f"Cargando {vale_file}...")

model = load_xbrl_with_arelle(vale_file, display_logs=True)
facts = extract_facts(model)

print("\n" + "=" * 70)
print("CONCEPTOS DE CASH FLOW")
print("=" * 70)

# Buscar conceptos relacionados con Operating CF
ocf_concepts = [name for name in facts.keys() if "operating" in name.lower() and "cash" in name.lower()]
print(f"\n📊 Encontrados {len(ocf_concepts)} conceptos de Operating CF:")
for name in sorted(ocf_concepts):
    print(f"  - {name}: {len(facts[name])} facts")

# Buscar CapEx
capex_concepts = [
    name
    for name in facts.keys()
    if "property" in name.lower() and ("purchase" in name.lower() or "acquisition" in name.lower())
]
print(f"\n🏗️  Encontrados {len(capex_concepts)} conceptos de CapEx:")
for name in sorted(capex_concepts)[:10]:  # Limitar a 10
    print(f"  - {name}: {len(facts[name])} facts")

# Mostrar valores específicos de Operating CF
print("\n" + "=" * 70)
print("VALORES DE OPERATING CF (2024)")
print("=" * 70)
for name in ocf_concepts:
    for fact in facts[name]:
        if hasattr(fact, "contextID") and "2024" in str(fact.contextID):
            value = fact.value if hasattr(fact, "value") else "N/A"
            print(f"{name}: {value}")
            break  # Solo el primero de 2024
