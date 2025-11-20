# filings.py
"""
Módulo responsable de:
- Leer metadata.json generado por Batch_edgar_downloader
- Seleccionar filings relevantes (10-Q del año actual y últimos 10-K)
- Fallback escaneando carpetas locales si metadata no existe
- Detección textual básica de REIT
"""
from Modulos_python import json, os, re, Path, datetime

# ============================================================
# 📁 Obtener lista de filings relevantes
# ============================================================
def get_filing_list(ticker_dir: Path):
    """
    Selección REAL para análisis financiero:

    1) Tomar los últimos 4 × 10-Q (independientemente del año)
    2) Tomar el último 10-K
    3) Mantener orden por fecha descendente
    """

    metadata_path = ticker_dir / "metadata.json"
    candidates = []

    # ---------------------------------------------------------------
    # 1. Cargar metadata.json
    # ---------------------------------------------------------------
    if metadata_path.exists():
        try:
            md = json.loads(metadata_path.read_text(encoding="utf-8"))
            for item in md.get("downloaded_files", []):
                form = (item.get("form") or "").upper()
                p = Path(item["path"])
                if not p.exists():
                    continue
                dt = datetime.fromisoformat(item["date"])

                candidates.append({
                    "path": p,
                    "form": form,
                    "dt": dt
                })

        except Exception as e:
            print(f"[WARN] Error leyendo metadata.json → {e}")

    if not candidates:
        return []

    # ---------------------------------------------------------------
    # 2. Separar 10-Q y 10-K
    # ---------------------------------------------------------------
    q = [c for c in candidates if c["form"] == "10-Q"]
    k = [c for c in candidates if c["form"] == "10-K"]

    # selecciona para empresas extranjera
    if not q and not k:
        q = [c for c in candidates if c["form"] == "20-F"]
        k = [c for c in candidates if c["form"] == "6-K"]

    q_sorted = sorted(q, key=lambda x: x["dt"], reverse=True)
    k_sorted = sorted(k, key=lambda x: x["dt"], reverse=True)

    # Tomar últimos 4 trimestres
    last_four_q = q_sorted[:4]

    # Tomar el último 10-K
    last_k = k_sorted[:1]

    # ---------------------------------------------------------------
    # 3. Combinar
    # ---------------------------------------------------------------
    final = last_four_q + last_k

    # Ordenar por fecha
    final = sorted(final, key=lambda x: x["dt"], reverse=True)

    return [c["path"] for c in final]


# ============================================================
# 🏢 Detección textual básica de REIT
# ============================================================
def detect_reit_status_from_text(file_path: Path):
    """
    Busca cadenas típicas:
    - 'real estate investment trust'
    - 'REIT'

    Esto complementa detect_reit_enhanced() del parser.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        if (
            "real estate investment trust" in text
            or "real-estate investment trust" in text
            or " reit " in text
        ):
            return True
    except:
        pass

    return False
