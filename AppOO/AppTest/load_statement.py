"""
Parser de extractos bancarios — Fase 1 del módulo Finanzas Personales.

Adaptadores implementados:
  - BbvaArTarjeta  : BBVA AR tarjetas de crédito (Mastercard y Visa)
                     Columnas: FECHA | DESCRIPCIÓN | NRO. CUPÓN | PESOS | DÓLARES

Uso:
    python AppTest/load_statement.py <ruta_pdf> [--dry-run]

Dependencias:
    pip install pdfplumber   (pymysql ya instalado en el entorno del proyecto)

Siguiente: BbvaArCuenta, SantanderAr
"""

import sys
import os
import re
import hashlib
import argparse
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pdfplumber
from pymysql import connect, Error

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("load_statement")

DB_CONFIG = {
    "user": "root",
    "password": "",
    "host": "localhost",
    "database": "bdinv",
}

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

MESES_ES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_amount_ar(text: str) -> Decimal | None:
    """Convierte número en formato argentino '1.234,56' → Decimal('1234.56').
    Devuelve None si el texto está vacío o no es numérico."""
    if not text:
        return None
    text = text.strip().replace(" ", "")
    if not text or text in ("-", "—"):
        return None
    # quitar puntos de miles, cambiar coma decimal por punto
    text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_date_bbva_tc(text: str, year_hint: int | None = None) -> date | None:
    """BBVA tarjetas: 'DD-Mon-YY'  ej: '15-Mar-25' → date(2025, 3, 15)"""
    text = text.strip()
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})$", text)
    if m:
        day, mes, yy = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = MESES_ES.get(mes)
        if month:
            year = 2000 + yy
            return date(year, month, day)
    return None


def apply_rules(desc: str, cursor) -> tuple[int | None, str]:
    """Busca la primera regla coincidente para desc.
    Devuelve (category_id, 'rule') o (None, None)."""
    cursor.execute(
        "SELECT id, pattern, match_type, category_id " "FROM fin_import_rules WHERE is_active=1 ORDER BY priority, id"
    )
    rules = cursor.fetchall()
    desc_upper = desc.upper()
    for rule_id, pattern, match_type, cat_id in rules:
        p = pattern.upper()
        matched = False
        if match_type == "exact":
            matched = desc_upper == p
        elif match_type == "contains":
            matched = p in desc_upper
        elif match_type == "startswith":
            matched = desc_upper.startswith(p)
        elif match_type == "regex":
            matched = bool(re.search(pattern, desc, re.IGNORECASE))
        if matched:
            cursor.execute(
                "UPDATE fin_import_rules SET hit_count=hit_count+1, last_hit_at=NOW() WHERE id=%s",
                (rule_id,),
            )
            return cat_id, "rule"
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador BBVA AR — Tarjetas de crédito (Mastercard / Visa)
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArTarjeta:
    """
    Parsea el PDF de resumen de tarjeta BBVA Argentina.

    Estructura de tabla esperada (pdfplumber):
        FECHA | DESCRIPCIÓN | NRO. CUPÓN | PESOS | DÓLARES

    Una fila de cargo tiene fecha en col 0 (DD-Mon-YY).
    Filas de continuación de descripción no tienen fecha.

    Cuotas en descripción: 'C.01/06' → installment_current=1, installment_total=6
    """

    HEADER_MARKER = "FECHA"
    SECTION_NAME = "bbva_tc"

    # Regex cuotas: 'C.01/06' o 'C01/06'
    RE_CUOTA = re.compile(r"\bC\.?(\d{1,2})/(\d{1,2})\b", re.IGNORECASE)

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)

    # ── helpers privados ──────────────────────────────────────────────────────

    def _parse_cuota(self, desc: str) -> tuple[int | None, int | None, str]:
        """Extrae cuota actual/total de la descripción. Devuelve (cur, tot, desc_limpia)."""
        m = self.RE_CUOTA.search(desc)
        if m:
            cur, tot = int(m.group(1)), int(m.group(2))
            desc_clean = self.RE_CUOTA.sub("", desc).strip()
            return cur, tot, desc_clean
        return None, None, desc

    def _is_date_cell(self, text: str) -> bool:
        return bool(re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}", text.strip()))

    def _extract_rows(self) -> list[dict]:
        """Lee el PDF y devuelve lista de dicts crudos (sin clasificar)."""
        rows = []
        current_row = None

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    in_data = False
                    for raw_row in table:
                        # limpiar celdas None
                        cells = [c.strip() if c else "" for c in raw_row]
                        if not any(cells):
                            continue

                        # detectar encabezado
                        if not in_data:
                            if any(self.HEADER_MARKER in c.upper() for c in cells):
                                in_data = True
                            continue

                        # fila con fecha = nuevo movimiento
                        if cells and self._is_date_cell(cells[0]):
                            if current_row:
                                rows.append(current_row)
                            # FECHA | DESCRIPCIÓN | NRO. CUPÓN | PESOS | DÓLARES
                            fecha_str = cells[0] if len(cells) > 0 else ""
                            desc = cells[1] if len(cells) > 1 else ""
                            cupón = cells[2] if len(cells) > 2 else ""
                            pesos = cells[3] if len(cells) > 3 else ""
                            dolares = cells[4] if len(cells) > 4 else ""

                            parsed_date = parse_date_bbva_tc(fecha_str)
                            current_row = {
                                "fecha_str": fecha_str,
                                "date": parsed_date,
                                "raw_description": desc,
                                "comprobante": cupón or None,
                                "pesos": pesos,
                                "dolares": dolares,
                            }
                        elif current_row and cells[0] == "":
                            # fila de continuación — concatenar descripción
                            extra = " ".join(c for c in cells if c)
                            current_row["raw_description"] += " " + extra

                    if current_row:
                        rows.append(current_row)
                        current_row = None

        return rows

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        """Convierte filas crudas en dicts listos para INSERT."""
        txns = []
        for r in rows:
            if not r.get("date"):
                logger.warning(f"  Fecha inválida: {r.get('fecha_str')} — fila omitida")
                continue

            raw_desc = r["raw_description"].strip()
            inst_cur, inst_tot, desc_clean = self._parse_cuota(raw_desc)

            # Determinar moneda y monto
            amount_pesos = parse_amount_ar(r.get("pesos", ""))
            amount_dolares = parse_amount_ar(r.get("dolares", ""))

            if amount_dolares is not None and amount_dolares != 0:
                amount = amount_dolares
                currency = "USD"
            elif amount_pesos is not None:
                amount = amount_pesos
                currency = "ARS"
            else:
                logger.warning(f"  Sin monto para: {raw_desc} — fila omitida")
                continue

            # Los cargos en tarjeta de crédito son expenses; créditos/pagos son income
            # En BBVA TC los pagos aparecen como negativos en la columna pesos
            txn_type = "income" if amount < 0 else "expense"
            amount = abs(amount)

            cat_id, classified_by = apply_rules(raw_desc, cursor)

            txns.append(
                {
                    "date": r["date"],
                    "type": txn_type,
                    "amount": amount,
                    "currency": currency,
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": desc_clean,
                    "raw_description": raw_desc,
                    "raw_description_detail": None,
                    "comprobante": r.get("comprobante"),
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": inst_cur,
                    "installment_total": inst_tot,
                }
            )

        return txns

    # ── método principal ──────────────────────────────────────────────────────

    def load(self, conn) -> dict:
        """Ejecuta el import. Devuelve stats: {inserted, skipped, errors}."""
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()

        # 1. Obtener account_id
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(
                f"Cuenta no encontrada para account_ref='{self.account_ref}'. "
                "Verificar run_finanzas_setup.py y volver a correrlo."
            )
        account_id, bank_id = row

        # 2. Verificar duplicado de import
        cursor.execute(
            "SELECT id, status FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        existing = cursor.fetchone()
        if existing:
            logger.warning(
                f"  Este PDF ya fue importado (import_id={existing[0]}, status={existing[1]}). "
                "Usa --force para reimportar."
            )
            return stats

        # 3. Registrar import
        if not self.dry_run:
            cursor.execute(
                """INSERT INTO fin_statement_imports
                   (account_id, bank_id, filename, file_hash, section, status)
                   VALUES (%s, %s, %s, %s, %s, 'pending')""",
                (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
            )
            conn.commit()
            import_id = cursor.lastrowid
        else:
            import_id = -1

        # 4. Parsear PDF
        logger.info("  Extrayendo filas del PDF...")
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        logger.info(f"  Filas encontradas: {len(raw_rows)}")

        # 5. Construir transacciones
        txns = self._build_transactions(raw_rows, account_id, import_id, cursor)

        # 6. INSERT (skip duplicados por dedup key)
        for txn in txns:
            try:
                if not self.dry_run:
                    cursor.execute(
                        """INSERT IGNORE INTO fin_transactions
                           (date, type, amount, currency, category_id, account_id,
                            description, raw_description, raw_description_detail,
                            comprobante, import_id, classified_by,
                            installment_current, installment_total)
                           VALUES
                           (%(date)s, %(type)s, %(amount)s, %(currency)s, %(category_id)s,
                            %(account_id)s, %(description)s, %(raw_description)s,
                            %(raw_description_detail)s, %(comprobante)s, %(import_id)s,
                            %(classified_by)s, %(installment_current)s, %(installment_total)s)""",
                        txn,
                    )
                    if cursor.rowcount == 1:
                        stats["inserted"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # dry-run: solo imprimir
                    logger.info(
                        f"  [DRY] {txn['date']} | {txn['type']:8s} | "
                        f"{txn['currency']} {txn['amount']:>12.2f} | "
                        f"cat={txn['category_id']} | {txn['raw_description'][:60]}"
                    )
                    stats["inserted"] += 1

            except Error as e:
                logger.error(f"  Error insertando: {e} — {txn.get('raw_description','')[:60]}")
                stats["errors"] += 1

        # 7. Actualizar import header
        if not self.dry_run:
            cursor.execute(
                """UPDATE fin_statement_imports
                   SET status='processed', row_count=%s, processed_count=%s, skipped_count=%s
                   WHERE id=%s""",
                (stats["rows_found"], stats["inserted"], stats["skipped"], import_id),
            )
            conn.commit()

        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

ADAPTER_MAP = {
    "bbva_tc": BbvaArTarjeta,
}


def main():
    parser = argparse.ArgumentParser(description="Importar extracto bancario en PDF")
    parser.add_argument("pdf", help="Ruta al archivo PDF")
    parser.add_argument(
        "--adapter",
        default="bbva_tc",
        choices=list(ADAPTER_MAP.keys()),
        help="Adaptador a usar (default: bbva_tc)",
    )
    parser.add_argument(
        "--account-ref",
        help="Referencia de cuenta (account_ref en fin_accounts). " "Ej: '4550-2610-1934-5373' para BBVA Mastercard",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parsear y mostrar sin escribir en BD",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        logger.error(f"Archivo no encontrado: {args.pdf}")
        sys.exit(1)

    if not args.account_ref:
        logger.error("--account-ref es requerido. Consultar fin_accounts en la BD.")
        sys.exit(1)

    AdapterClass = ADAPTER_MAP[args.adapter]
    adapter = AdapterClass(
        pdf_path=args.pdf,
        account_ref=args.account_ref,
        dry_run=args.dry_run,
    )

    logger.info(f"Archivo  : {args.pdf}")
    logger.info(f"Adaptador: {args.adapter}")
    logger.info(f"Cuenta   : {args.account_ref}")
    logger.info(f"Dry-run  : {args.dry_run}")

    if args.dry_run:
        stats = adapter.load(conn=None) if False else _dry_run_load(adapter)
    else:
        try:
            conn = connect(**DB_CONFIG)
            stats = adapter.load(conn)
            conn.close()
        except Error as e:
            logger.error(f"Error de conexión BD: {e}")
            sys.exit(1)

    logger.info(
        f"\nResultado: {stats['rows_found']} filas encontradas | "
        f"{stats['inserted']} insertadas | "
        f"{stats['skipped']} omitidas | "
        f"{stats['errors']} errores"
    )


def _dry_run_load(adapter: BbvaArTarjeta) -> dict:
    """Dry-run sin BD: parsea el PDF y muestra resultados."""
    stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
    raw_rows = adapter._extract_rows()
    stats["rows_found"] = len(raw_rows)
    logger.info(f"  Filas encontradas: {len(raw_rows)}")

    for r in raw_rows:
        if not r.get("date"):
            logger.warning(f"  Fecha inválida: {r.get('fecha_str')} — omitida")
            stats["errors"] += 1
            continue
        inst_cur, inst_tot, desc_clean = adapter._parse_cuota(r["raw_description"])
        amount_pesos = parse_amount_ar(r.get("pesos", ""))
        amount_dolares = parse_amount_ar(r.get("dolares", ""))
        amount = amount_dolares if (amount_dolares is not None and amount_dolares != 0) else amount_pesos
        currency = "USD" if (amount_dolares is not None and amount_dolares != 0) else "ARS"
        if amount is None:
            logger.warning(f"  Sin monto: {r['raw_description'][:60]} — omitida")
            stats["errors"] += 1
            continue
        txn_type = "income" if amount < 0 else "expense"
        logger.info(
            f"  {r['date']} | {txn_type:8s} | {currency} {abs(amount):>12.2f} | "
            f"cuota={inst_cur}/{inst_tot} | {desc_clean[:55]}"
        )
        stats["inserted"] += 1

    return stats


if __name__ == "__main__":
    main()
