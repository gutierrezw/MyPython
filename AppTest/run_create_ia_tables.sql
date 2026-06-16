-- ============================================================
-- Fase 1 Agente IA Autónomo — tablas de trazabilidad
-- Ejecutar una sola vez en schema bdinv
-- ============================================================

CREATE TABLE IF NOT EXISTS ia_trace (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    timestamp   DATETIME         DEFAULT CURRENT_TIMESTAMP,
    vehiculo    VARCHAR(20)      NOT NULL,
    simbolo     VARCHAR(20),
    decision    ENUM('BUY','SELL','HOLD','ALERTA') NOT NULL,
    monto       DECIMAL(12,2)    DEFAULT 0,
    motivo      TEXT,
    gates_ok    JSON,
    estado      ENUM('PENDIENTE','APROBADO','IGNORADO','EJECUTADO','FALLIDO') DEFAULT 'PENDIENTE',
    telegram_id VARCHAR(50),
    INDEX idx_timestamp (timestamp),
    INDEX idx_vehiculo_decision (vehiculo, decision),
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ia_mejoras (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    timestamp   DATETIME         DEFAULT CURRENT_TIMESTAMP,
    categoria   ENUM('agente','datos','proceso','decision','ui') NOT NULL,
    titulo      VARCHAR(200)     NOT NULL,
    descripcion TEXT,
    impacto     ENUM('alto','medio','bajo') DEFAULT 'medio',
    estado      ENUM('pendiente','en_revision','adoptado','descartado') DEFAULT 'pendiente',
    origen      VARCHAR(100),
    INDEX idx_estado (estado),
    INDEX idx_categoria (categoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
