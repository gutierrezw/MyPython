SELECT * FROM bdinv.diaria_cnv
-- where codCAFCI in (148,814,51)
order by fecha DESC
;


SELECT fecha, count(*) FROM bdinv.diaria_cnv
-- where codCAFCI in (148,814,51)
group by fecha
order by fecha DESC