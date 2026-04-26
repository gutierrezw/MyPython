"""
ValuationEngine.py
----------------------------------------
Motor principal de valoración de acciones.
Integra:
  - Módulo local get_data_growth_gurufocus.py
  - Datos desde SEC (EDGAR)
  - FinancialModelingPrep (API)
Autor: InversionesWildaga / Wilmer Gutierrez
"""

from Modulos_python import requests, datetime, yf, b64encode 
from get_data_growth_gurufocus import StockValuation
from get_financials_sec import SecFinancials
from Modulos_Mysql import BDsystem


class ValuationEngine:
    def __init__(self):
        self.SesionFMP = BDsystem.select_sesion(datetime.now(), accion="select", vehiculo="FMP")
        self.FMP_KEY = self.SesionFMP.get("private_key")
        if isinstance(self.FMP_KEY, bytes):
            self.FMP_KEY = self.FMP_KEY.decode("utf-8")

    # ---------------------------------------------------------
    def get_fmp_data(self, ticker: str):
        """Consulta FinancialModelingPrep para obtener estados financieros básicos."""
        try:
            url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?limit=1&apikey={self.FMP_KEY}"
            data = requests.get(url).json()[0]
            return {
                "source": "FMP",
                "NetIncome": data.get("netIncome"),
                "Depreciation": data.get("depreciationAndAmortization"),
                "OperatingCashFlow": data.get("netCashProvidedByOperatingActivities"),
                "CapitalExpenditures": data.get("capitalExpenditure"),
            }
        except Exception as e:
            print(f"❌ Error al obtener datos FMP: {e}")
            return None

    # ---------------------------------------------------------
    def get_financials(self, ticker: str):
        """Intenta obtener datos desde la SEC; si falla, usa FMP."""
        try:
            sec_data = SecFinancials(ticker).get_financials()
            if isinstance(sec_data, dict) and "source" in sec_data:
                return sec_data
        except Exception:
            pass
        return self.get_fmp_data(ticker)

    # ---------------------------------------------------------
    def run(self, ticker: str):
        """Ejecuta todo el flujo de valoración."""
        print("=" * 60)
        print(f"📊 Valorando {ticker} ...")

        # 1️⃣ Obtener info básica desde yfinance
        stock = StockValuation(ticker)
        price = stock.info.get("currentPrice", None)

        # 2️⃣ Obtener estados financieros externos (SEC/FMP)
        data = self.get_financials(ticker)
        if not data:
            print("❌ No se pudieron obtener datos financieros externos.")
            return

        # 3️⃣ Ejecutar valoración DDM
        ddm_results = stock.ddm_value(g=0.04, r=0.10)
        for r in ddm_results:
            print(r)

        # 4️⃣ Detectar REIT y aplicar modelo correspondiente
        if stock.is_reit():
            print(f"\n🏢 {ticker} es un REIT según los criterios analizados.")
            ffo_data = stock.estimate_ffo()
            print(ffo_data)
            if ffo_data.get("ffo_per_share"):
                ffo_per_share = ffo_data["ffo_per_share"]
                print(stock.valuation_pffo(ffo_per_share))
                print(stock.valuation_ffo_gordon(ffo_per_share))
        else:
            print(f"\n💼 {ticker} no es REIT. Se recomienda usar DCF o DDM.")

        # 5️⃣ Mostrar datos externos resumidos
        print("\n📂 Datos financieros externos:")
        print(data)


# ---------------------------------------------------------
if __name__ == "__main__":
    ticker = input("Ticker (ej: CCI, HASI, CVS): ").strip().upper()
    engine = ValuationEngine()
    engine.run(ticker)
