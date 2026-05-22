import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import BDsystem
from Modulos_python import anthropic

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_PROFILE = os.path.join(_BASE, "profiles", "main.json")
if os.path.exists(_PROFILE):
    with open(_PROFILE, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    if _cfg.get("db"):
        BDsystem.configure(_cfg["db"])
    if _cfg.get("tmp_path"):
        os.environ["APPOO_TMP"] = _cfg["tmp_path"]

_VEHICULOS = [
    ("ClaudeAPIS", "Sentimiento"),
    ("ClaudeAPIE", "ETF"),
    ("ClaudeAPIC", "Chat"),
]

if __name__ == "__main__":
    for vehiculo, modulo in _VEHICULOS:
        sesion = BDsystem.get_sesion_by_vehiculo(vehiculo)
        if not sesion:
            print(f"[{modulo}] ERROR: vehículo {vehiculo} no encontrado en sesion")
            continue

        api_key = sesion["userapi"].decode("utf-8")
        if not api_key:
            print(f"[{modulo}] ERROR: userapi vacía")
            continue

        try:
            msg = anthropic.Anthropic(api_key=api_key).messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{"role": "user", "content": "Respondé solo: OK"}],
            )
            print(f"[{modulo}] ✓ {api_key[:12]}...  →  {msg.content[0].text.strip()}")
        except Exception as e:
            print(f"[{modulo}] ERROR: {e}")
