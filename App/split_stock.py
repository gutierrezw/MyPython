from bd_conect import *

hoy = datetime.now()
position = select_inversion(tipoin='Stock', ticket='all')
for keys in position:
    if keys['tipoinv'] == 'Stock':
        activo = yf.Ticker(keys['ticket'])
        ptrading = select_booktrading(accion='low', account='U4214563', symbol=keys['ticket'])
        if ptrading:
            if not activo.splits.empty:
                print(ticket, activo.splits)
                for date, split in activo.splits.items():
                    fdate = datetime.strptime(date.strftime('%Y-%m-%d %H:%M:%S.%f'), '%Y-%m-%d %H:%M:%S.%f')
                    if ptrading[0]['fechahora'] < fdate:
                        values = dict()
                        values.update({'date': date})
                        values.update({'split': split})
                        # insert_split(symbol=keys['ticket'], values=values)



