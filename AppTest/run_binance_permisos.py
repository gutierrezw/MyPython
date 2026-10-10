"""
Por que Binance contesta -2010 "This account may not place or cancel orders". Solo lee: no coloca ni cancela nada.

    python AppTest\\run_binance_permisos.py

El error -2010 lo devuelve el motor de ordenes, no la validacion de la API key, asi que no distingue por si solo
entre una cuenta restringida por Binance y una clave sin permiso de trading. Las dos lecturas de aca si lo
distinguen:

    canTrade = False                    -> la restriccion es de la CUENTA (cambio de password/2FA, KYC, region)
    canTrade = True + spot/margin False -> la restriccion es de la API KEY (falta tildar el permiso)

Si ademas ipRestrict es True, la lista blanca de IP tiene que incluir la IP de salida de esta maquina.
Ninguna clave se imprime.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

from Class_ApiBinnace import BinanceClient


def main():
    client = BinanceClient(vehiculo="Crypto")
    print(f"vehiculo=Crypto  env={client.env}  base_url={client.urls['base_url']}")
    print("-" * 70)

    cuenta = client.spot.account_spot()
    if not isinstance(cuenta, dict):
        print(f"account_spot() no devolvio dict: {cuenta!r}")
        return

    print("CUENTA  /api/v3/account")
    for k in ("canTrade", "canDeposit", "canWithdraw", "accountType", "brokered", "requireSelfTradePrevention"):
        if k in cuenta:
            print(f"  {k:28} {cuenta[k]}")
    if cuenta.get("permissions"):
        print(f"  {'permissions':28} {cuenta['permissions']}")

    print("-" * 70)
    print("API KEY  /sapi/v1/account/apiRestrictions")
    restric = client.spot.sign_request("GET", "/sapi/v1/account/apiRestrictions", {})
    if isinstance(restric, dict):
        for k, v in restric.items():
            print(f"  {k:28} {v}")
    else:
        print(f"  no devolvio dict: {restric!r}")

    print("-" * 70)
    if cuenta.get("canTrade") is False:
        print("VEREDICTO: la restriccion es de la CUENTA. La API key no tiene nada que ver.")
        print("           Causa tipica: cambio de password, 2FA o email en las ultimas 24-48h.")
        print("           Se resuelve esperando el plazo o desde el soporte de Binance, no desde la app.")
    elif isinstance(restric, dict) and not restric.get("enableSpotAndMarginTrading", True):
        print("VEREDICTO: la restriccion es de la API KEY: le falta 'Enable Spot & Margin Trading'.")
        print("           Se tilda en Binance > API Management > Edit restrictions.")
    else:
        print("VEREDICTO: cuenta y clave habilitadas. Si la orden sigue fallando, el bloqueo es del")
        print("           simbolo o del par (VTHOUSDT en modo solo-cancelar) y no de la cuenta.")


if __name__ == "__main__":
    main()
