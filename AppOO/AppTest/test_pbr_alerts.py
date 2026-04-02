#!/usr/bin/env python
"""
Test de alertas mejoradas para PBR
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import get_zip_files
from valuation_arelle_engine import run_valuation

print("=" * 80)
print("🧪 TEST DE ALERTAS MEJORADAS - PBR")
print("=" * 80)

# Get PBR filings
ticker_dir = "EDGAR/PBR_EDGAR_Files"
file_list = get_zip_files(ticker_dir, display_logs=False)

# Run valuation
result = run_valuation(file_list=file_list, ticker="PBR", price=14.85, company_name="Petrobras", company_type="foreign")

if result:
    print("\n" + "=" * 80)
    print("⚠️ SISTEMA DE ALERTAS")
    print("=" * 80)

    alerts = result.get("alerts", {})
    risk = result.get("risk_assessment", {})

    # Critical alerts
    critical = alerts.get("critical", [])
    if critical:
        print(f"\n🚨 ALERTAS CRÍTICAS ({len(critical)}):")
        for alert in critical:
            print(f"\n  {alert.get('type')}")
            print(f"  {alert.get('message')}")
            print(f"  Recomendación: {alert.get('recommendation')}")
    else:
        print("\n✅ No hay alertas críticas")

    # Warnings
    warnings = alerts.get("warnings", [])
    if warnings:
        print(f"\n⚠️ ADVERTENCIAS ({len(warnings)}):")
        for alert in warnings:
            print(f"\n  {alert.get('type')}")
            print(f"  {alert.get('message')}")
            if "recommendation" in alert:
                print(f"  Recomendación: {alert.get('recommendation')}")
    else:
        print("\n✅ No hay advertencias")

    # Info
    info = alerts.get("info", [])
    if info:
        print(f"\n💡 INFORMACIÓN POSITIVA ({len(info)}):")
        for alert in info:
            print(f"\n  {alert.get('type')}")
            print(f"  {alert.get('message')}")

    # Overall risk
    print("\n" + "=" * 80)
    print("📊 EVALUACIÓN DE RIESGO")
    print("=" * 80)
    print(f"\n  Nivel: {risk.get('level')}")
    print(f"  {risk.get('message')}")
    print(f"\n  Critical: {risk.get('critical_count')}")
    print(f"  Warnings: {risk.get('warning_count')}")
    print(f"  Info: {risk.get('info_count')}")

    # Métricas clave
    print("\n" + "=" * 80)
    print("📈 MÉTRICAS CLAVE")
    print("=" * 80)

    per_share = result.get("per_share_metrics", {})
    fundamentals = result.get("fundamentals", {})
    cash_flow = fundamentals.get("cash_flow", {})

    ocf = cash_flow.get("operating_cf")
    dividends = cash_flow.get("dividends_paid")
    eps = per_share.get("eps")
    div_ps = per_share.get("dividend_per_share")

    print(f"\n  Operating Cash Flow:  ${ocf:,.0f}" if ocf else "  OCF: None")
    print(f"  Dividends Paid:       ${dividends:,.0f}" if dividends else "  Dividends: None")
    print(f"  EPS:                  ${eps:.2f}" if eps else "  EPS: None")
    print(f"  Dividend per Share:   ${div_ps:.2f}" if div_ps else "  Div/Share: None")

    if ocf and dividends:
        payout_ocf = (dividends / ocf) * 100
        print(f"\n  ✅ Payout (OCF):      {payout_ocf:.1f}%")

    if eps and div_ps:
        payout_ni = (div_ps / eps) * 100
        print(f"  ⚠️ Payout (EPS):      {payout_ni:.1f}% (no aplicable para capital intensivo)")

print("\n" + "=" * 80)
print("✅ Test complete")
print("=" * 80)
