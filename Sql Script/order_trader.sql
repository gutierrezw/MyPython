SELECT * FROM bdinv.order_trader
Where stampPlace > '2026-05-27 00:24:24.747000'
-- and  vehiculo = 'Stock'
;


SELECT vehiculo, date(stampPlace), status 
FROM bdinv.order_trader
group by vehiculo, date(stampPlace), status
;