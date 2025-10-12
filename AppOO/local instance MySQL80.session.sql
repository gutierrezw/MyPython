SELECT *
FROM bdinv.booktrading
Order by fechahora DESC;
SELECT *
FROM bdinv.diaria_performance
WHERE account = 'U4214563'
order by date DESC;
SELECT *
FROM bdinv.performa_inversion -- WHERE vehiculo = 'Crypto'  
ORDER BY fechaclose DESC;
SELECT *
FROM bdinv.inversion -- WHERE iactiva= 'Y';
WHERE ticket in ('ZILUSDT', 'VETUSDT');
SELECT *
FROM bdinv.extractos;
SELECT *
FROM bdinv.oportunidadesbuysell
WHERE estado = 'pendiente';