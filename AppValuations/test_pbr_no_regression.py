#!/usr/bin/env python
"""
test_pbr_no_regression.py
Verificar que PBR sigue extrayendo deuda correctamente después de agregar conceptos VALE
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import get_zip_files
from valuation_arelle_engine import run_valuation

print("="*80)
print("🧪 TEST DE NO REGRESIÓN - PBR (Petrobras)")
print("="*80)

# Get PBR filings
ticker_dir = "EDGAR/PBR_EDGAR_Files"
file_list = get_zip_files(ticker_dir, display_logs=False)

print(f"\n✅ Found {len(file_list)} filings for PBR")

# Run valuation with current market price
result = run_valuation(
    file_list=file_list,
    ticker="PBR",
    price=13.50,  # Current market price approx
    company_name="Petróleo Brasileiro S.A. - Petrobras",
    company_type="foreign"
)

if result:
    fundamentals = result.get("fundamentals", {})

    # Balance Sheet
    print("\n" + "="*80)
    print("📊 BALANCE SHEET - DEUDA")
    print("="*80)

    balance = fundamentals.get("balance_sheet", {})

    def fmt(val):
        return f"${val:,.0f}" if val is not None else "None"

    print(f"\n  Total Assets:         {fmt(balance.get('total_assets'))}")
    print(f"  Total Equity:         {fmt(balance.get('total_equity'))}")
    print(f"  Cash & Equivalents:   {fmt(balance.get('cash_and_equivalents'))}")
    print(f"\n  Short-Term Debt:      {fmt(balance.get('short_term_debt'))}")
    print(f"  Long-Term Debt:       {fmt(balance.get('long_term_debt'))}")
    print(f"  Total Debt:           {fmt(balance.get('total_debt'))}")
    print(f"  Net Debt:             {fmt(balance.get('net_debt'))}")

    # Leverage Ratios
    print("\n" + "="*80)
    print("📈 RATIOS DE APALANCAMIENTO")
    print("="*80)

    leverage = fundamentals.get("leverage_ratios", {})

    def fmt_pct(val):
        return f"{val:.2f}%" if val is not None else "None"

    print(f"\n  Debt-to-Equity:       {fmt_pct(leverage.get('debt_to_equity'))}")
    print(f"  Debt-to-Assets:       {fmt_pct(leverage.get('debt_to_assets'))}")
    print(f"  Net Debt-to-Equity:   {fmt_pct(leverage.get('net_debt_to_equity'))}")

    # Enterprise Value
    print("\n" + "="*80)
    print("💰 ENTERPRISE VALUE")
    print("="*80)

    ev = fundamentals.get("enterprise_value", {})

    print(f"\n  Market Cap:           {fmt(ev.get('market_cap'))}")
    print(f"  Enterprise Value:     {fmt(ev.get('enterprise_value'))}")

    ev_ocf = ev.get('ev_to_ocf')
    ev_ocf_str = f"{ev_ocf:.2f}x" if ev_ocf else "None"
    print(f"  EV/Operating CF:      {ev_ocf_str}")

    # Validación
    print("\n" + "="*80)
    print("✅ VALIDACIÓN DE NO REGRESIÓN")
    print("="*80)

    total_debt = balance.get('total_debt')
    short_term = balance.get('short_term_debt')
    long_term = balance.get('long_term_debt')

    if total_debt and total_debt > 0:
        print(f"\n✅ Total Debt extraída correctamente: ${total_debt:,.0f}")

        if short_term and short_term > 0:
            print(f"✅ Short-Term Debt extraída: ${short_term:,.0f}")
        else:
            print(f"⚠️  Short-Term Debt: {short_term}")

        if long_term and long_term > 0:
            print(f"✅ Long-Term Debt extraída: ${long_term:,.0f}")
        else:
            print(f"⚠️  Long-Term Debt: {long_term}")

        # Verificar suma
        if short_term and long_term:
            expected_total = short_term + long_term
            if abs(total_debt - expected_total) < 1000:
                print(f"✅ Total Debt = Short + Long (verificado)")
            else:
                print(f"⚠️  Discrepancia: Total={total_debt:,.0f} vs Sum={expected_total:,.0f}")

        d_to_e = leverage.get('debt_to_equity')
        if d_to_e:
            print(f"✅ Debt-to-Equity calculado: {d_to_e:.2f}%")

        ev_val = ev.get('enterprise_value')
        if ev_val:
            print(f"✅ Enterprise Value calculado: ${ev_val:,.0f}")

        print("\n" + "="*80)
        print("🎉 PBR: NO REGRESIÓN - TODO FUNCIONA CORRECTAMENTE")
        print("="*80)
    else:
        print("\n❌ REGRESIÓN DETECTADA: No se extrajeron métricas de deuda de PBR")
        print("⚠️  Los cambios para VALE rompieron la extracción de PBR")

else:
    print("\n❌ Analysis returned None")

print("\n" + "="*80)
print("✅ Test de no regresión completo")
print("="*80)
