"""
CLI para importar transacciones de Binance Pay (remesas salientes).
Llama a la API de Binance y carga en fin_transactions para la cuenta BINANCE-USDT.

Uso:
    python AppTest/load_pay.py --from 2026-01-01 --to 2026-03-31
    python AppTest/load_pay.py --from 2026-01-01 --to 2026-03-31 --dry-run
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from Modulos_python import connect, Error
from Class_Finance import BinancePay, DB_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("load_pay")


def parse_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Fecha inválida: {s!r} — usar formato YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(description="Importar transacciones Binance Pay en fin_transactions")
    parser.add_argument("--from", dest="date_from", required=True, type=parse_date, help="Fecha inicio (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", required=True, type=parse_date, help="Fecha fin (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar transacciones sin escribir en BD")
    args = parser.parse_args()

    if args.date_from > args.date_to:
        logger.error("--from debe ser anterior o igual a --to")
        sys.exit(1)

    adapter = BinancePay(date_from=args.date_from, date_to=args.date_to, dry_run=args.dry_run)

    logger.info(f"Rango   : {args.date_from} → {args.date_to}")
    logger.info(f"Dry-run : {args.dry_run}")

    if args.dry_run:
        stats = adapter.preview()
    else:
        try:
            conn = connect(**DB_CONFIG)
            stats = adapter.load(conn)
            conn.close()
        except Error as e:
            logger.error(f"Error BD: {e}")
            sys.exit(1)

    logger.info(
        f"\nResultado: {stats['rows_found']} encontradas | "
        f"{stats['inserted']} insertadas | "
        f"{stats['skipped']} omitidas | "
        f"{stats['errors']} errores"
    )


if __name__ == "__main__":
    main()
