-- Agregar json_audit_log a order_trader para audit trail completo
-- Fase 1: Logging GainsCapture + Preservation

ALTER TABLE order_trader
ADD COLUMN json_audit_log JSON DEFAULT NULL AFTER json_detalle;

-- Verificar que se agregó
SHOW COLUMNS FROM order_trader WHERE Field = 'json_audit_log';
