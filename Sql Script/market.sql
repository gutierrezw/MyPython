SELECT * 
FROM bdinv.market;


select categoriaActivo
FROM bdinv.market
GROUP BY categoriaActivo;





-- Script para agregar nuevos campos de dividendos de IB
ALTER TABLE market 
ADD COLUMN ttmDividends FLOAT AFTER trailingAnnualDividendYield,
ADD COLUMN nextDividend FLOAT AFTER ttmDividends;
