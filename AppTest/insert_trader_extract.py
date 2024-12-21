import csv
from operator import itemgetter
from globales import *
from rutinas import *
from bd_conect import *

# entrada = ['U4214563_20200709_20210708.csv', 'U4214563_20210709_20220708.csv',
#           'U4214563_20220709_20230708.csv', 'U4214563_20230709_20240329.csv']
entrada = ['U4214563_20220711_20230707.csv', 'U4214563_20230710_20240419.csv']

l = 0
datos = list()
ix = ['Trades', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency', 'Account', 'Symbol',
      'Date/Time', 'Exchange', 'Quantity', 'T. Prixe', 'C. Prixe', 'Proceeds', 'Comm/Fee', 'Basis',
      'Realized P/L', 'MTM P/L', 'Code']

for i in range(len(entrada)):
    with (open('C:\\Users\\54911\\Downloads\\' + entrada[i], newline='') as csvfile):
        spamreader = csv.reader(csvfile, delimiter=',')
        for row in spamreader:

            if ('Operaciones' in row) and ('Header' in row)  or ('Trades' in row) and ('Header' in row):
                ix = list()
                for i in range(len(row)):
                    ix.append(row[i])
                print(ix)
            """
            if ('Operaciones' in row) and ('Acciones' in row) and ('Orden' in row) or (
                 'Trades' in row) and ('Stocks' in row) and ('Order' in row):

                values = dict()
                values.update({'simbolo': row[ix.index('Symbol')]})
                values.update({'categoria': 'Stock'})
                values.update({'divisa': 'USD'})
                values.update({'cuenta': row[ix.index('Account')]})
                values.update({'fechahora': row[ix.index('Date/Time')]})
                values.update({'idtrans': numero_randon(amplitud=1000000000, fecha=row[ix.index('Date/Time')])})

                stock = Decimal(row[ix.index('Quantity')].replace(',', ''))
                basixo = Decimal(row[ix.index('Basis')]) / stock

                values.update({'preciotrans': Decimal(row[ix.index('T. Price')])})
                values.update({'preciocierre': row[ix.index('C. Price')]})
                values.update({'producto': abs(float(row[ix.index('Proceeds')]))})
                values.update({'tarifacomision': abs(Decimal(row[ix.index('Comm/Fee')]))})

                values.update({'basico': basico})
                values.update({'cantidad': stock})
                values.update({'gprealizadas': row[ix.index('Realized P/L')]})
                values.update({'mtmgp': row[ix.index('MTM P/L')]})
                values.update({'codigo': 'O' if stock > 0 else 'C'})

                datos.append(values)
                l += 1
            """
            if ('Operaciones' in row) and ('Cryptos' in row) and ('Orden' in row) or (
                    'Trades' in row) and ('Crypto' in row) and ('Order' in row):

                print(row)
                values = dict()
                simbolo = row[ix.index('Symbol')].replace('.USD-PAXOS', ' CRYPTO')
                values.update({'simbolo': simbolo})
                values.update({'categoria': 'Stock'})
                values.update({'divisa': 'USD'})
                values.update({'cuenta': 'U4214563'})

                values.update({'fechahora': row[ix.index('Date/Time')]})
                values.update({'idtrans': numero_randon(amplitud=1000000000, fecha=row[ix.index('Date/Time')])})

                stock = Decimal(row[ix.index('Quantity')].replace(',', ''))
                basico = Decimal(row[ix.index('Basis')]) / stock

                values.update({'preciotrans': Decimal(row[ix.index('T. Price')])})
                values.update({'preciocierre': row[ix.index('C. Price')]})
                values.update({'producto': abs(float(row[ix.index('Proceeds')]))})
                values.update({'tarifacomision': abs(Decimal(row[ix.index('Comm/Fee')]))})

                values.update({'basico': basico})
                values.update({'cantidad': stock})
                values.update({'gprealizadas': row[ix.index('Realized P/L')]})
                values.update({'mtmgp': row[ix.index('MTM P/L')]})
                values.update({'codigo': 'O' if stock > 0 else 'C'})

                datos.append(values)
                l += 1

if datos:
    datos_ord = sorted(datos, key=itemgetter('cuenta', 'simbolo', 'fechahora', ))
    print('reg=', l)
    print(len(datos_ord))

    for i in range(l):
        key = datos_ord[i]
        simbolo = key['simbolo']

        values = key.pop('simbolo')
        print(simbolo, key['fechahora'], key)
        insert_booktrading(values=key, symbol=simbolo)
