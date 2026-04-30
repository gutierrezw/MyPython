-- Agrega columna fecha_deliste a booktrading
-- Representa la fecha en que el activo dejó de cotizar (quiebra, fusión, OTC detenida)
-- detalle_book procesa hasta esa fecha y luego registra value=0 (pérdida total)
-- NULL = sin fecha conocida → comportamiento actual (skip si delisted=1)

ALTER TABLE booktrading
    ADD COLUMN fecha_deliste DATE NULL AFTER delisted;
