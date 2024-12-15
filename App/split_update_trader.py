from bd_conect import *


datos = list()
split, ix = select_split(symbol='all')
print(split)
print('===========================')

for keys in split:

    values, campos = list(), list()
    trade, ib = select_booktrading(accion='select*', account='U4214563', idivisa='USD', symbol=keys[ix.index('ticket')])
    for book in trade:
        if book[ib.index('fechahora')] <= keys[ix.index('date')]:

            fsplit = keys[ix.index('split')]
            if keys[ix.index('preciocantidad')] == 'P':
                pass

            if keys[ix.index('preciocantidad')] == 'A':
                values.append(book[ib.index('preciotrans')] / fsplit)
                values.append(book[ib.index('preciocierre')] / fsplit)
                values.append(book[ib.index('basico')] / fsplit)
                values.append(book[ib.index('cantidad')] * fsplit)
                values.append(book[ib.index('stock')] * fsplit)

                campos.append('preciotrans')
                campos.append('preciocierre')
                campos.append('basico')
                campos.append('cantidad')
                campos.append('stock')

    print(keys[ix.index('ticket')], values, campos)
    print(keys)
