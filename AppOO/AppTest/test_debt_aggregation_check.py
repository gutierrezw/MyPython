#!/usr/bin/env python
"""
test_debt_aggregation_check.py
Verificar si VALE requiere agregación de múltiples conceptos de deuda

Este script agrupa conceptos de deuda por contextID (fecha) para determinar
si VALE reporta deuda desagregada que debe sumarse.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value
from collections import defaultdict

print("=" * 80)
print("🧮 VERIFICACIÓN DE AGREGACIÓN DE DEUDA - VALE")
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

# Keywords para identificar conceptos de deuda
debt_keywords = ["borrow", "debt", "loan"]

print("\n" + "=" * 80)
print("🔎 IDENTIFICANDO CONCEPTOS DE DEUDA")
print("=" * 80)

# Recopilar todos los conceptos de deuda con sus facts
debt_facts = []

for name in filing.facts.keys():
    name_lower = name.lower()
    is_debt = any(kw in name_lower for kw in debt_keywords)

    if is_debt:
        for fact in filing.facts[name]:
            value = get_fact_value(fact)
            if value is not None:
                # Convertir a float si es posible
                try:
                    value_num = float(value)
                    if value_num > 0:  # Solo valores positivos
                        ctx_id = getattr(fact, "contextID", None)
                        if ctx_id:
                            debt_facts.append({"concept": name, "context_id": ctx_id, "value": value_num, "fact": fact})
                except (ValueError, TypeError):
                    # Si no se puede convertir a número, ignorar
                    pass

print(f"✅ Encontrados {len(debt_facts)} facts de deuda con valores válidos")

# Agrupar por contextID
by_context = defaultdict(list)

for item in debt_facts:
    ctx_id = item["context_id"]
    by_context[ctx_id].append(item)

print(f"✅ Agrupados en {len(by_context)} contextos diferentes")

# Analizar contextos para identificar INSTANT (balance sheet)
print("\n" + "=" * 80)
print("📊 ANÁLISIS POR CONTEXTO (INSTANT)")
print("=" * 80)

instant_contexts = []

for ctx_id, items in by_context.items():
    ctx = filing.contexts.get(ctx_id)
    if ctx and "instant" in ctx:
        instant_contexts.append((ctx_id, ctx, items))

print(f"\n✅ Encontrados {len(instant_contexts)} contextos INSTANT (balance sheet)")

# Identificar contextos con múltiples conceptos
multi_concept_contexts = []

for ctx_id, ctx, items in instant_contexts:
    unique_concepts = set(item["concept"] for item in items)
    if len(unique_concepts) > 1:
        multi_concept_contexts.append((ctx_id, ctx, items, unique_concepts))

print(
    f"\n{'⚠️ ' if multi_concept_contexts else '✅'} Contextos con múltiples conceptos de deuda: {len(multi_concept_contexts)}"
)

if multi_concept_contexts:
    print("\n" + "=" * 80)
    print("⚠️  AGREGACIÓN REQUERIDA DETECTADA")
    print("=" * 80)

    for ctx_id, ctx, items, unique_concepts in multi_concept_contexts[:5]:  # Máximo 5
        date = ctx.get("instant", "N/A")
        print(f"\n📅 Context: {ctx_id}")
        print(f"   Fecha: {date}")
        print(f"   Conceptos únicos: {len(unique_concepts)}")

        # Agrupar por concepto y sumar
        by_concept = defaultdict(float)
        for item in items:
            by_concept[item["concept"]] += item["value"]

        total = sum(by_concept.values())

        print(f"\n   Detalle:")
        for concept, value in sorted(by_concept.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {concept}")
            print(f"        └─ ${value:,.0f}")

        print(f"\n   💰 TOTAL AGREGADO: ${total:,.0f}")

    if len(multi_concept_contexts) > 5:
        print(f"\n   ... y {len(multi_concept_contexts) - 5} contextos más con agregación")

else:
    print("\n✅ NO se requiere agregación - cada contexto tiene un solo concepto")

# Analizar si hay conceptos que aparecen en múltiples fechas
print("\n" + "=" * 80)
print("📈 ANÁLISIS TEMPORAL DE CONCEPTOS")
print("=" * 80)

concept_dates = defaultdict(set)

for ctx_id, ctx, items in instant_contexts:
    date = ctx.get("instant")
    for item in items:
        if date:
            concept_dates[item["concept"]].add(str(date))

print(f"\nConceptos que aparecen en múltiples fechas:")
multi_date_concepts = {c: dates for c, dates in concept_dates.items() if len(dates) > 1}

if multi_date_concepts:
    for concept, dates in sorted(multi_date_concepts.items())[:10]:
        print(f"\n  • {concept}")
        print(f"    └─ Aparece en {len(dates)} fechas diferentes")
        for date in sorted(dates, reverse=True)[:3]:
            print(f"       - {date}")
else:
    print("  (Ninguno - cada concepto aparece solo una vez)")

# Resumen y recomendaciones
print("\n" + "=" * 80)
print("💡 CONCLUSIONES Y RECOMENDACIONES")
print("=" * 80)

if multi_concept_contexts:
    print("\n⚠️  RECOMENDACIÓN: Implementar try_names_aggregate()")
    print("\n  VALE desagrega la deuda en múltiples conceptos que deben sumarse.")
    print(f"  Encontramos {len(multi_concept_contexts)} contextos con agregación necesaria.")

    print("\n  📝 Conceptos que necesitan agregación:")
    all_aggregated_concepts = set()
    for _, _, _, unique_concepts in multi_concept_contexts:
        all_aggregated_concepts.update(unique_concepts)

    for concept in sorted(all_aggregated_concepts)[:15]:
        print(f"     • {concept}")

    if len(all_aggregated_concepts) > 15:
        print(f"     ... y {len(all_aggregated_concepts) - 15} más")

    print("\n  🔧 Acción requerida:")
    print("     1. Implementar try_names_aggregate() en valuation_xbrl_api.py")
    print("     2. Actualizar build_ttm() para usar agregación")
    print("     3. Validar que los facts tengan el mismo contextID antes de sumar")

else:
    print("\n✅ NO se requiere agregación compleja")
    print("\n  VALE parece usar un solo concepto por contexto.")
    print("  Solución más simple: agregar conceptos faltantes a build_ttm()")

# Identificar el concepto más reciente para cada categoría
print("\n" + "=" * 80)
print("🎯 CONCEPTOS MÁS RECIENTES (para build_ttm)")
print("=" * 80)

# Buscar conceptos current/short-term
current_concepts = {}
for ctx_id, ctx, items in instant_contexts:
    date = ctx.get("instant")
    for item in items:
        concept = item["concept"]
        if "current" in concept.lower() or "shortterm" in concept.lower() or "short-term" in concept.lower():
            if concept not in current_concepts or date > current_concepts[concept]["date"]:
                current_concepts[concept] = {"date": date, "value": item["value"], "context_id": ctx_id}

# Buscar conceptos non-current/long-term
noncurrent_concepts = {}
for ctx_id, ctx, items in instant_contexts:
    date = ctx.get("instant")
    for item in items:
        concept = item["concept"]
        if "noncurrent" in concept.lower() or "longterm" in concept.lower() or "long-term" in concept.lower():
            if concept not in noncurrent_concepts or date > noncurrent_concepts[concept]["date"]:
                noncurrent_concepts[concept] = {"date": date, "value": item["value"], "context_id": ctx_id}

if current_concepts:
    print("\n📌 Deuda de Corto Plazo (Current/Short-term):")
    for concept, info in sorted(current_concepts.items(), key=lambda x: x[1]["date"], reverse=True)[:5]:
        print(f"  • {concept}")
        print(f"    └─ Fecha: {info['date']}, Valor: ${info['value']:,.0f}")

if noncurrent_concepts:
    print("\n📌 Deuda de Largo Plazo (Non-current/Long-term):")
    for concept, info in sorted(noncurrent_concepts.items(), key=lambda x: x[1]["date"], reverse=True)[:5]:
        print(f"  • {concept}")
        print(f"    └─ Fecha: {info['date']}, Valor: ${info['value']:,.0f}")

print("\n" + "=" * 80)
print("✅ Verificación completa")
print("=" * 80)
print("\n💡 PRÓXIMOS PASOS:")
print("  1. Revisar resultados de test_vale_debt_comprehensive.py")
print("  2. Ejecutar: python test_pbr_vs_vale_comparison.py")
print("  3. Decidir estrategia de corrección basada en estos resultados")
