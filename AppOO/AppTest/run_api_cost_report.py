"""
run_api_cost_report.py - Prueba endpoint cost_report Anthropic Admin API
Ejecutar: python AppTest\run_api_cost_report.py
"""

import os
import json
import pathlib
import datetime
import requests

ADMIN_API_KEY = os.environ.get("ANTHROPIC_ADMIN_API_KEY", "")
OUTPUT_PATH = pathlib.Path(r"C:\Users\InversionesWildaga\Documents\deploy\tmp")

if not ADMIN_API_KEY:
    print("ERROR: definí la variable ANTHROPIC_ADMIN_API_KEY antes de correr el script.")
    exit(1)

now = datetime.datetime.utcnow()
start = now.replace(day=1)
end = now

print(f"Consultando rango: {start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}")

all_data = []
next_page = None

while True:
    params = {
        "starting_at": start.strftime("%Y-%m-%dT00:00:00Z"),
        "ending_at": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "group_by[]": "description",
        "bucket_width": "1d",
    }
    if next_page:
        params["page"] = next_page

    response = requests.get(
        "https://api.anthropic.com/v1/organizations/cost_report",
        headers={"anthropic-version": "2023-06-01", "x-api-key": ADMIN_API_KEY},
        params=params,
    )
    print(f"Status: {response.status_code}")
    response.raise_for_status()
    page = response.json()
    all_data.extend(page.get("data", []))

    if not page.get("has_more"):
        break
    next_page = page.get("next_page")

data = {"data": all_data, "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}

OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
dest = OUTPUT_PATH / "usage_report.json"
dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Reporte guardado en: {dest}")
print(json.dumps(data, indent=2))
