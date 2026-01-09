#!/usr/bin/env python
"""
Quick diagnostic to check actual fact names extracted by load_filing()
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing

print("="*80)
print("🔍 DIAGNOSTIC: Fact Names in PBR Filing")
print("="*80)

pbr_file = "EDGAR/PBR_EDGAR_Files/20F_Filings/pbrform20f_2024.htm"
print(f"\n📁 Loading: {pbr_file}")

filing = load_filing(pbr_file)

print(f"\n✅ Loaded {len(filing.facts)} unique concept names")
print("\n" + "="*80)
print("🔎 Searching for dividend-related concepts...")
print("="*80)

dividend_related = []
for name in filing.facts.keys():
    if 'dividend' in name.lower():
        dividend_related.append(name)

if dividend_related:
    print(f"\n✅ Found {len(dividend_related)} dividend concepts:")
    for name in sorted(dividend_related):
        num_facts = len(filing.facts[name])
        print(f"  • {name} ({num_facts} facts)")

        # Show first fact value
        if filing.facts[name]:
            fact = filing.facts[name][0]
            ctx_id = getattr(fact, 'contextID', 'N/A')
            value = getattr(fact, 'value', 'N/A')
            print(f"    └─ Example: Context={ctx_id}, Value={value}")
else:
    print("\n❌ NO dividend concepts found!")
    print("\n💡 Let's check what namespace prefixes are actually used:")

    # Get all unique prefixes
    prefixes = set()
    for name in filing.facts.keys():
        if ':' in name:
            prefix = name.split(':')[0]
            prefixes.add(prefix)

    print(f"\n📋 Found {len(prefixes)} unique namespace prefixes:")
    for prefix in sorted(prefixes):
        count = sum(1 for n in filing.facts.keys() if n.startswith(prefix + ':'))
        print(f"  • {prefix}: {count} concepts")

    # Show some IFRS concepts if they exist
    print("\n🌍 Sample of concepts from each prefix:")
    for prefix in sorted(prefixes)[:5]:  # Limit to 5
        matching = [n for n in filing.facts.keys() if n.startswith(prefix + ':')]
        if matching:
            print(f"\n  {prefix}:")
            for concept in sorted(matching)[:3]:
                print(f"    - {concept}")

print("\n" + "="*80)
print("✅ Diagnostic complete")
print("="*80)
