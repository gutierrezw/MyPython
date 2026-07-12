-- ============================================================
-- ib_flex_trades — trades descargados via IB Flex Query API
-- Fuente: reporte Flex con campos: ClientAccountID, Symbol,
--         CurrencyPrimary, DateTime, Quantity, TradePrice,
--         IBCommission, TransactionID, etc.
--
-- transaction_id es la clave de dedup (único por ejecución en IB).
-- Úsese para reconciliar con booktrading vía idtrans.
-- ============================================================

CREATE TABLE IF NOT EXISTS `ib_flex_trades` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT,

    -- Identificación
    `transaction_id`    BIGINT          NOT NULL,               -- TransactionID (IB execution_id)
    `account_id`        VARCHAR(20)     NOT NULL,               -- ClientAccountID  (ej: U4214563)
    `symbol`            VARCHAR(20)     NOT NULL,               -- Symbol
    `currency`          VARCHAR(10)     NOT NULL,               -- CurrencyPrimary
    `conid`             BIGINT          DEFAULT NULL,           -- IB Contract ID
    `description`       VARCHAR(150)    DEFAULT NULL,           -- Description

    -- Fechas
    `trade_datetime`    DATETIME        NOT NULL,               -- DateTime  (YYYYMMDD;HHmmss → DATETIME)
    `trade_date`        DATE            NOT NULL,               -- TradeDate (YYYYMMDD → DATE)

    -- Precio y cantidad
    `quantity`          DECIMAL(14, 4)  NOT NULL,               -- Quantity (neg = SELL)
    `price`             DECIMAL(14, 6)  NOT NULL,               -- TradePrice
    `trade_money`       DECIMAL(16, 4)  DEFAULT NULL,           -- TradeMoney  (valor bruto)
    `proceeds`          DECIMAL(16, 4)  DEFAULT NULL,           -- Proceeds    (neg en compras)

    -- Costos
    `taxes`             DECIMAL(12, 4)  DEFAULT 0,              -- Taxes
    `commission`        DECIMAL(12, 6)  DEFAULT 0,              -- IBCommission (guardado positivo)
    `cost_basis`        DECIMAL(16, 4)  DEFAULT NULL,           -- CostBasis

    -- Precios de cierre y P&L
    `close_price`       DECIMAL(14, 6)  DEFAULT NULL,           -- ClosePrice
    `mtm_pnl`           DECIMAL(14, 4)  DEFAULT NULL,           -- MtmPnl
    `realized_pnl`      DECIMAL(14, 4)  DEFAULT NULL,           -- FifoPnlRealized
    `capital_gains_pnl` DECIMAL(14, 4)  DEFAULT NULL,           -- CapitalGainsPnl
    `fx_pnl`            DECIMAL(14, 4)  DEFAULT NULL,           -- FxPnl

    -- FX
    `fx_rate`           DECIMAL(12, 6)  DEFAULT NULL,           -- FXRateToBase

    -- Clasificación
    `buy_sell`          ENUM('BUY','SELL') NOT NULL,            -- Buy/Sell
    `transaction_type`  VARCHAR(30)     DEFAULT NULL,           -- TransactionType (ej: ExchTrade)
    `order_id`          VARCHAR(60)     DEFAULT NULL,           -- BrokerageOrderID
    `order_reference`   VARCHAR(100)    DEFAULT NULL,           -- OrderReference

    -- Auditoría
    `import_stamp`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (`id`),
    UNIQUE  KEY `uq_transaction_id`         (`transaction_id`),
    INDEX   `idx_account_symbol_date`       (`account_id`, `symbol`, `trade_date`),
    INDEX   `idx_account_currency_symbol`   (`account_id`, `currency`, `symbol`),
    INDEX   `idx_trade_date`                (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
