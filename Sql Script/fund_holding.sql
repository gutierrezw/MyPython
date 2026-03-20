SELECT * 
FROM bdinv.fund_holdings
-- where symbol = "UUUU"
-- WHERE cusip is NULL
-- where  cusip = '0001051470'
;


-- Estadisticas de chequeo por symbol
SELECT symbol, count(*) 
FROM bdinv.fund_holdings
WHERE cusip is NULL
GROUP BY symbol;

-- Estadisticas de chequeo por cusip
SELECT COUNT(*) FROM funds;
SELECT COUNT(*) FROM fund_holdings;

SELECT COUNT(*) FROM funds WHERE cik IS NOT NULL;
SELECT COUNT(DISTINCT fund_id) FROM fund_holdings WHERE cusip IS NOT NULL;
SELECT COUNT(DISTINCT fund_id) FROM fund_holdings WHERE cusip IS NULL;
SELECT COUNT(DISTINCT cusip) FROM fund_holdings WHERE cusip IS NULL;
SELECT COUNT(*) FROM market;
SELECT COUNT(*) FROM market WHERE cusip IS NULL;

-- Distribución actual
SELECT categoriaActivo, COUNT(*) as total, 
       SUM(CASE WHEN encartera = 'Y' THEN 1 ELSE 0 END) as en_cartera
FROM market 
GROUP BY categoriaActivo 
ORDER BY total DESC;

-- Cuántos registros de fund_holdings tienen símbolo en nuestro market
SELECT 
    COUNT(*) AS fh_en_market,
    (SELECT COUNT(*) FROM fund_holdings WHERE cusip IS NOT NULL) AS fh_total
FROM fund_holdings fh
WHERE fh.symbol IN (SELECT symbol FROM market WHERE account = 'U4214563');

-- Cuántos fondos distintos tienen al menos 1 símbolo de nuestro market
SELECT COUNT(DISTINCT fh.fund_id) AS fondos_relevantes
FROM fund_holdings fh
WHERE fh.symbol IN (SELECT symbol FROM market WHERE account = 'U4214563');




