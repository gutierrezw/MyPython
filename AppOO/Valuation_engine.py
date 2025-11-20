# Valuation_engine.py
"""
Valuation Engine — Orquestador principal

Uso:
    from valuation.engine import ValuationEngine
    eng = ValuationEngine("AAPL", verbose=True)
    result = eng.run()

O desde CLI:
    python -m valuation.engine AAPL
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from Valuation_filings import get_filing_list, detect_reit_status_from_text
from Valuation_xbrl_parser import aggregate_xbrl_metrics, detect_reit_enhanced
from Valuation_calculators import calc_valuations
from Valuation_utils import get_yf_price, make_json_safe, save_result_to_file, print_valuation, print_valuation_from_file

# Default base dir (ajusta si usas otro path)
DEFAULT_BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")


class ValuationEngine:
    def __init__(self, ticker: str, base_dir: Optional[Path] = None, verbose: bool = False):
        self.ticker = ticker.upper()
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_BASE_DIR
        self.ticker_dir = Path(self.base_dir) / f"{self.ticker}_EDGAR_Files"
        self.verbose = verbose

    def _log(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def run(self) -> Optional[Dict[str, Any]]:
        """
        Ejecuta el flujo completo de valoración y devuelve un dict con el resultado.
        Guarda un JSON en valuation_outputs/<TICKER>_valuation.json
        """
        self._log(f"🔎 ValuationEngine.run -> ticker={self.ticker}")
        if not self.ticker_dir.exists():
            print(f"📂 No existe carpeta para {self.ticker} en {self.ticker_dir}. Ejecuta el downloader primero.")
            return None

        # 1) Seleccionar filings relevantes
        files = get_filing_list(self.ticker_dir)
        if not files:
            print("❌ No se encontraron filings relevantes.")
            return None

        self._log("📄 Archivos seleccionados (ordenados más reciente primero):")
        for f in files:
            self._log("  -", f)

        # 2) Parse XBRL y agregar TTM
        parsed_agg = aggregate_xbrl_metrics(files)
        print(f"keys parsed_agg: {list(parsed_agg.keys())}")
        
        self._log("🧾 Agregado XBRL (resumen):")
        if self.verbose:
            # imprimir keys importantes
            self._log("  files_used:", parsed_agg.get("files_used"))
            self._log("  ttm keys:", list(parsed_agg.get("ttm", {}).keys()))
            self._log("  shares:", parsed_agg.get("shares"))

        # 3) Detectar REIT (mejorado) y fallback textual
        is_reit = detect_reit_enhanced(parsed_agg, self.ticker)
        if not is_reit and files:
            try:
                if detect_reit_status_from_text(files[0]):
                    is_reit = True
            except Exception:
                pass
        self._log("🏢 is_reit:", is_reit)

        # 4) Obtener precio (Yahoo)
        price = get_yf_price(self.ticker)
        self._log("💵 Precio (Yahoo):", price)

        # 5) Preparar métricas para calculators.calc_valuations
        t = parsed_agg.get("ttm", {}) or {}
        metrics_for_calc = {
            "NetIncome": t.get("NetIncome_TTM"),
            "OperatingCashFlow": t.get("OperatingCashFlow_TTM"),
            "CapitalExpenditures": t.get("CapitalExpenditures_TTM"),
            "SharesOutstanding": parsed_agg.get("shares"),
            "FFO": t.get("FFO_TTM"),
            "AFFO": t.get("AFFO_TTM"),
            "DividendsPaid": t.get("DividendsPaid_TTM"),
            # Revenues no se agrega por ahora al TTM (puede derivarse de parsed_agg.per_file si necesario)
            "Revenues": None
        }

        self._log("🧮 Métricas TTM (para cálculos):", metrics_for_calc)

        # 6) Calcular múltiples y valores intrínsecos
        valuations = calc_valuations(metrics_for_calc, price, is_reit)
        self._log("📊 Valuations (resumen):")
        if self.verbose:
            for k, v in valuations.items():
                self._log(f"  {k}: {v}")

        # 7) Armar resultado final
        # Convertir rutas dentro de parsed_agg a strings si no lo están
        try:
            if "files_used" in parsed_agg:
                parsed_agg["files_used"] = [str(x) for x in parsed_agg.get("files_used", [])]
            if "per_file" in parsed_agg:
                for entry in parsed_agg.get("per_file", []):
                    if isinstance(entry.get("path"), Path):
                        entry["path"] = str(entry["path"])
        except Exception:
            pass

        result = {
            "ticker": self.ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": price,
            "is_reit": bool(is_reit),
            "source_file": str(files[0]) if files else None,
            "valuations": valuations,
            # incluir parsed_agg solo si verbose True (evita resultados enormes por defecto)
            **({"parsed_agg": parsed_agg} if self.verbose else {}),
        }

        # 8) Guardar resultado en JSON y retornar
        safe_result = make_json_safe(result)
        save_result_to_file(self.ticker, safe_result)

        self._log("✅ Valuation completada.")
        return result


# CLI support: python -m valuation.engine AAPL
def _cli_main(argv):
    if len(argv) < 2:
        print("Uso: python -m valuation.engine <TICKER> [base_dir] [--verbose]")
        return
    ticker = argv[1].strip().upper()
    base_dir = None
    verbose = False
    if len(argv) >= 3 and not argv[2].startswith("--"):
        base_dir = Path(argv[2])
    if "--verbose" in argv or "-v" in argv:
        verbose = True

    eng = ValuationEngine(ticker, base_dir=base_dir, verbose=verbose)
    res = eng.run()
    if res is not None:
        print("Resultado guardado para", ticker)


if __name__ == "__main__":
    # _cli_main(sys.argv)
    BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")
    VERBOSE = False
    ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
   
    eng = ValuationEngine(ticker, base_dir=BASE_DIR, verbose=VERBOSE)
    result = eng.run()
    print_valuation_from_file(f"valuation_outputs/{ticker}_valuation.json")
    if result is not None:
        print("Resultado guardado para", ticker)
