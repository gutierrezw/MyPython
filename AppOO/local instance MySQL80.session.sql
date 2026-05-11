UPDATE extractos e
    INNER JOIN (
        SELECT p.idcuenta,
            DATE_FORMAT(p.fechaclose, '%Y-%m') AS mes,
            p.value AS nav,
            p.costo_base
        FROM performa_inversion p
            INNER JOIN (
                SELECT idcuenta,
                    DATE_FORMAT(fechaclose, '%Y-%m') AS mes,
                    MAX(fechaclose) AS ultima
                FROM performa_inversion
                WHERE idcuenta IN ('BBVA0001', 'SANT0001')
                    AND vehiculo = 'BBVA.ARS'
                GROUP BY idcuenta,
                    DATE_FORMAT(fechaclose, '%Y-%m')
            ) ult ON p.idcuenta = ult.idcuenta
            AND DATE_FORMAT(p.fechaclose, '%Y-%m') = ult.mes
            AND p.fechaclose = ult.ultima
        WHERE p.vehiculo = 'BBVA.ARS'
    ) src ON e.idcuenta = src.idcuenta
    AND DATE_FORMAT(e.extracto, '%Y-%m') = src.mes
SET e.navcierre = src.nav,
    e.costobase = src.costo_base
WHERE e.idcuenta IN ('BBVA0001', 'SANT0001');
commit;