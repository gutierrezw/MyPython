-- Verifica que el constraint y la columna intent quedaron correctos en order_trader

-- 1. Definición actual de la columna
SHOW COLUMNS FROM bdinv.order_trader LIKE 'intent';

-- 2. Constraints activos en la tabla
SELECT CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'bdinv'
  AND TABLE_NAME = 'order_trader';

-- 3. Detalle del CHECK constraint
SELECT cc.CONSTRAINT_NAME, cc.CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS cc
JOIN information_schema.TABLE_CONSTRAINTS tc
    ON cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
    AND cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
WHERE tc.TABLE_SCHEMA = 'bdinv'
  AND tc.TABLE_NAME = 'order_trader'
  AND tc.CONSTRAINT_TYPE = 'CHECK';

-- 4. Distribución de valores intent actuales en la tabla
SELECT intent, COUNT(*) AS total
FROM bdinv.order_trader
GROUP BY intent
ORDER BY total DESC;
