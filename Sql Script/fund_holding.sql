SELECT * 
FROM bdinv.fund_holdings
where symbol = "UUUU"
-- WHERE cusip is NULL
;

SELECT f.id, f.fund_name, fh.symbol, fh.shares, fh.operation, fh.report_date
FROM fund_holdings fh
JOIN funds f ON f.id = fh.fund_id
ORDER BY fh.report_date DESC
;

