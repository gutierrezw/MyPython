"""
get_financials_sec.py
----------------------------------------
Descarga datos financieros de la SEC (EDGAR)
con manejo de errores y fallback automático.
Autor: InversionesWildaga / Wilmer
"""

from Modulos_python import requests, datetime
from Modulos_Mysql  import BDsystem

class SecFinancials:
    BASE_XBRL = "https://data.sec.gov/api/xbrl/company_facts/CIK{}.json"
    BASE_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{}.json"
    HEADERS = {"User-Agent": "InversionesWildaga (wilmer@correo.com)"}

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.cik = self.get_cik_from_ticker()
        
        self.SesionFMP = BDsystem.select_sesion(
            datetime.now(), accion="select", vehiculo="FMP"
        )
        # self.SesionFMP["private_key"]


    # ---------------------------------------------------------
    def get_cik_from_ticker(self) -> str:
        """Obtiene el CIK a partir del ticker"""
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=self.HEADERS)
        resp.raise_for_status()
        data = resp.json()

        for v in data.values():
            if v["ticker"].upper() == self.ticker:
                return str(v["cik_str"])
        raise ValueError(f"No se encontró CIK para el ticker {self.ticker}")

    # ---------------------------------------------------------
    def fetch_financial_facts(self) -> dict:
        """Descarga los datos XBRL si existen, si no intenta fallback a submissions"""
        urls = [
            self.BASE_XBRL.format(self.cik),
            self.BASE_XBRL.format(self.cik.zfill(10)),
        ]

        for url in urls:
            r = requests.get(url, headers=self.HEADERS)
            if r.status_code == 200:
                data = r.json().get("facts", {}).get("us-gaap", {})
                if data:
                    print(f"✅ Datos XBRL encontrados: {url}")
                    return data

        print("⚠️ No hay datos XBRL disponibles. Intentando obtener desde /submissions/")
        return self.fetch_from_submissions()

    # ---------------------------------------------------------
    def fetch_from_submissions(self) -> dict:
        """Si no hay XBRL, usa el endpoint /submissions para obtener los filings"""
        urls = [
            self.BASE_SUBMISSIONS.format(self.cik),
            self.BASE_SUBMISSIONS.format(self.cik.zfill(10)),
        ]
        for url in urls:
            r = requests.get(url, headers=self.HEADERS)
            if r.status_code == 200:
                data = r.json()
                filings = data.get("filings", {}).get("recent", {})
                if not filings:
                    continue
                forms = filings.get("form", [])
                docs = filings.get("primaryDocument", [])
                accs = filings.get("accessionNumber", [])

                for i, f in enumerate(forms):
                    if f in ["10-K", "10-Q"]:
                        acc = accs[i].replace("-", "")
                        doc = docs[i]
                        filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{acc}/{doc}"
                        print(f"✅ Último {f} encontrado: {filing_url}")
                        return {"source": "submission", "url": filing_url}
        print("❌ No se pudo obtener ningún filing válido.")
        return {}

    # ---------------------------------------------------------
    def extract_value(self, facts: dict, key: str) -> float:
        """Extrae el valor más reciente disponible para una clave XBRL"""
        try:
            data = facts[key]["units"]["USD"]
            latest = sorted(data, key=lambda x: x["end"], reverse=True)[0]
            return float(latest["val"])
        except Exception:
            return None

    # ---------------------------------------------------------
    def get_financials(self) -> dict:
        """Obtiene los datos financieros principales"""
        facts = self.fetch_financial_facts()

        # Si sólo tenemos la URL (submissions), devolver eso
        if isinstance(facts, dict) and "source" in facts:
            return facts

        items = {
            "NetIncome": ["NetIncomeLoss", "ProfitLoss"],
            "Depreciation": [
                "DepreciationAndAmortization",
                "DepreciationDepletionAndAmortization",
            ],
            "OperatingCashFlow": ["NetCashProvidedByUsedInOperatingActivities"],
            "CapitalExpenditures": [
                "PaymentsToAcquirePropertyPlantAndEquipment",
                "CapitalExpendituresIncurredButNotYetPaid",
            ],
        }

        results = {}
        for name, keys in items.items():
            for key in keys:
                val = self.extract_value(facts, key)
                if val is not None:
                    results[name] = val
                    break
            if name not in results:
                results[name] = None

        return results

    # ---------------------------------------------------------
    def summary(self):
        data = self.get_financials()
        print(f"\n=== SEC Financials for {self.ticker} ===")
        for k, v in data.items():
            print(f"{k:20}: {v}")
        return data


# ---------------------------------------------------------
if __name__ == "__main__":
    ticker = input("Ticker (ej: CCI o HASI): ").strip()
    sec = SecFinancials(ticker)
    fin = sec.summary()

    if fin.get("NetIncome") and fin.get("Depreciation"):
        ffo = fin["NetIncome"] + fin["Depreciation"]
        print(f"\nFFO estimado (NetIncome + Depreciation): {ffo:,.0f} USD")
