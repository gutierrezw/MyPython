SELECT * FROM bdinv.otros_activos
where cuenta = "B0000001";

SELECT symbol,  CONV(substr(SHA2(symbol, 256),1,15), 16, 10), SHA2(symbol, 256), SHA2(base_asset, 256)
FROM bdinv.otros_activos
where cuenta = "B0000001";

-- Update
-- update bdinv.otros_activos set idcrypto = CONV(substr(SHA2(symbol, 256),1,15), 16, 10)
-- where cuenta = "B0000001";commit;
