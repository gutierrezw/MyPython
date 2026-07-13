-- Report Center — motor genérico de reportes (ver 20-Proyecto/design-report-center.md)
-- Consumida por MyNode/server-api/lib/ReportManager.js. Primer consumidor: tipo_reporte='schema_health'.

CREATE TABLE IF NOT EXISTS reportes_historial (
    id                    BIGINT AUTO_INCREMENT PRIMARY KEY,
    tipo_reporte          VARCHAR(32) NOT NULL,
    fecha_ejecucion       DATETIME NOT NULL,
    categoria             VARCHAR(32) NOT NULL,
    referencia            VARCHAR(64) NOT NULL,
    tablas_afectadas      VARCHAR(128) NULL,
    reporte               LONGBLOB NOT NULL,
    estado                ENUM('detectado','propuesto','resuelto','descartado') NOT NULL DEFAULT 'detectado',
    propuesta_correccion  TEXT NULL,
    fecha_resolucion      DATETIME NULL,
    INDEX idx_tipo_ref_fecha (tipo_reporte, referencia, fecha_ejecucion)
);
