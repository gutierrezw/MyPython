#!/usr/bin/env python
"""
Script de diagnóstico para encontrar conceptos de dividendos en PBR (20-F IFRS)
"""
import sys
from pathlib import Path

# Agregar path
sys.path.insert(0, str(Path(__file__).parent))

from valuation_arelle_parser import load_xbrl_with_arelle, extract_facts

# Cargar el 20-F más reciente de PBR (Petrobras)
pbr_file = "EDGAR/PBR_EDGAR_Files/20F_Filings/pbrform20f_2024.htm"
print(f"🔍 Cargando {pbr_file}...")
print("=" * 80)

model = load_xbrl_with_arelle(pbr_file, display_logs=False)
facts = extract_facts(model)

print(f"\n✅ Total de conceptos XBRL encontrados: {len(facts)}")
print("=" * 80)

# ============================================================================
# BÚSQUEDA 1: Conceptos que contengan "Dividend" en el nombre
# ============================================================================
print("\n📊 CONCEPTOS QUE CONTIENEN 'DIVIDEND':")
print("=" * 80)

dividend_concepts = [name for name in facts.keys() if 'dividend' in name.lower()]
if dividend_concepts:
    for name in sorted(dividend_concepts):
        num_facts = len(facts[name])
        print(f"\n  ✓ {name}")
        print(f"    └─ {num_facts} facts encontrados")

        # Mostrar los primeros 3 valores
        for i, fact in enumerate(facts[name][:3]):
            context_id = getattr(fact, 'contextID', 'N/A')
            value = getattr(fact, 'value', 'N/A')
            unit = getattr(fact, 'unit', 'N/A')
            print(f"       [{i+1}] Context: {context_id} | Value: {value} | Unit: {unit}")
else:
    print("  ❌ No se encontraron conceptos con 'dividend' en el nombre")

# ============================================================================
# BÚSQUEDA 2: Conceptos relacionados con distribuciones a accionistas
# ============================================================================
print("\n\n💰 CONCEPTOS RELACIONADOS CON DISTRIBUCIONES A ACCIONISTAS:")
print("=" * 80)

distribution_keywords = ['distribution', 'payment', 'owner', 'shareholder', 'equity']
distribution_concepts = []

for keyword in distribution_keywords:
    matching = [name for name in facts.keys() if keyword in name.lower() and 'dividend' not in name.lower()]
    distribution_concepts.extend(matching)

# Eliminar duplicados
distribution_concepts = list(set(distribution_concepts))

if distribution_concepts:
    for name in sorted(distribution_concepts)[:15]:  # Limitar a 15 para no saturar
        num_facts = len(facts[name])
        print(f"\n  ✓ {name}")
        print(f"    └─ {num_facts} facts")
else:
    print("  ⚠️  No se encontraron conceptos de distribución")

# ============================================================================
# BÚSQUEDA 3: Conceptos específicos de IFRS para dividendos
# ============================================================================
print("\n\n🌍 CONCEPTOS IFRS ESPECÍFICOS DE DIVIDENDOS:")
print("=" * 80)

ifrs_dividend_concepts = [
    "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
    "ifrs-full:DividendsRecognisedAsDistributionsToOwnersOfParent",
    "ifrs-full:DividendsRecognisedAsDistributionsToOwners",
    "ifrs-full:DividendsPaid",
    "us-gaap:PaymentsOfDividends",
    "us-gaap:PaymentsOfDividendsCommonStock",
    "us-gaap:DividendsCommonStockCash",
]

found_ifrs = False
for concept in ifrs_dividend_concepts:
    if concept in facts:
        found_ifrs = True
        num_facts = len(facts[concept])
        print(f"\n  ✅ ENCONTRADO: {concept}")
        print(f"     └─ {num_facts} facts")

        # Mostrar valores
        for i, fact in enumerate(facts[concept][:3]):
            context_id = getattr(fact, 'contextID', 'N/A')
            value = getattr(fact, 'value', 'N/A')
            unit = getattr(fact, 'unit', 'N/A')
            print(f"        [{i+1}] Context: {context_id} | Value: {value} | Unit: {unit}")

if not found_ifrs:
    print("  ❌ Ninguno de los conceptos IFRS estándar fue encontrado")

# ============================================================================
# BÚSQUEDA 4: Cash Flow Statement - Financing Activities
# ============================================================================
print("\n\n💵 CONCEPTOS DE CASH FLOW - ACTIVIDADES DE FINANCIAMIENTO:")
print("=" * 80)

financing_concepts = [name for name in facts.keys() if 'financing' in name.lower() and 'cash' in name.lower()]

if financing_concepts:
    for name in sorted(financing_concepts)[:10]:
        num_facts = len(facts[name])
        print(f"\n  ✓ {name}")
        print(f"    └─ {num_facts} facts")

        # Mostrar primer valor
        if facts[name]:
            fact = facts[name][0]
            context_id = getattr(fact, 'contextID', 'N/A')
            value = getattr(fact, 'value', 'N/A')
            print(f"       Ejemplo: Context={context_id}, Value={value}")
else:
    print("  ⚠️  No se encontraron conceptos de actividades de financiamiento")

# ============================================================================
# BÚSQUEDA 5: Conceptos custom de PBR (namespace pbr:)
# ============================================================================
print("\n\n🏢 CONCEPTOS PERSONALIZADOS DE PETROBRAS (namespace pbr:):")
print("=" * 80)

pbr_concepts = [name for name in facts.keys() if name.startswith('pbr:')]
dividend_related_pbr = [name for name in pbr_concepts if any(kw in name.lower() for kw in ['dividend', 'distribution', 'payment', 'shareholder'])]

if dividend_related_pbr:
    for name in sorted(dividend_related_pbr):
        num_facts = len(facts[name])
        print(f"\n  ✓ {name}")
        print(f"    └─ {num_facts} facts")

        # Mostrar valores
        for i, fact in enumerate(facts[name][:2]):
            context_id = getattr(fact, 'contextID', 'N/A')
            value = getattr(fact, 'value', 'N/A')
            unit = getattr(fact, 'unit', 'N/A')
            print(f"       [{i+1}] Context: {context_id} | Value: {value} | Unit: {unit}")
else:
    print("  ℹ️  No se encontraron conceptos personalizados de PBR relacionados con dividendos")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n\n" + "=" * 80)
print("📋 RESUMEN DE DIAGNÓSTICO")
print("=" * 80)
print(f"Total de conceptos analizados: {len(facts)}")
print(f"Conceptos con 'dividend': {len(dividend_concepts)}")
print(f"Conceptos IFRS encontrados: {sum(1 for c in ifrs_dividend_concepts if c in facts)}")
print(f"Conceptos de financiamiento: {len(financing_concepts)}")
print(f"Conceptos custom PBR: {len(dividend_related_pbr)}")

if not dividend_concepts and not any(c in facts for c in ifrs_dividend_concepts):
    print("\n⚠️  CONCLUSIÓN: No se encontraron conceptos estándar de dividendos.")
    print("   Posibles razones:")
    print("   1. PBR usa un concepto custom no estándar")
    print("   2. Los dividendos están en el Statement of Changes in Equity")
    print("   3. Se reportan de forma agregada en otra sección")
    print("\n💡 RECOMENDACIÓN: Revisar manualmente el filing HTML para ver cómo reportan dividendos")

print("\n" + "=" * 80)
print("✅ Diagnóstico completado")
print("=" * 80)
