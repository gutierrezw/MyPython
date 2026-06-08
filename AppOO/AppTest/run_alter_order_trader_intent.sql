-- Amplía el constraint de intent en order_trader para incluir los nuevos orígenes de orden
-- Ejecutar una sola vez desde MySQL Workbench o CLI

-- Paso 1: verificar si el constraint existe antes de borrarlo
SET @chk_exists = (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = 'bdinv'
      AND TABLE_NAME = 'order_trader'
      AND CONSTRAINT_NAME = 'chk_intent'
      AND CONSTRAINT_TYPE = 'CHECK'
);

SET @sql = IF(@chk_exists > 0,
    'ALTER TABLE bdinv.order_trader DROP CHECK chk_intent',
    'SELECT ''chk_intent no existe, se omite DROP'' AS info'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Paso 2: modificar columna y agregar constraint nuevo
ALTER TABLE bdinv.order_trader
    MODIFY COLUMN intent char(20) DEFAULT NULL
        COMMENT 'ENTRY/TP1/TP2/EXIT=BotCrypto | PRESERV=Preservation | GAINS=GainsCapture | IA_SELL/IA_BUY=Telegram',
    ADD CONSTRAINT chk_intent CHECK (
        intent IN ('ENTRY', 'TP1', 'TP2', 'EXIT', 'PRESERV', 'GAINS', 'IA_SELL', 'IA_BUY', 'MANUAL')
    );
