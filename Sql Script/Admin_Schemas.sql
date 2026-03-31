-- l estado completo de todas las tablas
SELECT 
    t.TABLE_NAME,
    t.TABLE_ROWS                      AS filas,
    COUNT(s.INDEX_NAME)               AS indices_secundarios
FROM information_schema.TABLES t
LEFT JOIN information_schema.STATISTICS s 
    ON t.TABLE_SCHEMA = s.TABLE_SCHEMA 
    AND t.TABLE_NAME  = s.TABLE_NAME
    AND s.INDEX_NAME != 'PRIMARY'
    AND s.SEQ_IN_INDEX = 1
WHERE t.TABLE_SCHEMA = 'bdinv'
    AND t.TABLE_TYPE = 'BASE TABLE'
GROUP BY t.TABLE_NAME, t.TABLE_ROWS
ORDER BY t.TABLE_ROWS DESC;

-- Para saber qué índices necesita, ejecuta esto — muestra cómo se está consultando ahora mismo:
SELECT 
    digest_text                         AS query,
    count_star                          AS veces,
    ROUND(avg_timer_wait/1000000000, 3) AS avg_seg,
    sum_rows_examined                   AS filas_examinadas,
    sum_rows_sent                       AS filas_retornadas
FROM performance_schema.events_statements_summary_by_digest
WHERE digest_text LIKE '%fund_holdings%'
ORDER BY sum_rows_examined DESC
LIMIT 10;



-- ¿Filtras por fondo específico?
SELECT * FROM fund_holdings WHERE fund_id = 101;

-- ¿Por fecha de reporte?
SELECT * FROM fund_holdings WHERE report_date = '2025-12-31';

-- ¿Buscas posiciones de un instrumento específico?
SELECT * FROM fund_holdings WHERE cusip = '17275R102';

-- ¿Combinas filtros?
SELECT * FROM fund_holdings WHERE fund_id = 1 AND report_date > '2026-01-01'