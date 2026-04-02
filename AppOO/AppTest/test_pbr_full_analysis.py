#!/usr/bin/env python
"""
Full analysis test for PBR to verify dividend extraction works in complete workflow
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import get_zip_files
from valuation_arelle_engine import run_valuation

print("=" * 80)
print("🧪 FULL VALUATION ANALYSIS TEST - PBR")
print("=" * 80)

# Get PBR filings
ticker_dir = "EDGAR/PBR_EDGAR_Files"
file_list = get_zip_files(ticker_dir, display_logs=True)

print(f"\n✅ Found {len(file_list)} filings for PBR")

# Run valuation analysis
result = run_valuation(
    file_list=file_list, ticker="PBR", price=15.50, company_name="Petrobras", company_type="foreign"  # Example price
)

if result:
    print("\n" + "=" * 80)
    print("📊 DIVIDEND ANALYSIS RESULTS")
    print("=" * 80)

    div_analysis = result.get("dividend_analysis", [])
    if div_analysis:
        print(f"\n✅ Found {len(div_analysis)} dividend analysis items")
        print(f"  Type: {type(div_analysis)}")
    else:
        print("\n❌ No dividend analysis found")

    print("\n" + "=" * 80)
    print("💰 CASH FLOW METRICS")
    print("=" * 80)

    fundamentals = result.get("fundamentals", {})
    cash_flow = fundamentals.get("cash_flow", {})

    def fmt(val):
        return f"${val:,.0f}" if val is not None else "None"

    print(f"\n  Operating CF: {fmt(cash_flow.get('operating_cf'))}")
    print(f"  CapEx: {fmt(cash_flow.get('capex'))}")
    print(f"  Free Cash Flow: {fmt(cash_flow.get('free_cash_flow'))}")
    print(f"  Dividends Paid: {fmt(cash_flow.get('dividends_paid'))}")

    # Check if dividends_paid is populated
    dividends_paid = cash_flow.get("dividends_paid")
    if dividends_paid and dividends_paid > 0:
        print(f"\n✅ SUCCESS: Dividends paid extracted correctly: ${dividends_paid:,.0f}")
    elif dividends_paid is None:
        print("\n❌ FAILURE: dividends_paid is None")
    else:
        print(f"\n⚠️ WARNING: dividends_paid is {dividends_paid}")
else:
    print("\n❌ Analysis returned None")

print("\n" + "=" * 80)
print("✅ Test complete")
print("=" * 80)
