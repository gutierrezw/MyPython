import os
import re
import shutil
import hashlib
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from Modulos_python import pdfplumber, connect, Error

_logger = logging.getLogger("BankStatements")

DB_CONFIG = {
    "user": "root",
    "password": "Daga2004",
    "host": "localhost",
    "database": "bdinv",
}

EXTRACTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp", "extractos")
PROCESADOS_DIR = os.path.join(EXTRACTOS_DIR, "procesados")
DESCONOCIDOS_DIR = os.path.join(EXTRACTOS_DIR, "desconocidos")

# ─────────────────────────────────────────────────────────────────────────────
# Reglas de detección automática de banco/adaptador por contenido del PDF.
# Orden importa — primera coincidencia gana.
# (keyword_en_pdf, adapter_key, account_ref)  account_ref=None → multi-sección
# ─────────────────────────────────────────────────────────────────────────────

DETECTION_RULES = [
    ("Santander", "santander", None),
    ("196-009369/5", "bbva_ahorro", "196-009369/5"),
    ("196-004699/4", "bbva_cuenta", "196-004699/4"),
    ("1269461197", "bbva_tc", "TC-1269461197"),
    ("1175839390", "bbva_tc", "TC-1175839390"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades compartidas
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
    """Convierte número formato argentino '1.234,56' → Decimal('1234.56')."""
    if not text:
        return None
    text = text.strip().replace(" ", "")
    if not text or text in ("-", "—"):
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_date_bbva_tc(text: str) -> date | None:
    """BBVA tarjetas: 'DD-Mon-YY'  ej: '15-Mar-25' → date(2025, 3, 15)"""
    text = text.strip()
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})$", text)
    if m:
        day, mes, yy = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = MESES_ES.get(mes)
        if month:
            return date(2000 + yy, month, day)
    return None


def apply_rules(desc: str, cursor=None) -> tuple[int | None, str | None]:
    """Busca la primera regla activa coincidente para desc.
    Devuelve (category_id, 'rule') o (None, None)."""
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

    Columnas por X:
        x < 110          → FECHA (DD-Mon-YY)
        110 ≤ x < 370    → DESCRIPCIÓN
        370 ≤ x < 450    → NRO. CUPÓN
        450 ≤ x < 530    → PESOS
        x ≥ 530          → DÓLARES
    """

    SECTION_NAME = "bbva_tc"
    RE_CUOTA = re.compile(r"\bC\.?(\d{1,2})/(\d{1,2})\b", re.IGNORECASE)
    RE_DATE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$")

    X_DESC_MIN = 110
    X_CUPON_MIN = 370
    X_PESOS_MIN = 450
    X_DOLARES_MIN = 530

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

    def _parse_cuota(self, desc: str) -> tuple[int | None, int | None, str]:
        m = self.RE_CUOTA.search(desc)
        if m:
            cur, tot = int(m.group(1)), int(m.group(2))
            return cur, tot, self.RE_CUOTA.sub("", desc).strip()
        return None, None, desc

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

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
        rows = []
        in_detail = False
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 570]
                lines = self._words_to_lines(words)
                for line in lines:
                    text = " ".join(w["text"] for w in line)
                    if "FECHA" in text and "DESCRIPCIÓN" in text:
                        in_detail = True
                        continue
                    if in_detail and any(mk in text.upper() for mk in self.SKIP_MARKERS):
                        in_detail = False
                        continue
                    if not in_detail:
                        continue
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
        txns = []
        for r in rows:
            if not r.get("date"):
                _logger.warning(f"  Fecha inválida: {r.get('fecha_str')} — omitida")
                continue
            raw_desc = r["raw_description"].strip()
            inst_cur, inst_tot, desc_clean = self._parse_cuota(raw_desc)
            amount_pesos = parse_amount_ar(r.get("pesos", ""))
            amount_dolares = parse_amount_ar(r.get("dolares", ""))
            if amount_dolares is not None and amount_dolares != 0:
                amount, currency = amount_dolares, "USD"
            elif amount_pesos is not None:
                amount, currency = amount_pesos, "ARS"
            else:
                _logger.warning(f"  Sin monto: {raw_desc[:60]} — omitida")
                continue
            txn_type = "income" if amount < 0 else "expense"
            cat_id, classified_by = apply_rules(raw_desc, cursor)
            txns.append(
                {
                    "date": r["date"],
                    "type": txn_type,
                    "amount": abs(amount),
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

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        _logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            if not r.get("date"):
                stats["errors"] += 1
                continue
            inst_cur, inst_tot, desc_clean = self._parse_cuota(r["raw_description"])
            amount_pesos = parse_amount_ar(r.get("pesos", ""))
            amount_dolares = parse_amount_ar(r.get("dolares", ""))
            amount = amount_dolares if (amount_dolares is not None and amount_dolares != 0) else amount_pesos
            currency = "USD" if (amount_dolares is not None and amount_dolares != 0) else "ARS"
            if amount is None:
                stats["errors"] += 1
                continue
            txn_type = "income" if amount < 0 else "expense"
            _logger.info(
                f"  {r['date']} | {txn_type:8s} | {currency} {abs(amount):>12.2f} | "
                f"cuota={inst_cur}/{inst_tot} | {desc_clean[:55]}"
            )
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        cursor.execute(
            "SELECT id, status FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.warning("  PDF ya importado — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        txns = self._build_transactions(raw_rows, account_id, import_id, cursor)
        for txn in txns:
            try:
                cursor.execute(_INSERT_TXN_SQL, txn)
                stats["inserted" if cursor.rowcount == 1 else "skipped"] += 1
            except Error as e:
                _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                stats["errors"] += 1
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s WHERE id=%s",
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

    Columnas por X (calibradas del PDF real):
        x < 97           → FECHA  (DD/MM — año inferido del PDF)
        97  ≤ x < 134    → ORIGEN
        134 ≤ x < 400    → CONCEPTO
        400 ≤ x < 474    → DÉBITO
        474 ≤ x < 515    → CRÉDITO
        x ≥ 515          → SALDO (ignorado)
    """

    SECTION_NAME = "bbva_cuenta"
    RE_DATE = re.compile(r"^\d{2}/\d{2}$")
    RE_INLINE_AMOUNT = re.compile(r"\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})\s*$")

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

    def __init__(self, pdf_path: str, account_ref: str, dry_run: bool = False):
        self.pdf_path = pdf_path
        self.account_ref = account_ref.strip()
        self.dry_run = dry_run
        self.file_hash = sha256_file(pdf_path)
        self._year: int | None = None

    def _infer_year(self, words: list[dict]) -> int:
        for w in words:
            m = re.search(r"\b(20\d{2})\b", w["text"])
            if m:
                return int(m.group(1))
        return datetime.now().year

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE.match(text.strip()))

    def _parse_date(self, fecha_str: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})$", fecha_str.strip())
        if not m:
            return None
        day, month = int(m.group(1)), int(m.group(2))
        try:
            return date(self._year or datetime.now().year, month, day)
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
            all_words = []
            for page in pdf.pages:
                all_words.extend(page.extract_words(x_tolerance=3, y_tolerance=3))
            self._year = self._infer_year(all_words)
            _logger.info(f"  Año inferido: {self._year}")
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 570]
                lines = self._words_to_lines(words)
                for line in lines:
                    line_text = " ".join(w["text"] for w in line)
                    upper = line_text.upper()
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

    def _resolve_amount(self, r: dict) -> tuple[Decimal | None, str]:
        """Resuelve monto y tipo desde columnas DÉBITO/CRÉDITO o fallback inline."""
        debito = parse_amount_ar(r.get("debito", ""))
        credito = parse_amount_ar(r.get("credito", ""))
        concepto = r["concepto"].strip()
        if debito is not None and debito != 0:
            return abs(debito), "expense" if debito > 0 else "income", concepto
        if credito is not None and credito != 0:
            return abs(credito), "income", concepto
        # Fallback: monto incrustado al final del concepto
        m_inline = self.RE_INLINE_AMOUNT.search(concepto)
        if m_inline:
            inline_val = parse_amount_ar(m_inline.group(1))
            if inline_val is not None:
                concepto_clean = concepto[: m_inline.start()].strip()
                txn_type = "expense" if inline_val > 0 else "income"
                return abs(inline_val), txn_type, concepto_clean
        return None, None, concepto

    def _build_transactions(self, rows: list[dict], account_id: int, import_id: int, cursor) -> list[dict]:
        txns = []
        for r in rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                _logger.warning(f"  Fecha inválida: {r['fecha_str']} — omitida")
                continue
            amount, txn_type, concepto = self._resolve_amount(r)
            if amount is None:
                _logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
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

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        _logger.info(f"  Filas encontradas: {len(raw_rows)}")
        for r in raw_rows:
            txn_date = self._parse_date(r["fecha_str"])
            if not txn_date:
                stats["errors"] += 1
                continue
            amount, txn_type, concepto = self._resolve_amount(r)
            if amount is None:
                _logger.warning(f"  Sin monto: {r['concepto'][:60]} — omitida")
                stats["errors"] += 1
                continue
            _logger.info(
                f"  {txn_date} | {txn_type:8s} | ARS {amount:>12.2f} | "
                f"orig={r.get('origen') or '-':>4s} | {concepto[:50]}"
            )
            stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1",
            (self.account_ref,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Cuenta no encontrada: account_ref='{self.account_ref}'")
        account_id, bank_id = row
        cursor.execute(
            "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
            (self.file_hash, self.SECTION_NAME),
        )
        if cursor.fetchone():
            _logger.warning("  PDF ya importado — omitido")
            cursor.close()
            return stats
        cursor.execute(
            "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
            "VALUES (%s,%s,%s,%s,%s,'pending')",
            (account_id, bank_id, os.path.basename(self.pdf_path), self.file_hash, self.SECTION_NAME),
        )
        conn.commit()
        import_id = cursor.lastrowid
        raw_rows = self._extract_rows()
        stats["rows_found"] = len(raw_rows)
        txns = self._build_transactions(raw_rows, account_id, import_id, cursor)
        for txn in txns:
            try:
                cursor.execute(_INSERT_TXN_SQL, txn)
                stats["inserted" if cursor.rowcount == 1 else "skipped"] += 1
            except Error as e:
                _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                stats["errors"] += 1
        cursor.execute(
            "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s,skipped_count=%s WHERE id=%s",
            (stats["rows_found"], stats["inserted"], stats["skipped"], import_id),
        )
        conn.commit()
        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador BBVA AR — Caja de Ahorros ARS
# ─────────────────────────────────────────────────────────────────────────────


class BbvaArAhorro(BbvaArCuenta):
    """Layout idéntico a BbvaArCuenta. account_ref típico: '196-009369/5'"""

    SECTION_NAME = "bbva_ahorro"


# ─────────────────────────────────────────────────────────────────────────────
# Adaptador Santander AR — PDF unificado (cuenta + TC Visa + TC AmEx + débito)
# ─────────────────────────────────────────────────────────────────────────────


class SantanderAr:
    """
    Parsea el PDF mensual unificado de Santander Argentina.
    State machine detecta secciones por encabezados.

    Secciones → account_ref:
        cuenta_ars → 175-370719/9
        cuenta_usd → 175-370719/9-USD
        visa       → TC-0925
        amex       → TC-9541
        debito     → TD-2861
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

    def _is_date(self, text: str) -> bool:
        return bool(self.RE_DATE_DDMMYY.match(text.strip()))

    def _parse_date(self, text: str) -> date | None:
        m = re.match(r"(\d{2})/(\d{2})/(\d{2})$", text.strip())
        if not m:
            return None
        try:
            return date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None

    def _parse_signed_tokens(self, tokens: list[str]) -> Decimal | None:
        joined = " ".join(tokens).strip()
        negative = joined.startswith("-")
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

    def _extract_all(self) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {k: [] for k in self.ACCOUNT_REF_MAP}
        state = "none"
        product_ctx = "none"
        pending_san = False

        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                words = [w for w in page.extract_words(x_tolerance=3, y_tolerance=3) if w["x0"] < 600]
                lines = self._words_to_lines(words)
                for line in lines:
                    text = " ".join(w["text"] for w in line)
                    upper = text.upper()

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

                    if upper.strip() == "TARJETA SANTANDER":
                        pending_san = True
                        state = "none"
                        continue
                    if "TARJETA DE D" in upper and "BITO" in upper and len(line) <= 4:
                        product_ctx = "debito"
                        state = "none"
                        continue
                    if "CAJA DE AHORRO EN PESOS" in upper and "CUENTA CORRIENTE EN PESOS" in upper:
                        state = "cuenta_ars"
                        product_ctx = "cuenta"
                        continue
                    if "CAJA DE AHORRO EN" in upper and "LARES" in upper and product_ctx == "cuenta":
                        state = "cuenta_usd"
                        continue
                    if state in ("cuenta_ars", "cuenta_usd") and (
                        "SALDO TOTAL" in upper or "DETALLE IMPOSITIVO" in upper
                    ):
                        state = "none"
                        continue
                    if product_ctx in ("visa", "amex") and "PAGO ANTERIOR" in upper:
                        state = "tc_pagos"
                        continue
                    if "CONSUMOS DEL MES" in upper and product_ctx in ("visa", "amex"):
                        state = product_ctx
                        continue
                    if state in ("visa", "amex") and (
                        upper.startswith("IMPUESTOS")
                        or upper.startswith("CONSUMOS TOTALES")
                        or (upper.startswith("TOTAL CONSUMOS") and "DE " not in upper[:30])
                        or upper.startswith("TOTAL A PAGAR")
                    ):
                        state = "none"
                        continue
                    if state in ("visa", "amex") and "DESCRIPCI" in upper and "CUOTA" in upper:
                        continue
                    if state == "tc_pagos" and "CONSUMOS DEL MES" in upper:
                        state = product_ctx
                        continue
                    if product_ctx == "debito" and "ESTABLECIMIENTO" in upper and "IMPORTE" in upper:
                        state = "debito"
                        continue
                    if product_ctx == "debito" and "SERVICIO" in upper and "MEDIO DE PAGO" in upper:
                        state = "debito_pagos"
                        continue
                    if state == "debito" and upper.startswith("MONTO TOTAL"):
                        state = "none"
                        continue
                    if state == "debito_pagos" and upper.startswith("PAGOS TOTALES"):
                        state = "none"
                        continue

                    if state == "cuenta_ars":
                        self._process_cuenta_line(line, result["cuenta_ars"])
                    elif state == "cuenta_usd":
                        self._process_cuenta_usd_line(line, result["cuenta_usd"])
                    elif state in ("visa", "amex"):
                        self._process_tc_line(line, result[state])
                    elif state in ("debito", "debito_pagos"):
                        self._process_debito_line(line, result["debito"], expense=True)

        return result

    def _process_cuenta_line(self, line: list[dict], rows: list[dict]):
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        concepto = " ".join(cols["concepto"]).strip()
        if not self._is_date(fecha_str):
            return
        if any(s in concepto.upper() for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
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
                "currency": "ARS",
            }
        )

    def _process_cuenta_usd_line(self, line: list[dict], rows: list[dict]):
        cols = {k: [] for k in ("fecha", "comprobante", "concepto", "monto_ca", "monto_cc", "saldo")}
        for w in line:
            cols[self._classify_cuenta(w)].append(w["text"])
        fecha_str = " ".join(cols["fecha"]).strip()
        if not self._is_date(fecha_str):
            return
        concepto = " ".join(cols["concepto"]).strip()
        if any(s in concepto.upper() for s in ("SALDO INICIAL", "SALDO ANTERIOR")):
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
        if any(s in desc.upper() for s in ("SALDO ANTERIOR", "TU PAGO", "CR.", "CR.$")):
            return
        if cols["pesos"]:
            amount = self._parse_signed_tokens(cols["pesos"])
            currency = "ARS"
        elif cols["dolares"]:
            amount = self._parse_signed_tokens(cols["dolares"])
            currency = "USD"
        else:
            return
        if amount is None:
            return
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

    def _build_transactions(self, rows, account_id, import_id, section_key, cursor) -> list[dict]:
        txns = []
        for r in rows:
            if not r.get("date"):
                _logger.warning(f"  [{section_key}] Fecha inválida: {r.get('fecha_str')} — omitida")
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

    def preview(self) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        all_rows = self._extract_all()
        for section_key, rows in all_rows.items():
            if not rows:
                continue
            _logger.info(f"\n  ── {section_key} ({self.ACCOUNT_REF_MAP[section_key]}) — {len(rows)} filas ──")
            stats["rows_found"] += len(rows)
            for r in rows:
                if not r.get("date"):
                    stats["errors"] += 1
                    continue
                inst = f" [{r['installment_current']}/{r['installment_total']}]" if r.get("installment_current") else ""
                _logger.info(
                    f"  {r['date']} | {r['type']:8s} | {r.get('currency','ARS')} "
                    f"{r['amount']:>12.2f}{inst} | {r['concepto'][:50]}"
                )
                stats["inserted"] += 1
        return stats

    def load(self, conn) -> dict:
        stats = {"inserted": 0, "skipped": 0, "errors": 0, "rows_found": 0}
        cursor = conn.cursor()
        account_ids: dict[str, int] = {}
        bank_ids: dict[str, int] = {}
        for section_key, acct_ref in self.ACCOUNT_REF_MAP.items():
            cursor.execute("SELECT id, bank_id FROM fin_accounts WHERE account_ref=%s AND is_active=1", (acct_ref,))
            row = cursor.fetchone()
            if row:
                account_ids[section_key] = row[0]
                bank_ids[section_key] = row[1]
            else:
                _logger.warning(f"  Cuenta no encontrada: {acct_ref} ({section_key}) — omitida")

        import_ids: dict[str, int] = {}
        filename = os.path.basename(self.pdf_path)
        for section_key, section_name in self.SECTION_NAME_MAP.items():
            if section_key not in account_ids:
                continue
            cursor.execute(
                "SELECT id FROM fin_statement_imports WHERE file_hash=%s AND section=%s",
                (self.file_hash, section_name),
            )
            if cursor.fetchone():
                _logger.warning(f"  [{section_key}] Ya importado — omitido")
                import_ids[section_key] = -1
                continue
            cursor.execute(
                "INSERT INTO fin_statement_imports (account_id,bank_id,filename,file_hash,section,status) "
                "VALUES (%s,%s,%s,%s,%s,'pending')",
                (account_ids[section_key], bank_ids[section_key], filename, self.file_hash, section_name),
            )
            conn.commit()
            import_ids[section_key] = cursor.lastrowid

        all_rows = self._extract_all()
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
                    cursor.execute(_INSERT_TXN_SQL, txn)
                    if cursor.rowcount == 1:
                        stats["inserted"] += 1
                        inserted_sec += 1
                    else:
                        stats["skipped"] += 1
                except Error as e:
                    _logger.error(f"  Error: {e} — {txn.get('raw_description','')[:60]}")
                    stats["errors"] += 1
            cursor.execute(
                "UPDATE fin_statement_imports SET status='processed',row_count=%s,processed_count=%s WHERE id=%s",
                (len(rows), inserted_sec, import_id),
            )
            conn.commit()
            _logger.info(f"  [{section_key}] {len(rows)} filas → {inserted_sec} insertadas")

        cursor.close()
        return stats


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de adaptadores y SQL compartido
# ─────────────────────────────────────────────────────────────────────────────

ADAPTER_MAP = {
    "bbva_tc": BbvaArTarjeta,
    "bbva_cuenta": BbvaArCuenta,
    "bbva_ahorro": BbvaArAhorro,
    "santander": SantanderAr,
}

_INSERT_TXN_SQL = """
    INSERT IGNORE INTO fin_transactions
        (date, type, amount, currency, category_id, account_id,
         description, raw_description, raw_description_detail,
         comprobante, import_id, classified_by,
         installment_current, installment_total)
    VALUES
        (%(date)s, %(type)s, %(amount)s, %(currency)s, %(category_id)s,
         %(account_id)s, %(description)s, %(raw_description)s,
         %(raw_description_detail)s, %(comprobante)s, %(import_id)s,
         %(classified_by)s, %(installment_current)s, %(installment_total)s)
"""


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de escaneo automático de carpeta (dueña del dominio)
# ─────────────────────────────────────────────────────────────────────────────


def detect_adapter(pdf_path: str) -> tuple[str, str | None] | None:
    """Detecta adaptador y account_ref por contenido del PDF. Devuelve (key, ref) o None."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            words = []
            for page in pdf.pages[:2]:
                words.extend(w["text"] for w in page.extract_words(x_tolerance=3, y_tolerance=3))
                if len(words) >= 200:
                    break
            text = " ".join(words[:200])
    except Exception as e:
        _logger.error(f"  Error leyendo PDF: {e}")
        return None
    for keyword, adapter_key, account_ref in DETECTION_RULES:
        if keyword in text:
            return adapter_key, account_ref
    return None


def process_pdf(pdf_path: str) -> bool:
    """Detecta banco, carga en BD y devuelve True si OK (incluyendo ya-importado)."""
    filename = os.path.basename(pdf_path)
    _logger.info(f"── Procesando: {filename}")
    detected = detect_adapter(pdf_path)
    if not detected:
        _logger.warning(f"  Banco no reconocido: {filename}")
        return False
    adapter_key, account_ref = detected
    _logger.info(f"  Detectado: {adapter_key}  ref={account_ref or 'multi-sección'}")
    AdapterClass = ADAPTER_MAP.get(adapter_key)
    if not AdapterClass:
        _logger.error(f"  Adaptador '{adapter_key}' no encontrado")
        return False
    try:
        adapter = (
            AdapterClass(pdf_path=pdf_path)
            if AdapterClass is SantanderAr
            else AdapterClass(pdf_path=pdf_path, account_ref=account_ref)
        )
        conn = connect(**DB_CONFIG)
        stats = adapter.load(conn)
        conn.close()
        _logger.info(
            f"  {stats['rows_found']} filas | {stats['inserted']} ins | "
            f"{stats['skipped']} skip | {stats['errors']} err"
        )
        return True
    except Error as e:
        _logger.error(f"  Error BD: {e}")
        return False
    except Exception as e:
        _logger.error(f"  Error: {e}")
        return False


def scan_extractos() -> str:
    """Escanea EXTRACTOS_DIR, procesa PDFs nuevos, mueve procesados/desconocidos.
    Devuelve resumen en texto para el agente."""
    if not os.path.isdir(EXTRACTOS_DIR):
        return f"Carpeta no encontrada: {EXTRACTOS_DIR}"
    pdfs = sorted(
        os.path.join(EXTRACTOS_DIR, f)
        for f in os.listdir(EXTRACTOS_DIR)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(EXTRACTOS_DIR, f))
    )
    if not pdfs:
        return "Sin PDFs pendientes"
    ok_count = 0
    fail_count = 0
    import time

    for pdf_path in pdfs:
        ok = process_pdf(pdf_path)
        dest = PROCESADOS_DIR if ok else DESCONOCIDOS_DIR
        os.makedirs(dest, exist_ok=True)
        dest_file = os.path.join(dest, os.path.basename(pdf_path))
        if os.path.exists(dest_file):
            base, ext = os.path.splitext(os.path.basename(pdf_path))
            dest_file = os.path.join(dest, f"{base}_{int(time.time())}{ext}")
        shutil.move(pdf_path, dest_file)
        if ok:
            ok_count += 1
        else:
            fail_count += 1
    return f"Procesados: {ok_count} OK, {fail_count} fallidos de {len(pdfs)} PDFs"
