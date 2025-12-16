SELECT * FROM bdinv.order_trader
-- where vehiculo = 'Crypto';
where conid = '143628768818544279';

-- Update
update bdinv.order_trader set conid = CONV(substr(SHA2(symbol, 256),1,15), 16, 10)
where account = "B0000001";commit;