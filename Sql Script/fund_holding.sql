SELECT * 
FROM bdinv.fund_holdings
where symbol = "CCI"
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
SELECT COUNT(DISTINCT fund_id) FROM fund_holdings WHERE cusip IS NOT NULL;
SELECT COUNT(DISTINCT fund_id) FROM fund_holdings WHERE cusip IS NULL;




