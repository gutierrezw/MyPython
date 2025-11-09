--  select  desc por fecha colocacion 
SELECT * FROM bdinv.order_trader
WHERE date(stampPlace) >= '2025-10-05'
ORDER BY stampPlace DESC;

-- estadisticas por vehiculo
SELECT vehiculo, status, count(*) FROM bdinv.order_trader
GROUP BY vehiculo, status;

-- delete de order
DELETE FROM bdinv.order_trader
WHERE  status = "Inactive";
COMMIT;

-- reordena  tabla id
SELECT count(*) from bdinv.order_trader; 
SET @new_id = 0;
UPDATE bdinv.order_trader 
SET id = (@new_id := @new_id + 1)
ORDER BY id;
ALTER TABLE bdinv.order_trader 
AUTO_INCREMENT = 95;



