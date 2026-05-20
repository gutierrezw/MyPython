import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import logging
from Modulos_Utilitarios import read_json_tmp

_logger = logging.getLogger("TechScanner")
_TECH_TEMAS_FILE = "tech_temas.json"

THEME_MAP = {
    "ai_semiconductors": ["NVDA", "AMD", "INTC", "ASML", "QCOM", "MU"],
    "clean_energy": ["VST", "PLUG", "NEE", "ENPH", "FSLR", "CEG"],
    "biotech": ["PFE", "ABBV", "BMY", "AMGN", "GILD", "MRNA"],
    "blockchain": ["CGPT", "MSTR", "COIN"],
    "cloud_saas": ["MSFT", "AMZN", "GOOGL", "CRM", "NOW", "SNOW"],
    "robotics": ["ISRG", "ABB", "ROK", "TER"],
}


def load_temas_activos() -> list:
    return read_json_tmp(_TECH_TEMAS_FILE).get("temas", [])


def voto_tech_alignment(symbol: str, temas_activos: list) -> int:
    for tema, tickers in THEME_MAP.items():
        if symbol in tickers and tema in temas_activos:
            return 1
    return 0
