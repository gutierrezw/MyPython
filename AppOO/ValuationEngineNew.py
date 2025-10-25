"""
ValuationEngine.py
------------------------------------------------------------
Módulo de valoración integral para acciones y REITs
Basado en: FinancialModelingPrep (FMP) + yFinance
Autor: InversionesWildaga / Wilmer G.
Versión: Producción (Actualizada con FMP gratuito + FFO/AFFO)
------------------------------------------------------------
"""
from Modulos_python import requests, datetime, yf
from Modulos_Mysql import BDsystem


# ============================================================
# 1️⃣ Clase: FMPClient
# ============================================================
class FMPClient:
    """Cliente para obtener datos financieros desde FinancialModelingPrep."""

    BASE_URL = "https://financialmodelingprep.com/api/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, endpoint: str):
        """Manejo de solicitudes genéricas."""
        url = f"{self.BASE_URL}/{endpoint}?limit=1&apikey={self.api_key}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data[0] if isinstance(data, list) and data else data
        except Exception as e:
            print(f"❌ Error al conectar con FMP ({endpoint}): {e}")
            return None

    def get_fundamentals(self, ticker: str):
        """Obtiene métricas clave desde los endpoints gratuitos."""
        # key_metrics = self._get(f"key-metrics-ttm/{ticker.upper()}")
        # ratios = self._get(f"ratios/{ticker.upper()}")
        key_metrics = self._get(f"key-metrics/{ticker.upper()}")
        ratios = self._get(f"financial-growth/{ticker.upper()}")
        profile = self._get(f"profile/{ticker.upper()}")
        quote = self._get(f"quote/{ticker.upper()}")

        if not key_metrics and not ratios:
            print("⚠️ No se pudieron obtener datos válidos desde FMP.")
            return {}

        fundamentals = {
            "symbol": ticker,
            "companyName": profile.get("companyName") if profile else None,
            "sector": profile.get("sector") if profile else None,
            "industry": profile.get("industry") if profile else None,
            "description": profile.get("description") if profile else None,
            "price": quote.get("price") if quote else None,
            "eps": key_metrics.get("eps") if key_metrics else None,
            "dividendPerShare": key_metrics.get("dividendPerShare") if key_metrics else None,
            "freeCashFlowPerShare": key_metrics.get("freeCashFlowPerShare") if key_metrics else None,
            "payoutRatio": ratios.get("payoutRatio") if ratios else None,
            "roe": ratios.get("returnOnEquity") if ratios else None,
            "debtToEquity": ratios.get("debtToEquity") if ratios else None,
            "date": key_metrics.get("date") if key_metrics else None,
        }

        return fundamentals


# ============================================================
# 2️⃣ Clase: ValuationModels
# ============================================================
class ValuationModels:
    """Modelos de valoración: DDM, DCF, FFO."""

    @staticmethod
    def ddm(dividend: float, r: float, g: float):
        if not dividend or dividend <= 0 or r <= g:
            return None
        return dividend * (1 + g) / (r - g)

    @staticmethod
    def dcf(fcf_per_share: float, r: float, g: float):
        if not fcf_per_share or fcf_per_share <= 0:
            return None
        return fcf_per_share * (1 + g) / (r - g)

    @staticmethod
    def ffo_model(ffo_per_share: float, multiple: float = 12):
        if ffo_per_share is None or ffo_per_share <= 0:
            return None
        return ffo_per_share * multiple


# ============================================================
# 3️⃣ Clase: ValuationEngine
# ============================================================
class ValuationEngine:
    """Motor principal que orquesta todo el proceso de valoración."""

    def __init__(self):
        SesionFMP = BDsystem.select_sesion(datetime.now(), accion="select", vehiculo="FMP")
        api_key = SesionFMP.get("private_key")
        if isinstance(api_key, bytes):
            api_key = api_key.decode("utf-8")
        self.fmp = FMPClient(api_key)
        self.models = ValuationModels()

    def is_reit(self, description: str, sector: str) -> bool:
        text = f"{description or ''} {sector or ''}".lower()
        return any(k in text for k in ["reit", "real estate", "property trust"])

    def estimate_ffo_from_fmp(self, fundamentals: dict):
        """Estimación básica de FFO y AFFO."""
        eps = fundamentals.get("eps") or 0
        depreciation = fundamentals.get("depreciationAndAmortizationPerShare") or 0.3 * eps
        ffo = eps + depreciation
        affo = ffo * 0.9  # 10% mantenimiento estimado
        fundamentals.update({
            "ffo_per_share": ffo,
            "affo_per_share": affo,
        })
        return fundamentals

    def value(self, ticker: str):
        print("=" * 60)
        print(f"📊 Valorando {ticker} ...")

        data = self.fmp.get_fundamentals(ticker)
        if not data:
            print("❌ No se pudieron obtener datos de FMP.")
            return

        try:
            yf_price = yf.Ticker(ticker).info.get("currentPrice")
            if yf_price:
                data["price"] = yf_price
        except Exception:
            pass

        is_reit = self.is_reit(data.get("description"), data.get("sector"))
        price = data.get("price") or 1

        print(f"🏢 Empresa detectada como {'REIT' if is_reit else 'Corporación regular'}.")
        print(f"💲 Precio actual: {price}")

        results = {}

        if is_reit:
            data = self.estimate_ffo_from_fmp(data)
            ffo_val = self.models.ffo_model(data["ffo_per_share"])
            if ffo_val:
                margin = (ffo_val / price - 1) * 100
                results = {
                    "model": "REIT / FFO",
                    "ffo_per_share": data["ffo_per_share"],
                    "affo_per_share": data["affo_per_share"],
                    "fair_value": ffo_val,
                    "margin_of_safety": margin,
                }
        else:
            dcf_val = self.models.dcf(data.get("freeCashFlowPerShare"), r=0.10, g=0.03)
            ddm_val = self.models.ddm(data.get("dividendPerShare"), r=0.10, g=0.04)
            results["DCF"] = dcf_val
            results["DDM"] = ddm_val

        print("\n=== Resultados ===")
        for k, v in results.items():
            print(f"{k:20}: {v}")
        print(f"\n📂 Fuente: FinancialModelingPrep | Fecha: {data.get('date')}")
        return results


# ============================================================
# Ejecución directa
# ============================================================
if __name__ == "__main__":
    ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
    engine = ValuationEngine()
    engine.value(ticker)
