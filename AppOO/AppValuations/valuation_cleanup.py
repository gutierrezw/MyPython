# valuation_cleanup.py
"""
Módulo de depuración y limpieza de archivos EDGAR descargados.

Funciones principales:
- validate_downloads(ticker): Valida que los archivos descargados sean correctos
- cleanup_directory(ticker, dry_run=True): Limpia archivos obsoletos/duplicados
- fix_downloads(ticker): Re-descarga archivos faltantes o corruptos
"""

from Modulos_python import os, json, timezone, re
from datetime import datetime
from pathlib import Path

# =====================================================
# Configuración
# =====================================================
BASE_DIR = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR"

# Límites esperados (debe coincidir con valuation_edgar_downloader.py)
EXPECTED_LIMITS = {
    "10-K": 5,
    "10-Q": 8,
    "20-F": 3
}


# =====================================================
# Funciones de validación
# =====================================================
def extract_period_from_filename(filename: str) -> str | None:
    """
    Extrae la fecha del período del nombre del archivo.
    Ejemplos:
        hasi-20241231.htm -> 2024-12-31
        hasi-20240930.htm -> 2024-09-30
    """
    match = re.search(r'-(\d{8})\.(htm|xml)', filename)
    if match:
        date_str = match.group(1)  # YYYYMMDD
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except:
            return None
    return None


def validate_date_consistency(filing: dict) -> dict:
    """
    Valida que la fecha del filing sea consistente con el nombre del archivo.

    Returns:
        {
            "valid": bool,
            "filing_date": str,
            "period_date": str,
            "issue": str (si hay problema)
        }
    """
    filing_date = filing.get("date")
    filename = filing.get("file", "")
    period_date = extract_period_from_filename(filename)

    result = {
        "valid": True,
        "filing_date": filing_date,
        "period_date": period_date,
        "filename": filename
    }

    if not period_date:
        result["valid"] = False
        result["issue"] = "No se pudo extraer fecha del período del filename"
        return result

    # Para 10-Q y 10-K, el filing_date debe ser POSTERIOR al period_date
    # (las empresas reportan después de cerrar el período)
    try:
        filing_dt = datetime.strptime(filing_date, "%Y-%m-%d")
        period_dt = datetime.strptime(period_date, "%Y-%m-%d")

        if filing_dt < period_dt:
            result["valid"] = False
            result["issue"] = f"Filing date ({filing_date}) anterior al período ({period_date})"
            return result

        # ✅ CAMBIO: Permitir hasta 180 días para 10-K (pueden tardar más)
        # Para 10-Q normalmente son ~45 días, para 10-K pueden ser ~90 días
        form_type = filing.get("form", "")
        max_days = 180 if form_type == "10-K" else 120

        days_diff = (filing_dt - period_dt).days
        if days_diff > max_days:
            result["valid"] = False
            result["issue"] = f"Filing date {days_diff} días después del período (esperado <{max_days})"
            return result

    except Exception as e:
        result["valid"] = False
        result["issue"] = f"Error al parsear fechas: {e}"

    return result


def validate_downloads(ticker: str, display=True) -> dict:
    """
    Valida que los archivos descargados sean correctos y estén completos.

    Returns:
        {
            "ticker": str,
            "total_files": int,
            "valid_files": int,
            "invalid_files": int,
            "missing_forms": dict,  # {form: cantidad_faltante}
            "issues": [{"file": str, "issue": str}]
        }
    """
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_EDGAR_Files")
    metadata_path = os.path.join(ticker_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        return {
            "error": f"No se encontró metadata.json para {ticker}",
            "path": metadata_path
        }

    # Leer metadata
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    downloaded_files = metadata.get("downloaded_files", [])
    company_type = metadata.get("company_type", "domestic")

    # Determinar formularios esperados
    if company_type == "foreign":
        expected_forms = ["20-F"]
    else:
        expected_forms = ["10-K", "10-Q"]

    # Contar archivos por tipo (solo no-ZIP)
    counts = {}
    for form in expected_forms:
        counts[form] = sum(1 for f in downloaded_files if f["form"] == form and not f.get("is_zip", False))

    # Validar fechas
    issues = []
    valid_count = 0
    invalid_count = 0

    for filing in downloaded_files:
        if filing.get("is_zip", False):
            continue  # Skip ZIPs en validación de fechas

        validation = validate_date_consistency(filing)

        if validation["valid"]:
            valid_count += 1
        else:
            invalid_count += 1
            issues.append({
                "file": filing["file"],
                "form": filing["form"],
                "issue": validation["issue"],
                "filing_date": validation["filing_date"],
                "period_date": validation["period_date"]
            })

    # Identificar faltantes
    missing_forms = {}
    for form in expected_forms:
        expected = EXPECTED_LIMITS.get(form, 5)
        actual = counts.get(form, 0)
        if actual < expected:
            missing_forms[form] = expected - actual

    result = {
        "ticker": ticker,
        "company_type": company_type,
        "total_files": len([f for f in downloaded_files if not f.get("is_zip", False)]),
        "valid_files": valid_count,
        "invalid_files": invalid_count,
        "counts_by_form": counts,
        "expected_counts": {f: EXPECTED_LIMITS.get(f, 5) for f in expected_forms},
        "missing_forms": missing_forms,
        "issues": issues
    }

    if display:
        print("=" * 70)
        print(f"📊 VALIDACIÓN: {ticker}")
        print("=" * 70)
        print(f"Tipo de empresa: {company_type}")
        print(f"\n📁 Archivos descargados:")
        for form in expected_forms:
            actual = counts.get(form, 0)
            expected = EXPECTED_LIMITS.get(form, 5)
            status = "✅" if actual >= expected else "⚠️"
            print(f"  {status} {form}: {actual}/{expected}")

        if missing_forms:
            print(f"\n⚠️  Formularios faltantes:")
            for form, missing in missing_forms.items():
                print(f"  - {form}: Faltan {missing} archivos")

        print(f"\n📋 Validación de fechas:")
        print(f"  ✅ Válidos: {valid_count}")
        print(f"  ❌ Inválidos: {invalid_count}")

        if issues:
            print(f"\n❌ PROBLEMAS DETECTADOS:")
            for issue in issues[:10]:  # Mostrar máximo 10
                print(f"  • {issue['form']} - {issue['file']}")
                print(f"    └─ {issue['issue']}")
                print(f"       Filing: {issue['filing_date']} | Período: {issue['period_date']}")

        print("\n" + "=" * 70)

    return result


def cleanup_directory(ticker: str, dry_run=True, display=True) -> dict:
    """
    Limpia archivos obsoletos y duplicados del directorio de descargas.
    ✅ ACTUALIZA metadata.json después de eliminar archivos.

    Args:
        ticker: Ticker de la empresa
        dry_run: Si True, solo muestra qué haría sin eliminar nada
        display: Si mostrar mensajes

    Returns:
        {
            "files_to_delete": [str],
            "deleted": bool,
            "space_freed": int (bytes),
            "metadata_updated": bool
        }
    """
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_EDGAR_Files")

    if not os.path.exists(ticker_dir):
        return {"error": f"Directorio no existe: {ticker_dir}"}

    # Archivos en el directorio
    all_files = []
    for root, dirs, files in os.walk(ticker_dir):
        for file in files:
            if file != "metadata.json":
                all_files.append(os.path.join(root, file))

    # Leer metadata para saber qué archivos DEBEN estar
    metadata_path = os.path.join(ticker_dir, "metadata.json")
    expected_files = set()
    metadata = None

    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        for filing in metadata.get("downloaded_files", []):
            expected_files.add(filing["path"])

    # Identificar archivos huérfanos (no en metadata)
    orphan_files = [f for f in all_files if f not in expected_files]

    space_freed = sum(os.path.getsize(f) for f in orphan_files if os.path.exists(f))

    result = {
        "files_to_delete": orphan_files,
        "deleted": False,
        "space_freed": space_freed,
        "metadata_updated": False
    }

    if display:
        print("=" * 70)
        print(f"🧹 LIMPIEZA: {ticker}")
        print("=" * 70)
        print(f"Total archivos en directorio: {len(all_files)}")
        print(f"Archivos en metadata: {len(expected_files)}")
        print(f"Archivos huérfanos: {len(orphan_files)}")
        print(f"Espacio a liberar: {space_freed / 1024:.2f} KB")

        if orphan_files:
            print(f"\n📂 Archivos a eliminar:")
            for f in orphan_files[:20]:  # Mostrar máximo 20
                print(f"  - {os.path.basename(f)}")
            if len(orphan_files) > 20:
                print(f"  ... y {len(orphan_files) - 20} más")

        if not dry_run:
            print("\n⚠️  ELIMINANDO ARCHIVOS...")
        else:
            print("\n💡 Modo DRY RUN - No se eliminó nada")
            print("   Para eliminar realmente, usa: cleanup_directory(ticker, dry_run=False)")

        print("=" * 70)

    # Eliminar archivos si no es dry_run
    if not dry_run:
        deleted_count = 0
        for f in orphan_files:
            try:
                os.remove(f)
                deleted_count += 1
            except Exception as e:
                if display:
                    print(f"❌ Error al eliminar {f}: {e}")

        result["deleted"] = deleted_count > 0

        # ✅ ACTUALIZAR metadata.json: Verificar que todos los archivos listados existen
        if metadata and os.path.exists(metadata_path):
            original_count = len(metadata.get("downloaded_files", []))

            # Filtrar solo archivos que REALMENTE existen en disco
            valid_files = []
            for filing in metadata.get("downloaded_files", []):
                if os.path.exists(filing["path"]):
                    valid_files.append(filing)

            # Actualizar metadata solo si cambió algo
            if len(valid_files) != original_count:
                metadata["downloaded_files"] = valid_files
                metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
                metadata["cleanup_performed"] = True
                metadata["files_removed"] = original_count - len(valid_files)

                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)

                result["metadata_updated"] = True

                if display:
                    print(f"\n✅ metadata.json actualizado:")
                    print(f"   Archivos antes: {original_count}")
                    print(f"   Archivos después: {len(valid_files)}")
                    print(f"   Eliminados del metadata: {original_count - len(valid_files)}")

    return result


def fix_downloads(ticker: str, display=True) -> dict:
    """
    Identifica y corrige problemas con las descargas.

    Esta función:
    1. Valida las descargas actuales
    2. Si hay problemas, sugiere acciones correctivas
    3. Opcionalmente, re-ejecuta el downloader

    Returns:
        {
            "validation": dict,  # Resultado de validate_downloads()
            "needs_redownload": bool,
            "suggestions": [str]
        }
    """
    validation = validate_downloads(ticker, display=False)

    if "error" in validation:
        return validation

    needs_redownload = False
    suggestions = []

    # Analizar problemas
    if validation["invalid_files"] > 0:
        needs_redownload = True
        suggestions.append(f"❌ {validation['invalid_files']} archivos con fechas inválidas")

    if validation["missing_forms"]:
        needs_redownload = True
        for form, missing in validation["missing_forms"].items():
            suggestions.append(f"⚠️  Faltan {missing} archivos {form}")

    # Si hay problemas de fechas futuras, definitivamente necesita re-descarga
    future_issues = [i for i in validation["issues"] if "anterior al período" in i["issue"]]
    if future_issues:
        needs_redownload = True
        suggestions.append(f"⚠️  {len(future_issues)} archivos con fechas futuras detectadas")

    result = {
        "validation": validation,
        "needs_redownload": needs_redownload,
        "suggestions": suggestions
    }

    if display:
        print("=" * 70)
        print(f"🔧 DIAGNÓSTICO: {ticker}")
        print("=" * 70)

        if not needs_redownload:
            print("✅ Todo está correcto - No se necesita acción")
        else:
            print("⚠️  SE DETECTARON PROBLEMAS:")
            for suggestion in suggestions:
                print(f"   {suggestion}")

            print("\n💡 ACCIÓN RECOMENDADA:")
            print("   1. Limpia archivos obsoletos: cleanup_directory(ticker, dry_run=False)")
            print("   2. Re-descarga archivos: download_filing(ticker, display=True)")
            print("   3. Valida nuevamente: validate_downloads(ticker)")

        print("=" * 70)

    return result


def diagnose_ttm_coverage(ticker: str, display=True) -> dict:
    """
    Diagnostica si tenemos los trimestres necesarios para calcular TTM actual.

    En 2025, el TTM actual debería ser:
    - Q4 2024 (Oct-Dec 2024)
    - Q1 2025 (Jan-Mar 2025)
    - Q2 2025 (Apr-Jun 2025)
    - Q3 2025 (Jul-Sep 2025)

    Returns:
        {
            "has_ttm": bool,
            "quarters_available": [str],
            "quarters_missing": [str],
            "can_use_annual_fallback": bool
        }
    """
    ticker_dir = os.path.join(BASE_DIR, f"{ticker}_EDGAR_Files")
    metadata_path = os.path.join(ticker_dir, "metadata.json")

    if not os.path.exists(metadata_path):
        return {"error": f"No se encontró metadata.json para {ticker}"}

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Extraer períodos de los 10-Q
    quarters_available = []
    for filing in metadata.get("downloaded_files", []):
        if filing["form"] == "10-Q" and not filing.get("is_zip", False):
            period = extract_period_from_filename(filing["file"])
            if period:
                quarters_available.append(period)

    # Extraer años de los 10-K
    annuals_available = []
    for filing in metadata.get("downloaded_files", []):
        if filing["form"] == "10-K" and not filing.get("is_zip", False):
            period = extract_period_from_filename(filing["file"])
            if period:
                annuals_available.append(period)

    quarters_available.sort(reverse=True)  # Más recientes primero
    annuals_available.sort(reverse=True)

    # Trimestres esperados para TTM 2025 (Q4 2024 - Q3 2025)
    expected_quarters = [
        "2025-09-30",  # Q3 2025
        "2025-06-30",  # Q2 2025
        "2025-03-31",  # Q1 2025
        "2024-12-31",  # Q4 2024 (puede estar en 10-K 2024)
    ]

    # Verificar qué tenemos
    quarters_missing = []
    for q in expected_quarters:
        if q not in quarters_available:
            quarters_missing.append(q)

    # Verificar si podemos usar fallback anual
    can_use_fallback = "2024-12-31" in annuals_available

    has_ttm = len(quarters_missing) == 0 or (len(quarters_missing) == 1 and can_use_fallback and "2024-12-31" in quarters_missing)

    result = {
        "has_ttm": has_ttm,
        "quarters_available": quarters_available,
        "quarters_missing": quarters_missing,
        "annuals_available": annuals_available,
        "can_use_annual_fallback": can_use_fallback
    }

    if display:
        print("=" * 70)
        print(f"📊 DIAGNÓSTICO TTM: {ticker}")
        print("=" * 70)

        # Mostrar todos los trimestres disponibles
        print(f"\n📁 Trimestres disponibles ({len(quarters_available)} total):")
        for q in quarters_available:
            print(f"  ✅ {q}")

        print(f"\n📁 Años completos disponibles ({len(annuals_available)} total):")
        for a in annuals_available:
            print(f"  ✅ {a}")

        print(f"\n🎯 Trimestres necesarios para TTM 2025:")
        for q in expected_quarters:
            status = "✅" if q in quarters_available else ("⚠️" if q in annuals_available else "❌")
            source = ""
            if q in quarters_available:
                source = " (10-Q)"
            elif q in annuals_available:
                source = " (10-K disponible)"
            print(f"  {status} {q}{source}")

        if quarters_missing:
            print(f"\n⚠️  Trimestres faltantes: {len(quarters_missing)}")
            for q in quarters_missing:
                print(f"  - {q}")

        if can_use_fallback and "2024-12-31" in quarters_missing:
            print(f"\n💡 Nota: Q4 2024 (2024-12-31) está en el 10-K 2024")
            print(f"   El sistema usará el año completo como fallback")

        if has_ttm:
            print(f"\n✅ RESULTADO: Datos suficientes para calcular TTM")
        else:
            print(f"\n❌ RESULTADO: Faltan datos - necesita re-descargar")

        print("=" * 70)

    return result


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python valuation_cleanup.py TICKER [accion]")
        print("\nAcciones disponibles:")
        print("  validate  - Valida descargas (default)")
        print("  cleanup   - Limpia archivos huérfanos (dry run)")
        print("  fix       - Diagnostica y sugiere correcciones")
        print("  ttm       - Diagnóstico de cobertura TTM")
        print("\nEjemplo:")
        print("  python valuation_cleanup.py HASI ttm")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    action = sys.argv[2].lower() if len(sys.argv) > 2 else "validate"

    if action == "validate":
        validate_downloads(ticker, display=True)
    elif action == "cleanup":
        cleanup_directory(ticker, dry_run=True, display=True)
    elif action == "fix":
        fix_downloads(ticker, display=True)
    elif action == "ttm":
        diagnose_ttm_coverage(ticker, display=True)
    else:
        print(f"❌ Acción desconocida: {action}")
        sys.exit(1)
