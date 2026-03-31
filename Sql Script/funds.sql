SELECT * FROM bdinv.funds
-- where CIK = '0001051470'
;
TRUNCATE TABLE funds;

SELECT id, fund_name, cik FROM funds WHERE fund_name LIKE '%VANGUARD%' LIMIT 10;

SELECT f.fund_name, ff.filing_date, ff.xml_url, ff.xml_local_path
FROM fund_filings ff 
JOIN funds f ON f.fund_id = ff.fund_id 
WHERE f.fund_id = 1
ORDER BY ff.filing_date DESC LIMIT 5;


SELECT 
    digest_text                          AS query,
    count_star                           AS veces_ejecutada,
    ROUND(avg_timer_wait/1000000000, 3)  AS avg_segundos,
    ROUND(max_timer_wait/1000000000, 3)  AS max_segundos,
    sum_no_index_used                    AS sin_indice,
    sum_rows_examined                    AS filas_examinadas,
    sum_rows_sent                        AS filas_retornadas
FROM performance_schema.events_statements_summary_by_digest
WHERE digest_text NOT LIKE '%performance_schema%'
  AND digest_text NOT LIKE '%information_schema%'
  AND sum_no_index_used > 0
ORDER BY sum_rows_examined DESC
LIMIT 20;

