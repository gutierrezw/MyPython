-- Candidatos detectados por Scanner_YouTube (staging antes de entrar a market)
CREATE TABLE IF NOT EXISTS youtube_candidatos (
    symbol        VARCHAR(10)   NOT NULL,
    company_name  VARCHAR(100)  DEFAULT NULL,
    sector        VARCHAR(60)   DEFAULT NULL,
    website       VARCHAR(200)  DEFAULT NULL,
    apariciones   INT           NOT NULL DEFAULT 1,
    confidence    DECIMAL(3,2)  NOT NULL,
    market_cap    BIGINT        DEFAULT NULL,
    canales       VARCHAR(300)  DEFAULT NULL,    -- canales que lo mencionaron (csv)
    primera_vez   DATE          NOT NULL,
    ultima_vez    DATE          NOT NULL,
    status        VARCHAR(10)   NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    PRIMARY KEY (symbol),
    INDEX idx_status (status),
    INDEX idx_ultima_vez (ultima_vez)
);

-- Agregar columna website si no existe
ALTER TABLE youtube_candidatos ADD COLUMN IF NOT EXISTS website VARCHAR(200) DEFAULT NULL AFTER sector;
