-- symbol_decision_history: Audit trail de decisiones por símbolo
-- Registra cada evento (CLAUDE, ENVIADA, FILLED, etc) de GainsCapture y Preservation
-- Indexado por symbol para análisis posterior

CREATE TABLE IF NOT EXISTS symbol_decision_history (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  symbol VARCHAR(10) NOT NULL,
  agente ENUM('GainsCapture', 'Preservation') NOT NULL,
  timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  tag ENUM('CLAUDE', 'ATR-CAP', 'ENVIADA', 'MODIFICADA', 'FILLED', 'CANCELLED', 'EXIT') NOT NULL,
  mensaje TEXT,
  json_contexto JSON,
  order_trader_id INT DEFAULT NULL,

  INDEX idx_symbol_timestamp (symbol, timestamp),
  INDEX idx_agente (agente),
  INDEX idx_symbol_agente (symbol, agente),
  INDEX idx_tag (tag),
  INDEX idx_timestamp (timestamp),
  INDEX idx_order_trader_id (order_trader_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
