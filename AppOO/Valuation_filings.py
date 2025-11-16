# filings.py
"""
Módulo responsable de:
- Leer metadata.json generado por Batch_edgar_downloader
- Seleccionar filings relevantes (10-Q del año actual y últimos 10-K)
- Fallback escaneando carpetas locales si metadata no existe
- Detección textual básica de REIT
"""

import json
import re
from pathlib import Path
from datetime import datetime


# ============================================================
# 📁 Obtener lista de filings relevantes
# ============================================================
def get_filing_list(ticker_dir: Path):
    """
    Retorna lista de Path ordenada:

    1. Todos los 10-Q del año actual (si existen)
    2. Últimos 5 10-K
    3. Fallback: últimos 5 archivos cualquiera disponibles

    La metadata.json permite reconstruir fácilmente los paths.
    """
    metadata_path = ticker_dir / "metadata.json"
    candidates = []

    # --------------------------------------------------------
    # 1️⃣ LEER metadata.json (si existe)
    # --------------------------------------------------------
    if metadata_path.exists():
        try:
            md = json.loads(metadata_path.read_text(encoding="utf-8"))
            for item in md.get("downloaded_files", []):
                if not isinstance(item, dict):
                    continue

                pstr = (
                    item.get("path")
                    or item.get("local_path")
                    or item.get("file")
                    or item.get("local_name")
                )

                form = (item.get("form") or "").upper()
                date_str = (
                    item.get("date")
                    or item.get("downloaded_date")
                    or item.get("timestamp")
                )

                if not pstr:
                    continue

                # Normaliza path
                p = Path(pstr)
                if not p.is_absolute():
                    p = ticker_dir / p

                if not p.exists():
                    continue

                # Normaliza fecha
                dt = None
                if isinstance(date_str, str):
                    for fmt in (
                        "%Y-%m-%d",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f",
                    ):
                        try:
                            dt = datetime.fromisoformat(date_str)
                            break
                        except:
                            try:
                                dt = datetime.strptime(date_str, fmt)
                                break
                            except:
                                dt = None
                if dt is None:
                    try:
                        dt = datetime.fromtimestamp(p.stat().st_mtime)
                    except:
                        dt = datetime(1900, 1, 1)

                # Guardar como candidato
                if p.suffix.lower() in (".htm", ".html", ".xml"):
                    candidates.append(
                        {"path": p, "form": form, "dt": dt}
                    )
        except Exception as e:
            print(f"⚠️ Error leyendo metadata.json: {e}")

    # --------------------------------------------------------
    # 2️⃣ Fallback: buscar archivos manualmente en carpetas 10Q/10K
    # --------------------------------------------------------
    if not candidates:
        for sub in ["10Q_Filings", "10K_Filings", "6K_Filings", "20F_Filings"]:
            d = ticker_dir / sub
            if d.exists():
                for ext in ("*.htm", "*.html", "*.xml"):
                    for f in d.glob(ext):
                        form = ""
                        if "10q" in sub.lower() or re.search(r"10-?q", f.name, re.I):
                            form = "10-Q"
                        elif "10k" in sub.lower() or re.search(r"10-?k", f.name, re.I):
                            form = "10-K"

                        dt = datetime.fromtimestamp(f.stat().st_mtime)
                        candidates.append(
                            {"path": f, "form": form, "dt": dt}
                        )

    if not candidates:
        return []

    # --------------------------------------------------------
    # 3️⃣ Selección: 10-Q del año actual + últimos 10-K
    # --------------------------------------------------------
    year_now = datetime.now().year

    # Filtrar 10-Q
    ten_qs = [
        c for c in candidates
        if c["form"].upper().startswith("10-Q")
           or re.search(r"10-?q", c["path"].name, re.I)
    ]
    ten_qs_year = [c for c in ten_qs if c["dt"].year == year_now]
    ten_qs_year = sorted(ten_qs_year, key=lambda x: x["dt"], reverse=True)

    # Filtrar 10-K
    ten_ks = [
        c for c in candidates
        if c["form"].upper().startswith("10-K")
           or re.search(r"10-?k", c["path"].name, re.I)
    ]
    ten_ks = sorted(ten_ks, key=lambda x: x["dt"], reverse=True)[:5]

    chosen = ten_qs_year + ten_ks

    # Si no hay nada del año actual, tomar el último 10-Q
    if not chosen:
        if ten_qs:
            chosen = [sorted(ten_qs, key=lambda x: x["dt"], reverse=True)[0]] + ten_ks
        else:
            # Últimos 5 cualquiera
            chosen = sorted(candidates, key=lambda x: x["dt"], reverse=True)[:5]

    return [c["path"] for c in chosen]


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
