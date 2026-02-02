SELECT * FROM bdinv.order_trader;


SELECT vehiculo, status, count(*) 
FROM bdinv.order_trader
group by vehiculo, status;


-- ALTER TABLE order_trader
-- ADD CONSTRAINT chk_intent
-- CHECK (intent IN ('ENTRY','TP1','TP2','EXIT'));