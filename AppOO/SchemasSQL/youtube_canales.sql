-- Canales de YouTube monitoreados por el Scanner_YouTube
CREATE TABLE IF NOT EXISTS youtube_canales (
    id              INT          NOT NULL AUTO_INCREMENT,
    canal           VARCHAR(60)  NOT NULL,               -- nombre/handle legible
    channel_id      VARCHAR(30)  NOT NULL,               -- UC... (YouTube channel ID)
    url             VARCHAR(120) DEFAULT NULL,            -- https://www.youtube.com/@handle
    active          TINYINT(1)   NOT NULL DEFAULT 1,     -- 1=activo, 0=pausado
    score           TINYINT      NOT NULL DEFAULT 50,    -- 0-100: calidad percibida del canal
    detecciones     INT          NOT NULL DEFAULT 0,     -- acumulado de tickers detectados
    validados       INT          NOT NULL DEFAULT 0,     -- acumulado de tickers validados (en market)
    last_scan       DATETIME     DEFAULT NULL,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_channel_id (channel_id)
);

-- Datos iniciales (score=50 neutro — se ajusta con el uso)
INSERT IGNORE INTO youtube_canales (canal, channel_id, url) VALUES
    ('DanyPerezTrader',   'UCDhxeQwPPUdIdwu0W9ud_Jg', 'https://www.youtube.com/@DanyPerezTrader'),
    ('Invierteygana',     'UC29Uya07F0sVo6j7kKDXJnQ', 'https://www.youtube.com/@Invierteygana'),
    ('MapadeMercados',    'UClAt-9bKF4jyNMU9WmiNpKA', 'https://www.youtube.com/@MapadeMercados'),
    ('elinformek',        'UCJQQVLyM6wtPleV4wFBK06g', 'https://www.youtube.com/@elinformek'),
    ('Renta4BancoESP',    'UCLITO_RoijmgfYWi_kmiONA', 'https://www.youtube.com/@Renta4BancoESP'),
    ('ElClubDeInversion', 'UCtWEGc5ws4HvMvCW-hVY-Gw', 'https://www.youtube.com/@ElClubDeInversion');
