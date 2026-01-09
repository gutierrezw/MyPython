#!/usr/bin/env python
"""
Regression test for HASI to verify US-GAAP dividend extraction still works
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import get_zip_files
from valuation_arelle_engine import run_valuation

print("="*80)
print("🧪 REGRESSION TEST - HASI (US-GAAP)")
print("="*80)

# Get HASI filings
ticker_dir = "EDGAR/HASI_EDGAR_Files"
file_list = get_zip_files(ticker_dir, display_logs=False)

print(f"\n✅ Found {len(file_list)} filings for HASI")

# Run valuation analysis
result = run_valuation(
    file_list=file_list,
    ticker="HASI",
    price=32.50,  # Example price
    company_name="Hannon Armstrong",
    company_type="domestic"
)

if result:
    print("\n" + "="*80)
    print("💰 CASH FLOW METRICS")
    print("="*80)

    fundamentals = result.get("fundamentals", {})
    cash_flow = fundamentals.get("cash_flow", {})

    def fmt(val):
        return f"${val:,.0f}" if val is not None else "None"

    print(f"\n  Operating CF: {fmt(cash_flow.get('operating_cf'))}")
    print(f"  CapEx: {fmt(cash_flow.get('capex'))}")
    print(f"  Free Cash Flow: {fmt(cash_flow.get('free_cash_flow'))}")
    print(f"  Dividends Paid: {fmt(cash_flow.get('dividends_paid'))}")

    # Check dividends
    dividends_paid = cash_flow.get('dividends_paid')
    if dividends_paid and dividends_paid > 0:
        print(f"\n✅ SUCCESS: US-GAAP dividends still working: ${dividends_paid:,.0f}")
    elif dividends_paid is None:
        print("\n❌ REGRESSION: dividends_paid is now None (was working before)")
    else:
        print(f"\n⚠️ WARNING: dividends_paid is {dividends_paid}")

    # Check REIT metrics
    print("\n" + "="*80)
    print("🏢 REIT METRICS")
    print("="*80)

    reit = result.get("reit_metrics", {})
    is_reit = reit.get("is_reit", False)

    per_share = result.get("per_share_metrics", {})
    ffo_ps = per_share.get("ffo_per_share")
    affo_ps = per_share.get("affo_per_share")

    print(f"\n  Is REIT: {is_reit}")
    print(f"  FFO per share: {fmt(ffo_ps) if ffo_ps else 'None'}")
    print(f"  AFFO per share: {fmt(affo_ps) if affo_ps else 'None'}")

    if is_reit and ffo_ps:
        print(f"\n✅ SUCCESS: REIT detection and metrics working")
    else:
        print(f"\n⚠️ WARNING: REIT metrics may have issues")

else:
    print("\n❌ Analysis returned None")

print("\n" + "="*80)
print("✅ Regression test complete")
print("="*80)
