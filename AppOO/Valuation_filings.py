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
# 📁 Obtener .zip de filings relevantes
# ============================================================
def get_zip_files(ticker_dir: Path):
    import os


import json
import zipfile
from datetime import datetime


def get_zip_files(ticker_dir, display_logs=False):
    """
    Usa metadata.json para retornar los filings relevantes:
    - ZIP → con lista de INSTANCE FILES internos
    - HTM → se marca como INLINE XBRL
    - XML sueltos → se toman directamente

    Retorna lista: [ (path, instance_list), ... ] ordenados por fecha.
    """

    metadata_path = os.path.join(ticker_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        if display_logs:
            print("⚠ No existe metadata.json")
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    files = []
    for item in meta.get("downloaded_files", []):
        date_str = item.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = item.get("path")
        if not path or not os.path.exists(path):
            continue

        if item.get("is_zip", False):
            # inspeccionar ZIP
            inst = []
            try:
                with zipfile.ZipFile(path, "r") as z:
                    for name in z.namelist():
                        low = name.lower()
                        if low.endswith(".xml") and not any(
                            k in low for k in ["cal", "pre", "def", "lab"]
                        ):
                            inst.append(name)
            except:
                pass

            files.append((dt, path, inst))

        else:
            # HTM inline XBRL
            if path.lower().endswith(".htm"):
                files.append((dt, path, ["INLINE"]))
            # XML suelto
            elif path.lower().endswith(".xml"):
                files.append((dt, path, [path]))

    # ordenar por fecha
    files.sort(key=lambda x: x[0], reverse=True)

    # devolver (path, instance_list)
    return [(p, inst) for _, p, inst in files]


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
