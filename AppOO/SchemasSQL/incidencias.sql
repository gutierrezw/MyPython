CREATE TABLE IF NOT EXISTS incidencias (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    timestamp     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tipo          VARCHAR(50)     NULL,
    msg           TEXT            NOT NULL,
    telegram      TINYINT(1)      NOT NULL DEFAULT 1,
    enviado_tg    TINYINT(1)      NOT NULL DEFAULT 0,
    leida         TINYINT(1)      NOT NULL DEFAULT 0,
    INDEX idx_leida (leida),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
