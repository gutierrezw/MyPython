SELECT *  
FROM bdinv.oportunidadesbuysell
WHERE estado = 'pendiente'
-- WHERE estado = 'ejecutada'
-- WHERE estado = 'rechazada'
;


SELECT estado, count(*) 
FROM bdinv.oportunidadesbuysell
group by estado
-- WHERE estado = 'pendiente'
;

-- UPDATE bdinv.oportunidadesbuysell 
-- SET estado = 'ejecutada'
-- WHERE estado = 'ejecutado';commit