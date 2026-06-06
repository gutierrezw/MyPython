SELECT * FROM bdinv.order_trader
ORDER BY stampPlace DESC
;

SELECT *
FROM bdinv.order_trader 
WHERE orderType = 'STP LMT' AND side = 'SELL'
ORDER BY stampPlace DESC;

