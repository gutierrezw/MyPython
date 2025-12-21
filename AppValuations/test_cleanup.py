# test_cleanup.py
"""Script de prueba para valuation_cleanup"""

from valuation_cleanup import diagnose_ttm_coverage, validate_downloads

print("\n" + "=" * 70)
print("PRUEBA 1: Diagnóstico TTM para HASI")
print("=" * 70)

ttm_result = diagnose_ttm_coverage("HASI", display=True)

print("\n" + "=" * 70)
print("PRUEBA 2: Validación de descargas para HASI")
print("=" * 70)

validate_result = validate_downloads("HASI", display=True)

print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)
print(f"Tiene datos para TTM: {ttm_result.get('has_ttm', False)}")
print(f"Trimestres disponibles: {len(ttm_result.get('quarters_available', []))}")
print(f"Trimestres faltantes: {len(ttm_result.get('quarters_missing', []))}")
print(f"Archivos válidos: {validate_result.get('valid_files', 0)}")
print(f"Archivos inválidos: {validate_result.get('invalid_files', 0)}")
