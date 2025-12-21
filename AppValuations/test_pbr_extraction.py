#!/usr/bin/env python
"""
Test de extracción específica de dividendos para PBR
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from valuation_xbrl_api import load_filing, build_ttm

print("="*80)
print("🧪 TEST DE EXTRACCIÓN DE DIVIDENDOS - PBR")
print("="*80)

# Cargar el filing de PBR
pbr_file = "EDGAR/PBR_EDGAR_Files/20F_Filings/pbrform20f_2024.htm"
print(f"\n📁 Cargando: {pbr_file}")

filing = load_filing(pbr_file)
print(f"✅ Filing cargado correctamente")
print(f"   Total de facts: {len(filing.facts)}")
print(f"   Total de contexts: {len(filing.contexts)}")

# Construir TTM
print("\n" + "="*80)
print("📊 CONSTRUYENDO TTM (Trailing Twelve Months)")
print("="*80)

ttm = build_ttm([filing])

print("\n✅ TTM construido. Resultados:")
print("-"*80)

# Mostrar todos los valores extraídos
for key, value in ttm.items():
    if value is not None:
        if isinstance(value, (int, float)):
            print(f"  {key:30s}: {value:,.0f}")
        else:
            print(f"  {key:30s}: {value}")
    else:
        print(f"  {key:30s}: ❌ None")

# Análisis específico de dividendos
print("\n" + "="*80)
print("🔍 ANÁLISIS DETALLADO DE DIVIDENDOS")
print("="*80)

dividends_paid = ttm.get("DividendsPaid")

if dividends_paid is None:
    print("\n❌ PROBLEMA: DividendsPaid es None")
    print("\nPosibles causas:")
    print("  1. El concepto IFRS no se encontró en los facts")
    print("  2. El contexto temporal no coincide")
    print("  3. El filtro duration/instant está fallando")

    # Intentar buscar manualmente
    print("\n🔍 Buscando manualmente conceptos de dividendos...")

    dividend_concepts_to_try = [
        "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
        "ifrs-full:DividendsRecognisedAsDistributionsToOwnersOfParent",
        "us-gaap:PaymentsOfDividends",
        "us-gaap:PaymentsOfDividendsCommonStock",
    ]

    for concept in dividend_concepts_to_try:
        facts = filing.get_facts(concept)
        if facts:
            print(f"\n  ✅ ENCONTRADO: {concept}")
            print(f"     Total facts: {len(facts)}")

            # Mostrar primeros 3 facts
            for i, fact in enumerate(facts[:3]):
                ctx_id = getattr(fact, 'contextID', 'N/A')
                value = getattr(fact, 'value', 'N/A')

                # Obtener info del contexto
                ctx = filing.contexts.get(ctx_id, {})
                ctx_type = "DURATION" if "start" in ctx and "end" in ctx else "INSTANT" if "instant" in ctx else "UNKNOWN"

                if "start" in ctx and "end" in ctx:
                    period = f"{ctx['start']} to {ctx['end']}"
                elif "instant" in ctx:
                    period = f"instant: {ctx['instant']}"
                else:
                    period = "Unknown period"

                print(f"     [{i+1}] Value: {value}")
                print(f"         Context: {ctx_id} ({ctx_type})")
                print(f"         Period: {period}")
        else:
            print(f"  ❌ NO ENCONTRADO: {concept}")

else:
    print(f"\n✅ DividendsPaid extraído correctamente: {dividends_paid:,.0f}")

    # Verificar si es negativo (como debería ser)
    if dividends_paid < 0:
        print(f"   ✓ Valor es negativo (correcto para cash outflow)")
        print(f"   ✓ Dividendos pagados: ${abs(dividends_paid):,.0f}")
    else:
        print(f"   ⚠️ Valor es positivo (inusual, debería ser negativo)")

# Comparación con el valor esperado del diagnóstico
print("\n" + "="*80)
print("📋 COMPARACIÓN CON DIAGNÓSTICO")
print("="*80)

expected_value = -18327000000  # Del diagnóstico anterior
extracted_value = ttm.get("DividendsPaid")

print(f"\nValor esperado (del diagnóstico): ${abs(expected_value):,.0f}")
print(f"Valor extraído (build_ttm):       {f'${abs(extracted_value):,.0f}' if extracted_value else 'None'}")

if extracted_value:
    if abs(extracted_value - expected_value) < 1000000:  # Tolerancia de 1M
        print("\n✅ ¡ÉXITO! Los valores coinciden")
    else:
        diff = abs(extracted_value - expected_value)
        print(f"\n⚠️ Los valores difieren por: ${diff:,.0f}")
else:
    print("\n❌ FALLO: No se pudo extraer el valor")

print("\n" + "="*80)
print("✅ Test completado")
print("="*80)
