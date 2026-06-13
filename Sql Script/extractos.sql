SELECT * FROM bdinv.extractos
WHERE idcuenta = 'SANT0001'
-- WHERE idcuenta = 'BBVA0001'
order by extracto DESC;

SELECT idcuenta, DATE_FORMAT(extracto, '%Y-%m') AS mes, navcierre, costobase
FROM extractos
WHERE idcuenta IN ('BBVA0001', 'SANT0001')
  AND extracto >= '2025-10-01'
ORDER BY idcuenta, extracto;
