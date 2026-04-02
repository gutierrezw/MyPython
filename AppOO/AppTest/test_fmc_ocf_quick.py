#!/usr/bin/env python
"""
Quick diagnostic: Operating Cash Flow concepts in FMC
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, get_fact_value

print("=" * 80)
print("🔍 QUICK DIAGNOSTIC: Operating Cash Flow - FMC")
print("=" * 80)

fmc_file = "EDGAR/FMC_EDGAR_Files/10K_Filings/fmc-20241231.htm"
print(f"\n📁 Loading: {fmc_file}")

filing = load_filing(fmc_file)
print(f"✅ Loaded {len(filing.facts)} unique concepts")

print("\n" + "=" * 80)
print("🔎 Searching for Operating Cash Flow concepts...")
print("=" * 80)

# Buscar conceptos con "cash" y "operat"
ocf_concepts = []
for name in filing.facts.keys():
    name_lower = name.lower()
    if ("cash" in name_lower and "operat" in name_lower) or "netcash" in name_lower:
        ocf_concepts.append(name)

if ocf_concepts:
    print(f"\n✅ Found {len(ocf_concepts)} Operating Cash Flow related concepts:")
    for name in sorted(ocf_concepts):
        facts = filing.facts[name]
        num_facts = len(facts)
        print(f"\n  • {name} ({num_facts} facts)")

        # Show first 2 fact values
        for i, fact in enumerate(facts[:2]):
            value = get_fact_value(fact)
            ctx_id = getattr(fact, "contextID", "N/A")

            # Get context info
            ctx = filing.contexts.get(ctx_id)
            if ctx:
                ctx_type = "DURATION" if "end" in ctx else "INSTANT"
                date = ctx.get("end") or ctx.get("instant", "N/A")
            else:
                ctx_type = "N/A"
                date = "N/A"

            print(f"    [{i+1}] Value: {value} | Type: {ctx_type} | Date: {date}")
else:
    print("\n❌ NO Operating Cash Flow concepts found!")

# Check concepts build_ttm() is looking for
print("\n" + "=" * 80)
print("🎯 Concepts that build_ttm() searches for:")
print("=" * 80)

sought = [
    "us-gaap:NetCashProvidedByUsedInOperatingActivities",
    "us-gaap:CashProvidedByUsedInOperatingActivities",
]

for concept in sought:
    found = "✅ FOUND" if concept in filing.facts else "❌ NOT FOUND"
    print(f"  {concept}: {found}")

# List all us-gaap:*Cash* concepts
print("\n" + "=" * 80)
print("📋 ALL us-gaap concepts containing 'Cash':")
print("=" * 80)

us_gaap_cash = [n for n in filing.facts.keys() if n.startswith("us-gaap:") and "cash" in n.lower()]
print(f"\nFound {len(us_gaap_cash)} us-gaap:*Cash* concepts")
for concept in sorted(us_gaap_cash)[:20]:
    print(f"  • {concept}")
if len(us_gaap_cash) > 20:
    print(f"  ... and {len(us_gaap_cash) - 20} more")

print("\n" + "=" * 80)
print("✅ Diagnostic complete")
print("=" * 80)
