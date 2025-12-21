#!/usr/bin/env python
"""
Investigar conceptos XBRL de deuda en US-GAAP e IFRS
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing

print("="*80)
print("🔍 ANÁLISIS DE CONCEPTOS DE DEUDA")
print("="*80)

# PBR (IFRS)
print("\n📊 PBR (IFRS - 20-F)")
print("-"*80)
pbr_filing = load_filing("EDGAR/PBR_EDGAR_Files/20F_Filings/pbrform20f_2024.htm")

pbr_debt = {}
for name in pbr_filing.facts.keys():
    lower_name = name.lower()
    if any(kw in lower_name for kw in ['borrowing', 'debt']) and 'total' in lower_name:
        if 'member' not in lower_name and 'disclosure' not in lower_name:
            facts = pbr_filing.facts[name]
            if facts and hasattr(facts[0], 'value'):
                val = facts[0].value
                if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('-','').isdigit()):
                    pbr_debt[name] = val

for name, val in sorted(pbr_debt.items()):
    try:
        if isinstance(val, str):
            val = float(val)
        print(f"  {name}: ${val:,.0f}")
    except:
        print(f"  {name}: {val}")

# Buscar específicamente los conceptos clave
print("\n🎯 CONCEPTOS CLAVE IFRS:")
key_ifrs = [
    "ifrs-full:Borrowings",
    "ifrs-full:NoncurrentBorrowings",
    "ifrs-full:CurrentBorrowings",
    "ifrs-full:LongtermBorrowings",
    "ifrs-full:ShorttermBorrowings",
]

for concept in key_ifrs:
    if concept in pbr_filing.facts:
        facts = pbr_filing.facts[concept]
        if facts:
            val = facts[0].value
            ctx = facts[0].contextID
            print(f"  ✅ {concept}")
            print(f"     Value: {val}, Context: {ctx}")
    else:
        print(f"  ❌ {concept} - NOT FOUND")

print("\n" + "="*80)
print("📊 CONCEPTOS US-GAAP ESTÁNDAR")
print("="*80)

us_gaap_concepts = [
    "us-gaap:LongTermDebt",
    "us-gaap:ShortTermBorrowings",
    "us-gaap:LongTermDebtCurrent",
    "us-gaap:LongTermDebtNoncurrent",
    "us-gaap:DebtCurrent",
    "us-gaap:DebtNoncurrent",
]

print("\n💡 Conceptos a buscar en empresas US-GAAP:")
for concept in us_gaap_concepts:
    print(f"  • {concept}")

print("\n" + "="*80)
print("✅ Análisis completado")
print("="*80)
