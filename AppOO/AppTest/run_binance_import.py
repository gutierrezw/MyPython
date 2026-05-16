"""
Importa historial de trades Binance Spot → booktrading.

Uso:
    python run_binance_import.py --desde 2024-01-01
    python run_binance_import.py --desde 2024-01-01 --dry-run
    python run_binance_import.py --desde 2024-01-01 --simbolos BTC ETH BNB

Configuración (config_import.json en la misma carpeta):
    {
        "api_key": "TU_API_KEY",
        "api_secret": "TU_API_SECRET",
        "account": "B0000001",
        "vehiculo": "Crypto",
        "db": {
            "host": "localhost",
            "user": "root",
            "password": "",
            "database": "bdinv"
        }
    }
"""

import sys
import os
import json
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from binance.spot import Spot
from Modulos_Mysql import BDsystem, RepositorioOportunidadesBuySell

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_import.json")

QUOTE_ASSETS = ["USDT", "BTC", "ETH", "BNB", "BUSD"]


def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"ERROR: No se encontró {CONFIG_FILE}")
        print("Creá el archivo con tu API key y configuración de BD.")
        sys.exit(1)
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_account_symbols(client):
    """Obtiene símbolos con balance > 0 en la cuenta."""
    info = client.account()
    balances = [
        b["asset"]
        for b in info.get("balances", [])
        if float(b["free"]) + float(b["locked"]) > 0 and b["asset"] not in QUOTE_ASSETS
    ]
    return [f"{a}USDT" for a in balances]


def procesar_trades(client, symbol, desde_ms, hasta_ms, account, vehiculo, dry_run, repo):
    """Descarga y procesa trades de un símbolo en ventanas de 24hs."""
    stats = {"procesadas": 0, "insertadas": 0, "duplicadas": 0, "errores": 0}
    ticket = symbol.replace("USDT", "")

    ventana_inicio = desde_ms
    while ventana_inicio < hasta_ms:
        ventana_fin = min(ventana_inicio + 86400000, hasta_ms)  # 24hs en ms
        try:
            trades = client.my_trades(symbol, startTime=ventana_inicio, endTime=ventana_fin, limit=1000)
            for t in trades:
                try:
                    qty = float(t.get("qty", 0.0))
                    qty = qty if t["isBuyer"] else -qty
                    precio = float(t.get("price", 0.0))
                    registro = {
                        "categoria": vehiculo,
                        "divisa": "USD",
                        "cuenta": account,
                        "fechahora": datetime.fromtimestamp(t["time"] / 1000),
                        "idtrans": str(t["id"]),
                        "cantidad": qty,
                        "producto": float(t.get("quoteQty", 0.0)),
                        "preciotrans": precio,
                        "preciocierre": precio,
                        "tarifacomision": float(t.get("commission", 0.0)) * precio,
                        "mtmgp": 0.0,
                        "gprealizadas": 0.0,
                        "codigo": "O" if t["isBuyer"] else "C",
                    }
                    stats["procesadas"] += 1

                    if dry_run:
                        accion = "BUY" if t["isBuyer"] else "SELL"
                        print(
                            f"  [DRY] {registro['fechahora'].strftime('%Y-%m-%d %H:%M')} | "
                            f"{ticket} {accion} {abs(qty):.6f} @ {precio:.4f} USDT"
                        )
                        stats["insertadas"] += 1
                    else:
                        found = repo.get_hash_booktrading(accion="valida", values=registro, symbol=ticket)
                        if not found:
                            repo.insert_booktrading(values=registro, symbol=ticket)
                            stats["insertadas"] += 1
                        else:
                            stats["duplicadas"] += 1
                except Exception as e:
                    stats["errores"] += 1
                    print(f"    ERROR trade {t.get('id')}: {e}")
        except Exception as e:
            print(f"    ERROR API [{datetime.fromtimestamp(ventana_inicio/1000).strftime('%Y-%m-%d')}]: {e}")
            stats["errores"] += 1

        ventana_inicio = ventana_fin

    return stats


def main():
    parser = argparse.ArgumentParser(description="Importar trades Binance Spot → booktrading")
    parser.add_argument("--desde", required=True, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--simbolos", nargs="+", help="Símbolos a importar (ej: BTC ETH). Default: auto-detecta")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar sin insertar en BD")
    args = parser.parse_args()

    cfg = load_config()
    BDsystem.configure(cfg.get("db", {}))

    client = Spot(api_key=cfg["api_key"], api_secret=cfg["api_secret"])
    repo = RepositorioOportunidadesBuySell()
    account = cfg.get("account", "B0000001")
    vehiculo = cfg.get("vehiculo", "Crypto")

    try:
        desde = datetime.strptime(args.desde, "%Y-%m-%d")
    except ValueError:
        print("ERROR: formato de fecha inválido. Usar YYYY-MM-DD")
        sys.exit(1)

    desde_ms = int(desde.timestamp() * 1000)
    hasta_ms = int(datetime.now().timestamp() * 1000)

    if args.simbolos:
        simbolos = [s if s.endswith("USDT") else f"{s}USDT" for s in args.simbolos]
    else:
        print("Auto-detectando símbolos desde balance de cuenta...")
        simbolos = get_account_symbols(client)
        if not simbolos:
            print("No se encontraron balances con activos. Usá --simbolos para especificar.")
            sys.exit(1)

    print("=" * 60)
    print(f"Importar trades Binance Spot → booktrading")
    print(f"Desde    : {args.desde}")
    print(f"Símbolos : {', '.join(simbolos)}")
    print(f"Cuenta   : {account}  |  Vehiculo: {vehiculo}")
    print(f"Dry-run  : {args.dry_run}")
    print("=" * 60)

    totales = {"procesadas": 0, "insertadas": 0, "duplicadas": 0, "errores": 0}

    for symbol in simbolos:
        print(f"\n{'─'*60}")
        print(f"  {symbol}")
        print(f"{'─'*60}")
        stats = procesar_trades(client, symbol, desde_ms, hasta_ms, account, vehiculo, args.dry_run, repo)
        for k in totales:
            totales[k] += stats[k]
        print(
            f"  → procesadas={stats['procesadas']}  insertadas={stats['insertadas']}  "
            f"duplicadas={stats['duplicadas']}  errores={stats['errores']}"
        )

    print("\n" + "=" * 60)
    print("RESUMEN TOTAL")
    print(f"  Procesadas  : {totales['procesadas']}")
    print(f"  Insertadas  : {totales['insertadas']}")
    print(f"  Duplicadas  : {totales['duplicadas']}")
    print(f"  Errores     : {totales['errores']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
