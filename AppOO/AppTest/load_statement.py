"""
Parser de extractos bancarios — Fase 1 del módulo Finanzas Personales.

Adaptadores implementados:
  - BbvaArTarjeta  : BBVA AR tarjetas de crédito (Mastercard y Visa)
                     Columnas: FECHA | DESCRIPCIÓN | NRO. CUPÓN | PESOS | DÓLARES
  - BbvaArCuenta   : BBVA AR cuenta corriente ARS
                     Columnas: FECHA | ORIGEN | CONCEPTO | DÉBITO | CRÉDITO | SALDO
  - SantanderAr    : PDF unificado Santander (cuenta ARS/USD, Visa, AmEx, débito)
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

from Modulos_python import pdfplumber, connect, Error

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


def apply_rules(desc: str, cursor=None) -> tuple[int | None, str | None]:
    """Busca la primera regla coincidente para desc.
    Devuelve (category_id, 'rule') o (None, None).
    Si cursor es None (dry-run) solo evalúa sin actualizar hit_count."""
    if cursor is None:
        return None, None
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
    Parsea el PDF de resumen de tarjeta BBVA Argentina (Visa / Mastercard).

    El PDF no tiene tablas estructuradas — usa texto plano con layout posicional.
    Se reconstruyen filas agrupando words por coordenada Y (tolerancia ±3pt)
    y asignando columnas por rangos de X:

        x < 110          → FECHA (DD-Mon-YY)
        110 ≤ x < 370    → DESCRIPCIÓN
        370 ≤ x < 450    → NRO. CUPÓN
        450 ≤ x < 530    → PESOS
        x ≥ 530          → DÓLARES

    Cuotas en descripción: 'C.03/03' → installment_current=3, installment_total=3
    Secciones ignoradas: encabezado, resumen, legales, impuestos/intereses.
    """

    SECTION_NAME = "bbva_tc"
    RE_CUOTA = re.compile(r"\bC\.?(\d{1,2})/(\d{1,2})\b", re.IGNORECASE)
    RE_DATE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$")

    # Límites X de columnas (calibrados con coordenadas reales del PDF)
    X_DESC_MIN = 110
    X_CUPON_MIN = 370
    X_PESOS_MIN = 450
    X_DOLARES_MIN = 530

    # Palabras que marcan secciones a ignorar
    SKIP_MARKERS = {
        "SALDO ANTERIOR",
        "SALDO ACTUAL",
        "TOTAL CONSUMOS",
        "INTERESES FINANCIACION",
        "DB IVA",
        "PAGO MÍNIMO",
        "TOTAL CONSUMOS DE",
    }

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)

    # ── helpers privados ──────────────────────────────────────────────────────

    def _parse_cuota(self, desc: str) -> tuple[int | None, int | None, str]:
        m = self.RE_CUOTA.search(desc)
        if m:
            cur, tot = int(m.group(1)), int(m.group(2))
            return cur, tot, self.RE_CUOTA.sub("", desc).strip()
        return None, None, desc

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _words_to_lines(self, words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        """Agrupa words por línea usando tolerancia en Y."""
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _line_text(self, words: list[dict]) -> str:
        return " ".join(w["text"] for w in words)

    def _classify_word(self, w: dict) -> str:
        x = w["x0"]
        if x < self.X_DESC_MIN:
            return "fecha"
        if x < self.X_CUPON_MIN:
            return "desc"
        if x < self.X_PESOS_MIN:
            return "cupon"
        if x < self.X_DOLARES_MIN:
            return "pesos"
        return "dolares"

    def _extract_rows(self) -> list[dict]:
        """Lee el PDF por coordenadas y devuelve lista de dicts crudos."""
        rows = []
        in_detail = False

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                # filtrar columna lateral (x > 570 — texto rotado del banco)
                words = [w for w in words if w["x0"] < 570]
                lines = self._words_to_lines(words)

                for line in lines:
                    text = self._line_text(line)

                    # detectar inicio de sección de detalle
                    if "FECHA" in text and "DESCRIPCIÓN" in text:
                        in_detail = True
                        continue

                    # detectar fin de sección (impuestos / legales)
                    if in_detail and any(mk in text.upper() for mk in self.SKIP_MARKERS):
                        in_detail = False
                        continue

                    # títulos de sub-sección (pagos / consumos)
                    if not in_detail:
                        continue

                    # clasificar words de la línea por columna
                    cols = {"fecha": [], "desc": [], "cupon": [], "pesos": [], "dolares": []}
                    for w in line:
                        cols[self._classify_word(w)].append(w["text"])

                    fecha_str = " ".join(cols["fecha"]).strip()
                    if not self._is_date(fecha_str):
                        continue

                    rows.append(
                        {
                            "fecha_str": fecha_str,
                            "date": parse_date_bbva_tc(fecha_str),
                            "raw_description": " ".join(cols["desc"]).strip(),
                            "comprobante": " ".join(cols["cupon"]).strip() or None,
                            "pesos": " ".join(cols["pesos"]).strip(),
                            "dolares": " ".join(cols["dolares"]).strip(),
                        }
                    )

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

    # ── dry-run preview ───────────────────────────────────────────────────────

    def preview(self) -> dict:
        """Parsea el PDF y muestra transacciones sin escribir en BD."""
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            if not r.get("date"):
                logger.warning(f"  Fecha inválida: {r.get('fecha_str')} — omitida")
                stats["errors"] += 1
                continue
            inst_cur, inst_tot, desc_clean = self._parse_cuota(r["raw_description"])
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
# Adaptador BBVA AR — Cuenta Corriente ARS
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArCuenta:
    """
    Parsea el PDF de resumen de cuenta corriente BBVA Argentina.

    El PDF no tiene tablas estructuradas — usa texto posicional.
    Columnas detectadas por rangos de X (calibrados del PDF real):

        x < 97           → FECHA  (DD/MM — año inferido del PDF)
        97  ≤ x < 134    → ORIGEN (código de canal: D, 104, etc.)
        134 ≤ x < 407    → CONCEPTO
        407 ≤ x < 474    → DÉBITO  (expense — valor absoluto)
        474 ≤ x < 540    → CRÉDITO (income)
        x ≥ 540          → SALDO   (ignorado)

    El año se infiere buscando el primer '20XX' en el texto del PDF.
    """

    SECTION_NAME = "bbva_cuenta"
    RE_DATE = re.compile(r"^\d{2}/\d{2}$")

    X_ORIGEN_MIN = 97
    X_CONCEPTO_MIN = 134
    X_DEBITO_MIN = 400
    X_CREDITO_MIN = 474
    X_SALDO_MIN = 515

    SKIP_MARKERS = {
        "SALDO ANTERIOR",
        "TOTALES DEL",
        "TOTAL DÉBITOS",
        "TOTAL CRÉDITOS",
        "Página",
    }

    # Monto incrustado al final del concepto: "-4.700,00" o "-27.000,00"
    RE_INLINE_AMOUNT = re.compile(r"\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$")

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._year: int | None = None

    # ── helpers privados ──────────────────────────────────────────────────────

    def _infer_year(self, words: list[dict]) -> int:
        """Escanea el texto buscando el primer '20XX'."""
        for w in words:
            m = re.search(r"\b(20\d{2})\b", w["text"])
            if m:
                return int(m.group(1))
        return datetime.now().year

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _parse_date(self, fecha_str: str) -> date | None:
        """'DD/MM' → date usando el año inferido del PDF."""
        m = re.match(r"(\d{2})/(\d{2})$", fecha_str.strip())
        if not m:
            return None
        day, month = int(m.group(1)), int(m.group(2))
        year = self._year or datetime.now().year
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _words_to_lines(self, words: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _classify_word(self, w: dict) -> str:
        x = w["x0"]
        if x < self.X_ORIGEN_MIN:
            return "fecha"
        if x < self.X_CONCEPTO_MIN:
            return "origen"
        if x < self.X_DEBITO_MIN:
            return "concepto"
        if x < self.X_CREDITO_MIN:
            return "debito"
        if x < self.X_SALDO_MIN:
            return "credito"
        return "saldo"

    def _extract_rows(self) -> list[dict]:
        rows = []
        in_detail = False

        with pdfplumber.open(self.pdf_path) as pdf:
            # Inferir año desde el texto completo del PDF
            all_words = []
            for page in pdf.pages:
                all_words.extend(page.extract_words(x_tolerance=3, y_tolerance=3))
            self._year = self._infer_year(all_words)
            logger.info(f"  Año inferido del PDF: {self._year}")

            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                words = [w for w in words if w["x0"] < 570]
                lines = self._words_to_lines(words)

                for line in lines:
                    line_text = " ".join(w["text"] for w in line)
                    upper = line_text.upper()

                    # Detectar encabezado de sección de detalle
                    if "FECHA" in upper and "CONCEPTO" in upper and "DÉBITO" in upper:
                        in_detail = True
                        continue

                    if not in_detail:
                        continue

                    if any(mk.upper() in upper for mk in self.SKIP_MARKERS):
                        continue

                    cols = {"fecha": [], "origen": [], "concepto": [], "debito": [], "credito": [], "saldo": []}
                    for w in line:
                        cols[self._classify_word(w)].append(w["text"])

                    fecha_str = " ".join(cols["fecha"]).strip()
                    if not self._is_date(fecha_str):
                        continue

                    concepto = " ".join(cols["concepto"]).strip()
                    if not concepto:
                        continue

                    rows.append(
                        {
                            "fecha_str": fecha_str,
                            "origen": " ".join(cols["origen"]).strip() or None,
                            "concepto": concepto,
                            "debito": " ".join(cols["debito"]).strip(),
                            "credito": " ".join(cols["credito"]).strip(),
                        }
                    )

        return rows

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for r in rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                logger.warning(f"  Fecha inválida: {r['fecha_str']} — omitida")
                continue

            debito = parse_amount_ar(r.get("debito", ""))
            credito = parse_amount_ar(r.get("credito", ""))

            concepto = r["concepto"].strip()
            if debito is not None and debito != 0:
                amount = abs(debito)
                txn_type = "expense"
            elif credito is not None and credito != 0:
                amount = abs(credito)
                txn_type = "income"
            else:
                # Fallback: monto incrustado al final del concepto (ej: "CR/DB DEBIN -4.700,00")
                m_inline = self.RE_INLINE_AMOUNT.search(concepto)
                if m_inline:
                    inline_val = parse_amount_ar(m_inline.group(1))
                    if inline_val is not None:
                        amount = abs(inline_val)
                        txn_type = "expense" if inline_val > 0 else "income"
                        concepto = concepto[: m_inline.start()].strip()
                        logger.info(f"  Monto extraído del concepto: {amount} ({txn_type})")
                    else:
                        logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
                        continue
                else:
                    logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
                    continue
            cat_id, classified_by = apply_rules(concepto, cursor)

            txns.append(
                {
                    "date": txn_date,
                    "type": txn_type,
                    "amount": amount,
                    "currency": "ARS",
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": concepto,
                    "raw_description": concepto,
                    "raw_description_detail": r.get("origen"),
                    "comprobante": None,
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": None,
                    "installment_total": None,
                }
            )

        return txns

    # ── dry-run preview ───────────────────────────────────────────────────────

    def preview(self) -> dict:
        """Parsea el PDF y muestra transacciones sin escribir en BD."""
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                logger.warning(f"  Fecha inválida: {r['fecha_str']} — omitida")
                stats["errors"] += 1
                continue
            debito = parse_amount_ar(r.get("debito", ""))
            credito = parse_amount_ar(r.get("credito", ""))
            concepto = r["concepto"].strip()
            if debito is not None and debito != 0:
                amount, txn_type = abs(debito), "expense"
            elif credito is not None and credito != 0:
                amount, txn_type = abs(credito), "income"
            else:
                m_inline = self.RE_INLINE_AMOUNT.search(concepto)
                if m_inline:
                    inline_val = parse_amount_ar(m_inline.group(1))
                    if inline_val is not None:
                        amount = abs(inline_val)
                        txn_type = "expense" if inline_val > 0 else "income"
                        concepto = concepto[: m_inline.start()].strip()
                    else:
                        logger.warning(f"  Sin monto: {concepto[:60]} — omitida")
                        stats["errors"] += 1
                        continue
                else:
                    logger.warning(f"  Sin monto: {concepto[:60]} — omitida")
                    stats["errors"] += 1
                    continue
            logger.info(
                f"  {txn_date} | {txn_type:8s} | ARS {amount:>12.2f} | "
                f"orig={r.get('origen') or '-':>4s} | {concepto[:50]}"
            )
            stats["inserted"] += 1
        return stats

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
                f"Cuenta no encontrada para account_ref='{self.account_ref}'. " "Verificar run_finanzas_setup.py."
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
        cursor.execute(
            """INSERT INTO fin_statement_imports
               (account_id, bank_id, filename, file_hash, section, status)
               VALUES (%s, %s, %s, %s, %s, 'pending')""",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid

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
            except Error as e:
                logger.error(f"  Error insertando: {e} — {txn.get('raw_description', '')[:60]}")
                stats["errors"] += 1

        # 7. Actualizar import header
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
# Adaptador BBVA AR — Caja de Ahorros ARS
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArAhorro(BbvaArCuenta):
    """
    Parsea el PDF de resumen de caja de ahorros BBVA Argentina.

    Layout idéntico a BbvaArCuenta — mismas columnas posicionales.
    Solo difiere el SECTION_NAME para el registro de imports.

    account_ref típico: '196-009369/5'
    """

    SECTION_NAME = "bbva_ahorro"


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Santander AR — PDF unificado (cuenta + TC Visa + TC AmEx + débito)
# ─────────────────────────────────────────────────────────────────────────────


class SantanderAr:
    """
    Parsea el PDF mensual unificado de Santander Argentina.

    El PDF contiene múltiples secciones en un solo archivo.  Un estado interno
    (state machine) detecta la sección activa por el texto de los encabezados.

    Secciones y account_ref correspondiente:
        cuenta_ars  → 175-370719/9         (CA + CC en pesos)
        cuenta_usd  → 175-370719/9-USD     (CA en dólares)
        visa        → TC-0925              (TC Visa, consumos del mes)
        amex        → TC-9541              (TC AmEx, consumos del mes)
        debito      → TD-2861              (compras + pagos con débito)

    Para cuenta ARS, columnas por X:
        x < 65       → FECHA  (DD/MM/YY)
        65 ≤ x < 115 → COMPROBANTE
        115 ≤ x < 340→ CONCEPTO
        340 ≤ x < 416→ MONTO CA pesos
        416 ≤ x < 524→ MONTO CC pesos
        x ≥ 524      → SALDO (ignorado)

    Para TC (Visa / AmEx):
        x < 80       → FECHA
        80 ≤ x < 145 → COMPROBANTE
        145 ≤ x < 345→ DESCRIPCIÓN
        345 ≤ x < 415→ CUOTA  (ej: "01 de 03")
        415 ≤ x < 500→ PESOS
        x ≥ 500      → DÓLARES

    Para débito:
        x < 86       → FECHA
        86 ≤ x < 151 → COMPROBANTE
        151 ≤ x < 488→ DESCRIPCIÓN (establecimiento / servicio)
        x ≥ 488      → IMPORTE
    """

    ACCOUNT_REF_MAP = {
        "cuenta_ars": "175-370719/9",
        "cuenta_usd": "175-370719/9-USD",
        "visa": "TC-0925",
        "amex": "TC-9541",
        "debito": "TD-2861",
    }
    SECTION_NAME_MAP = {
        "cuenta_ars": "santander_cuenta_ars",
        "cuenta_usd": "santander_cuenta_usd",
        "visa": "santander_visa",
        "amex": "santander_amex",
        "debito": "santander_debito",
    }

    RE_DATE_DDMMYY = re.compile(r"^\d{2}/\d{2}/\d{2}$")
    RE_CUOTA_SAN = re.compile(r"^(\d{1,2})\s+de\s+(\d{1,2})$", re.IGNORECASE)

    def __init__(self, pdf_path: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._year: int = datetime.now().year

    # ── helpers ──────────────────────────────────────────────────────────────

    def _words_to_lines(self, words: list[dict], y_tol: float = 4.0) -> list[list[dict]]:
        if not words:
            return []
        lines, current = [], [words[0]]
        for w in words[1:]:
            if abs(w["top"] - current[0]["top"]) <= y_tol:
                current.append(w)
            else:
                lines.append(sorted(current, key=lambda x: x["x0"]))
                current = [w]
        lines.append(sorted(current, key=lambda x: x["x0"]))
        return lines

    def _line_text(self, line: list[dict]) -> str:
        return " ".join(w["text"] for w in line)

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE_DDMMYY.match(text.strip()))

    def _parse_date(self, text: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})/(\d{2})$", text.strip())
        if not m:
            return None
        day, month, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(2000 + yy, month, day)
        except ValueError:
            return None

    def _parse_signed_tokens(self, tokens: list[str]) -> Decimal | None:
        """Convierte lista de tokens ['$','1.234,56'] o ['-$','56,00'] a Decimal."""
        joined = " ".join(tokens).strip()
        # detectar signo
        negative = joined.startswith("-")
        # quitar símbolos de moneda
        cleaned = re.sub(r"[-]?[\$]|U\$S|U\$\s*S", "", joined).strip()
        value = parse_amount_ar(cleaned)
        if value is None:
            return None
        return -value if negative else value

    def _classify_cuenta(self, w: dict) -> str:
        x = w["x0"]
        if x < 65:
            return "fecha"
        if x < 115:
            return "comprobante"
        if x < 340:
            return "concepto"
        if x < 416:
            return "monto_ca"
        if x < 524:
            return "monto_cc"
        return "saldo"

    def _classify_tc(self, w: dict) -> str:
        x = w["x0"]
        if x < 80:
            return "fecha"
        if x < 140:
            return "comprobante"
        if x < 345:
            return "descripcion"
        if x < 415:
            return "cuota"
        if x < 500:
            return "pesos"
        return "dolares"

    def _classify_debito(self, w: dict) -> str:
        x = w["x0"]
        if x < 60:
            return "fecha"
        if x < 144:
            return "comprobante"
        if x < 480:
            return "descripcion"
        return "importe"

    # ── extracción por sección ────────────────────────────────────────────────

    def _extract_all(self) -> dict[str, list[dict]]:
        """Recorre el PDF detectando secciones y extrae filas por sección.

        Estado de la máquina:
          state       = sección de datos activa ("cuenta_ars" | "cuenta_usd" |
                        "visa" | "amex" | "debito" | "debito_pagos" |
                        "tc_pagos" | "none")
          product_ctx = último producto detectado por header de página
                        ("visa" | "amex" | "debito" | "cuenta" | "none")
          pending_san = flag: vimos "TARJETA SANTANDER" y esperamos la
                        siguiente línea para resolver el producto
        """
        result: dict[str, list[dict]] = {k: [] for k in self.ACCOUNT_REF_MAP}
        state = "none"
        product_ctx = "none"
        pending_san = False  # "TARJETA SANTANDER" sin resolver aún

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                words = [w for w in words if w["x0"] < 600]
                lines = self._words_to_lines(words)

                for line in lines:
                    text = self._line_text(line)
                    upper = text.upper()

                    # ── resolver producto pendiente ────────────────────────
                    if pending_san:
                        pending_san = False
                        if "VISA" in upper:
                            product_ctx = "visa"
                            state = "none"
                            continue
                        if "AMERICAN EXPRESS" in upper:
                            product_ctx = "amex"
                            state = "none"
                            continue
                        # no era una TC conocida — ignorar

                    # ── detectar encabezados de producto ─────────────────
                    if upper.strip() == "TARJETA SANTANDER":
                        pending_san = True
                        state = "none"
                        continue
                    # Débito — solo el header de página (línea corta, ≤4 words)
                    # evita match con transacciones "Compra con tarjeta de debito"
                    if "TARJETA DE D" in upper and "BITO" in upper and len(line) <= 4:
                        product_ctx = "debito"
                        state = "none"
                        continue

                    # ── detectar encabezados de columnas / secciones ──────
                    # Cuenta ARS
                    if "CAJA DE AHORRO EN PESOS" in upper and "CUENTA CORRIENTE EN PESOS" in upper:
                        state = "cuenta_ars"
                        product_ctx = "cuenta"
                        continue
                    # Cuenta USD
                    if "CAJA DE AHORRO EN" in upper and "LARES" in upper and product_ctx == "cuenta":
                        state = "cuenta_usd"
                        continue
                    # Cuenta: fin
                    if state in ("cuenta_ars", "cuenta_usd") and (
                        "SALDO TOTAL" in upper or "DETALLE IMPOSITIVO" in upper
                    ):
                        state = "none"
                        continue

                    # TC: sección de pagos anteriores → ignorar
                    if product_ctx in ("visa", "amex") and "PAGO ANTERIOR" in upper:
                        state = "tc_pagos"
                        continue
                    # TC: inicio de consumos del mes
                    if "CONSUMOS DEL MES" in upper and product_ctx in ("visa", "amex"):
                        state = product_ctx
                        continue
                    # TC: fin de consumos
                    # "CONSUMOS TOTALES $ ..." y "TOTAL A PAGAR" marcan fin.
                    # "TOTAL CONSUMOS DE ..." es sub-header → no terminar.
                    if state in ("visa", "amex") and (
                        upper.startswith("IMPUESTOS")
                        or upper.startswith("CONSUMOS TOTALES")
                        or (upper.startswith("TOTAL CONSUMOS") and "DE " not in upper[:30])
                        or upper.startswith("TOTAL A PAGAR")
                    ):
                        state = "none"
                        continue
                    # TC: saltar header de columnas
                    if state in ("visa", "amex") and "DESCRIPCI" in upper and "CUOTA" in upper:
                        continue
                    # tc_pagos → consumos
                    if state == "tc_pagos" and "CONSUMOS DEL MES" in upper:
                        state = product_ctx
                        continue

                    # Débito: header compras
                    if product_ctx == "debito" and "ESTABLECIMIENTO" in upper and "IMPORTE" in upper:
                        state = "debito"
                        continue
                    # Débito: header pagos
                    if product_ctx == "debito" and "SERVICIO" in upper and "MEDIO DE PAGO" in upper:
                        state = "debito_pagos"
                        continue
                    # Débito: fin compras
                    if state == "debito" and upper.startswith("MONTO TOTAL"):
                        state = "none"
                        continue
                    # Débito: fin pagos
                    if state == "debito_pagos" and upper.startswith("PAGOS TOTALES"):
                        state = "none"
                        continue

                    # ── procesar línea según estado activo ────────────────
                    if state == "cuenta_ars":
                        self._process_cuenta_line(line, result["cuenta_ars"], "cuenta_ars")
                    elif state == "cuenta_usd":
                        self._process_cuenta_usd_line(line, result["cuenta_usd"])
                    elif state in ("visa", "amex"):
                        self._process_tc_line(line, result[state])
                    elif state == "debito":
                        self._process_debito_line(line, result["debito"], expense=True)
                    elif state == "debito_pagos":
                        self._process_debito_line(line, result["debito"], expense=True)

        return result

    def _process_cuenta_line(self, line: list[dict], rows: list[dict], section: str):
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])

        fecha_str = " ".join(cols["fecha"]).strip()
        concepto = " ".join(cols["concepto"]).strip()

        if not self._is_date(fecha_str):
            return  # líneas de detalle sin fecha → ignorar

        # Skips
        upper_c = concepto.upper()
        if any(s in upper_c for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
            return

        # Monto: preferir CA pesos; si no, CC pesos
        monto_tokens = cols["monto_ca"] or cols["monto_cc"]
        amount = self._parse_signed_tokens(monto_tokens)
        if amount is None:
            return

        txn_type = "expense" if amount < 0 else "income"
        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": concepto,
                "amount": abs(amount),
                "type": txn_type,
                "currency": "ARS",
            }
        )

    def _process_cuenta_usd_line(self, line: list[dict], rows: list[dict]):
        """Para la sección USD: mismas columnas pero monto en U$S."""
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])

        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            return

        concepto = " ".join(cols["concepto"]).strip()
        upper_c = concepto.upper()
        if any(s in upper_c for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
            return

        monto_tokens = cols["monto_ca"] or cols["monto_cc"]
        amount = self._parse_signed_tokens(monto_tokens)
        if amount is None:
            return

        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": concepto,
                "amount": abs(amount),
                "type": "expense" if amount < 0 else "income",
                "currency": "USD",
            }
        )

    def _process_tc_line(self, line: list[dict], rows: list[dict]):
        cols = {k: [] for k in ("fecha", "comprobante", "descripcion", "cuota", "pesos", "dolares")}
        for w in line:
            cols[self._classify_tc(w)].append(w["text"])

        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            return

        desc = " ".join(cols["descripcion"]).strip()
        if not desc:
            return

        # Skip saldo anterior y pagos que puedan filtrarse
        upper_d = desc.upper()
        if any(s in upper_d for s in ("SALDO ANTERIOR", "TU PAGO", "CR.", "CR.$")):
            return

        # Monto: preferir pesos; si solo dólares, usar dólares
        pesos_tokens = cols["pesos"]
        dolares_tokens = cols["dolares"]
        if pesos_tokens:
            amount = self._parse_signed_tokens(pesos_tokens)
            currency = "ARS"
        elif dolares_tokens:
            amount = self._parse_signed_tokens(dolares_tokens)
            currency = "USD"
        else:
            return

        if amount is None:
            return

        # Cuota: "01 de 03" → installment_current=1, installment_total=3
        cuota_text = " ".join(cols["cuota"]).strip()
        inst_cur, inst_tot = None, None
        m = self.RE_CUOTA_SAN.match(cuota_text)
        if m:
            inst_cur, inst_tot = int(m.group(1)), int(m.group(2))

        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": desc,
                "amount": abs(amount),
                "type": "expense" if amount >= 0 else "income",
                "currency": currency,
                "installment_current": inst_cur,
                "installment_total": inst_tot,
            }
        )

    def _process_debito_line(self, line: list[dict], rows: list[dict], expense: bool):
        cols = {k: [] for k in ("fecha", "comprobante", "descripcion", "importe")}
        for w in line:
            cols[self._classify_debito(w)].append(w["text"])

        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            return

        desc = " ".join(cols["descripcion"]).strip()
        if not desc:
            return

        amount = self._parse_signed_tokens(cols["importe"])
        if amount is None:
            return

        rows.append(
            {
                "fecha_str": fecha_str,
                "date": self._parse_date(fecha_str),
                "comprobante": " ".join(cols["comprobante"]).strip() or None,
                "concepto": desc,
                "amount": abs(amount),
                "type": "expense" if expense else "income",
                "currency": "ARS",
                "installment_current": None,
                "installment_total": None,
            }
        )

    # ── build transactions ────────────────────────────────────────────────────

    def _build_transactions(
        self,
        rows: list[dict],
        account_id: int,
        import_id: int,
        section_key: str,
        cursor,
    ) -> list[dict]:
        txns = []
        for r in rows:
            if not r.get("date"):
                logger.warning(f"  [{section_key}] Fecha inválida: {r.get('fecha_str')} — omitida")
                continue
            cat_id, classified_by = apply_rules(r["concepto"], cursor)
            txns.append(
                {
                    "date": r["date"],
                    "type": r["type"],
                    "amount": r["amount"],
                    "currency": r.get("currency", "ARS"),
                    "category_id": cat_id,
                    "account_id": account_id,
                    "description": r["concepto"],
                    "raw_description": r["concepto"],
                    "raw_description_detail": None,
                    "comprobante": r.get("comprobante"),
                    "import_id": import_id,
                    "classified_by": classified_by,
                    "installment_current": r.get("installment_current"),
                    "installment_total": r.get("installment_total"),
                }
            )
        return txns

    # ── dry-run preview ───────────────────────────────────────────────────────

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        all_rows = self._extract_all()
        for section_key, rows in all_rows.items():
            if not rows:
                continue
            acct_ref = self.ACCOUNT_REF_MAP[section_key]
            logger.info(f"\n  ── {section_key} ({acct_ref}) — {len(rows)} filas ──")
            stats["rows_found"] += len(rows)
            for r in rows:
                if not r.get("date"):
                    stats["errors"] += 1
                    continue
                inst = ""
                if r.get("installment_current"):
                    inst = f" [{r['installment_current']}/{r['installment_total']}]"
                logger.info(
                    f"  {r['date']} | {r['type']:8s} | {r.get('currency','ARS')} "
                    f"{r['amount']:>12.2f}{inst} | {r['concepto'][:50]}"
                )
                stats["inserted"] += 1
        return stats

    # ── método principal ──────────────────────────────────────────────────────

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()

        # Pre-cargar account_ids por section_key
        account_ids: dict[str, int] = {}
        bank_ids: dict[str, int] = {}
        for section_key, acct_ref in self.ACCOUNT_REF_MAP.items():
            cursor.execute(
                "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
                (acct_ref,),
            )
            row = cursor.fetchone()
            if row:
                account_ids[section_key] = row[0]
                bank_ids[section_key] = row[1]
            else:
                logger.warning(f"  Cuenta no encontrada: {acct_ref} ({section_key}) — sección omitida")

        # Registrar un import_id por sección
        import_ids: dict[str, int] = {}
        filename = os.path.basename(self.pdf_path)
        for section_key in self.SECTION_NAME_MAP:
            if section_key not in account_ids:
                continue
            section_name = self.SECTION_NAME_MAP[section_key]
            cursor.execute(
                "SELECT id, status FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
                (self.file_hash, section_name),
            )
            existing = cursor.fetchone()
            if existing:
                logger.warning(
                    f"  [{section_key}] Ya importado (import_id={existing[0]}). " "Usa --force para reimportar."
                )
                import_ids[section_key] = -1  # skip
                continue
            cursor.execute(
                """INSERT INTO fin_statement_imports
                   (account_id, bank_id, filename, file_hash, section, status)
                   VALUES (%s, %s, %s, %s, %s, 'pending')""",
                (account_ids[section_key], bank_ids[section_key], filename, self.file_hash, section_name),
            )
            conn.commit()
            import_ids[section_key] = cursor.lastrowid

        # Parsear el PDF
        logger.info("  Extrayendo secciones del PDF...")
        all_rows = self._extract_all()

        # Insertar por sección
        for section_key, rows in all_rows.items():
            if import_ids.get(section_key) == -1:
                continue
            if section_key not in account_ids or section_key not in import_ids:
                continue
            stats["rows_found"] += len(rows)
            import_id = import_ids[section_key]
            txns = self._build_transactions(rows, account_ids[section_key], import_id, section_key, cursor)
            inserted_sec = 0
            for txn in txns:
                try:
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
                        inserted_sec += 1
                    else:
                        stats["skipped"] += 1
                except Error as e:
                    logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                    stats["errors"] += 1

            cursor.execute(
                """UPDATE fin_statement_imports
                   SET status='processed', row_count=%s, processed_count=%s
                   WHERE id=%s""",
                (len(rows), inserted_sec, import_id),
            )
            conn.commit()
            logger.info(f"  [{section_key}] {len(rows)} filas → {inserted_sec} insertadas")

        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

ADAPTER_MAP = {
    "bbva_tc": BbvaArTarjeta,
    "bbva_cuenta": BbvaArCuenta,
    "bbva_ahorro": BbvaArAhorro,
    "santander": SantanderAr,
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
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Mostrar coordenadas X/Y de palabras del PDF (calibración de columnas)",
    )
    parser.add_argument(
        "--inspect-page",
        type=int,
        default=0,
        help="Página a inspeccionar con --inspect (default: 0)",
    )
    parser.add_argument(
        "--inspect-words",
        type=int,
        default=100,
        help="Cantidad de palabras a mostrar con --inspect (default: 100)",
    )
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
    # SantanderAr es multi-sección: no requiere --account-ref
    multi_section = AdapterClass is SantanderAr
    if not multi_section and not args.account_ref:
        logger.error("--account-ref es requerido. Consultar fin_accounts en la BD.")
        sys.exit(1)

    if multi_section:
        adapter = AdapterClass(pdf_path=args.pdf, dry_run=args.dry_run)
    else:
        adapter = AdapterClass(pdf_path=args.pdf, account_ref=args.account_ref, dry_run=args.dry_run)

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
            logger.error(f"Error de conexión BD: {e}")
            sys.exit(1)

    logger.info(
        f"\nResultado: {stats['rows_found']} filas encontradas | "
        f"{stats['inserted']} insertadas | "
        f"{stats['skipped']} omitidas | "
        f"{stats['errors']} errores"
    )


if __name__ == "__main__":
    main()
