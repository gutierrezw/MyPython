"""
AppTest/run_youtube_scanner.py
Prueba manual del Scanner_YouTube sin abrir la app.
Uso: python AppTest/run_youtube_scanner.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_PROFILE = os.path.join(_BASE, "profiles", "main.json")
if os.path.exists(_PROFILE):
    with open(_PROFILE, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    from Modulos_Mysql import BDsystem

    if _cfg.get("db"):
        BDsystem.configure(_cfg["db"])
    if _cfg.get("tmp_path"):
        os.environ["APPOO_TMP"] = _cfg["tmp_path"]

import logging

logging.basicConfig(level=logging.WARNING, format="%(name)s — %(message)s")

from Modulos_Mysql import BDsystem
from ConvergIA.Scanner_YouTube import scan_youtube
from Modulos_Utilitarios import read_json_tmp

ACCOUNT = "U4214563"

sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIS")
api_key = sesion["userapi"].decode("utf-8") if sesion else os.environ.get("ANTHROPIC_API_KEY", "")

print(f"\n=== YouTube Scanner — cuenta {ACCOUNT} ===\n")
result = scan_youtube(ACCOUNT, api_key)

print(f"\nResumen:")
print(f"  Videos nuevos: {result['videos']}")
print(f"  Ya vistos:     {result['videos_skip']}  ← no se mandan a Claude")
print(f"  Financieros:   {result['filtered']}")
print(f"  Detectados:    {result['detected']}")
print(f"  Nuevos válidos:{result['new_validated']}")

detected_raw = result.get("detected_raw", {})
if detected_raw:
    print(f"\nDetectados por Claude (antes de validar):")
    for ticker, conf in sorted(detected_raw.items(), key=lambda x: -x[1]):
        print(f"  {ticker:6s}  conf={conf:.2f}")
else:
    print("\n  (ningún ticker detectado por Claude)")

validated = result.get("validated", {})
if validated:
    print(f"\nNuevos validados (yfinance ok, no están en market):")
    for ticker, data in sorted(validated.items(), key=lambda x: -x[1].get("confidence", 0)):
        mc = data.get("market_cap", 0)
        mc_str = f"${mc/1e9:.1f}B" if mc >= 1e9 else f"${mc/1e6:.0f}M"
        print(f"  {ticker:6s}  conf={data['confidence']:.2f}  mktcap={mc_str}")

staging = read_json_tmp("youtube_candidates").get("candidates", {})
if staging:
    print(f"\nStaging acumulado (youtube_candidates.json) — {len(staging)} tickers:")
    for ticker, data in sorted(staging.items(), key=lambda x: -x[1].get("confidence", 0)):
        mc = data.get("market_cap", 0)
        mc_str = f"${mc/1e9:.1f}B" if mc >= 1e9 else f"${mc/1e6:.0f}M"
        print(f"  {ticker:6s}  conf={data['confidence']:.2f}  mktcap={mc_str}")
else:
    print("\nStaging vacío.")
