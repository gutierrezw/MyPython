"""
Diagnóstico rápido de sesión IBKR Client Portal Gateway.
Ejecutar con gateway activo y autenticado:
    python AppTest/check_ib_session.py
"""

import sys
import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

BASE = "https://localhost:5501/v1/api"


def get(endpoint):
    try:
        r = requests.get(f"{BASE}/{endpoint}", verify=False, timeout=5)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return None, str(e)


def post(endpoint):
    try:
        r = requests.post(f"{BASE}/{endpoint}", verify=False, timeout=5)
        return r.status_code, r.json() if r.content else {}
    except Exception as e:
        return None, str(e)


def sep(titulo):
    print(f"\n{'='*50}")
    print(f"  {titulo}")
    print("=" * 50)


# ── Cuenta en BD ──────────────────────────────────────
sep("Cuenta en BD (sesion vehiculo='Stock')")
sesion = BDsystem.get_sesion_by_vehiculo("Stock")
cuenta_bd = sesion["idcuenta"] if sesion else "NO ENCONTRADA"
print(f"  idcuenta  : {cuenta_bd!r}")
print(f"  iduser    : {sesion.get('iduser', '?')!r}" if sesion else "")

# ── Auth status ───────────────────────────────────────
sep("/iserver/auth/status  (POST)")
code, data = post("iserver/auth/status")
print(f"  HTTP {code}")
print(json.dumps(data, indent=4))

# ── Tickle ────────────────────────────────────────────
sep("/tickle  (POST)")
code, data = post("tickle")
print(f"  HTTP {code}")
if isinstance(data, dict):
    iserver = data.get("iserver", {})
    auth_status = iserver.get("authStatus", {})
    print(f"  authenticated : {auth_status.get('authenticated')}")
    print(f"  connected     : {auth_status.get('connected')}")
    print(f"  competing     : {auth_status.get('competing')}")
else:
    print(f"  {data}")

# ── Cuentas del servidor ──────────────────────────────
sep("/iserver/accounts  (GET)")
code, data = get("iserver/accounts")
print(f"  HTTP {code}")
print(json.dumps(data, indent=4))

if isinstance(data, dict) and "accounts" in data:
    accounts = data["accounts"]
    print(f"\n  ✔ Cuentas IBKR    : {accounts}")
    print(f"  ✔ Cuenta en BD    : {cuenta_bd!r}")
    if cuenta_bd in accounts:
        print(f"  ✅ MATCH — la cuenta está en la lista")
    else:
        print(f"  ❌ MISMATCH — la cuenta NO está en la lista de IBKR")

# ── Portfolio accounts ────────────────────────────────
sep("/portfolio/accounts  (GET)")
code, data = get("portfolio/accounts")
print(f"  HTTP {code}")
if isinstance(data, list):
    for acc in data:
        print(f"  id={acc.get('id')!r}  accountId={acc.get('accountId')!r}  type={acc.get('type')!r}")
else:
    print(json.dumps(data, indent=4))
