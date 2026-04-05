"""
Backfill masivo de operaciones C2C Binance — últimos 12 meses.

Descarga operaciones BUY completadas en ARS y VES e inserta en booktrading.
La API C2C solo admite ventanas de 30 días → itera mes a mes.

Uso:
    C:\\...\\venv\\Scripts\\python.exe AppTest/run_c2c_backfill.py
    C:\\...\\venv\\Scripts\\python.exe AppTest/run_c2c_backfill.py --dry-run
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Class_ApiBinnace import BinanceClient
from Modulos_Mysql import RepositorioOportunidadesBuySell

# VES: vende USDT para obtener bolívares (SELL).
# ARS se carga por otra vía (trade_USDT_diario en DashMainV9_ia.py).
FIATS_CONFIG = {
    "VES": "SELL",
}
SYMBOL = "USDT"


def procesar_trama(
    trama: dict, fiat: str, trade_type: str, dry_run: bool, repo: RepositorioOportunidadesBuySell
) -> dict:
    """Procesa la respuesta de get_c2c_trade_history e inserta en booktrading."""
    stats = {"procesadas": 0, "insertadas": 0, "duplicadas": 0, "ignoradas": 0}

    if not trama or "data" not in trama:
        return stats

    trader = []
    for row in trama["data"]:
        if row.get("tradeType") == trade_type and row.get("orderStatus") == "COMPLETED" and row.get("fiat") == fiat:
            fecha = datetime.fromtimestamp(row["createTime"] / 1000)
            values = {
                "categoria": row["fiat"],
                "divisa": "USD",
                "cuenta": row["fiat"] + "-0001",
                "fechahora": fecha,
                "idtrans": row["advNo"],
                "cantidad": float(row["takerAmount"]),
                "preciotrans": float(row["unitPrice"]),
                "preciocierre": float(row["unitPrice"]),
                "producto": float(row["totalPrice"]),
                "tarifacomision": 0.0,
                "gprealizadas": 0.0,
                "mtmgp": 0.0,
                "codigo": "O",
            }
            trader.append(values)
            stats["procesadas"] += 1

    trader.sort(key=lambda x: x["fechahora"])

    for registro in trader:
        fiat = registro["categoria"]
        if dry_run:
            print(
                f"  [DRY] {registro['fechahora'].strftime('%Y-%m-%d %H:%M')} | "
                f"{fiat} | {registro['cantidad']:.4f} USDT @ {registro['preciotrans']:.2f} | "
                f"total={registro['producto']:.2f}"
            )
            stats["insertadas"] += 1
            continue

        found = repo.get_hash_booktrading(accion="valida", values=registro, symbol=SYMBOL)
        if not found:
            repo.insert_booktrading(values=registro, symbol=SYMBOL)
            stats["insertadas"] += 1
        else:
            stats["duplicadas"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill C2C Binance 12 meses")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar sin insertar en BD")
    parser.add_argument("--meses", type=int, default=12, help="Cantidad de meses hacia atrás (default: 12)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Backfill C2C Binance — últimos {args.meses} meses")
    print(f"Fiats: {', '.join(f'{f}({t})' for f, t in sorted(FIATS_CONFIG.items()))}")
    print(f"Dry-run: {args.dry_run}")
    print("=" * 60)

    client = BinanceClient().spot
    repo = RepositorioOportunidadesBuySell()

    hoy = datetime.today().replace(hour=23, minute=59, second=59, microsecond=0)
    inicio = (hoy - relativedelta(months=args.meses)).replace(day=1, hour=0, minute=0, second=0)

    totales = {"procesadas": 0, "insertadas": 0, "duplicadas": 0, "ignoradas": 0}

    # Por cada fiat, iterar ventanas de 30 días (límite de la API C2C)
    for fiat, trade_type in sorted(FIATS_CONFIG.items()):
        print(f"\n{'─'*60}")
        print(f"  Fiat: {fiat}  |  tradeType: {trade_type}")
        print(f"{'─'*60}")

        ventana_inicio = inicio
        while ventana_inicio < hoy:
            ventana_fin = min(ventana_inicio + relativedelta(months=1) - timedelta(seconds=1), hoy)

            start_ms = int(ventana_inicio.timestamp() * 1000)
            end_ms = int(ventana_fin.timestamp() * 1000)

            label = (
                f"{ventana_inicio.strftime('%Y-%m')} "
                f"[{ventana_inicio.strftime('%d/%m')} → {ventana_fin.strftime('%d/%m/%Y')}]"
            )
            print(f"\n  [{label}]")

            try:
                response = client.get_c2c_trade_history(
                    tradeType=trade_type,
                    startTimestamp=start_ms,
                    endTimestamp=end_ms,
                    rows=100,
                    fiat=fiat,
                )
                stats = procesar_trama(response, fiat=fiat, trade_type=trade_type, dry_run=args.dry_run, repo=repo)

                print(
                    f"    API: {stats['procesadas']} operaciones "
                    f"| insertadas: {stats['insertadas']} "
                    f"| duplicadas: {stats['duplicadas']}"
                )
                for k in totales:
                    totales[k] += stats[k]

            except Exception as e:
                print(f"    ERROR: {e}")

            ventana_inicio = ventana_inicio + relativedelta(months=1)

    print("\n" + "=" * 60)
    print("RESUMEN TOTAL")
    print(f"  Operaciones encontradas : {totales['procesadas']}")
    print(f"  Insertadas              : {totales['insertadas']}")
    print(f"  Duplicadas (ya existían): {totales['duplicadas']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
