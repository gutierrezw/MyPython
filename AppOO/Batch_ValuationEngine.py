"""
ValuationEngineNew.py
Versión mejorada: integra metadata.json de EDGAR.

- Usa datos locales en EDGAR/<TICKER>_EDGAR_Files/
- Si existe metadata.json, toma de allí los archivos XML/XBRL
- Detecta REITs
- Calcula valor intrínseco con DDM, DCF o FFO/AFFO
- Devuelve un diccionario listo para el BuyAgent o persistencia
"""

import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import yfinance as yf
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

# ---------------------------
# CONFIGURACIÓN
# ---------------------------
# Ignorar warning si se fuerza parseo XML
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BASE_EDGAR_DIR = r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR"
DEFAULT_DISCOUNT_RATE = 0.10
DEFAULT_TERMINAL_GROWTH = 0.03
DEFAULT_FFO_MULTIPLE = 12.0
DEFAULT_DDM_G = 0.04

XBRL_KEYS = {
    "NetIncomeLoss": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "OperatingCashFlow": ["NetCashProvidedByUsedInOperatingActivities"],
    "CapitalExpenditures": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "Depreciation": ["DepreciationDepletionAndAmortization"],
    "DividendsPaid": ["DividendsPaid", "DividendsCashPaid"],
    "SharesOutstanding": ["WeightedAverageNumberOfSharesOutstandingBasic"]
}

# ---------------------------
# UTILIDADES
# ---------------------------
def now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(",", "")
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        return float(s)
    except Exception:
        return None


def parse_ixbrl_file(file_path: str):
    """
    Lee un archivo Inline XBRL (HTML/XBRL) y devuelve un diccionario con valores clave de us-gaap.
    """
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    data = {}
    for tag in soup.find_all(["ix:nonfraction", "ix:nonnumeric"]):
        name = tag.get("name")
        if name and name.startswith("us-gaap:"):
            concept = name.split(":")[1]
            value = tag.text.strip().replace(",", "")
            if value and concept not in data:
                try:
                    data[concept] = float(value)
                except ValueError:
                    data[concept] = value

    return data


def find_latest_xbrl_file(ticker_dir: str):
    """
    Localiza el archivo XBRL más reciente usando metadata.json.
    Si lo encuentra, lo parsea con BeautifulSoup para extraer datos Inline XBRL.
    Retorna (latest_file_path, raw_data_dict)
    """
    metadata_path = Path(ticker_dir) / "metadata.json"
    if not metadata_path.exists():
        print("⚠️ No se encontró metadata.json en el directorio.")
        return None, {}

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    # Soporta tanto 'xbrl_files' como estructura por subcarpetas
    xbrl_files = []

    if "xbrl_files" in metadata:
        # Caso simple: lista directa de archivos
        xbrl_files = metadata.get("xbrl_files", [])
    else:
        # Caso extendido: buscar dentro de 10K_Filings, 10Q_Filings, etc.
        for key in ["10K_Filings", "10Q_Filings", "6K_Filings", "20F_Filings"]:
            sub = metadata.get(key, [])
            if isinstance(sub, list):
                xbrl_files.extend(sub)

    if not xbrl_files:
        print("⚠️ No se encontraron archivos XBRL válidos en metadata.json.")
        return None, {}

    # Normalizar rutas (absolutas o relativas)
    resolved_files = []
    for f in xbrl_files:
        p = Path(f)
        if not p.is_absolute():
            p = Path(ticker_dir) / p
        if p.exists() and (p.suffix.lower() in [".htm", ".html", ".xml"]):
            resolved_files.append(p)

    if not resolved_files:
        print("⚠️ Ningún archivo XBRL encontrado físicamente en disco.")
        return None, {}

    # Selecciona el más reciente por fecha de modificación
    latest_path = max(resolved_files, key=lambda x: x.stat().st_mtime)
    print(f"✅ Archivo XBRL más reciente detectado: {latest_path.name}")

    # Parsear Inline XBRL
    raw_data = {}
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "lxml")

        for tag in soup.find_all(["ix:nonfraction", "ix:nonnumeric"]):
            name = tag.get("name")
            if name and name.startswith("us-gaap:"):
                concept = name.split(":")[1]
                value = tag.text.strip().replace(",", "")
                if value and concept not in raw_data:
                    try:
                        raw_data[concept] = float(value)
                    except ValueError:
                        raw_data[concept] = value

        print(f"✅ {len(raw_data)} métricas XBRL extraídas exitosamente.")

    except Exception as e:
        print(f"⚠️ Error al parsear el archivo XBRL ({latest_path.name}): {e}")

    return latest_path, raw_data


def extract_tag_value_from_xml(xml_text: str, possible_tags: List[str]) -> Optional[float]:
    try:
        soup = BeautifulSoup(xml_text, "xml")
    except Exception:
        soup = BeautifulSoup(xml_text, "html.parser")

    for tagname in possible_tags:
        tags = soup.find_all(lambda tag: tag.name and tag.name.lower().endswith(tagname.lower()))
        for el in reversed(tags):
            txt = el.get_text(strip=True)
            val = safe_float(txt)
            if val is not None:
                return val
    return None

def extract_context_periods(soup):
    """
    Extrae los contextos (períodos de tiempo) definidos dentro del documento XBRL.
    Devuelve un diccionario donde la clave es el ID del contexto y el valor es el rango de fechas.
    """
    contexts = {}
    for ctx in soup.find_all("xbrli:context"):
        ctx_id = ctx.get("id")
        start = ctx.find("xbrli:startdate")
        end = ctx.find("xbrli:enddate")
        instant = ctx.find("xbrli:instant")

        if start and end:
            contexts[ctx_id] = {
                "type": "duration",
                "start": start.text.strip(),
                "end": end.text.strip()
            }
        elif instant:
            contexts[ctx_id] = {
                "type": "instant",
                "date": instant.text.strip()
            }

    return contexts

# ---------------------------
# CLASE PRINCIPAL
# ---------------------------
class ValuationEngine:
    def __init__(self, ticker: str, edgar_dir: str = BASE_EDGAR_DIR):
        self.ticker = ticker.upper()
        self.edgar_dir = edgar_dir
        self.ticker_path = os.path.join(edgar_dir, f"{self.ticker}_EDGAR_Files")
        self.price = None
        self.shares = None
        self.metadata = {}

    def locate_files(self):
        """
        Localiza archivos relevantes del ticker usando metadata.json si existe.
        Si no hay metadata.json, intenta detectar manualmente subdirectorios EDGAR.
        Retorna un diccionario con los paths detectados.
        """
        ticker = self.ticker.upper()
        ticker_dir = self.ticker_path
     
        if not ticker_dir.exists():
            print(f"⚠️ No existe el directorio para {ticker}. Ejecuta primero edgar_downloader.py.")
            return {"xbrl": None, "index_files": []}

        metadata_path = ticker_dir / "metadata.json"

        if metadata_path.exists():
            xbrl_file, raw_data = find_latest_xbrl_file(ticker_dir)
            print(f"🔍 Wilmer {ticker_dir}")
            print(f"🔍 Wilmer {ticker}: 'xbrl': '{xbrl_file}', 'raw_data': {raw_data}")

        else:
            print("⚠️ No se encontró metadata.json, intentando detección manual...")

            # Detección manual en subcarpetas conocidas
            possible_dirs = [
                ticker_dir / "10Q_Filings",
                ticker_dir / "10K_Filings",
                ticker_dir / "6K_Filings",
                ticker_dir / "20F_Filings",
            ]

            candidates = []
            for d in possible_dirs:
                if d.exists():
                    candidates.extend(list(d.glob("*.htm")) + list(d.glob("*.xml")))

            if candidates:
                latest_file = max(candidates, key=lambda x: x.stat().st_mtime)
                print(f"✅ Archivo más reciente (sin metadata): {latest_file.name}")
                xbrl_file = latest_file
                raw_data = {}
            else:
                print(f"⚠️ No se encontraron archivos válidos en {ticker_dir}")
                return {"xbrl": None, "index_files": []}

        print(f"🔍 Archivos localizados para {ticker}: {{'xbrl': '{xbrl_file}', 'index_files': []}}")

        # Retornar tanto el path como los datos XBRL extraídos
        self.raw_data = raw_data
        return {"xbrl": str(xbrl_file) if xbrl_file else None, "index_files": []}

    def parse_inline_xbrl(self, xbrl_path):
        """
        Parsea el archivo Inline XBRL (.htm o .xml) y extrae información estructurada.
        Además obtiene los contextos para análisis temporal.
        """
        try:
            with open(xbrl_path, "r", encoding="utf-8") as f:
                xml_text = f.read()

            # Usamos BeautifulSoup con lxml (parser XML robusto)
            soup = BeautifulSoup(xml_text, "lxml")

            # 🔍 Extraer contextos del XBRL
            self.contexts = extract_context_periods(soup)

            # 📊 Extraer datos básicos (valores numéricos y no numéricos)
            elements = {}
            for tag in soup.find_all(["ix:nonfraction", "ix:nonnumeric"]):
                name = tag.get("name")
                if not name:
                    continue
                context = tag.get("contextref")
                value = tag.text.strip()

                elements[name] = {
                    "value": value,
                    "context": context
                }

            return elements

        except Exception as e:
            print(f"❌ Error al parsear XBRL: {e}")
            return {}
  
    def fetch_yf_data(self):
        try:
            t = yf.Ticker(self.ticker)
            info = t.info
            self.price = safe_float(info.get("currentPrice") or info.get("regularMarketPrice"))
            self.shares = safe_float(info.get("sharesOutstanding"))
            self.metadata["summary"] = (info.get("longBusinessSummary") or "").lower()
            self.metadata["sector"] = (info.get("sector") or "").lower()
        except Exception:
            pass

    def detect_reit(self) -> bool:
        s = self.metadata.get("summary", "")
        sec = self.metadata.get("sector", "")
        return any(k in s for k in ("reit", "real estate")) or "reit" in sec or "real estate" in sec

    def estimate_ffo_affo(self, d: Dict[str, Any]) -> Dict[str, float]:
        ni = safe_float(d.get("NetIncomeLoss"))
        dep = safe_float(d.get("Depreciation")) or 0
        capex = abs(safe_float(d.get("CapitalExpenditures")) or 0)
        ffo = ni + dep if ni is not None else None
        affo = ffo - 0.4 * capex if ffo is not None else None
        ffo_ps = ffo / self.shares if ffo and self.shares else None
        affo_ps = affo / self.shares if affo and self.shares else None
        return {"ffo": ffo, "affo": affo, "ffo_per_share": ffo_ps, "affo_per_share": affo_ps}

    def calc_ddm(self, div_ps, g, r):
        try:
            if div_ps and r > g:
                return div_ps * (1 + g) / (r - g)
        except Exception:
            pass
        return None

    def calc_dcf(self, fcf, g, r, term_g):
        try:
            if fcf and r > term_g:
                val = 0
                for t in range(1, 6):
                    cf = fcf * (1 + g) ** t
                    val += cf / (1 + r) ** t
                tv = fcf * (1 + g) ** 5 * (1 + term_g) / (r - term_g)
                val += tv / (1 + r) ** 5
                return val / self.shares if self.shares else val
        except Exception:
            pass
        return None

    def run(self):
        """
        Flujo principal del ValuationEngine:
        1. Localiza archivos EDGAR (usando metadata.json si existe)
        2. Carga datos XBRL si es posible
        3. Determina si es REIT
        4. Calcula valor intrínseco según el modelo
        5. Devuelve resultados en formato diccionario
        """
        self.ticker_path = Path(self.edgar_dir) / f"{ticker}_EDGAR_Files"

        print(f"🔎 Buscando archivos para {ticker} ...")
        files = self.locate_files()

        xbrl_file = files.get("xbrl")
        if not xbrl_file:
            print("❌ No se encontró archivo XBRL o HTML válido.")
            return None

        print(f"📂 Archivo XBRL seleccionado: {xbrl_file}")

        # Si el archivo existe, procesar inline XBRL o HTML fallback
        extracted_data = {}
        try:
            raw = getattr(self, "raw_data", {}) or {}
            if not raw:
                raw_data = self.parse_inline_xbrl(xbrl_file)
            else:
                raw_data = raw
            extracted_data.update(raw_data)
        except Exception as e:
            print(f"⚠️ Error al analizar XBRL: {e}")

        # Detectar si es REIT
        is_reit = self.detect_reit()

        # Obtener precio de mercado
        self.fetch_yf_data()
        current_price = self.price
        shares_out = self.shares or extracted_data.get("shares_outstanding")

        # Calcular valor intrínseco
        valuation = self.calculate_valuation(extracted_data, is_reit)

        result = {
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": current_price,
            "shares": shares_out,
            "source_files": files,
            "raw": extracted_data,
            "is_reit": is_reit,
            "models": valuation,
        }

        print("\n=== Resultado resumido ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return result


# ---------------------------
# EJECUCIÓN INTERACTIVA
# ---------------------------
if __name__ == "__main__":
    ticker = input("💼 Ingrese el ticker (ej: CCI, HASI, AAPL): ").strip().upper()
    engine = ValuationEngine(ticker)
    out = engine.run()
    print("\n=== Resultado resumido ===")
    print(json.dumps(out, indent=2))
