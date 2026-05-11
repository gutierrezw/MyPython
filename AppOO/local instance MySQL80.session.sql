-- diaria_cnv: sin cuenta, es global de precios CNV (solo FCI, no afecta stocks)
SELECT table_name,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) AS mb
FROM information_schema.tables
WHERE table_schema = 'bdinv'
ORDER BY table_name;