#!/usr/bin/env python
"""
test_pbr_vs_vale_comparison.py
Análisis diferencial: PBR (funciona) vs VALE (falla)

Compara la estructura XBRL de ambos filings para identificar
por qué PBR extrae deuda correctamente y VALE no.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("="*80)
print("🔄 COMPARACIÓN DIFERENCIAL: PBR vs VALE")
print("="*80)

# Cargar ambos filings
pbr_file = "EDGAR/PBR_EDGAR_Files/20F_Filings/pbrform20f_2024.htm"
vale_file = "EDGAR/VALE_EDGAR_Files/20F_Filings/valeform20f_2024.htm"

print(f"\n📁 Cargando PBR: {pbr_file}")
try:
    pbr_filing = load_filing(pbr_file)
    print(f"✅ PBR cargado: {len(pbr_filing.facts)} conceptos únicos")
except Exception as e:
    print(f"❌ Error al cargar PBR: {e}")
    pbr_filing = None

print(f"\n📁 Cargando VALE: {vale_file}")
try:
    vale_filing = load_filing(vale_file)
    print(f"✅ VALE cargado: {len(vale_filing.facts)} conceptos únicos")
except Exception as e:
    print(f"❌ Error al cargar VALE: {e}")
    vale_filing = None

if not pbr_filing or not vale_filing:
    print("\n❌ No se pudieron cargar ambos filings. Abortando.")
    sys.exit(1)

# Keywords para buscar deuda
debt_keywords = ['borrow', 'debt', 'loan']

print("\n" + "="*80)
print("🔎 IDENTIFICANDO CONCEPTOS DE DEUDA")
print("="*80)

def get_debt_concepts(filing):
    """Extrae conceptos relacionados con deuda"""
    debt_concepts = []
    for name in filing.facts.keys():
        name_lower = name.lower()
        if any(kw in name_lower for kw in debt_keywords):
            debt_concepts.append(name)
    return set(debt_concepts)

pbr_debt = get_debt_concepts(pbr_filing)
vale_debt = get_debt_concepts(vale_filing)

print(f"\n📊 PBR: {len(pbr_debt)} conceptos de deuda")
print(f"📊 VALE: {len(vale_debt)} conceptos de deuda")

# Comparar conceptos
common = pbr_debt & vale_debt
only_pbr = pbr_debt - vale_debt
only_vale = vale_debt - pbr_debt

print(f"\n✅ En común: {len(common)} conceptos")
print(f"🔵 Solo en PBR: {len(only_pbr)} conceptos")
print(f"🟡 Solo en VALE: {len(only_vale)} conceptos")

# Mostrar conceptos comunes
print("\n" + "="*80)
print("✅ CONCEPTOS COMUNES (ambos tienen)")
print("="*80)

if common:
    # Agrupar por relevancia
    current_common = [c for c in common if 'current' in c.lower()]
    noncurrent_common = [c for c in common if 'noncurrent' in c.lower()]
    other_common = [c for c in common if c not in current_common and c not in noncurrent_common]

    if current_common:
        print("\n📌 Current/Short-term:")
        for concept in sorted(current_common):
            print(f"  • {concept}")

    if noncurrent_common:
        print("\n📌 Non-current/Long-term:")
        for concept in sorted(noncurrent_common):
            print(f"  • {concept}")

    if other_common:
        print("\n📌 Otros:")
        for concept in sorted(other_common)[:10]:
            print(f"  • {concept}")
        if len(other_common) > 10:
            print(f"  ... y {len(other_common) - 10} más")
else:
    print("\n⚠️  No hay conceptos en común - PBR y VALE usan nomenclatura completamente diferente")

# Mostrar conceptos solo en PBR
print("\n" + "="*80)
print("🔵 CONCEPTOS SOLO EN PBR (por qué PBR funciona)")
print("="*80)

if only_pbr:
    # Filtrar los más relevantes
    pbr_current = [c for c in only_pbr if 'current' in c.lower() or 'shortterm' in c.lower()]
    pbr_noncurrent = [c for c in only_pbr if 'noncurrent' in c.lower() or 'longterm' in c.lower()]

    if pbr_current:
        print("\n📌 PBR - Deuda de Corto Plazo:")
        for concept in sorted(pbr_current)[:10]:
            # Obtener valor de ejemplo
            facts = pbr_filing.facts[concept]
            if facts:
                value = get_fact_value(facts[0])
                print(f"  • {concept}")
                if value:
                    try:
                        print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                    except (ValueError, TypeError):
                        print(f"    └─ Valor: {value}")
                else:
                    print(f"    └─ Valor: N/A")
        if len(pbr_current) > 10:
            print(f"  ... y {len(pbr_current) - 10} más")

    if pbr_noncurrent:
        print("\n📌 PBR - Deuda de Largo Plazo:")
        for concept in sorted(pbr_noncurrent)[:10]:
            facts = pbr_filing.facts[concept]
            if facts:
                value = get_fact_value(facts[0])
                print(f"  • {concept}")
                if value:
                    try:
                        print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                    except (ValueError, TypeError):
                        print(f"    └─ Valor: {value}")
                else:
                    print(f"    └─ Valor: N/A")
        if len(pbr_noncurrent) > 10:
            print(f"  ... y {len(pbr_noncurrent) - 10} más")

    # Otros conceptos
    pbr_other = [c for c in only_pbr if c not in pbr_current and c not in pbr_noncurrent]
    if pbr_other:
        print(f"\n📌 PBR - Otros ({len(pbr_other)} conceptos)")
        for concept in sorted(pbr_other)[:5]:
            print(f"  • {concept}")
        if len(pbr_other) > 5:
            print(f"  ... y {len(pbr_other) - 5} más")
else:
    print("\n✅ PBR no tiene conceptos únicos (usa solo conceptos comunes)")

# Mostrar conceptos solo en VALE
print("\n" + "="*80)
print("🟡 CONCEPTOS SOLO EN VALE (clave para la solución)")
print("="*80)

if only_vale:
    # Filtrar los más relevantes
    vale_current = [c for c in only_vale if 'current' in c.lower() or 'shortterm' in c.lower()]
    vale_noncurrent = [c for c in only_vale if 'noncurrent' in c.lower() or 'longterm' in c.lower()]

    # Identificar namespace
    vale_namespace = [c for c in only_vale if c.startswith('vale:')]
    ifrs_namespace = [c for c in only_vale if c.startswith('ifrs-full:')]

    print(f"\n📊 Distribución de namespace:")
    print(f"  • vale: {len(vale_namespace)} conceptos")
    print(f"  • ifrs-full: {len(ifrs_namespace)} conceptos")

    if vale_current:
        print("\n⭐ VALE - Deuda de Corto Plazo (CRÍTICO):")
        for concept in sorted(vale_current):
            facts = vale_filing.facts[concept]
            if facts:
                value = get_fact_value(facts[0])
                print(f"  • {concept}")
                if value:
                    try:
                        print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                    except (ValueError, TypeError):
                        print(f"    └─ Valor: {value}")
                else:
                    print(f"    └─ Valor: N/A")

    if vale_noncurrent:
        print("\n⭐ VALE - Deuda de Largo Plazo (CRÍTICO):")
        for concept in sorted(vale_noncurrent):
            facts = vale_filing.facts[concept]
            if facts:
                value = get_fact_value(facts[0])
                print(f"  • {concept}")
                if value:
                    try:
                        print(f"    └─ Valor ejemplo: ${float(value):,.0f}")
                    except (ValueError, TypeError):
                        print(f"    └─ Valor: {value}")
                else:
                    print(f"    └─ Valor: N/A")

    # Otros conceptos VALE
    vale_other = [c for c in only_vale if c not in vale_current and c not in vale_noncurrent]
    if vale_other:
        print(f"\n📌 VALE - Otros ({len(vale_other)} conceptos):")
        for concept in sorted(vale_other)[:10]:
            print(f"  • {concept}")
        if len(vale_other) > 10:
            print(f"  ... y {len(vale_other) - 10} más")

else:
    print("\n✅ VALE no tiene conceptos únicos (usa solo conceptos comunes)")

# Análisis de los conceptos que build_ttm() está buscando
print("\n" + "="*80)
print("🎯 CONCEPTOS QUE build_ttm() BUSCA ACTUALMENTE")
print("="*80)

current_seeking = [
    "us-gaap:ShortTermBorrowings",
    "us-gaap:DebtCurrent",
    "us-gaap:LongTermDebtCurrent",
    "ifrs-full:ShorttermBorrowings",
    "ifrs-full:CurrentBorrowings",
    "ifrs-full:CurrentPortionOfLongtermBorrowings",
]

noncurrent_seeking = [
    "us-gaap:LongTermDebtNoncurrent",
    "us-gaap:LongTermDebt",
    "us-gaap:DebtNoncurrent",
    "ifrs-full:LongtermBorrowings",
    "ifrs-full:NoncurrentBorrowings",
]

print("\n📋 Buscando Short-Term Debt:")
for concept in current_seeking:
    in_pbr = "✅ PBR" if concept in pbr_debt else "❌ PBR"
    in_vale = "✅ VALE" if concept in vale_debt else "❌ VALE"
    print(f"  {concept}")
    print(f"    {in_pbr}  |  {in_vale}")

print("\n📋 Buscando Long-Term Debt:")
for concept in noncurrent_seeking:
    in_pbr = "✅ PBR" if concept in pbr_debt else "❌ PBR"
    in_vale = "✅ VALE" if concept in vale_debt else "❌ VALE"
    print(f"  {concept}")
    print(f"    {in_pbr}  |  {in_vale}")

# Conclusiones
print("\n" + "="*80)
print("💡 ANÁLISIS Y CONCLUSIONES")
print("="*80)

# Identificar conceptos que PBR tiene pero VALE no
pbr_has_sought = any(c in pbr_debt for c in current_seeking + noncurrent_seeking)
vale_has_sought = any(c in vale_debt for c in current_seeking + noncurrent_seeking)

print(f"\n🔍 PBR tiene conceptos buscados por build_ttm(): {'✅ SÍ' if pbr_has_sought else '❌ NO'}")
print(f"🔍 VALE tiene conceptos buscados por build_ttm(): {'✅ SÍ' if vale_has_sought else '❌ NO'}")

if pbr_has_sought and not vale_has_sought:
    print("\n⚠️  DIAGNÓSTICO: VALE no tiene los conceptos IFRS que build_ttm() busca")
    print("\n📝 SOLUCIÓN:")

    if vale_namespace:
        print("   ✅ VALE usa namespace custom (vale:)")
        print("   → Agregar conceptos vale: específicos a build_ttm() fallback")
        print(f"\n   Conceptos vale: encontrados ({len(vale_namespace)}):")
        for concept in sorted(vale_namespace)[:10]:
            print(f"      • {concept}")

    if ifrs_namespace:
        print(f"\n   ✅ VALE usa conceptos IFRS no estándar ({len(ifrs_namespace)} conceptos)")
        print("   → Ampliar lista de conceptos IFRS en build_ttm()")
        print(f"\n   Conceptos IFRS únicos de VALE:")
        for concept in sorted(ifrs_namespace)[:10]:
            print(f"      • {concept}")

elif vale_has_sought:
    print("\n✅ VALE tiene conceptos que build_ttm() busca")
    print("⚠️  El problema podría ser:")
    print("   • Contexto temporal incorrecto (DURATION vs INSTANT)")
    print("   • Dimensiones/members no manejados")
    print("   • Problema en select_best_fact()")

print("\n" + "="*80)
print("✅ Comparación completa")
print("="*80)
print("\n💡 PRÓXIMOS PASOS:")
print("  1. Revisar conceptos únicos de VALE identificados arriba")
print("  2. Ejecutar: python test_debt_metrics.py (ver estado actual)")
print("  3. Implementar corrección basada en conceptos encontrados")
