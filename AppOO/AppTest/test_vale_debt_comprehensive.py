#!/usr/bin/env python
"""
test_vale_debt_comprehensive.py
Diagnóstico exhaustivo de conceptos de deuda en VALE

Este script analiza en profundidad qué conceptos XBRL relacionados con deuda
están presentes en el filing de VALE y muestra sus características.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value
from datetime import datetime

print("=" * 80)
print("🔍 DIAGNÓSTICO EXHAUSTIVO DE DEUDA - VALE")
print("=" * 80)

# Cargar filing de VALE
vale_file = "EDGAR/VALE_EDGAR_Files/20F_Filings/valeform20f_2024.htm"
print(f"\n📁 Cargando: {vale_file}")

try:
    filing = load_filing(vale_file)
    print(f"✅ Filing cargado: {len(filing.facts)} conceptos únicos")
except Exception as e:
    print(f"❌ Error al cargar filing: {e}")
    sys.exit(1)

# Keywords para buscar conceptos relacionados con deuda
keywords = ["borrow", "debt", "loan", "financ", "liabilit", "obligation"]

print("\n" + "=" * 80)
print("🔎 BÚSQUEDA DE CONCEPTOS RELACIONADOS CON DEUDA")
print("=" * 80)

debt_concepts = {}

for name in filing.facts.keys():
    name_lower = name.lower()
    for keyword in keywords:
        if keyword in name_lower:
            debt_concepts[name] = filing.facts[name]
            break

print(f"\n✅ Encontrados {len(debt_concepts)} conceptos relacionados con deuda")

# Agrupar por namespace
vale_concepts = []
ifrs_concepts = []
other_concepts = []

for name in debt_concepts.keys():
    if name.startswith("vale:"):
        vale_concepts.append(name)
    elif name.startswith("ifrs-full:"):
        ifrs_concepts.append(name)
    else:
        other_concepts.append(name)

print(f"\n📊 DISTRIBUCIÓN POR NAMESPACE:")
print(f"  • vale: {len(vale_concepts)} conceptos")
print(f"  • ifrs-full: {len(ifrs_concepts)} conceptos")
print(f"  • otros: {len(other_concepts)} conceptos")

# Mostrar detalles de cada concepto
print("\n" + "=" * 80)
print("📋 DETALLES DE CONCEPTOS ENCONTRADOS")
print("=" * 80)


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


# Analizar conceptos vale: (prioridad alta)
if vale_concepts:
    print("\n" + "=" * 80)
    print("⭐ CONCEPTOS CUSTOM DE VALE (vale:)")
    print("=" * 80)
    for concept in sorted(vale_concepts):
        analyze_concept(concept, debt_concepts[concept])

# Analizar conceptos ifrs-full: (prioridad media)
if ifrs_concepts:
    print("\n" + "=" * 80)
    print("🌍 CONCEPTOS IFRS ESTÁNDAR (ifrs-full:)")
    print("=" * 80)

    # Filtrar los más relevantes primero
    priority_keywords = ["borrow", "debt", "loan"]
    priority_concepts = []
    other_ifrs = []

    for concept in sorted(ifrs_concepts):
        is_priority = any(kw in concept.lower() for kw in priority_keywords)
        if is_priority:
            priority_concepts.append(concept)
        else:
            other_ifrs.append(concept)

    print(f"\n📌 Conceptos prioritarios ({len(priority_concepts)}):")
    for concept in priority_concepts[:10]:  # Máximo 10
        analyze_concept(concept, debt_concepts[concept])

    if len(priority_concepts) > 10:
        print(f"\n... y {len(priority_concepts) - 10} conceptos prioritarios más")

    if other_ifrs:
        print(f"\n📋 Otros conceptos IFRS ({len(other_ifrs)}):")
        for concept in other_ifrs[:5]:  # Máximo 5
            print(f"  • {concept}")
        if len(other_ifrs) > 5:
            print(f"  ... y {len(other_ifrs) - 5} más")

# Analizar otros conceptos
if other_concepts:
    print("\n" + "=" * 80)
    print("🔸 OTROS CONCEPTOS")
    print("=" * 80)
    for concept in sorted(other_concepts)[:5]:
        analyze_concept(concept, debt_concepts[concept])

# Resumen y recomendaciones
print("\n" + "=" * 80)
print("💡 ANÁLISIS Y RECOMENDACIONES")
print("=" * 80)

print("\n🎯 CONCEPTOS CLAVE IDENTIFICADOS:")

# Buscar conceptos específicos de deuda
current_borrowings = [c for c in debt_concepts.keys() if "current" in c.lower() and "borrow" in c.lower()]
noncurrent_borrowings = [c for c in debt_concepts.keys() if "noncurrent" in c.lower() and "borrow" in c.lower()]
shortterm = [c for c in debt_concepts.keys() if "shortterm" in c.lower() or "short-term" in c.lower()]
longterm = [c for c in debt_concepts.keys() if "longterm" in c.lower() or "long-term" in c.lower()]

if current_borrowings:
    print(f"\n✅ Current Borrowings encontrados ({len(current_borrowings)}):")
    for c in current_borrowings:
        print(f"  • {c}")

if noncurrent_borrowings:
    print(f"\n✅ Non-current Borrowings encontrados ({len(noncurrent_borrowings)}):")
    for c in noncurrent_borrowings:
        print(f"  • {c}")

if shortterm:
    print(f"\n✅ Short-term debt encontrados ({len(shortterm)}):")
    for c in shortterm:
        print(f"  • {c}")

if longterm:
    print(f"\n✅ Long-term debt encontrados ({len(longterm)}):")
    for c in longterm:
        print(f"  • {c}")

# Determinar escenario
print("\n" + "=" * 80)
print("🔮 ESCENARIO IDENTIFICADO:")
print("=" * 80)

if vale_concepts:
    print("\n⚠️  ESCENARIO A: VALE usa namespace custom (vale:)")
    print("  → Necesitarás agregar conceptos vale: a build_ttm() fallback")
    print(f"  → Conceptos custom encontrados: {len(vale_concepts)}")

if len(current_borrowings) > 1 or len(noncurrent_borrowings) > 1:
    print("\n⚠️  ESCENARIO B: Posible agregación requerida")
    print("  → Múltiples conceptos por categoría")
    print("  → Ejecuta test_debt_aggregation_check.py para confirmar")

if ifrs_concepts and not vale_concepts:
    print("\n⚠️  ESCENARIO C: VALE usa conceptos IFRS estándar")
    print("  → Verificar si están en la lista de build_ttm()")
    print("  → Ejecuta test_pbr_vs_vale_comparison.py para comparar")

print("\n" + "=" * 80)
print("✅ Diagnóstico completo")
print("=" * 80)
print("\n💡 PRÓXIMOS PASOS:")
print("  1. Ejecutar: python test_debt_aggregation_check.py")
print("  2. Ejecutar: python test_pbr_vs_vale_comparison.py")
print("  3. Ejecutar: python test_debt_metrics.py (para ver estado actual)")
