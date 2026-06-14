"""
Reporte semanal de métricas de código — AppOO
Ejecutar manualmente cada lunes o cuando se quiera un snapshot.

Uso:
    python weekly_report.py

Genera:
    reports/YYYY-WNN_metrics.json   — datos estructurados (para comparar)
    reports/YYYY-WNN_report.txt     — reporte legible
    reports/latest_report.txt       — siempre apunta al último
"""

import ast
import glob
import json
import os
import subprocess
import sys
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
APP_DIR = os.path.join(os.path.dirname(__file__), "..", "AppOO")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
EXCLUDE_DIRS = {".idea", "__pycache__", ".git", "venv", ".venv", "AppTest"}

os.makedirs(REPORTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _week_label() -> str:
    """Retorna etiqueta tipo 2026-W12."""
    today = date.today()
    return f"{today.year}-W{today.isocalendar()[1]:02d}"


def _collect_py_files() -> list:
    """Recorre APP_DIR recursivamente y retorna todos los .py excluyendo directorios ignorados."""
    result = []
    for root, dirs, files in os.walk(APP_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                result.append(os.path.join(root, fname))
    return sorted(result)


def _scan_files() -> dict:
    """Escanea archivos .py y retorna métricas por archivo."""
    results = {}
    for filepath in _collect_py_files():
        rel = os.path.relpath(filepath, APP_DIR)
        try:
            src = open(filepath, encoding="utf-8", errors="ignore").read()
            lines = src.count("\n")
            tree = ast.parse(src)
            classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            methods = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
            results[rel] = {"lines": lines, "classes": classes, "methods": methods}
        except Exception as e:
            results[rel] = {"lines": 0, "classes": 0, "methods": 0, "error": str(e)}
    return results


def _totals(files: dict) -> dict:
    return {
        "lines": sum(f["lines"] for f in files.values()),
        "classes": sum(f["classes"] for f in files.values()),
        "methods": sum(f["methods"] for f in files.values()),
        "files": len(files),
    }


def _run_vulture() -> list:
    """Ejecuta vulture y retorna lista de hallazgos."""
    exclude_patterns = ",".join(EXCLUDE_DIRS)
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "vulture",
                APP_DIR,
                "--min-confidence",
                "80",
                "--exclude",
                exclude_patterns,
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        return lines
    except subprocess.TimeoutExpired:
        return ["ERROR ejecutando vulture: timeout (>180s)"]
    except Exception as e:
        return [f"ERROR ejecutando vulture: {e}"]


def _git_stats_week() -> dict:
    """Estadísticas git de los últimos 7 días."""
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "--since=7 days ago"],
            capture_output=True,
            text=True,
            cwd=APP_DIR,
        ).stdout.strip()
        commits = [l for l in log.splitlines() if l]

        stat = subprocess.run(
            ["git", "diff", "--stat", "HEAD~" + str(max(len(commits), 1)), "HEAD"],
            capture_output=True,
            text=True,
            cwd=APP_DIR,
        ).stdout.strip()

        last_line = stat.splitlines()[-1] if stat else ""
        return {
            "commits": len(commits),
            "commit_list": commits,
            "diff_summary": last_line,
        }
    except Exception as e:
        return {"commits": 0, "commit_list": [], "diff_summary": str(e)}


def _load_previous() -> dict | None:
    """Carga el JSON del reporte anterior (si existe)."""
    jsons = sorted(glob.glob(os.path.join(REPORTS_DIR, "*_metrics.json")))
    week = _week_label()
    # Excluir el de la semana actual si ya existiera
    prev = [f for f in jsons if week not in os.path.basename(f)]
    if not prev:
        return None
    with open(prev[-1]) as f:
        return json.load(f)


def _delta(current: int, previous: int | None) -> str:
    if previous is None:
        return ""
    diff = current - previous
    if diff == 0:
        return "  (=)"
    return f"  ({'+' if diff > 0 else ''}{diff:,})"


# ---------------------------------------------------------------------------
# Generar reporte
# ---------------------------------------------------------------------------


def generate():
    week = _week_label()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files = _scan_files()
    totals = _totals(files)
    vulture_hits = _run_vulture()
    git = _git_stats_week()
    prev = _load_previous()
    prev_t = prev["totals"] if prev else None

    # --- JSON ---
    data = {
        "week": week,
        "date": now,
        "totals": totals,
        "files": files,
        "vulture": vulture_hits,
        "git": git,
    }
    json_path = os.path.join(REPORTS_DIR, f"{week}_metrics.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # --- Texto legible ---
    sep = "─" * 72
    lines_out = []
    a = lines_out.append

    a(f"{'=' * 72}")
    a(f"  REPORTE SEMANAL — AppOO   {week}   generado: {now}")
    a(f"{'=' * 72}")
    a("")

    # Totales
    a("TOTALES")
    a(sep)
    a(f"  Archivos  : {totals['files']:>6,}{_delta(totals['files'],   prev_t['files']   if prev_t else None)}")
    a(f"  Líneas    : {totals['lines']:>6,}{_delta(totals['lines'],   prev_t['lines']   if prev_t else None)}")
    a(f"  Clases    : {totals['classes']:>6,}{_delta(totals['classes'], prev_t['classes'] if prev_t else None)}")
    a(f"  Métodos   : {totals['methods']:>6,}{_delta(totals['methods'], prev_t['methods'] if prev_t else None)}")
    a("")

    # Top 10 archivos por líneas
    a("TOP 10 ARCHIVOS POR LÍNEAS")
    a(sep)
    top10 = sorted(files.items(), key=lambda x: x[1]["lines"], reverse=True)[:10]
    for name, m in top10:
        a(f"  {name:<50}  {m['lines']:>6,} líneas  {m['classes']:>2} cls  {m['methods']:>4} mét")
    a("")

    # Git
    a("ACTIVIDAD GIT (últimos 7 días)")
    a(sep)
    a(f"  Commits   : {git['commits']}")
    a(f"  Resumen   : {git['diff_summary']}")
    for c in git["commit_list"][:10]:
        a(f"    · {c}")
    a("")

    # Vulture
    dead_imports = [v for v in vulture_hits if "unused import" in v]
    dead_vars = [v for v in vulture_hits if "unused variable" in v]
    dead_code = [v for v in vulture_hits if "unreachable code" in v]
    dead_methods = [v for v in vulture_hits if "unused method" in v or "unused function" in v]

    a("CÓDIGO MUERTO — vulture (≥80% confianza)")
    a(sep)
    a(f"  Imports no usados : {len(dead_imports):>4}")
    a(f"  Variables muertas : {len(dead_vars):>4}")
    a(f"  Código inalcanzable: {len(dead_code):>4}")
    a(f"  Métodos/funciones : {len(dead_methods):>4}")
    a(f"  TOTAL hallazgos   : {len(vulture_hits):>4}")
    a("")

    if dead_methods:
        a("  Métodos/funciones sin uso:")
        for v in dead_methods[:20]:
            a(f"    · {v}")
        a("")

    if dead_imports:
        a("  Imports sin uso (primeros 20):")
        for v in dead_imports[:20]:
            a(f"    · {v}")
        a("")

    # Delta vs semana anterior
    if prev:
        a(f"COMPARACIÓN VS SEMANA ANTERIOR ({prev['week']})")
        a(sep)
        for key, label in [
            ("lines", "Líneas"),
            ("methods", "Métodos"),
            ("classes", "Clases"),
        ]:
            delta = totals[key] - prev_t[key]
            sign = "+" if delta >= 0 else ""
            a(f"  {label:<12}: {prev_t[key]:>6,} → {totals[key]:>6,}  ({sign}{delta:,})")
        prev_vulture = len(prev.get("vulture", []))
        delta_v = len(vulture_hits) - prev_vulture
        sign = "+" if delta_v >= 0 else ""
        a(f"  {'Cod.muerto':<12}: {prev_vulture:>6,} → {len(vulture_hits):>6,}  ({sign}{delta_v})")
        a("")

    a("=" * 72)

    report_txt = "\n".join(lines_out)

    txt_path = os.path.join(REPORTS_DIR, f"{week}_report.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(report_txt)

    latest_path = os.path.join(REPORTS_DIR, "latest_report.txt")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(report_txt)

    print(report_txt)
    print(f"\nArchivos guardados:")
    print(f"  {json_path}")
    print(f"  {txt_path}")
    print(f"  {latest_path}")


if __name__ == "__main__":
    generate()
