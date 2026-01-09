#!/usr/bin/env python
"""
test_hasi_balance_sheet.py
Análisis completo del Balance Sheet de HASI para identificar estructura de equity

Objetivo: Encontrar el concepto exacto que HASI usa para Total Stockholders' Equity
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("="*80)
print("🔍 ANÁLISIS COMPLETO DE BALANCE SHEET - HASI")
print("="*80)

# Cargar filing
hasi_file = "EDGAR/HASI_EDGAR_Files/10K_Filings/hasi-20231231.htm"
print(f"\n📁 Cargando: {hasi_file}")

filing = load_filing(hasi_file)
print(f"✅ Cargado: {len(filing.facts)} conceptos únicos")

# Buscar Assets primero (para comparación)
print("\n" + "="*80)
print("📊 PASO 1: IDENTIFICAR ASSETS")
print("="*80)

assets_concepts = {}
for name in filing.facts.keys():
    name_lower = name.lower()
    if 'asset' in name_lower and ('total' in name_lower or name_lower.endswith('assets')):
        assets_concepts[name] = filing.facts[name]

print(f"\n✅ Encontrados {len(assets_concepts)} conceptos de Assets:")
for concept in sorted(assets_concepts.keys()):
    facts = assets_concepts[concept]
    if facts:
        value = get_fact_value(facts[0])
        try:
            print(f"  • {concept}: ${float(value):,.0f}")
        except (ValueError, TypeError):
            print(f"  • {concept}: {value}")

# Buscar Liabilities
print("\n" + "="*80)
print("📊 PASO 2: IDENTIFICAR LIABILITIES")
print("="*80)

liabilities_concepts = {}
for name in filing.facts.keys():
    name_lower = name.lower()
    if 'liabilit' in name_lower and ('total' in name_lower or name_lower.endswith('liabilities')):
        liabilities_concepts[name] = filing.facts[name]

print(f"\n✅ Encontrados {len(liabilities_concepts)} conceptos de Liabilities:")
for concept in sorted(liabilities_concepts.keys()):
    facts = liabilities_concepts[concept]
    if facts:
        value = get_fact_value(facts[0])
        try:
            print(f"  • {concept}: ${float(value):,.0f}")
        except (ValueError, TypeError):
            print(f"  • {concept}: {value}")

# Buscar balance sheet equation: Assets = Liabilities + Equity
print("\n" + "="*80)
print("📊 PASO 3: BUSCAR CONCEPTOS DE BALANCE SHEET EQUATION")
print("="*80)

# Buscar LiabilitiesAndStockholdersEquity (debe = Assets)
bal_sheet_concepts = {}
for name in filing.facts.keys():
    name_lower = name.lower()
    if (('liabilit' in name_lower and 'equity' in name_lower) or
        ('liabilit' in name_lower and 'stockholder' in name_lower)):
        bal_sheet_concepts[name] = filing.facts[name]

print(f"\n✅ Conceptos de Balance Sheet Equation ({len(bal_sheet_concepts)}):")
for concept in sorted(bal_sheet_concepts.keys()):
    facts = bal_sheet_concepts[concept]
    if facts:
        value = get_fact_value(facts[0])
        try:
            print(f"  • {concept}: ${float(value):,.0f}")
        except (ValueError, TypeError):
            print(f"  • {concept}: {value}")

# Buscar conceptos que contengan "Equity" pero no sean disclosure notes
print("\n" + "="*80)
print("📊 PASO 4: BUSCAR CONCEPTOS DE EQUITY (EXCLUYENDO NOTES)")
print("="*80)

equity_balance = {}
for name in filing.facts.keys():
    name_lower = name.lower()
    # Buscar equity pero excluir disclosure notes y adjustments
    if ('equity' in name_lower and
        'note' not in name_lower and
        'disclosure' not in name_lower and
        'text' not in name_lower and
        'table' not in name_lower and
        'policy' not in name_lower):

        # Obtener primer fact para verificar si es numérico
        facts = filing.facts[name]
        if facts:
            value = get_fact_value(facts[0])
            # Solo incluir si tiene valor numérico
            if value is not None:
                try:
                    float(value)
                    equity_balance[name] = filing.facts[name]
                except (ValueError, TypeError):
                    pass

print(f"\n✅ Encontrados {len(equity_balance)} conceptos numéricos de Equity:")

# Agrupar por tipo
instant_equity = {}
duration_equity = {}

for concept, facts in equity_balance.items():
    # Verificar tipo de contexto
    if facts:
        ctx_id = getattr(facts[0], 'contextID', None)
        if ctx_id:
            ctx = filing.contexts.get(ctx_id)
            if ctx:
                if "instant" in ctx:
                    instant_equity[concept] = facts
                else:
                    duration_equity[concept] = facts

print(f"\n📌 INSTANT (Balance Sheet - valores de punto en tiempo):")
for concept in sorted(instant_equity.keys()):
    facts = instant_equity[concept]
    if facts:
        value = get_fact_value(facts[0])
        ctx_id = getattr(facts[0], 'contextID', 'N/A')
        ctx = filing.contexts.get(ctx_id)
        date = ctx.get("instant", "N/A") if ctx else "N/A"

        try:
            val_str = f"${float(value):,.0f}"
        except (ValueError, TypeError):
            val_str = str(value)

        print(f"  • {concept}")
        print(f"    └─ Valor: {val_str} @ {date}")

print(f"\n📌 DURATION (Cash Flow/Changes - valores de período):")
for concept in sorted(duration_equity.keys())[:10]:  # Limitar a 10
    print(f"  • {concept}")

# Análisis de partners capital (HASI es partnership structure)
print("\n" + "="*80)
print("📊 PASO 5: BUSCAR PARTNERSHIP/MEMBERS CAPITAL")
print("="*80)

partnership_concepts = {}
for name in filing.facts.keys():
    name_lower = name.lower()
    if (('partner' in name_lower or 'member' in name_lower) and
        ('capital' in name_lower or 'equity' in name_lower) and
        'note' not in name_lower and
        'text' not in name_lower):

        facts = filing.facts[name]
        if facts:
            value = get_fact_value(facts[0])
            if value is not None:
                try:
                    float(value)
                    partnership_concepts[name] = filing.facts[name]
                except (ValueError, TypeError):
                    pass

if partnership_concepts:
    print(f"\n✅ Encontrados {len(partnership_concepts)} conceptos de Partnership:")
    for concept in sorted(partnership_concepts.keys()):
        facts = partnership_concepts[concept]
        if facts:
            value = get_fact_value(facts[0])
            try:
                print(f"  • {concept}: ${float(value):,.0f}")
            except (ValueError, TypeError):
                print(f"  • {concept}: {value}")
else:
    print("\n❌ No se encontraron conceptos de Partnership/Members Capital")

# Verificación final: calcular equity como Assets - Liabilities
print("\n" + "="*80)
print("💡 VERIFICACIÓN: Assets - Liabilities = Equity")
print("="*80)

# Buscar Assets más probable
assets_val = None
assets_concept = None
for concept in ['us-gaap:Assets', 'us-gaap:TotalAssets', 'hasi:Assets']:
    if concept in filing.facts:
        facts = filing.facts[concept]
        if facts:
            assets_val = get_fact_value(facts[0])
            assets_concept = concept
            break

# Buscar Liabilities más probable
liab_val = None
liab_concept = None
for concept in ['us-gaap:Liabilities', 'us-gaap:TotalLiabilities', 'hasi:Liabilities']:
    if concept in filing.facts:
        facts = filing.facts[concept]
        if facts:
            liab_val = get_fact_value(facts[0])
            liab_concept = concept
            break

if assets_val and liab_val:
    try:
        assets_num = float(assets_val)
        liab_num = float(liab_val)
        calculated_equity = assets_num - liab_num

        print(f"\n✅ Assets ({assets_concept}): ${assets_num:,.0f}")
        print(f"✅ Liabilities ({liab_concept}): ${liab_num:,.0f}")
        print(f"📊 Equity Calculado: ${calculated_equity:,.0f}")

        # Buscar concepto que coincida con este valor
        print(f"\n🔍 Buscando concepto con valor cercano a ${calculated_equity:,.0f}...")

        tolerance = calculated_equity * 0.01  # 1% tolerancia
        matches = []

        for concept, facts in instant_equity.items():
            if facts:
                value = get_fact_value(facts[0])
                try:
                    val_num = float(value)
                    if abs(val_num - calculated_equity) < tolerance:
                        matches.append((concept, val_num))
                except (ValueError, TypeError):
                    pass

        if matches:
            print(f"\n✅ ENCONTRADOS {len(matches)} CONCEPTOS CON VALOR COINCIDENTE:")
            for concept, value in matches:
                print(f"  ⭐ {concept}: ${value:,.0f}")
        else:
            print("\n❌ No se encontró concepto exacto. Posibles causas:")
            print("   • HASI usa estructura compleja (UPREIT)")
            print("   • Equity reportado incluye noncontrolling interest")
            print("   • Concepto tiene nombre no estándar")

    except (ValueError, TypeError) as e:
        print(f"\n❌ Error en cálculo: {e}")
else:
    print("\n⚠️  No se pudieron extraer Assets o Liabilities para verificación")

print("\n" + "="*80)
print("✅ Análisis completo")
print("="*80)
