#!/usr/bin/env python
"""
test_hasi_equity_diagnostic.py
Diagnóstico de conceptos de Total Equity/Stockholders' Equity en HASI

HASI (Hannon Armstrong) es US-GAAP domestic REIT, pero Total Equity retorna null.
Este script identifica qué concepto específico usa HASI para reportar equity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("=" * 80)
print("🔍 DIAGNÓSTICO DE TOTAL EQUITY - HASI")
print("=" * 80)

# Cargar filing más reciente de HASI
hasi_file = "EDGAR/HASI_EDGAR_Files/10K_Filings/hasi-20231231.htm"
print(f"\n📁 Cargando: {hasi_file}")

try:
    filing = load_filing(hasi_file)
    print(f"✅ Filing cargado: {len(filing.facts)} conceptos únicos")
except Exception as e:
    print(f"❌ Error al cargar filing: {e}")
    sys.exit(1)

# Keywords para buscar conceptos de equity
equity_keywords = ["equity", "stockholder", "shareholder", "partner", "capital"]

print("\n" + "=" * 80)
print("🔎 BÚSQUEDA DE CONCEPTOS DE EQUITY")
print("=" * 80)

equity_concepts = {}

for name in filing.facts.keys():
    name_lower = name.lower()
    # Buscar conceptos que contengan equity, stockholder, shareholder
    if any(kw in name_lower for kw in equity_keywords):
        equity_concepts[name] = filing.facts[name]

print(f"\n✅ Encontrados {len(equity_concepts)} conceptos relacionados con Equity")

# Agrupar por namespace
hasi_concepts = []
us_gaap_concepts = []
other_concepts = []

for name in equity_concepts.keys():
    if name.startswith("hasi:"):
        hasi_concepts.append(name)
    elif name.startswith("us-gaap:"):
        us_gaap_concepts.append(name)
    else:
        other_concepts.append(name)

print(f"\n📊 DISTRIBUCIÓN POR NAMESPACE:")
print(f"  • hasi: {len(hasi_concepts)} conceptos")
print(f"  • us-gaap: {len(us_gaap_concepts)} conceptos")
print(f"  • otros: {len(other_concepts)} conceptos")


# Función para analizar un concepto
def analyze_concept(concept_name, facts):
    """Analiza un concepto y muestra sus características"""
    print(f"\n🔹 {concept_name}")
    print(f"  └─ Total facts: {len(facts)}")

    for i, fact in enumerate(facts[:2]):  # Mostrar máximo 2 facts
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


# Filtrar conceptos más relevantes (total/consolidated equity)
total_equity_candidates = []
for name in equity_concepts.keys():
    name_lower = name.lower()
    # Buscar "total" o "stockholders" pero evitar "attributable", "parent", "noncontrolling"
    if (
        ("total" in name_lower or "stockholder" in name_lower)
        and "equity" in name_lower
        and "noncontrol" not in name_lower
        and "attributable" not in name_lower
        and "parent" not in name_lower
    ):
        total_equity_candidates.append(name)

print("\n" + "=" * 80)
print("⭐ CANDIDATOS MÁS PROBABLES PARA TOTAL EQUITY")
print("=" * 80)

if total_equity_candidates:
    print(f"\n✅ Encontrados {len(total_equity_candidates)} candidatos:")
    for concept in sorted(total_equity_candidates):
        analyze_concept(concept, equity_concepts[concept])
else:
    print("\n⚠️  No se encontraron candidatos obvios")

# Mostrar conceptos US-GAAP
if us_gaap_concepts:
    print("\n" + "=" * 80)
    print("📋 TODOS LOS CONCEPTOS US-GAAP DE EQUITY")
    print("=" * 80)

    # Filtrar los más relevantes
    relevant = [c for c in us_gaap_concepts if "total" in c.lower() or "stockholder" in c.lower()]

    if relevant:
        print(f"\n✅ Conceptos relevantes ({len(relevant)}):")
        for concept in sorted(relevant):
            analyze_concept(concept, equity_concepts[concept])

    # Mostrar lista completa
    print(f"\n📌 Lista completa de US-GAAP equity concepts ({len(us_gaap_concepts)}):")
    for concept in sorted(us_gaap_concepts):
        print(f"  • {concept}")

# Mostrar conceptos HASI custom
if hasi_concepts:
    print("\n" + "=" * 80)
    print("🔸 CONCEPTOS CUSTOM DE HASI (hasi:)")
    print("=" * 80)

    for concept in sorted(hasi_concepts):
        analyze_concept(concept, equity_concepts[concept])

# Verificar conceptos que build_ttm() está buscando
print("\n" + "=" * 80)
print("🎯 CONCEPTOS QUE build_ttm() BUSCA ACTUALMENTE")
print("=" * 80)

current_seeking = [
    "us-gaap:StockholdersEquity",
    "us-gaap:TotalEquity",
    "us-gaap:PartnersCapital",
    "ifrs-full:Equity",
]

print("\n📋 Verificando conceptos buscados:")
for concept in current_seeking:
    in_hasi = "✅ ENCONTRADO" if concept in equity_concepts else "❌ NO ENCONTRADO"
    print(f"  {concept}")
    print(f"    {in_hasi}")
    if concept in equity_concepts:
        # Mostrar valor de ejemplo
        facts = equity_concepts[concept]
        if facts:
            value = get_fact_value(facts[0])
            if value:
                try:
                    print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                except (ValueError, TypeError):
                    print(f"    └─ Valor: {value}")

# Conclusiones
print("\n" + "=" * 80)
print("💡 CONCLUSIONES Y RECOMENDACIONES")
print("=" * 80)

if total_equity_candidates:
    print(f"\n✅ Encontrados {len(total_equity_candidates)} candidatos para Total Equity")
    print("\n📝 Conceptos que deben agregarse a build_ttm():")
    for concept in sorted(total_equity_candidates):
        print(f"   • {concept}")

if hasi_concepts:
    print(f"\n⚠️  HASI usa {len(hasi_concepts)} conceptos custom (hasi:)")
    print("\n📝 Conceptos custom que deben agregarse a fallback:")
    for concept in sorted(hasi_concepts):
        print(f"   • {concept}")

if not total_equity_candidates and not hasi_concepts:
    print("\n❌ NO SE ENCONTRARON CONCEPTOS OBVIOS")
    print("\n🔍 Posibles causas:")
    print("   1. El concepto tiene un nombre no estándar")
    print("   2. HASI reporta equity de forma diferente (REIT structure)")
    print("   3. El valor está en un contexto con dimensiones especiales")

print("\n" + "=" * 80)
print("✅ Diagnóstico completo")
print("=" * 80)
print("\n💡 PRÓXIMOS PASOS:")
print("  1. Revisar conceptos identificados arriba")
print("  2. Agregar conceptos a valuation_xbrl_api.py líneas 494-508")
print("  3. Ejecutar test de validación con HASI")
