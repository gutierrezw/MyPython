#!/usr/bin/env python
"""
test_hasi_upreit_structure.py
Diagnóstico específico para estructura UPREIT de HASI

En estructuras UPREIT:
Total Equity = Stockholders' Equity + Noncontrolling Interest
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("="*80)
print("🔍 DIAGNÓSTICO UPREIT - HASI")
print("="*80)

# Cargar filing
hasi_file = "EDGAR/HASI_EDGAR_Files/10K_Filings/hasi-20231231.htm"
print(f"\n📁 Cargando: {hasi_file}")

filing = load_filing(hasi_file)
print(f"✅ Cargado: {len(filing.facts)} conceptos")

# Buscar componentes de equity en UPREIT
print("\n" + "="*80)
print("📊 COMPONENTES DE EQUITY EN UPREIT")
print("="*80)

# Equity calculado
assets_val = get_fact_value(filing.facts['us-gaap:Assets'][0])
liab_val = get_fact_value(filing.facts['us-gaap:Liabilities'][0])
calculated_equity = float(assets_val) - float(liab_val)

print(f"\n💡 Equity calculado (Assets - Liabilities): ${calculated_equity:,.0f}")

# Buscar Stockholders' Equity (componente REIT)
print("\n" + "="*80)
print("🔎 BUSCAR: Stockholders' Equity (parte REIT)")
print("="*80)

stockholders_concepts = []
for name in filing.facts.keys():
    name_lower = name.lower()
    if (('stockholder' in name_lower or 'shareholder' in name_lower) and
        'equity' in name_lower and
        'attributable' not in name_lower and
        'note' not in name_lower and
        'text' not in name_lower):
        stockholders_concepts.append(name)

if stockholders_concepts:
    print(f"\n✅ Encontrados {len(stockholders_concepts)} conceptos:")
    for concept in sorted(stockholders_concepts):
        facts = filing.facts[concept]
        if facts:
            # Verificar si es INSTANT
            ctx_id = getattr(facts[0], 'contextID', None)
            if ctx_id:
                ctx = filing.contexts.get(ctx_id)
                if ctx and "instant" in ctx:
                    value = get_fact_value(facts[0])
                    try:
                        val_num = float(value)
                        date = ctx.get("instant", "N/A")
                        print(f"  ⭐ {concept}")
                        print(f"     └─ Valor: ${val_num:,.0f} @ {date}")
                    except (ValueError, TypeError):
                        pass

# Buscar Noncontrolling Interest (Operating Partnership units)
print("\n" + "="*80)
print("🔎 BUSCAR: Noncontrolling Interest (OP units)")
print("="*80)

noncontrolling_concepts = []
for name in filing.facts.keys():
    name_lower = name.lower()
    if (('noncontrol' in name_lower or 'non-control' in name_lower or 'minority' in name_lower) and
        'note' not in name_lower and
        'text' not in name_lower):
        noncontrolling_concepts.append(name)

if noncontrolling_concepts:
    print(f"\n✅ Encontrados {len(noncontrolling_concepts)} conceptos:")
    for concept in sorted(noncontrolling_concepts):
        facts = filing.facts[concept]
        if facts:
            # Verificar si es INSTANT
            ctx_id = getattr(facts[0], 'contextID', None)
            if ctx_id:
                ctx = filing.contexts.get(ctx_id)
                if ctx and "instant" in ctx:
                    value = get_fact_value(facts[0])
                    try:
                        val_num = float(value)
                        date = ctx.get("instant", "N/A")
                        print(f"  ⭐ {concept}")
                        print(f"     └─ Valor: ${val_num:,.0f} @ {date}")
                    except (ValueError, TypeError):
                        pass

# Buscar conceptos con "Attributable" (typical UPREIT structure)
print("\n" + "="*80)
print("🔎 BUSCAR: Equity Attributable to Parent/Company")
print("="*80)

attributable_concepts = []
for name in filing.facts.keys():
    name_lower = name.lower()
    if ('attributable' in name_lower and 'equity' in name_lower and
        'note' not in name_lower and
        'text' not in name_lower):
        attributable_concepts.append(name)

if attributable_concepts:
    print(f"\n✅ Encontrados {len(attributable_concepts)} conceptos:")
    for concept in sorted(attributable_concepts):
        facts = filing.facts[concept]
        if facts:
            # Verificar si es INSTANT
            ctx_id = getattr(facts[0], 'contextID', None)
            if ctx_id:
                ctx = filing.contexts.get(ctx_id)
                if ctx and "instant" in ctx:
                    value = get_fact_value(facts[0])
                    try:
                        val_num = float(value)
                        date = ctx.get("instant", "N/A")
                        print(f"  ⭐ {concept}")
                        print(f"     └─ Valor: ${val_num:,.0f} @ {date}")
                    except (ValueError, TypeError):
                        pass

# Buscar "equity" con "including" (Total Equity Including Noncontrolling)
print("\n" + "="*80)
print("🔎 BUSCAR: Total Equity (Including Noncontrolling)")
print("="*80)

total_equity_concepts = []
for name in filing.facts.keys():
    name_lower = name.lower()
    if ('equity' in name_lower and
        ('including' in name_lower or 'total' in name_lower) and
        'note' not in name_lower and
        'text' not in name_lower and
        'policy' not in name_lower):
        total_equity_concepts.append(name)

if total_equity_concepts:
    print(f"\n✅ Encontrados {len(total_equity_concepts)} conceptos:")
    for concept in sorted(total_equity_concepts):
        facts = filing.facts[concept]
        if facts:
            # Verificar si es INSTANT
            ctx_id = getattr(facts[0], 'contextID', None)
            if ctx_id:
                ctx = filing.contexts.get(ctx_id)
                if ctx and "instant" in ctx:
                    value = get_fact_value(facts[0])
                    try:
                        val_num = float(value)
                        date = ctx.get("instant", "N/A")
                        # Resaltar si coincide con equity calculado
                        tolerance = calculated_equity * 0.01
                        match = "✅ COINCIDE!" if abs(val_num - calculated_equity) < tolerance else ""
                        print(f"  ⭐ {concept} {match}")
                        print(f"     └─ Valor: ${val_num:,.0f} @ {date}")
                    except (ValueError, TypeError):
                        pass

# Verificar sumatoria: Stockholders' + Noncontrolling = Total
print("\n" + "="*80)
print("💡 VERIFICACIÓN: Stockholders + Noncontrolling = Total")
print("="*80)

# Buscar conceptos más comunes
stockholders = None
noncontrolling = None

# Try standard concepts
for concept in ['us-gaap:StockholdersEquity',
                'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']:
    if concept in filing.facts:
        facts = filing.facts[concept]
        if facts and 'IncludingPortion' not in concept:
            val = get_fact_value(facts[0])
            if val:
                try:
                    stockholders = float(val)
                    print(f"\n✅ Stockholders' Equity: ${stockholders:,.0f}")
                    print(f"   └─ Concepto: {concept}")
                    break
                except (ValueError, TypeError):
                    pass

for concept in ['us-gaap:MinorityInterest',
                'us-gaap:PartnersCapitalAttributableToNoncontrollingInterest']:
    if concept in filing.facts:
        facts = filing.facts[concept]
        if facts:
            val = get_fact_value(facts[0])
            if val:
                try:
                    noncontrolling = float(val)
                    print(f"\n✅ Noncontrolling Interest: ${noncontrolling:,.0f}")
                    print(f"   └─ Concepto: {concept}")
                    break
                except (ValueError, TypeError):
                    pass

if stockholders and noncontrolling:
    total = stockholders + noncontrolling
    print(f"\n📊 Total Equity (suma): ${total:,.0f}")
    print(f"📊 Total Equity (calculado): ${calculated_equity:,.0f}")

    diff = abs(total - calculated_equity)
    if diff < 1000:
        print(f"\n✅ COINCIDENCIA PERFECTA (diff: ${diff:,.0f})")
    elif diff < calculated_equity * 0.01:
        print(f"\n✅ COINCIDENCIA ACEPTABLE (diff: ${diff:,.0f})")
    else:
        print(f"\n⚠️  DISCREPANCIA: ${diff:,.0f}")

# Listar TODOS los conceptos con valor ~$2.1B
print("\n" + "="*80)
print("🔎 BUSCAR: Todos los conceptos con valor ~$2.1B")
print("="*80)

print(f"\nBuscando conceptos con valor entre $2.0B y $2.3B...")

tolerance = 200_000_000  # ±200M
min_val = calculated_equity - tolerance
max_val = calculated_equity + tolerance

matches = []

for name in filing.facts.keys():
    facts = filing.facts[name]
    if facts:
        # Solo INSTANT contexts
        ctx_id = getattr(facts[0], 'contextID', None)
        if ctx_id:
            ctx = filing.contexts.get(ctx_id)
            if ctx and "instant" in ctx:
                value = get_fact_value(facts[0])
                try:
                    val_num = float(value)
                    if min_val <= val_num <= max_val:
                        matches.append((name, val_num))
                except (ValueError, TypeError):
                    pass

if matches:
    print(f"\n✅ Encontrados {len(matches)} conceptos en rango:")
    for concept, value in sorted(matches, key=lambda x: x[1], reverse=True):
        diff = value - calculated_equity
        print(f"  • {concept}")
        print(f"    └─ Valor: ${value:,.0f} (diff: ${diff:+,.0f})")
else:
    print("\n❌ No se encontraron conceptos en el rango esperado")

print("\n" + "="*80)
print("✅ Diagnóstico UPREIT completo")
print("="*80)
