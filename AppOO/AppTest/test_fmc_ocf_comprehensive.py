#!/usr/bin/env python
"""
test_fmc_ocf_comprehensive.py
Diagnóstico exhaustivo de conceptos de Operating Cash Flow en FMC

FMC Corporation es US-GAAP domestic, por lo que debería usar conceptos estándar.
Este script identifica qué concepto específico usa FMC.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("=" * 80)
print("🔍 DIAGNÓSTICO DE OPERATING CASH FLOW - FMC")
print("=" * 80)

# Cargar filing más reciente de FMC
fmc_file = "EDGAR/FMC_EDGAR_Files/10K_Filings/fmc-20241231.htm"
print(f"\n📁 Cargando: {fmc_file}")

try:
    filing = load_filing(fmc_file)
    print(f"✅ Filing cargado: {len(filing.facts)} conceptos únicos")
except Exception as e:
    print(f"❌ Error al cargar filing: {e}")
    sys.exit(1)

# Keywords para buscar conceptos de cash flow
keywords = ["cash", "operating", "activities"]

print("\n" + "=" * 80)
print("🔎 BÚSQUEDA DE CONCEPTOS DE CASH FLOW")
print("=" * 80)

cash_flow_concepts = {}

for name in filing.facts.keys():
    name_lower = name.lower()
    # Buscar conceptos que contengan cash AND operating
    if ("cash" in name_lower or "cashflow" in name_lower) and "operat" in name_lower:
        cash_flow_concepts[name] = filing.facts[name]

print(f"\n✅ Encontrados {len(cash_flow_concepts)} conceptos de Operating Cash Flow")

# Agrupar por namespace
fmc_concepts = []
us_gaap_concepts = []
other_concepts = []

for name in cash_flow_concepts.keys():
    if name.startswith("fmc:"):
        fmc_concepts.append(name)
    elif name.startswith("us-gaap:"):
        us_gaap_concepts.append(name)
    else:
        other_concepts.append(name)

print(f"\n📊 DISTRIBUCIÓN POR NAMESPACE:")
print(f"  • fmc: {len(fmc_concepts)} conceptos")
print(f"  • us-gaap: {len(us_gaap_concepts)} conceptos")
print(f"  • otros: {len(other_concepts)} conceptos")


# Función para analizar un concepto
def analyze_concept(concept_name, facts):
    """Analiza un concepto y muestra sus características"""
    print(f"\n🔹 {concept_name}")
    print(f"  └─ Total facts: {len(facts)}")

    for i, fact in enumerate(facts[:3]):  # Mostrar máximo 3 facts
        # Contexto
        ctx_id = getattr(fact, "contextID", "N/A")
        ctx = filing.contexts.get(ctx_id)

        if ctx:
            ctx_type = "INSTANT" if "instant" in ctx else "DURATION"
            if "instant" in ctx:
                date = ctx["instant"]
            elif "end" in ctx:
                date = ctx["end"]
            else:
                date = "N/A"
        else:
            ctx_type = "N/A"
            date = "N/A"

        # Valor
        value = get_fact_value(fact)

        # Unidades y decimals
        unit_id = getattr(fact, "unitID", "N/A")
        decimals = getattr(fact, "decimals", "N/A")

        # Dimensiones (members)
        members = []
        if ctx and "dims" in ctx:
            members = list(ctx["dims"].keys())

        print(f"  └─ Fact {i+1}/{len(facts)}:")
        print(f"      • Valor: {value}")
        print(f"      • Contexto: {ctx_type} @ {date}")
        print(f"      • Unidad: {unit_id}, Decimals: {decimals}")
        if members:
            print(f"      • Dimensiones: {members}")


# Mostrar conceptos US-GAAP
if us_gaap_concepts:
    print("\n" + "=" * 80)
    print("⭐ CONCEPTOS US-GAAP (ESTÁNDAR)")
    print("=" * 80)

    for concept in sorted(us_gaap_concepts):
        analyze_concept(concept, cash_flow_concepts[concept])

# Mostrar conceptos FMC custom
if fmc_concepts:
    print("\n" + "=" * 80)
    print("🔸 CONCEPTOS CUSTOM DE FMC (fmc:)")
    print("=" * 80)

    for concept in sorted(fmc_concepts):
        analyze_concept(concept, cash_flow_concepts[concept])

# Mostrar otros conceptos
if other_concepts:
    print("\n" + "=" * 80)
    print("📋 OTROS CONCEPTOS")
    print("=" * 80)

    for concept in sorted(other_concepts):
        analyze_concept(concept, cash_flow_concepts[concept])

# Buscar conceptos específicos que build_ttm() está buscando
print("\n" + "=" * 80)
print("🎯 CONCEPTOS QUE build_ttm() BUSCA ACTUALMENTE")
print("=" * 80)

current_seeking = [
    "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "us-gaap:CashProvidedByUsedInOperatingActivities",
    "ifrs-full:CashFlowsFromUsedInOperatingActivities",
]

print("\n📋 Verificando conceptos buscados:")
for concept in current_seeking:
    in_fmc = "✅ ENCONTRADO" if concept in cash_flow_concepts else "❌ NO ENCONTRADO"
    print(f"  {concept}")
    print(f"    {in_fmc}")

# Si ningún concepto fue encontrado, buscar variaciones
if not any(concept in cash_flow_concepts for concept in current_seeking):
    print("\n⚠️  NINGÚN CONCEPTO ESTÁNDAR ENCONTRADO")
    print("\n🔍 Buscando variaciones en todos los conceptos...")

    # Buscar cualquier concepto que tenga "cash" y "operat" en el nombre
    all_cash_operating = []
    for name in filing.facts.keys():
        name_lower = name.lower()
        if "cash" in name_lower and "operat" in name_lower:
            all_cash_operating.append(name)

    if all_cash_operating:
        print(f"\n✅ Encontrados {len(all_cash_operating)} conceptos relacionados:")
        for concept in sorted(all_cash_operating)[:15]:
            facts = filing.facts[concept]
            value = get_fact_value(facts[0]) if facts else None
            print(f"  • {concept}")
            if value:
                try:
                    print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                except (ValueError, TypeError):
                    print(f"    └─ Valor: {value}")

# Conclusiones
print("\n" + "=" * 80)
print("💡 CONCLUSIONES Y RECOMENDACIONES")
print("=" * 80)

if us_gaap_concepts:
    print(f"\n✅ FMC usa {len(us_gaap_concepts)} conceptos US-GAAP estándar")
    print("\n📝 Conceptos encontrados que deben agregarse a build_ttm():")
    for concept in sorted(us_gaap_concepts):
        print(f"   • {concept}")

if fmc_concepts:
    print(f"\n⚠️  FMC usa {len(fmc_concepts)} conceptos custom (fmc:)")
    print("\n📝 Conceptos custom que deben agregarse a fallback:")
    for concept in sorted(fmc_concepts):
        print(f"   • {concept}")

if not us_gaap_concepts and not fmc_concepts:
    print("\n❌ NO SE ENCONTRARON CONCEPTOS OBVIOS")
    print("\n🔍 Posibles causas:")
    print("   1. El concepto tiene un nombre no estándar")
    print("   2. FMC reporta cash flow de forma diferente")
    print("   3. El valor está en un contexto con dimensiones especiales")

print("\n" + "=" * 80)
print("✅ Diagnóstico completo")
print("=" * 80)
print("\n💡 PRÓXIMOS PASOS:")
print("  1. Revisar conceptos identificados arriba")
print("  2. Agregar conceptos a valuation_xbrl_api.py líneas 463-475")
print("  3. Ejecutar test de validación")
