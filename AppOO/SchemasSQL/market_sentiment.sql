-- Lecturas de sentimiento por símbolo (frecuencia horaria)
CREATE TABLE IF NOT EXISTS market_sentiment (
    symbol          VARCHAR(10)  NOT NULL,
    fecha_hora      DATETIME     NOT NULL,
    sentimiento     TINYINT      NOT NULL,        -- -1, 0, +1
    headlines_count TINYINT      DEFAULT 0,       -- calidad: cuántas noticias analizó
    fuente          VARCHAR(10)  DEFAULT 'yahoo', -- 'yahoo' | 'ib'
    PRIMARY KEY (symbol, fecha_hora),
    INDEX idx_symbol_fecha (symbol, fecha_hora)
);

-- Interpretación diaria del patrón histórico por símbolo (Claude)
CREATE TABLE IF NOT EXISTS market_sentiment_analysis (
    symbol          VARCHAR(10)  NOT NULL,
    fecha           DATE         NOT NULL,
    interpretacion  TEXT,
    patron          VARCHAR(20)  DEFAULT 'neutro', -- 'acumulacion' | 'distribucion' | 'neutro' | 'inflexion'
    PRIMARY KEY (symbol, fecha)
);
