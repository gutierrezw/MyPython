"""
AppTest/run_api_cost_raw.py
Muestra la respuesta cruda de la Anthropic Admin API (cost_report + api_keys).
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import requests
from datetime import date

_API_BASE = "https://api.anthropic.com"
_API_VER = "2023-06-01"

# API key: argumento CLI, variable de entorno, o input manual
if len(sys.argv) > 1:
    api_key = sys.argv[1]
else:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    api_key = input("Pegá tu API key de Admin (ClaudeAPIA): ").strip()

headers = {"anthropic-version": _API_VER, "x-api-key": api_key}

hoy = date.today()
inicio = date(hoy.year, hoy.month, 1).strftime("%Y-%m-%dT00:00:00Z")
fin = hoy.strftime("%Y-%m-%dT23:59:59Z")

print("=" * 80)
print("1) GET /v1/organizations/cost_report  (group_by=description, 1 bucket)")
print("=" * 80)
params = [
    ("starting_at", inicio),
    ("ending_at", fin),
    ("bucket_width", "1d"),
    ("group_by[]", "description"),
    ("limit", "1"),
]
r = requests.get(f"{_API_BASE}/v1/organizations/cost_report", headers=headers, params=params, timeout=15)
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2)[:3000])

print("\n" + "=" * 80)
print("2) GET /v1/organizations/cost_report  (group_by=workspace_id, 1 bucket)")
print("=" * 80)
params2 = [
    ("starting_at", inicio),
    ("ending_at", fin),
    ("bucket_width", "1d"),
    ("group_by[]", "workspace_id"),
    ("limit", "1"),
]
r2 = requests.get(f"{_API_BASE}/v1/organizations/cost_report", headers=headers, params=params2, timeout=15)
print(f"Status: {r2.status_code}")
print(json.dumps(r2.json(), indent=2)[:3000])

print("\n" + "=" * 80)
print("3) GET /v1/organizations/workspaces")
print("=" * 80)
r3 = requests.get(f"{_API_BASE}/v1/organizations/workspaces", headers=headers, timeout=15)
print(f"Status: {r3.status_code}")
print(json.dumps(r3.json(), indent=2)[:2000])

print("\n" + "=" * 80)
print("4) GET /v1/organizations/api_keys")
print("=" * 80)
r4 = requests.get(f"{_API_BASE}/v1/organizations/api_keys", headers=headers, timeout=15)
print(f"Status: {r4.status_code}")
print(json.dumps(r4.json(), indent=2)[:2000])
