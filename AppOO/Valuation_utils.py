# utils.py
"""
Funciones utilitarias:
- safe_parse_number(): limpia y convierte textos numéricos
- make_json_safe(): convierte objetos en estructuras serializables
- get_yf_price(): obtiene precio desde Yahoo Finance API
"""

import os
import re
import json
import time
import requests
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional

# ============================================================
# 🔢 Normaliza texto
# ============================================================
def _normalize_number_text(s: str):
    """Extrae número de un texto (ej: '1,234', '(1,234)', '$1,234') -> float."""
    if not s:
        return None
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    m = re.search(r"[-+]?\d{1,3}(?:[,\d]{0,})(?:\.\d+)?", s.replace("(", "-").replace(")", ""))
    if not m:
        # try float in scientific
        m2 = re.search(r"[-+]?\d+\.\d+e[-+]?\d+", s, re.I)
        if m2:
            try:
                return float(m2.group(0))
            except:
                return None
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except:
        return None

# ============================================================
# 🔢 Busca texto numerico
# ============================================================
def _find_number_in_adjacent_cells(tr, keywords):
    """Busca en las celdas del mismo <tr> un texto numérico cercano a keywords."""
    tds = tr.find_all(["td", "th"])
    # flatten texts
    texts = [ (i, td.get_text(" ", strip=True)) for i, td in enumerate(tds) ]
    for i, txt in texts:
        low = txt.lower()
        for kw in keywords:
            if kw in low:
                # prefer right-most numeric cell after keyword
                # scan right
                for j in range(i+1, len(tds)):
                    val = _normalize_number_text(tds[j].get_text(" ", strip=True))
                    if val is not None:
                        return val
                # else scan left
                for j in range(i-1, -1, -1):
                    val = _normalize_number_text(tds[j].get_text(" ", strip=True))
                    if val is not None:
                        return val
    return None
# ============================================================
# 🔢 guarda json resultado en directorio
# ============================================================
def save_result_to_file(ticker, result, output_dir="valuation_outputs"):
    """
    Guarda el resultado (previamente convertido a JSON-safe) en un archivo .json.
    Crea el directorio si no existe.
    """
    os.makedirs(output_dir, exist_ok=True)

    filename = Path(output_dir) / f"{ticker}_valuation.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"💾 Resultado guardado en: {filename}")

# ============================================================
# 🔢 Limpieza numérica segura
# ============================================================
def safe_parse_number(txt):
    """
    Intenta convertir texto a número.
    Maneja: $, comas, espacios, negativos con paréntesis, etc.
    """
    if txt is None:
        return None

    s = str(txt).strip()
    if s in ("", "-", "—"):
        return None

    s = (
        s.replace("$", "")
        .replace(",", "")
        .replace("\u00A0", "")
        .strip()
    )

    # (123) → -123
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1].strip()

    try:
        if "." in s:
            v = float(s)
        else:
            v = int(s)
        return -v if neg else v
    except Exception:
        try:
            return float(s)
        except Exception:
            return None


# ============================================================
# 🔄 Conversión JSON-safe
# ============================================================
def make_json_safe(obj):
    """
    Convierte recursivamente:
    - datetime/date → ISO string
    - Path → string
    - dict/list/tuple → estructuras seguras
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [make_json_safe(x) for x in obj]

    return obj


# ============================================================
# 💵 Precio Yahoo Finance (simple)
# ============================================================
def get_yf_price(ticker: str):
    """
    Obtiene precio desde Yahoo.
    Incluye:
    - User-Agent para evitar 429
    - Retries progresivos
    - 2 endpoints de fallback
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    # --- Endpoints en orden de preferencia ---
    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    ]

    for attempt in range(3):
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                
                # Evitar 429
                if r.status_code == 429:
                    time.sleep(1 + attempt)
                    continue

                r.raise_for_status()
                data = r.json()

                # Intento 1 → chart endpoint
                try:
                    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                except Exception:
                    pass

                # Intento 2 → quoteSummary endpoint
                try:
                    return data["quoteSummary"]["result"][0]["price"]["regularMarketPrice"]["raw"]
                except Exception:
                    pass

            except Exception:
                time.sleep(0.5 + attempt)

    return None


# Valuation_printer.py
"""
Valuation Printer
-----------------
Módulo para imprimir por pantalla el resultado generado por Valuation_engine.

Uso típico:
-----------
from Valuation_printer import print_valuation
result = json.load(open("valuation_outputs/AAPL_valuation.json"))
print_valuation(result)

O desde engine:
print_valuation(engine.run())
"""

# -----------------------------------------------------------
# Función principal
# -----------------------------------------------------------
def print_valuation(data: Dict[str, Any]):
    """Imprime un informe de valoración formateado."""

    ticker = data.get("ticker")
    price = data.get("price")
    timestamp = data.get("timestamp")
    is_reit = data.get("is_reit", False)
    valuations = data.get("valuations", {})

    print("\n" + "=" * 70)
    print(f" VALUATION REPORT — {ticker}")
    print("=" * 70)

    print(f"📅 Fecha     : {timestamp}")
    print(f"💵 Precio    : {price}")
    print(f"🏢 Es REIT   : {'Sí' if is_reit else 'No'}")
    print("-" * 70)

    # --------------------------
    # MÉTRICAS GENERALES
    # --------------------------
    print("📊 MÉTRICAS GENERALES:")
    print("-" * 70)

    _print_metric("EPS", valuations.get("EPS"))
    _print_metric("P/E", valuations.get("P/E"))
    _print_metric("P/FCF", valuations.get("P/FCF"))
    _print_metric("P/S", valuations.get("P/S"))
    _print_metric("FCF (TTM)", valuations.get("FCF"))
    _print_metric("Dividend/share", valuations.get("Dividend_per_share"))
    _print_metric("DDM value", valuations.get("DDM_value"))
    _print_metric("DCF value/share", valuations.get("DCF_value_per_share"))

    # --------------------------
    # MÉTRICAS REIT (solo si aplica)
    # --------------------------
    if is_reit:
        print("\n🏢 MÉTRICAS REIT:")
        print("-" * 70)
        _print_metric("FFO/share", valuations.get("FFO_per_share"))
        _print_metric("AFFO/share", valuations.get("AFFO_per_share"))
        _print_metric("P/FFO", valuations.get("P/FFO"))
        _print_metric("P/AFFO", valuations.get("P/AFFO"))

    # --------------------------
    # SHARES Y BASES
    # --------------------------
    print("\n📌 BASES DE CÁLCULO:")
    print("-" * 70)
    _print_metric("Shares Outstanding", valuations.get("SharesOutstanding"))
    _print_metric("Net Income (TTM)", valuations.get("NetIncome"))
    _print_metric("OCF (TTM)", valuations.get("OperatingCashFlow"))
    _print_metric("CapEx (TTM)", valuations.get("CapitalExpenditures"))

    if is_reit:
        _print_metric("FFO (TTM)", valuations.get("FFO"))
        _print_metric("AFFO (TTM)", valuations.get("AFFO"))

    print("=" * 70)
    print(" FIN DEL INFORME ")
    print("=" * 70 + "\n")


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def _print_metric(label: str, value: Optional[Any]):
    """Formato uniforme para métricas."""
    if value is None:
        value = "—"
    print(f"{label:<20}: {value}")


# -----------------------------------------------------------
# Utilidad opcional: leer desde archivo
# -----------------------------------------------------------
def print_valuation_from_file(path: Path):
    """Carga JSON desde archivo y lo imprime."""
    if not Path(path).exists():
        print(f"❌ Archivo no encontrado: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print_valuation(data)
