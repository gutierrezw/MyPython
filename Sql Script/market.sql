SELECT * 
FROM bdinv.market
where categoriaActivo in ('I', 'S', 'X')
and  encartera = 'Y';