-- Active: 1780958678823@@127.0.0.1@3306@bdinv
SELECT * FROM bdinv.order_trader ORDER BY stampPlace DESC;

SELECT *
FROM bdinv.order_trader
WHERE
    orderType = 'STP LMT'
    AND side = 'SELL'
ORDER BY stampPlace DESC;