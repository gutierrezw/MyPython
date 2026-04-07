"""
CLI para importar extractos bancarios manualmente.
La lógica de parseo vive en Class_Finance.py.

Uso:
    python AppTest/load_statement.py <ruta_pdf> --adapter bbva_ahorro --account-ref "196-009369/5"
    python AppTest/load_statement.py <ruta_pdf> --adapter santander --dry-run
    python AppTest/load_statement.py <ruta_pdf> --inspect
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_python import pdfplumber, connect, Error
from Class_Finance import ADAPTER_MAP, SantanderAr, DB_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("load_statement")


def main():
    parser = argparse.ArgumentParser(description="Importar extracto bancario en PDF")
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument(
        "--adapter",
        default="bbva_tc",
        choices=list(ADAPTER_MAP.keys()),
        help="Adaptador a usar (default: bbva_tc)",
    )
    parser.add_argument("--account-ref", help="Referencia de cuenta en fin_accounts")
    parser.add_argument("--dry-run", action="store_true", help="Parsear sin escribir en BD")
    parser.add_argument("--inspect", action="store_true", help="Mostrar coordenadas X/Y del PDF")
    parser.add_argument("--inspect-page", type=int, default=0, help="Página a inspeccionar (default: 0)")
    parser.add_argument("--inspect-words", type=int, default=100, help="Palabras a mostrar (default: 100)")
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        logger.error(f"Archivo no encontrado: {args.pdf}")
        sys.exit(1)

    if args.inspect:
        with pdfplumber.open(args.pdf) as pdf:
            page = pdf.pages[args.inspect_page]
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            print(
                f"Página {args.inspect_page} — {len(words)} palabras, mostrando {min(args.inspect_words, len(words))}"
            )
            print(f"{'x0':>8}  {'top':>8}  texto")
            print("-" * 50)
            for w in words[: args.inspect_words]:
                print(f"{w['x0']:8.1f}  {w['top']:8.1f}  {w['text']}")
        sys.exit(0)

    AdapterClass = ADAPTER_MAP[args.adapter]
    multi_section = AdapterClass is SantanderAr
    if not multi_section and not args.account_ref:
        logger.error("--account-ref es requerido para este adaptador.")
        sys.exit(1)

    adapter = (
        AdapterClass(pdf_path=args.pdf, dry_run=args.dry_run)
        if multi_section
        else AdapterClass(pdf_path=args.pdf, account_ref=args.account_ref, dry_run=args.dry_run)
    )

    logger.info(f"Archivo  : {args.pdf}")
    logger.info(f"Adaptador: {args.adapter}")
    if not multi_section:
        logger.info(f"Cuenta   : {args.account_ref}")
    logger.info(f"Dry-run  : {args.dry_run}")

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
        f"\nResultado: {stats['rows_found']} filas | "
        f"{stats['inserted']} insertadas | "
        f"{stats['skipped']} omitidas | "
        f"{stats['errors']} errores"
    )


if __name__ == "__main__":
    main()
