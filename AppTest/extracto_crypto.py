from Modulos_Mysql import select_booktrading, select_sesion, select_performa_inversion, insert_extracto
from Modulos_python import yf, pd, datetime, timedelta
# from Class_gestion import constuir_extracto_crypto

def construir_extracto(desde=None, hasta=None):

    # información de sesión
    vehiculo = 'Crypto'
    sesion = select_sesion(datetime.now(), accion='select', vehiculo=vehiculo)
    account = sesion['idcuenta']

    if desde is not None:
        # Obtener información de la cartera del booktrading
        book, ix = select_booktrading(accion='desde_hasta',
                                      account=account,
                                      idivisa='USD',
                                      fecha=desde,
                                      hasta=hasta)
    elif desde is None:
        book, ix = select_booktrading(accion='cartera',
                                      account=account,
                                      idivisa='USD')

    # Obtener desempeño del vehículo
    performa, iy = select_performa_inversion(account=account,
                                             vehiculo=vehiculo,
                                             accion='all')

    # dataframe(): para obtener ingresos, costos y comisiones ------------------------------------------------------------
    datos = pd.DataFrame(book, columns=ix)
    datos = datos.drop(columns=['id', 'sec', 'split', 'factor_cambio','updateStamp', 'categoria',
                                'position_inversion', 'idtrans', 'divisa', 'cuenta', 'sell', 'activa',
                                'cantidad', 'simbolo', 'preciocierre', 'preciotrans', 'basico', 'mtmgp', 'stock'])


    # Dataframe() with datos de costo base y value -----------------------------------------------------------------------
    idatos = pd.DataFrame(performa, columns=iy)
    idatos = idatos.drop(columns=['id', 'idcuenta', 'vehiculo', 'referencia','p_referencia', 'p_vehiculo', 'timestamp'])

    idatos['dividendos'] = idatos['dividends']
    idatos['navcierre'] = idatos['value']
    idatos['Date'] = pd.to_datetime(idatos['fechaclose'])

    idatos.set_index('Date', inplace=True)
    idatos = idatos.drop(columns=['fechaclose', 'dividends', 'value'])


    # Seleccionar solo los fines de mes
    idatos.index = pd.to_datetime(idatos.index)
    m_idatos = idatos[idatos.index.is_month_end]

    # cambia formato de index para aparear con los beneficios
    m_idatos.index = pd.to_datetime(m_idatos.index)
    m_idatos.index = m_idatos.index.strftime('%Y-%m')


    # identificar en columnas compras y ventas --------------------------------------------------------------------------
    datos["depositos"] = datos.apply(lambda row: row["producto"] if row["codigo"] == "O" else 0, axis=1)
    datos["retiros"] = datos.apply(lambda row: -row["producto"] if row["codigo"] == "C" else 0, axis=1)
    datos["perdidas"] = datos.apply(lambda row: -row["gprealizadas"] if row["gprealizadas"] < 0 else 0, axis=1)
    datos["crecimiento"] = datos.apply(lambda row: row["gprealizadas"] if row["gprealizadas"] > 0 else 0, axis=1)
    datos["costos"] =  datos["perdidas"] + datos["tarifacomision"]
    datos["beneficios"] = datos["crecimiento"] - datos["costos"]
    datos["comisiones"] = datos["tarifacomision"]
    datos["idevengo"] = .0
    datos["imargen"] = .0
    datos['Date'] = pd.to_datetime(datos['fechahora'])
    datos['tax'] = .0
    datos['fee'] = .0

    # agrupa por meses y suma los valores, cambia formato index para aparear y obtener costo_base mensual
    datos = datos.drop(columns=['fechahora', 'producto', 'tarifacomision'])
    datos.set_index('Date', inplace=True)
    datos.index = pd.to_datetime(datos.index)

    datos.index = datos.index.strftime('%Y-%m')
    m_datos = datos.groupby(datos.index).sum()

    resumen = pd.merge(m_datos, m_idatos, on="Date", how="left")
    resumen = resumen.bfill()
    resumen.index = pd.to_datetime(resumen.index)

    # deja como fin de mes las fechas Dataframe
    resumen.index = resumen.index + pd.offsets.MonthEnd(0)
    print(resumen)

    anterior = .0
    for row in resumen.itertuples():
        values = {'extracto': row.Index.date(),
                  'idcuenta': 'B0000001',
                  'depositos': row.depositos,
                  'retiros': row.retiros,
                  'crecimiento': row.crecimiento,
                  'dividendos': row.dividendos,
                  'perdidas': row.perdidas,
                  'fee': row.fee,
                  'comisiones': row.comisiones,
                  'tax': row.tax,
                  'navcierre': row.navcierre,
                  'cierreanterior': anterior,
                  'costobase': row.costo_base,
                  'idevengo': row.idevengo,
                  'imargen': row.imargen,
                  }
        anterior = row.navcierre

    print('Nro extractos {}'.format(values['extracto']), resumen.shape[0])
    print(values)
        # insert_extracto(account='B0000001', values=values)


if __name__ == '__main__':

    # calcula fecha para creación de extractos
    hoy = datetime.now()
    dias = hoy.day
    fin = hoy - timedelta(days=dias)

    inicio = fin - timedelta(days=365)
    f_desde = inicio.strftime("%Y-%m-%d")
    f_hasta = fin.strftime("%Y-%m-%d")

    print('Procesa desde {} hasta {}'.format(f_desde, f_hasta))
    print('=' * 41)
    # dede, hasta = None, None
    construir_extracto(desde=f_desde, hasta=f_hasta)


