"""
Setup inicial del módulo de Finanzas Personales.
Crea tablas en bdinv y carga datos base (bancos, cuentas, categorías, reglas).
Ejecutar una sola vez. Es idempotente — usa IF NOT EXISTS y ON DUPLICATE KEY.

Uso: python AppTest/run_finanzas_setup.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymysql import connect, Error

DB_CONFIG = {
    "user": "root",
    "password": "",
    "host": "localhost",
    "database": "bdinv",
}

# ─────────────────────────────────────────────────────────────────────────────
# DDL — tablas
# ─────────────────────────────────────────────────────────────────────────────

TABLES = {}

TABLES["fin_exchange_rates"] = """
CREATE TABLE IF NOT EXISTS fin_exchange_rates (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    from_currency   CHAR(3)      NOT NULL,
    to_currency     CHAR(4)      NOT NULL DEFAULT 'USDT',
    rate            DECIMAL(18,8) NOT NULL,
    date            DATE         NOT NULL,
    source          ENUM('binance','manual') NOT NULL DEFAULT 'manual',
    pair            VARCHAR(20),
    UNIQUE KEY uq_rate_date (from_currency, to_currency, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_banks"] = """
CREATE TABLE IF NOT EXISTS fin_banks (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(80)  NOT NULL,
    country         CHAR(2)      NOT NULL DEFAULT 'AR',
    adapter_class   VARCHAR(80),
    date_format     VARCHAR(20),
    delimiter       CHAR(1)      DEFAULT ',',
    encoding        VARCHAR(20)  DEFAULT 'utf-8',
    currency        CHAR(3)      DEFAULT 'ARS',
    gmail_sender    VARCHAR(120),
    notes           TEXT,
    is_active       TINYINT(1)   NOT NULL DEFAULT 1,
    UNIQUE KEY uq_bank_name (name, country)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_accounts"] = """
CREATE TABLE IF NOT EXISTS fin_accounts (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    name                  VARCHAR(80)  NOT NULL,
    type                  ENUM('checking','credit','savings','investment','debit') NOT NULL,
    currency              CHAR(3)      NOT NULL DEFAULT 'ARS',
    balance               DECIMAL(18,2) DEFAULT 0.00,
    opening_balance       DECIMAL(18,2) DEFAULT 0.00,
    credit_limit          DECIMAL(18,2) DEFAULT NULL,
    bank_id               INT          NOT NULL,
    account_number_last4  CHAR(10)     DEFAULT NULL,
    account_ref           VARCHAR(40)  DEFAULT NULL COMMENT 'Número de cuenta completo o referencia del banco',
    institution           VARCHAR(80)  DEFAULT NULL,
    is_active             TINYINT(1)   NOT NULL DEFAULT 1,
    FOREIGN KEY (bank_id) REFERENCES fin_banks(id),
    UNIQUE KEY uq_account (bank_id, account_ref, currency)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_statement_imports"] = """
CREATE TABLE IF NOT EXISTS fin_statement_imports (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    account_id       INT          NOT NULL,
    bank_id          INT          NOT NULL,
    filename         VARCHAR(200),
    file_hash        CHAR(64)     NOT NULL COMMENT 'SHA-256 del archivo',
    section          VARCHAR(60)  DEFAULT NULL COMMENT 'Sección dentro del PDF (ej: visa_credito, cuenta_ars)',
    period_from      DATE         DEFAULT NULL,
    period_to        DATE         DEFAULT NULL,
    imported_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_count        INT          DEFAULT 0,
    processed_count  INT          DEFAULT 0,
    skipped_count    INT          DEFAULT 0,
    status           ENUM('pending','processed','error') NOT NULL DEFAULT 'pending',
    error_log        TEXT,
    FOREIGN KEY (account_id) REFERENCES fin_accounts(id),
    FOREIGN KEY (bank_id)    REFERENCES fin_banks(id),
    UNIQUE KEY uq_import (file_hash, section)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_categories"] = """
CREATE TABLE IF NOT EXISTS fin_categories (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(80)  NOT NULL,
    type        ENUM('income','expense','transfer') NOT NULL DEFAULT 'expense',
    parent_id   INT          DEFAULT NULL,
    color       CHAR(7)      DEFAULT '#888888',
    icon        VARCHAR(40)  DEFAULT NULL,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    FOREIGN KEY (parent_id) REFERENCES fin_categories(id),
    UNIQUE KEY uq_cat_name (name, type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_import_rules"] = """
CREATE TABLE IF NOT EXISTS fin_import_rules (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    pattern      VARCHAR(200) NOT NULL,
    match_type   ENUM('exact','contains','startswith','regex') NOT NULL DEFAULT 'contains',
    category_id  INT          NOT NULL,
    priority     INT          NOT NULL DEFAULT 100,
    is_active    TINYINT(1)   NOT NULL DEFAULT 1,
    created_by   ENUM('user','ai','system') NOT NULL DEFAULT 'system',
    hit_count    INT          NOT NULL DEFAULT 0,
    last_hit_at  DATETIME     DEFAULT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES fin_categories(id),
    UNIQUE KEY uq_rule (pattern, match_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

TABLES["fin_transactions"] = """
CREATE TABLE IF NOT EXISTS fin_transactions (
    id                       INT AUTO_INCREMENT PRIMARY KEY,
    date                     DATE         NOT NULL,
    type                     ENUM('income','expense','transfer') NOT NULL,
    amount                   DECIMAL(18,2) NOT NULL,
    currency                 CHAR(3)      NOT NULL DEFAULT 'ARS',
    amount_usdt              DECIMAL(18,8) DEFAULT NULL COMMENT 'Convertido a USDT al rate del día',
    category_id              INT          DEFAULT NULL,
    account_id               INT          NOT NULL,
    description              VARCHAR(300) DEFAULT NULL COMMENT 'Descripción limpia (editable)',
    raw_description          VARCHAR(300) NOT NULL   COMMENT 'Texto original del extracto — no editar',
    raw_description_detail   VARCHAR(300) DEFAULT NULL COMMENT 'Segunda línea del extracto (Santander)',
    comprobante              VARCHAR(20)  DEFAULT NULL COMMENT 'Número de referencia/cupón del banco',
    import_id                INT          DEFAULT NULL,
    classified_by            ENUM('rule','ai','manual') DEFAULT NULL,
    classification_confidence FLOAT        DEFAULT NULL,
    is_recurring             TINYINT(1)   NOT NULL DEFAULT 0,
    recurring_group_id       INT          DEFAULT NULL,
    installment_current      TINYINT      DEFAULT NULL COMMENT 'Cuota actual (ej: 1)',
    installment_total        TINYINT      DEFAULT NULL COMMENT 'Total cuotas (ej: 6)',
    tags                     VARCHAR(200) DEFAULT NULL,
    notes                    TEXT         DEFAULT NULL,
    needs_review             TINYINT(1)   NOT NULL DEFAULT 0,
    created_at               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES fin_categories(id),
    FOREIGN KEY (account_id)  REFERENCES fin_accounts(id),
    FOREIGN KEY (import_id)   REFERENCES fin_statement_imports(id),
    UNIQUE KEY uq_tx (account_id, date, amount, raw_description(150))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# ─────────────────────────────────────────────────────────────────────────────
# Datos base — bancos
# ─────────────────────────────────────────────────────────────────────────────

BANKS = [
    {
        "name": "Santander",
        "country": "AR",
        "adapter_class": "SantanderArPdf",
        "date_format": "%d/%m/%y",
        "currency": "ARS",
        "gmail_sender": "notificaciones@santander.com.ar",
        "notes": "PDF unificado: cuenta + Visa TC + AmEx TC + Débito en un solo archivo. "
        "Secciones detectadas por header. Formato fecha DD/MM/YY.",
    },
    {
        "name": "BBVA",
        "country": "AR",
        "adapter_class": "BbvaArPdf",
        "date_format": "%d-%b-%y",
        "currency": "ARS",
        "gmail_sender": "notificaciones@bbva.com.ar",
        "notes": "PDFs separados por producto: cuenta, Visa, Mastercard. "
        "TC usa fecha DD-Mon-YY (mes en español). Cuota embebida en descripción C.NN/NN.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Datos base — cuentas (dependen de que los bancos ya estén insertados)
# ─────────────────────────────────────────────────────────────────────────────
# Se completan con bank_id dinámico al momento de insertar.

ACCOUNTS_BY_BANK = {
    "Santander": [
        {
            "name": "Santander CA/CC ARS",
            "type": "checking",
            "currency": "ARS",
            "account_ref": "175-370719/9",
            "account_number_last4": "7199",
            "institution": "Banco Santander Argentina S.A.",
        },
        {
            "name": "Santander CA USD",
            "type": "savings",
            "currency": "USD",
            "account_ref": "175-370719/9-USD",
            "account_number_last4": "7199",
            "institution": "Banco Santander Argentina S.A.",
        },
        {
            "name": "Santander Visa Crédito",
            "type": "credit",
            "currency": "ARS",
            "account_ref": "TC-0925",
            "account_number_last4": "0925",
            "credit_limit": 2526000.00,
            "institution": "Banco Santander Argentina S.A.",
        },
        {
            "name": "Santander AmEx Crédito",
            "type": "credit",
            "currency": "ARS",
            "account_ref": "TC-9541",
            "account_number_last4": "9541",
            "credit_limit": 2526000.00,
            "institution": "Banco Santander Argentina S.A.",
        },
        {
            "name": "Santander Débito",
            "type": "debit",
            "currency": "ARS",
            "account_ref": "TD-2861",
            "account_number_last4": "2861",
            "institution": "Banco Santander Argentina S.A.",
        },
    ],
    "BBVA": [
        {
            "name": "BBVA CC ARS",
            "type": "checking",
            "currency": "ARS",
            "account_ref": "196-004699/4",
            "account_number_last4": "4699",
            "institution": "Banco BBVA Argentina S.A.",
        },
        {
            "name": "BBVA CA USD",
            "type": "savings",
            "currency": "USD",
            "account_ref": "196-003750/1",
            "account_number_last4": "3750",
            "institution": "Banco BBVA Argentina S.A.",
        },
        {
            "name": "BBVA Mastercard Black",
            "type": "credit",
            "currency": "ARS",
            "account_ref": "TC-1269461197",
            "account_number_last4": "1197",
            "credit_limit": 11000000.00,
            "institution": "Banco BBVA Argentina S.A.",
        },
        {
            "name": "BBVA Visa Signature",
            "type": "credit",
            "currency": "ARS",
            "account_ref": "TC-1175839390",
            "account_number_last4": "9390",
            "credit_limit": 11000000.00,
            "institution": "Banco BBVA Argentina S.A.",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Datos base — categorías
# Formato: (name, type, parent_name_or_None, color)
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = [
    # ── GASTOS ────────────────────────────────────────────────────────────────
    ("Alimentación", "expense", None, "#E74C3C"),
    ("Supermercado", "expense", "Alimentación", "#E74C3C"),
    ("Restaurantes", "expense", "Alimentación", "#E74C3C"),
    ("Delivery", "expense", "Alimentación", "#E74C3C"),
    ("Almacén/Kiosco", "expense", "Alimentación", "#E74C3C"),
    ("Transporte", "expense", None, "#E67E22"),
    ("Combustible", "expense", "Transporte", "#E67E22"),
    ("Taxi/Uber/Cabify", "expense", "Transporte", "#E67E22"),
    ("Transporte público", "expense", "Transporte", "#E67E22"),
    ("SUBE", "expense", "Transporte", "#E67E22"),
    ("Hogar", "expense", None, "#9B59B6"),
    ("Arriendo", "expense", "Hogar", "#9B59B6"),
    ("Servicios", "expense", "Hogar", "#9B59B6"),
    ("Mantenimiento", "expense", "Hogar", "#9B59B6"),
    ("Expensas", "expense", "Hogar", "#9B59B6"),
    ("Salud", "expense", None, "#1ABC9C"),
    ("Médico", "expense", "Salud", "#1ABC9C"),
    ("Farmacia", "expense", "Salud", "#1ABC9C"),
    ("Seguro salud", "expense", "Salud", "#1ABC9C"),
    ("Entretenimiento", "expense", None, "#3498DB"),
    ("Streaming", "expense", "Entretenimiento", "#3498DB"),
    ("Eventos", "expense", "Entretenimiento", "#3498DB"),
    ("Deportes", "expense", "Entretenimiento", "#3498DB"),
    ("Shopping", "expense", "Entretenimiento", "#3498DB"),
    ("Educación", "expense", None, "#2ECC71"),
    ("Tecnología", "expense", None, "#34495E"),
    ("Suscripciones", "expense", "Tecnología", "#34495E"),
    ("Hardware/Software", "expense", "Tecnología", "#34495E"),
    ("Ropa y calzado", "expense", None, "#F39C12"),
    ("Viajes", "expense", None, "#16A085"),
    ("Finanzas", "expense", None, "#C0392B"),
    ("Cuotas crédito", "expense", "Finanzas", "#C0392B"),
    ("Intereses", "expense", "Finanzas", "#C0392B"),
    ("Comisiones bancarias", "expense", "Finanzas", "#C0392B"),
    ("Impuestos bancarios", "expense", "Finanzas", "#C0392B"),
    ("Mascotas", "expense", None, "#D35400"),
    ("Otros gastos", "expense", None, "#95A5A6"),
    # ── INGRESOS ──────────────────────────────────────────────────────────────
    ("Salario", "income", None, "#27AE60"),
    ("Freelance/Honorarios", "income", None, "#2ECC71"),
    ("Inversiones", "income", None, "#27AE60"),
    ("Dividendos", "income", "Inversiones", "#27AE60"),
    ("Fondos comunes", "income", "Inversiones", "#27AE60"),
    ("Arriendos recibidos", "income", None, "#27AE60"),
    ("Bonificaciones", "income", None, "#2ECC71"),
    ("Otros ingresos", "income", None, "#95A5A6"),
    # ── TRANSFERENCIAS ────────────────────────────────────────────────────────
    ("Transferencia entre cuentas", "transfer", None, "#7F8C8D"),
    ("Pago tarjeta crédito", "transfer", None, "#7F8C8D"),
    ("Cripto puente", "transfer", None, "#F39C12"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Datos base — reglas de clasificación
# Formato: (pattern, match_type, category_name)
# ─────────────────────────────────────────────────────────────────────────────

RULES = [
    # Supermercados
    ("DIA", "startswith", "Supermercado"),
    ("VEA", "startswith", "Supermercado"),
    ("CARREFOUR", "startswith", "Supermercado"),
    ("COTO", "startswith", "Supermercado"),
    ("JUMBO", "startswith", "Supermercado"),
    ("DISCO", "startswith", "Supermercado"),
    ("WALMART", "contains", "Supermercado"),
    ("EL GRANERO", "contains", "Supermercado"),
    ("OPENPAY*EL GRANERO", "contains", "Supermercado"),
    # Restaurantes / comida
    ("MCDONALD", "contains", "Restaurantes"),
    ("MC DONALD", "contains", "Restaurantes"),
    ("BURGER", "contains", "Restaurantes"),
    ("KFC", "startswith", "Restaurantes"),
    ("SUBWAY", "contains", "Restaurantes"),
    ("MOSTAZA", "contains", "Restaurantes"),
    ("NOODLE", "contains", "Restaurantes"),
    ("SUSHI", "contains", "Restaurantes"),
    ("LUCCIANOS", "contains", "Restaurantes"),
    ("P COMEDOR", "contains", "Restaurantes"),
    ("SAIGON", "contains", "Restaurantes"),
    # Delivery
    ("PEDIDOSYA", "contains", "Delivery"),
    ("RAPPI", "contains", "Delivery"),
    ("GLOVO", "contains", "Delivery"),
    # Transporte
    ("UBER", "startswith", "Taxi/Uber/Cabify"),
    ("CABIFY", "startswith", "Taxi/Uber/Cabify"),
    ("DIDI", "startswith", "Taxi/Uber/Cabify"),
    ("CABIFY", "contains", "Taxi/Uber/Cabify"),
    ("SUBE", "contains", "SUBE"),
    ("RECARGA SUBE", "contains", "SUBE"),
    # Streaming / suscripciones
    ("NETFLIX", "contains", "Streaming"),
    ("NETFLIX.COM", "contains", "Streaming"),
    ("SPOTIFY", "contains", "Streaming"),
    ("DISNEY", "contains", "Streaming"),
    ("AMAZON PRIME", "contains", "Streaming"),
    ("HBO", "contains", "Streaming"),
    ("APPLE.COM/BILL", "contains", "Suscripciones"),
    ("CLAUDE.AI", "contains", "Suscripciones"),
    ("ANTHROPIC", "contains", "Suscripciones"),
    ("ADOBE", "contains", "Suscripciones"),
    ("CLAROPAY", "contains", "Servicios"),
    # Tecnología / shopping
    ("LOOK SHOPPING", "contains", "Shopping"),
    ("SHOPPING", "contains", "Shopping"),
    ("GALERIAS PACIFICO", "contains", "Shopping"),
    # Ropa / deporte
    ("SPORTING", "contains", "Deportes"),
    ("ROSSI DEPORTES", "contains", "Deportes"),
    ("VAYPOL", "contains", "Ropa y calzado"),
    ("ARREDO", "contains", "Ropa y calzado"),
    # Mercado Pago (varios — needs_review=True, usuario clasifica)
    ("MERPAGO", "startswith", "Otros gastos"),
    ("MERCADOPAGO", "startswith", "Otros gastos"),
    # Finanzas
    ("COMISION POR SERVICIO", "contains", "Comisiones bancarias"),
    ("IVA 21%", "contains", "Impuestos bancarios"),
    ("IMPUESTO LEY", "contains", "Impuestos bancarios"),
    ("IMPUESTO SELLOS", "contains", "Impuestos bancarios"),
    ("IIBB", "contains", "Impuestos bancarios"),
    ("IVA RG", "contains", "Impuestos bancarios"),
    ("DB.RG", "contains", "Impuestos bancarios"),
    ("INTERESES FINANCIACION", "contains", "Intereses"),
    ("COBRO DE INTERES", "contains", "Intereses"),
    ("INTERES SALDO DEUDOR", "contains", "Intereses"),
    # Transferencias
    ("PAGO DE TARJETA DE CREDITO", "contains", "Pago tarjeta crédito"),
    ("SU PAGO EN PESOS", "contains", "Pago tarjeta crédito"),
    ("TRANSFERENCIA RECIBIDA", "contains", "Transferencia entre cuentas"),
    ("TRANSFERENCIA REALIZADA", "contains", "Transferencia entre cuentas"),
    ("TRANSFERENCIA INMEDIATA", "contains", "Transferencia entre cuentas"),
    ("TRANSFERENCIA NO GRAVADA", "contains", "Transferencia entre cuentas"),
    # Inversiones (income)
    ("RESCATE FONDOS COMUNES", "contains", "Fondos comunes"),
    ("SUSCRIPCION FONDOS COMUNES", "contains", "Fondos comunes"),
    ("LIQUIDACION TITULOS", "contains", "Inversiones"),
    ("LIQUIDACION OPER ACCIONES", "contains", "Inversiones"),
    # Bonificaciones (income)
    ("BONIF. CONSUMO", "startswith", "Bonificaciones"),
    ("BONIFICACION PROMOCION", "contains", "Bonificaciones"),
    ("PROMO MODO", "contains", "Bonificaciones"),
    ("PAGO INTERES POR SALDO", "contains", "Bonificaciones"),
    # Mascotas
    ("PET MALL", "contains", "Mascotas"),
    ("AVELLANEDA PET", "contains", "Mascotas"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def get_connection():
    return connect(**DB_CONFIG)


def create_tables(cursor):
    for name, ddl in TABLES.items():
        cursor.execute(ddl)
        print(f"  [OK] tabla {name}")


def insert_banks(cursor):
    sql = """
        INSERT INTO fin_banks (name, country, adapter_class, date_format, currency, gmail_sender, notes)
        VALUES (%(name)s, %(country)s, %(adapter_class)s, %(date_format)s,
                %(currency)s, %(gmail_sender)s, %(notes)s)
        ON DUPLICATE KEY UPDATE
            adapter_class = VALUES(adapter_class),
            date_format   = VALUES(date_format),
            gmail_sender  = VALUES(gmail_sender),
            notes         = VALUES(notes)
    """
    for bank in BANKS:
        cursor.execute(sql, bank)
        print(f"  [OK] banco {bank['name']}")


def get_bank_ids(cursor):
    cursor.execute("SELECT id, name FROM fin_banks")
    return {row[1]: row[0] for row in cursor.fetchall()}


def insert_accounts(cursor, bank_ids):
    sql = """
        INSERT INTO fin_accounts
            (name, type, currency, account_ref, account_number_last4, credit_limit, bank_id, institution)
        VALUES
            (%(name)s, %(type)s, %(currency)s, %(account_ref)s, %(account_number_last4)s,
             %(credit_limit)s, %(bank_id)s, %(institution)s)
        ON DUPLICATE KEY UPDATE
            name         = VALUES(name),
            credit_limit = VALUES(credit_limit),
            institution  = VALUES(institution)
    """
    for bank_name, accounts in ACCOUNTS_BY_BANK.items():
        bank_id = bank_ids.get(bank_name)
        if not bank_id:
            print(f"  [WARN] banco '{bank_name}' no encontrado, saltando cuentas")
            continue
        for acc in accounts:
            acc["bank_id"] = bank_id
            acc.setdefault("credit_limit", None)
            cursor.execute(sql, acc)
            print(f"  [OK] cuenta {acc['name']}")


def insert_categories(cursor):
    sql_parent = """
        INSERT INTO fin_categories (name, type, parent_id, color)
        VALUES (%(name)s, %(type)s, NULL, %(color)s)
        ON DUPLICATE KEY UPDATE color = VALUES(color)
    """
    sql_child = """
        INSERT INTO fin_categories (name, type, parent_id, color)
        VALUES (%(name)s, %(type)s, %(parent_id)s, %(color)s)
        ON DUPLICATE KEY UPDATE parent_id = VALUES(parent_id), color = VALUES(color)
    """

    # Primer pasada: insertar padres
    for name, ctype, parent, color in CATEGORIES:
        if parent is None:
            cursor.execute(sql_parent, {"name": name, "type": ctype, "color": color})

    # Obtener IDs de padres
    cursor.execute("SELECT id, name FROM fin_categories")
    cat_ids = {row[1]: row[0] for row in cursor.fetchall()}

    # Segunda pasada: insertar hijos
    for name, ctype, parent, color in CATEGORIES:
        if parent is not None:
            parent_id = cat_ids.get(parent)
            if not parent_id:
                print(f"  [WARN] categoría padre '{parent}' no encontrada para '{name}'")
                continue
            cursor.execute(sql_child, {"name": name, "type": ctype, "parent_id": parent_id, "color": color})

    print(f"  [OK] {len(CATEGORIES)} categorías")


def insert_rules(cursor):
    # Obtener IDs de categorías
    cursor.execute("SELECT id, name FROM fin_categories")
    cat_ids = {row[1]: row[0] for row in cursor.fetchall()}

    sql = """
        INSERT INTO fin_import_rules (pattern, match_type, category_id, priority, created_by)
        VALUES (%(pattern)s, %(match_type)s, %(category_id)s, 100, 'system')
        ON DUPLICATE KEY UPDATE
            category_id = VALUES(category_id),
            is_active   = 1
    """
    inserted = 0
    skipped = 0
    for pattern, match_type, cat_name in RULES:
        cat_id = cat_ids.get(cat_name)
        if not cat_id:
            print(f"  [WARN] categoría '{cat_name}' no encontrada para regla '{pattern}'")
            skipped += 1
            continue
        cursor.execute(sql, {"pattern": pattern, "match_type": match_type, "category_id": cat_id})
        inserted += 1

    print(f"  [OK] {inserted} reglas insertadas, {skipped} saltadas")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    print("=" * 60)
    print("Setup módulo Finanzas Personales")
    print("=" * 60)

    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("\n[1] Creando tablas...")
        create_tables(cursor)
        conn.commit()

        print("\n[2] Insertando bancos...")
        insert_banks(cursor)
        conn.commit()

        print("\n[3] Insertando cuentas...")
        bank_ids = get_bank_ids(cursor)
        insert_accounts(cursor, bank_ids)
        conn.commit()

        print("\n[4] Insertando categorías...")
        insert_categories(cursor)
        conn.commit()

        print("\n[5] Insertando reglas de clasificación...")
        insert_rules(cursor)
        conn.commit()

        print("\n" + "=" * 60)
        print("Setup completado exitosamente.")
        print("=" * 60)

        # Resumen
        for tabla in ["fin_banks", "fin_accounts", "fin_categories", "fin_import_rules"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            print(f"  {tabla}: {count} registros")

    except Error as e:
        print(f"\n[ERROR] {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
