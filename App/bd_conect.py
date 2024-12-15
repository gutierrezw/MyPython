import numpy as np
from pymysql import connect

from globales import *
from rutinas import *


def connect_dbase(tabla, display=False) -> object:
    conn = None
    try:
        conn = connect(host="localhost", user="root", password="Daga2004", database="bdinv")
        if display:
            print("[Messg]: connect a Mysql: " + tabla)

    except connect.Error as e:
        print("[MySql:: connect_dbase()] ", e)

    return conn


def select_sesion(fecha, orden='{"RetS": "ASC"}', accion=False, invertir=0, filtro=None, vehiculo='Stock') -> dict:
    """
    @param fecha:
    @param orden:
    @param accion:
    @param invertir:
    @param filtro:
    @param vehiculo:
    @return:
    """

    sql = "SELECT * FROM sesion  WHERE vehiculo='%s'"
    conn = connect_dbase("select.sesion", False)
    try:
        cursor = conn.cursor()
        cursor.execute(sql % vehiculo)
        qry = cursor.fetchone()
        ix = [columna[0] for columna in cursor.description]

        fesesion = qry[ix.index('fesesion')]
        or_cartera = qry[ix.index('orcartera')]
        pinvertir = qry[ix.index('Pinvertir')]
        xstrategy = qry[ix.index('xstrategy')]


        sesion = dict.fromkeys(ix, 0)
        sesion['fefund'] = qry[ix.index('fefund')]

        if accion == 'update':
            upd = """UPDATE sesion SET fesesion='%s', orcartera='%s' WHERE vehiculo='%s';"""
            fesesion = fecha
            conn = connect_dbase("Sesion.Update", False)
            cursor = conn.cursor()
            cursor.execute(upd % (fesesion, orden, vehiculo))
            conn.commit()

            sesion['fectime'] = fesesion
            sesion['fesesion'] = fesesion
            sesion['orcartera'] = orden
            sesion['Pinvertir'] = invertir

        if accion == 'select':
            sesion['fectime'] = fecha
            sesion['fesesion'] = fesesion
            sesion['orcartera'] = or_cartera
            sesion['Pinvertir'] = pinvertir
            sesion['xstrategy'] = xstrategy

        if accion == 'updateFun':
            upd = """UPDATE sesion SET fechaFund='%s' WHERE vehiculo='%s';"""
            sesion['fefund'] = fecha
            conn = connect_dbase("Fe.fundamental.Update", False)
            cursor = conn.cursor()
            cursor.execute(upd % (fecha, vehiculo))
            conn.commit()

        if accion == 'updatexstrategy':
            if filtro:
                upd = """UPDATE sesion SET xstrategy='%s' WHERE vehiculo='%s';"""
                sesion['xstrategy'] = filtro
                conn = connect_dbase("Strategy.Update", False)
                cursor = conn.cursor()
                cursor.execute(upd % (filtro, vehiculo))
                conn.commit()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_sesion()]: {}".format(error))

    cursor.close()
    sesion['id'] = qry[ix.index('id')]
    sesion['iduser'] = qry[ix.index('iduser')]
    sesion['idcuenta'] = qry[ix.index('idcuenta')]
    sesion['userapi'] = qry[ix.index('userapi')]
    sesion['userpass'] = qry[ix.index('userpass')]
    sesion['vehiculo'] = qry[ix.index('vehiculo')]
    sesion['Pinvertir'] = qry[ix.index('Pinvertir')]
    sesion['fiscalYear'] = qry[ix.index('fiscalYear')]

    return sesion


def update_washlist(cursor=None, upd=None, val=None, ticket=None):
    """
    @param cursor:  washlist cursor donde es llamada la rutina
    @param upd:  list() de campos para actualizar en washlist
    @param val:  list() de valores que acompañan a upd
    @param ticket: symbol o ticket que se actualiza en washlist
    @return:  Actualiza fila a partir de symbol y campos pasados como parameter
    """
    qry = "UPDATE washList SET "
    listvalues = list()
    try:
        for i in range(len(val)):
            if not is_numeric(val[i]):
                if upd[i] in ('last', 'low', 'high', 'open', 'change'):
                    val[i] = "0" if is_null(val[i]) else val[i]
                    listvalues.append(float(val[i].replace("C", "0")))
                else:
                    if upd[i] == 'exdiv':
                        string = val[i]
                        listvalues.append(string.replace("'", "-"))
                    else:
                        listvalues.append(val[i])
            else:
                listvalues.append(val[i])                         # cambio de nombre por ser palabras reservadas
            upd[i] = "pchange" if upd[i] == 'change' else upd[i]  # Mysql
            upd[i] = "pdiv" if upd[i] == 'div' else upd[i]

            qry = qry + upd[i] + "='%s', "

        listvalues.append(ticket)
        valuesupd = tuple(listvalues)
        qry = qry + "WHERE ticket='%s';"
        qry = qry.replace(", WHERE", " WHERE")
        cursor.execute(qry % valuesupd)

    except Exception as error:
        print("[Mysql::  update_washlist()]: {}".format(error))


def insert_washlist(cursor=None, upd=None, val=None, ticket=None):
    """
    @param cursor:  washlist cursor donde es llamada la rutina
    @param upd:  list() de campos para insertar en washlist
    @param val:  list() de valores que acompañan a upd
    @param ticket: symbol o ticket que se inserta en washlist
    @return:  Agrega fila a partir de symbol y campos pasados como parameter
    """

    listvalues = list()
    cursor.execute("SELECT MAX(id) FROM washList")
    row = cursor.fetchone()
    listvalues.append(row[0] + 1)

    qry = "INSERT INTO washList (id, "

    for i in range(len(val)):
        if not is_numeric(val[i]):
            if upd[i] == 'last':
                listvalues.append(float(val[i].replace("C", "0")))
            else:
                if upd[i] == 'exdiv':
                    string = val[i]
                    listvalues.append(string.replace("'", "-"))
                else:
                    listvalues.append(val[i])
        else:
            listvalues.append(val[i])

        upd[i] = "pchange" if upd[i] == 'change' else upd[i]
        upd[i] = "pdiv" if upd[i] == 'div' else upd[i]

        qry = qry + upd[i] + ", "

    listvalues.append(ticket)
    valuesins = tuple(listvalues)
    qry = qry + "ticket) VALUES ({});".format(",".join('%s' for _ in range(len(valuesins))))
    cursor.execute(qry, valuesins)


def select_washlist(display=False) -> list:
    conn = connect_dbase("select.washList", display)
    cursor = conn.cursor()

    datos = list()
    cursor.execute("SELECT * FROM washList;")
    qry = cursor.fetchall()

    ix = [column[0] for column in cursor.description]
    for row in qry:
        keys = {}

        for i in range(1, len(ix)):
            if is_none(row[i]):
                keys[ix[i]] = ' '
            else:
                if is_numeric(row[i]) and ix[i] != 'conid':
                    keys[ix[i]] = float(row[i])
                else:
                    keys[ix[i]] = row[i]
        datos.append(keys)

    return datos


def update_datos_mkt(mkt_aper, fieldx) -> dict:
    """
    @param mkt_aper:
    @param fieldx:
    @return:
    """
    conn = connect_dbase("update.washList", False)
    cursor = conn.cursor()
    try:
        pass
    except conn.ProgrammingError as error:
        print("[Mysql::  update_datos_mkt()]: {}".format(error))
    """
    campos que vienen de la API
    fieldx = {'last': '31', 'high': '70',
              'low': '71', 'change': '82',
              'hw52': '7293', 'lw52': '7294',
              'open': '7295', 'close': '7296',
              'div': '7286', 'Yieldp': '7287',
              'exdiv': '7288', 'dvttm': '7672'}
    """
    ix = list(fieldx.keys())
    for i in range(len(ix)):
        fieldx.update({fieldx[ix[i]]: ix[i]})  # campos de API en formato dict
    """
        elimina los campos que no van whaslist
    """
    fieldx.pop("conidEx")
    fieldx.pop("ticker")
    fieldx.pop("ticket")

    for keys in range(len(mkt_aper)):
        linea = mkt_aper[keys]
        val = list()
        upd = list()
        for j in linea:
            if j in fieldx:
                if not is_numeric(fieldx[j]):
                    if not is_none(linea[j]):
                        if is_numeric(linea[j]):
                            val.append(float(linea[j]))
                        else:
                            val.append(linea[j])

                        upd.append(fieldx[j])

        sql = "SELECT count(*) FROM (SELECT ticket  washList  WHERE ticket ='%s');"
        print(sql % (linea['ticket']))
        cursor.execute(sql % (linea['ticket']))
        found = cursor.fetchone()[0]
        if found:
            update_washlist(cursor, upd, val, linea['ticket'])
            conn.commit()
        else:
            insert_washlist(cursor, upd, val, linea['ticket'])
            conn.commit()

    cursor.close()
    conn.close()

    datos = select_washlist(display=False)
    return datos


def read_estrategia() -> dict:
    """

    @return: construye estructura con a partir JOIN entre inversion y estrategia
    """

    conn = connect_dbase("select.estrategia", False)
    cursor = conn.cursor()
    sql = '''SELECT a.*, b.descripcion, b.vehiculo FROM (SELECT * FROM inversion WHERE iactiva = 'Y') a 
             LEFT JOIN  estrategia b ON a.estrategia = b.estrategia  ORDER BY a.estrategia;'''

    cursor.execute(sql)
    ixx = [column[0] for column in cursor.description]
    xcur = cursor.fetchall()
    yestrategia = dict()
    if xcur:
        xrow = xcur[0][ixx.index('estrategia')]
        vehi = xcur[0][ixx.index('vehiculo')]
        xlis = list()
        i = 1

        for i in range(len(xcur)):
            if xrow != xcur[i][ixx.index('estrategia')]:
                yestrategia[xrow] = {vehi: {xcur[i-1][ixx.index('descripcion')]: xlis}}
                xrow = xcur[i][ixx.index('estrategia')]
                vehi = xcur[i][ixx.index('vehiculo')]
                xlis = list()

            xlis.append({xcur[i][ixx.index('ticket')]: xcur[i][ixx.index('costobase')],
                                              'Peso': xcur[i][ixx.index('peso')],
                                         'Dividendo': xcur[i][ixx.index('dividendo')],
                                          'Objetivo': xcur[i][ixx.index('objetivo')],
                                           'Empresa': xcur[i][ixx.index('empresa')],
                                        'Estrategia': xcur[i][ixx.index('estrategia')]})

        yestrategia[xrow] = {vehi: {xcur[i-1][ixx.index('descripcion')]: xlis}}

    cursor.close()
    conn.close()
    return yestrategia


def select_estrategia(accion, ticket=None, ivehiculo=None) -> list:
    """
    @param accion:  que es solicitado a la función: Delete, Estrategia, Tabla, Select
    @param ticket:   nombre del symbol
    @param ivehiculo: tipo de inversión
    @return: lista de registros de la tabla estrategia JOIN inversión
    """
    conn = connect_dbase("select.inversion")
    cursor = conn.cursor()
    qry, sql = None, None
    xlis = list()

    try:
        if accion == 'detalle':
            qry = '''SELECT * FROM inversion WHERE iactiva="Y" ORDER BY ticket'''

        if accion == 'estrategia':
            qry = '''SELECT a.*, b.descripcion FROM (SELECT DISTINCT estrategia 
                                                     FROM bdinv.inversion where iactiva = 'Y')
                            a JOIN  (SELECT * FROM estrategia WHERE vehiculo = '{}') b 
                            ON a.estrategia = b.estrategia;'''.format(ivehiculo)

        if accion == 'tabla':
            qry = '''SELECT * FROM estrategia ORDER BY estrategia'''

        if accion == 'Select':
            qry = "SELECT objetivo FROM inversion  WHERE ticket ='%s';" % ticket

        cursor.execute(qry)
        sql = cursor.fetchall()

    except conn.ProgrammingError as error:
        print("[Mysql error]: {}".format(error))

    if sql:
        if accion == 'detalle':
            columnas = [columna[0] for columna in cursor.description]
            for fila in sql:
                x = dict(zip(columnas, fila))
                xlis.append(x)

        if accion == 'tabla':
            columnas = [columna[0] for columna in cursor.description]
            for fila in sql:
                x = dict(zip(columnas, fila))
                xlis.append(x)

        if accion == 'estrategia':
            columnas = [columna[0] for columna in cursor.description]
            for fila in sql:
                xlis.append(fila[0] + ' - ' + fila[1])

        if accion == 'Select':
            columnas = [columna[0] for columna in cursor.description]
            for fila in sql:
                x = dict(zip(columnas, fila))
                xlis.append(x)

    return xlis


def select_inversion(tipoin: str = 'Stock', ticket='all') -> list:
    """
    @param tipoin:  se indica el tipo de activo
    @param ticket:  simbolo especifico a consultar
    @return: Lista de activos de la cartera asociada al tipoin, incluye el last - precio
    """
    conn = connect_dbase("select.inversion", False)
    cursor = conn.cursor()
    qry, sql = None, None
    xlis, curs = list(), list()
    try:
        if ticket == 'all':
            # GWI001
            # qry = """SELECT a.*, b.pchange, b.conid, b.estrategia, a.unrealizedpnl, a.deuda,
            #      b.last * a.position as mktValue, b.last as mktPrice, b.targetprice, b.hw52
            #         FROM inversion a, washlist b
            #         WHERE a.tipoinv ='%s'
            #         AND   a.iactiva = '%s'
            #         AND   b.ticket = a.ticket;"""
            qry = """SELECT  a.*, b.pchange, b.conid, b.estrategia, b.last * a.position as mktValue, b.open,
                             b.last as mktPrice, b.targetprice, b.hw52 FROM (SELECT * FROM inversion 
                                                                              WHERE tipoinv ='%s' 
                                                                              AND   iactiva = '%s') AS a, washlist b  
                       WHERE b.ticket = a.ticket;"""
            cursor.execute(qry % (tipoin, 'Y'))
            curs = cursor.fetchall()

        if ticket == 'hist':
            # GWI001
            #  qry = """SELECT a.*, b.pchange, b.conid, b.estrategia, a.unrealizedpnl, a.deuda,
            #  b.last * a.position as mktValue, b.last as mktPrice
            #  FROM inversion a, washlist b  WHERE b.ticket = a.ticket AND a.tipoinv='%s';"""
            qry = """SELECT  a.*, b.pchange, b.conid, b.estrategia, b.last * a.position as mktValue, b.open,
                             b.last as mktPrice, b.targetprice, b.hw52 FROM (SELECT * FROM inversion 
                                                                              WHERE tipoinv ='%s') AS a, washlist b  
                       WHERE b.ticket = a.ticket;"""
            cursor.execute(qry % tipoin)
            curs = cursor.fetchall()

        if ticket not in ('all', 'hist'):
            # GWI001
            # qry = """SELECT a.*, b.pchange, b.conid, b.estrategia, a.unrealizedpnl, a.deuda,
            #      b.last * a.position as mktValue, b.last as mktPrice
            #         FROM inversion a, washlist b
            #         WHERE a.tipoinv ='%s'
            #         AND   a.iactiva = '%s'
            #         AND   a.ticket = '%s'
            #         AND   b.ticket = a.ticket;"""
            qry = """SELECT  a.*, b.pchange, b.conid, b.estrategia, b.last * a.position as mktValue, b.open, 
                             b.last as mktPrice, b.targetprice, b.hw52 FROM (SELECT * FROM inversion 
                                                                              WHERE tipoinv ='%s' AND iactiva = '%s'
                                                                                AND ticket = '%s') AS a, washlist b  
                       WHERE b.ticket = a.ticket;"""

            cursor.execute(qry % (tipoin, 'Y', ticket))
            curs = cursor.fetchone()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_inversion()]: {}".format(error))

    ix = [column[0] for column in cursor.description]
    if curs:
        if ticket in ('all', 'hist'):
            for row in curs:
                x = dict(zip(ix, row))
                xlis.append(x)
        else:
            xlis.append(dict(zip(ix, curs)))

    cursor.close()
    conn.close()
    return xlis


def update_inversion(positions=None, tipo='Stock', account='U4214563'):
    """
    @param positions: cartera activa que se actualiza en inversiones
    @param tipo:  tipo de cartera "Stock", "Crypto"
    @param account:
    @return: actualiza lo que hay positions en inversiones
    """
    def update(keys, values):

        qry = """UPDATE inversion  SET estrategia = '%s',  empresa = '%s', position = '%s', peso = '%s',   
                            costobase = '%s', dividendo = '%s', objetivo = '%s', retorno = '%s',
                            unrealizedpnl = '%s', deuda = '%s',  mrkprice = '%s', iactiva = '%s', sector = '%s'
                            WHERE ticket ='%s' AND   useraccount ='%s';"""

        xlistvalues.append(keys['estrategia'])
        xlistvalues.append(keys['empresa'])
        xlistvalues.append(keys['position'])
        xlistvalues.append(keys['Peso'])
        xlistvalues.append(keys['CosS'])
        xlistvalues.append(found[ix.index('dividendo')] * keys['position'])
        xlistvalues.append(keys['Obje'])
        xlistvalues.append(keys['RetS'])
        xlistvalues.append(keys['unrealizedpnl'])
        xlistvalues.append(keys['deuda'])
        xlistvalues.append(keys['mrkprice'])
        xlistvalues.append('Y')
        xlistvalues.append(keys['sector'])

        xlistvalues.append(values[0])
        xlistvalues.append(values[1])
        valuesupd = tuple(xlistvalues)
        cursor.execute(qry % valuesupd)

    def insert(keys, values):
        fectime = datetime.now()
        qry = """INSERT INTO inversion (ticket, iactiva, fealta, febaja, estrategia, empresa, costobase, 
                                                   mrkprice, sector, tipoinv, useraccount)"""

        ylistvalues = list()
        ylistvalues.append(values[0])
        for i in range(len(xlistvalues)):
            ylistvalues.append(xlistvalues[i])

        ylistvalues.append('Y')
        ylistvalues.append(fectime)
        ylistvalues.append(baja)
        ylistvalues.append(keys['estrategia'])
        ylistvalues.append(keys['empresa'])
        ylistvalues.append(keys['CosS'])
        ylistvalues.append(keys['mrkprice'])
        ylistvalues.append(keys['sector'])
        ylistvalues.append(tipo)
        ylistvalues.append(account)

        valuesins = tuple(ylistvalues)
        qry = qry + " VALUES ({});".format(",".join('%s' for _ in range(len(ylistvalues))))
        cursor.execute(qry, valuesins)


    conn = connect_dbase("update.inversion", False)
    cursor = conn.cursor()
    baja = "9999-12-31"
    qry, sql = None, None
    try:
        # GWI001
        # sql = """SELECT a.objetivo, b.dvttm as dividendo FROM inversion a, washlist b
        #         WHERE a.ticket ='%s' AND a.useraccount ='%s'
        #         AND   b.ticket = a.ticket;"""
        sql = """SELECT a.objetivo, b.dvttm as dividendo, a.ticket
                   FROM (SELECT ticket, objetivo FROM inversion  
                          WHERE ticket ='%s' AND useraccount ='%s') AS a, washlist b WHERE b.ticket = '%s';"""

    except conn.ProgrammingError as error:
        print("[Mysql:: update_inversion()]: {}".format(error))

    for keys in positions:
        xlistvalues = list()
        values = (keys['ticket'].strip(), account, keys['ticket'].strip())
        cursor.execute(sql % values)
        found = cursor.fetchone()
        ix = [column[0] for column in cursor.description]

        if found:
            update(keys, values)
        else:
            insert(keys, values)

        conn.commit()
    """
    @ realiza baja de tickets de inversión que no estan positions
    """
    qry = """SELECT a.* FROM (SELECT * FROM inversion  WHERE tipoinv = '%s') a, estrategia b
             WHERE b.estrategia = a.estrategia"""
    cursor.execute(qry % tipo)
    curs = cursor.fetchall()

    if curs:
        ix = [column[0] for column in cursor.description]
        for row in curs:
            itrue, keys = buscar_ticker(positions, row[ix.index('ticket')])
            if not itrue and (row[ix.index('iactiva')] != 'N'):
                fectime = datetime.now()
                xlistvalues = list()
                xlistvalues.append(fectime)
                xlistvalues.append('N')
                xlistvalues.append(row[ix.index('ticket')])
                valuesupd = tuple(xlistvalues)

                qry = "UPDATE inversion  SET febaja ='%s', iactiva = '%s' WHERE ticket = '%s';"
                cursor.execute(qry % valuesupd)
                conn.commit()

    cursor.close()
    conn.close()


def delete_inversion(ticket=None, account='U4214563'):
    """
    @param ticket: simbolo a eliminar de cartera de inversión
    @param account:
    @return: elimina registro de la tabla inversión
    """

    conn = connect_dbase("delete.inversion", False)
    cursor = conn.cursor()
    qry = None
    try:
        qry = """DELETE FROM inversion WHERE ticket ='%s' AND useraccount ='%s';"""
        print(qry % (ticket, account))
        cursor.execute(qry % (ticket, account))
        conn.commit()
        cursor.close()
        conn.close()

    except conn.ProgrammingError as error:
        print("[Mysql:: delete_inversion()]: {}".format(error))


def select_plan(idcuenta) -> dict:
    """
    @param idcuenta: cuenta ID de inversor
    @return: estructura de plan de inversiones
    """
    conn = connect_dbase("select.plan")
    cursor = conn.cursor()
    try:
        qry = """SELECT * from plan WHERE idcuenta = '%s';"""
        cursor.execute(qry % idcuenta)

    except conn.ProgrammingError as error:
        print("[Mysql:: select_plan()]: {}".format(error))

    sql = cursor.fetchall()
    xlis = list()

    if sql:
        columnas = [columna[0] for columna in cursor.description]
        for fila in sql:
            x = dict(zip(columnas, fila))
            xlis.append(x)
    return xlis


def select_trazaplan(idcuenta, orden='ASC') -> dict:
    """
    @param idcuenta:   cuenta ID de inversor
    @param orden:   ordenamiento de la salida
    @return:  registros trazaplan ejecutados y actual
    """
    conn = connect_dbase("select.plan")
    cursor = conn.cursor()
    try:
        qry = """SELECT * FROM (SELECT * from trazaplan WHERE idcuenta = '%s') AS a
                 ORDER BY a.meta %s;"""
        cursor.execute(qry % (idcuenta, orden))

    except conn.ProgrammingError as error:
        print("[Mysql:: select_trazaplan()]: {}".format(error))

    sql = cursor.fetchall()

    xlis = list()

    if sql:
        columnas = [columna[0] for columna in cursor.description]
        for fila in sql:
            x = dict(zip(columnas, fila))
            xlis.append(x)
    return xlis


def update_trazaplan(idcuenta=None, costobase=0, inversion=0, div=0, rend=0, crec=0, condicion=None):
    """
    @param idcuenta:  cuenta ID de inversor
    @param costobase:  Total inversion
    @param inversion:  valor de mercado de la inversion
    @param div:  Total dividendo o ingresos pasivos al año
    @param rend:  Total rendimiento de la inversión
    @param crec:  Total crecimiento de capital
    @param condicion: en que se encuentra la meta:: (Ejecución, Cumplido)
    @return:
    """
    conn = connect_dbase("select.trazaplan")
    cursor = conn.cursor()
    qry = """SELECT meta, vision FROM bdinv.trazaplan WHERE idcuenta = '%s' and status = 'Ejecucion';"""
    try:
        pass
    except conn.ProgrammingError as error:
        print("[Mysql:: update_trazaplan()]: {}".format(error))

    cursor.execute(qry % idcuenta)
    sql = cursor.fetchall()

    if sql:
        ix = [columna[0] for columna in cursor.description]
        smeta = sql[0][ix.index('meta')]
        svisi = sql[0][ix.index('vision')]
        sefec = (costobase - svisi) / svisi

        conn = connect_dbase("update.trazaplan")
        cursor = conn.cursor()

        qry = """UPDATE trazaplan SET costobase = '%s', efectividad = '%s', tinversion = '%s', 
                 status = '%s', dividendo='%s', trendimiento='%s', ccapital='%s'
                 WHERE idcuenta = '%s' AND meta = '%s' ;"""

        valuesupd = tuple([costobase, sefec, inversion, 'Ejecucion', div, rend, crec, idcuenta, smeta])
        cursor.execute(qry % valuesupd)

        if condicion == 'Cumplido':
            qry = """UPDATE trazaplan SET status = '%s'     WHERE idcuenta = '%s' AND meta = '%s' ;"""
            valuesupd = tuple([condicion, idcuenta, smeta])
            cursor.execute(qry % valuesupd)

            qry = """UPDATE trazaplan SET status = '%s'     WHERE idcuenta = '%s' AND meta = '%s' ;"""
            valuesupd = tuple(['Ejecucion', idcuenta, smeta + 1])
            cursor.execute(qry % valuesupd)
        conn.commit()

        conn = connect_dbase("update.plan")
        cursor = conn.cursor()
        qry = """UPDATE plan SET indicador = '%s', actual = '%s', objetivo = '%s'
                 WHERE idcuenta = '%s' AND vision = '%s' ;"""
        valuesupd = tuple([div, inversion, div / inversion, idcuenta, 'Financiera'])
        cursor.execute(qry % valuesupd)
        conn.commit()


def select_variablesplan(idcuenta) -> dict:
    conn = connect_dbase("select.plan")
    cursor = conn.cursor()
    xlis = list()
    qry, sql = None, None
    try:
        qry = """SELECT * from variablesplan WHERE idcuenta = '%s';"""
        cursor.execute(qry % idcuenta)

    except conn.ProgrammingError as error:
        print("[Mysql:: select_variablesplan()]: {}".format(error))

    sql = cursor.fetchall()

    if sql:
        columnas = [columna[0] for columna in cursor.description]
        for fila in sql:
            x = dict(zip(columnas, fila))
            xlis.append(x)
    return xlis


def select_extracto(account=None, extract='last') -> dict:
    """
    @param account: id de cuenta de inversión
    @param extract: fecha o extract de extracto a consultar
    @return: lista de registros seleccionados
    """
    conn = connect_dbase("select.extracto")
    cursor = conn.cursor()
    xlis = list()
    try:
        if extract == 'last':
            qry = """SELECT * FROM extractos WHERE idcuenta='%s' ORDER BY extracto DESC;"""
            cursor.execute(qry % account)
            sql = cursor.fetchone()

        if extract == 'sum':
            qry = """SELECT sum(depositos), sum(retiros), sum(crecimiento), sum(dividendos), sum(perdidas),
                            sum(fee), sum(comisiones), sum(tax), sum(idevengo), sum(imargen)
                     FROM extractos WHERE idcuenta='%s'
                                      AND year(extracto) = (SELECT MAX(year(extracto)) FROM extractos);"""
            cursor.execute(qry % account)
            sql = cursor.fetchone()

        if extract == 'fiscal':
            hasta = datetime.now().date()
            year = hasta.year - 1
            desde = datetime.strptime(str(year)+'-08-31', "%Y-%m-%d").date()
            qry = """SELECT sum(depositos), sum(retiros), sum(crecimiento), sum(dividendos), sum(perdidas),
                            sum(fee), sum(comisiones), sum(tax), sum(idevengo), sum(imargen), avg(cierreanterior)
                     FROM extractos WHERE idcuenta='%s'
                                      AND extracto >= '%s' and extracto <= '%s';"""
            cursor.execute(qry % (account, desde, hasta))
            sql = cursor.fetchone()

        if extract == 'select*':
            qry = """SELECT * FROM extractos WHERE idcuenta='%s' ORDER BY extracto DESC;"""
            cursor.execute(qry % account)
            sql = cursor.fetchall()


        if extract not in ('last', 'sum', 'fiscal', 'select*'):
            qry = """SELECT * FROM extractos WHERE idcuenta='%s' AND extracto = '%s';"""
            cursor.execute(qry % (account, extract))
            sql = cursor.fetchone()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_extracto()]: {}".format(error))

    if sql:
        columnas = [columna[0] for columna in cursor.description]
        if extract in ('last', 'sum', 'fiscal'):
            xlis.append(dict(zip(columnas, sql)))
        else:
            for fila in sql:
                x = dict(zip(columnas, fila))
                xlis.append(x)
    return xlis


def insert_extracto(account=None, values=None):
    """
    @param account: id de cuenta de inversión
    @param values:   lista de valores de campos a insertar
    @return:
    """
    def insert(qry, listvalues):

        listvalues.append(account)
        listvalues.append(acierre)
        i = 0
        for key, valor in values.items():
            if key not in ('id', 'idcuenta', 'cierreanterior'):
                listvalues.append(valor)
                qry = qry + key + ", "
                i += 1

        listvalues.append(id_next)
        valuesins = tuple(listvalues)
        qry = qry + "id) VALUES ({});".format(",".join('%s' for _ in range(len(valuesins))))
        cursor.execute(qry, valuesins)
        conn.commit()
        cursor.close()

    conn = connect_dbase("select.extractos")
    cursor = conn.cursor()

    uextract = select_extracto(account=account, extract='last')
    acierre = uextract[0]['cierreanterior']
    id_next = uextract[0]['id'] + 1
    listvalues = list()
    qry = "INSERT INTO extractos (idcuenta, cierreanterior,"
    try:
        #
        # valida que extracto a ingresar sea consecutivo al ultimo extracto
        if uextract[0] and bool(values):

            if valida_meses_consecutivos(inicio=uextract[0]['extracto'], fin=values['extracto']):
                insert(qry, listvalues)
        else:
            if not is_none(account) and bool(values):
                # queda validar la account antes de insertar
                # insert()
                pass

    except conn.ProgrammingError as error:
        print("[Mysql:: insert_extracto()]: {}".format(error))



def select_objeto(codigo=None, usamodo=None) -> object:
    """
    @param codigo:  id del registro a seleccionar
    @param usamodo:  grupo de registros a seleccionar
    @return: lista de objetos
    """
    conn = connect_dbase("select.sys_objeto")
    cursor = conn.cursor()
    listvalues = list()
    qry, sql, objeto = None, None, None

    try:
        if codigo is not None:
            qry = "SELECT objeto FROM sys_objeto WHERE id = '%s';"
            listvalues = [codigo]
        if usamodo is not None:
            qry = "SELECT id, descripcion FROM sys_objeto WHERE usamodulo = %s;"
            listvalues = [usamodo]

    except conn.ProgrammingError as error:
        print("[Mysql:: select_objeto()]: {}".format(error))

    valuesqry = tuple(listvalues)
    cursor.execute(qry, valuesqry)

    if codigo is not None:
        sql = cursor.fetchone()
    else:
        if usamodo is not None:
            sql = cursor.fetchall()

    xlis = list()

    if sql:
        ix = [columna[0] for columna in cursor.description]

        if usamodo is not None:
            for fila in sql:
                x = dict(zip(ix, fila))
                xlis.append(x)
        else:
            objeto = sql[ix.index('objeto')]
            xlis.append({'id': codigo})

    cursor.close()
    conn.close()
    return objeto, xlis


def select_crypto(symbol=None) -> object:
    """
    @param symbol:
    @return: retorna list() de asset
    """
    conn = connect_dbase("select.crypto_activos")
    cursor = conn.cursor()
    qry, sql, found, desc = None, None, False, None

    try:
        if symbol == 'all':
            qry = "SELECT * FROM crypto_activos;"
            cursor.execute(qry)
            sql = cursor.fetchall()
        else:
            qry = "SELECT * FROM crypto_activos WHERE symbol = %s;"
            cursor.execute(qry, symbol)
            sql = cursor.fetchone()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_crypto()]: {}".format(error))

    xlis = list()
    if sql:
        found = True
        ix = [columna[0] for columna in cursor.description]

        if symbol != 'all':
            xlis.append(dict(zip(ix, sql)))

        if symbol == 'all':
            for keys in sql:
                xlis.append(dict(zip(ix, keys)))

    cursor.close()
    conn.close()
    return xlis, found


def update_crypto(values=None, symbol=None):
    """

    @param values:
    @param symbol:
    @return:
    """
    conn = connect_dbase("update.crypto")
    cursor = conn.cursor()
    valuesins = list()
    qry = "UPDATE crypto_activos SET "

    try:
        found = select_crypto(symbol=symbol)
        if found:

            for keys, vals in values.items():

                qry = qry + keys + "='%s', "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry = qry + "WHERE symbol='%s';"
            qry = qry.replace(", WHERE", " WHERE")

            valuesupd = tuple(valuesins)
            cursor.execute(qry % valuesupd)

    except conn.ProgrammingError as error:
        print("[Mysql:: update_crypto()]: {}".format(error))

    conn.commit()
    cursor.close()


def insert_crypto(symbol=None):
    """
    @param symbol: ticket a consultar en crypto
    @return:
    """
    conn = connect_dbase("insert.crypto_activos")
    cursor = conn.cursor()
    valuesins = list()
    qry, values, xlis, found = ' ', dict(), list(), False
    ix = ('cuenta', 'idcrypto', 'descripcion', 'base_asset', 'quote_asset', 'objetivo', 'fecupdate')
    try:
        row, found = select_crypto(symbol=symbol)

        if not found:

            ticket = yf.Ticker(symbol.replace("USDT", "-USD"))
            name = ticket.info['name'] if 'name' in ticket.info else ' '
            avg = ticket.info['previousClose'] if 'previousClose' in ticket.info else 0
            h52w = ticket.info['fiftyTwoWeekHigh'] if 'fiftyTwoWeekHigh' in ticket.info else 0

            qry = "INSERT INTO crypto_activos ("

            values.update({'cuenta': 'B0000001'})
            values.update({'idcrypto': np.random.randint(1, 10000001)})
            values.update({'descripcion': name})
            values.update({'base_asset': symbol.replace("USDT", "")})
            values.update({'quote_asset': 'USDT'})
            values.update({'avgcost': avg})
            values.update({'objetivo': h52w})
            values.update({'fecupdate': datetime.now()})

            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry = qry + "symbol) VALUES ({});".format(",".join("'%s'" for _ in range(len(valuesins))))
            cursor.execute(qry, tuple(valuesins))
            xlis.append(values)

        else:
            xlis.append(dict(zip(ix, row))['cuenta'])

    except conn.ProgrammingError as error:
        print("[Mysql::  insert_crypto()]: {}".format(error))

    conn.commit()
    cursor.close()
    return xlis, found


def select_booktrading(accion='last', account='B0000001', idivisa='USD', idtrans=None,
                       fecha=None, symbol='SPX') -> list:
    """
    @param accion: tipo de consultar
    @param account: id cuenta de inversion
    @param idivisa: ticket a consultar en booktrading
    @param fecha: fecha de consults
    @param symbol: ticket a consultar en booktrading
    @param idtrans: Nro de transaccion
    @param fecha: fecha de transaccion
    @return: lista de registros seleccionados
    """
    conn = connect_dbase("select.booktrading")
    cursor = conn.cursor()
    xlist, sql = list(), None
    try:
        if accion == 'inc_BTC':
            qry = """SELECT min(fecha_hora) FROM booktrading;"""
            cursor.execute(qry)
            sql = cursor.fetchone()

        if accion == 'last':
            """
            @ para el calculo de precio medio solo se toma stock y basico de ultima operación
            @ sumar producto + comisiones 
            """
            # GWI001
            # qry = """SELECT x.sec, x.fechahora, x.stock, x.basico x.gprealizadas FROM booktrading as x
            #          WHERE cuenta = '%s' AND divisa = '%s' AND simbolo = '%s' AND activa = 'Y'
            #          AND  sec = (SELECT max(sec) FROM booktrading
            #                      WHERE cuenta = x.cuenta AND divisa = x.divisa AND simbolo = x.simbolo
            #                                              AND activa = 'Y');"""
            qry = """SELECT a.* FROM (SELECT sec, fechahora, stock, basico, gprealizadas, cantidad, 
                                             tarifacomision, idtrans FROM booktrading 
                                             WHERE cuenta = '%s' AND divisa = '%s' 
                                               AND simbolo = '%s' AND activa = 'Y') AS a
                                             ORDER BY fechahora DESC, idtrans DESC;"""

            cursor.execute(qry % (account, idivisa, symbol))
            sql = cursor.fetchone()

        if accion == 'low':
            # GWI001
            # qry = """SELECT * FROM booktrading as x WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s'
            #         AND activa = 'Y'
            #         AND   sec = (SELECT min(sec) FROM booktrading
            #                      WHERE cuenta = x.cuenta AND divisa = x.divisa AND activa = 'Y'
            #                      AND simbolo = x.simbolo);"""
            qry = """SELECT a.* FROM (SELECT * FROM booktrading  WHERE cuenta = '%s'  
                                                                 AND divisa = '%s' AND simbolo = '%s') AS a 
                                                                 ORDER BY fechahora ASC;"""
            cursor.execute(qry % (account, idivisa, symbol))
            sql = cursor.fetchone()

        if accion == 'valida':
            # qry = """SELECT * FROM booktrading as x WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s'
            #         AND activa = 'Y' AND idtrans = '%s';"""
            qry = """SELECT * FROM booktrading as x WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' 
                                                      AND idtrans = '%s';"""

            cursor.execute(qry % (account, idivisa, symbol, idtrans))
            sql = cursor.fetchone()

        if accion == 'select':
            # GWI001
            # qry = """SELECT DATE(fechahora), basico, stock, gprealizadas FROM booktrading
            #         WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' AND activa = 'Y'
            #         ORDER BY fechahora ASC;"""
            qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock, gprealizadas FROM booktrading  
                                       WHERE cuenta = '%s'  AND divisa = '%s' 
                                         AND simbolo = '%s' AND activa = 'Y') AS a 
                                       ORDER BY DATE(fechahora) ASC;"""

            cursor.execute(qry % (account, idivisa, symbol))
            sql = cursor.fetchall()

        if accion == 'fecha':
            istamp = pd.to_datetime(fecha)
            estamp = istamp + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            # GWI001
            # qry = """SELECT DATE(fechahora), basico, stock  FROM booktrading
            #                WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' AND codigo = 'O'
            #                AND fechahora >= '%s' AND fechahora <= '%s' ORDER BY fechahora ASC;"""
            qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock  FROM booktrading  
                                       WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' AND codigo = 'O'
                                         AND fechahora >= '%s' AND fechahora <= '%s') AS a
                                       ORDER BY  DATE(fechahora) ASC;"""
            cursor.execute(qry % (account, idivisa, symbol, istamp, estamp))
            sql = cursor.fetchall()

        if accion == 'Trade':
            istamp = pd.to_datetime(fecha)
            qry = """SELECT * FROM booktrading  WHERE cuenta = '%s' AND divisa = '%s' 
                                                  AND simbolo ='%s' AND fechahora = '%s' AND idtrans = '%s';"""
            cursor.execute(qry % (account, idivisa, symbol, istamp, idtrans))
            sql = cursor.fetchall()

        if accion == 'timestamp':
            qry = """SELECT max(a.fechahora) as fechahora FROM 
                            (SELECT fechahora FROM booktrading  
                              WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y') AS a;"""

            cursor.execute(qry % (account, idivisa))
            sql = cursor.fetchone()

        if accion == 'select*':
            # GWI001
            # qry = """SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s'
            #                                   AND simbolo = '%s' AND activa = 'Y' ORDER BY fechahora ASC;"""
            qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s' 
                                                                  AND simbolo = '%s' AND activa = 'Y') AS a 
                                                                  ORDER BY fechahora ASC, idtrans ASC;"""

            cursor.execute(qry % (account, idivisa, symbol))
            sql = cursor.fetchall()

        if accion == 'cuenta':
            # GWI001
            # qry = """SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s' ORDER BY fechahora ASC;"""
            qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s') AS a 
                                     ORDER BY fechahora ASC;"""

            cursor.execute(qry % (account, idivisa))
            sql = cursor.fetchall()

        if accion == 'performa':
            # GWI001
            # qry = """SELECT DATE(fechahora), basico, stock, gprealizadas, codigo FROM booktrading
            #               WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s'
            #               ORDER BY fechahora ASC;"""
            qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock, gprealizadas, codigo, comisiones
                                      FROM booktrading  WHERE cuenta = '%s'  AND divisa = '%s' 
                                                          AND simbolo = '%s') AS a ORDER BY DATE(fechahora) ASC;"""

            cursor.execute(qry % (account, idivisa, symbol))
            sql = cursor.fetchall()

        # opción para reconstruir performa de la cartera
        if accion == 'cartera':
            qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s'
                                                                   AND codigo in ('C', 'O')) AS a
                                                                 ORDER BY simbolo, fechahora ASC;"""

            cursor.execute(qry % (account, idivisa))
            sql = cursor.fetchall()

    except conn.ProgrammingError as error:
        print("[Mysql error]: {}".format(error))

    xlis, columnas = list(), list()

    if sql:
        columnas = [columna[0] for columna in cursor.description]
        if accion in ('last', 'low', 'valida', 'timestamp', 'id', 'Trade'):
            xlis.append(dict(zip(columnas, sql)))
            return xlis
        else:
            xlis = sql
            return xlis, columnas
    else:
        if accion in ('last', 'low', 'valida', 'timestamp', 'id', 'Trade'):
            return xlis
        else:
            return xlis, columnas


def insert_booktrading(values=None,  symbol='SPX'):
    """

    @param values:   lista de valores de campos a insertar
    @param symbol: ticket a consultar en booktrading
    @return:
    """
    ix = ['id', 'sec', 'categoria', 'divisa', 'cuenta', 'simbolo', 'fechahora', 'idtrans', 'cantidad',
          'preciotrans', 'preciocierre', 'producto', 'tarifacomision', 'basico', 'gprealizadas',
          'mtmgp', 'codigo', 'stock', 'activa', 'split']

    def update_indicador_activa():
        """
         @return: Mantiene indicador activa, en función de las sesiones de venta
        """
        conn = connect_dbase("update.booktrading")
        cursor = conn.cursor()
        sql = """UPDATE booktrading SET activa = 'N' 
                         WHERE cuenta = '%s' AND divisa = '%s' AND simbolo = '%s';"""
        qry = """UPDATE booktrading SET activa = 'N' 
                         WHERE cuenta = '%s' AND divisa = '%s' AND simbolo = '%s' and idtrans = '%s';"""
        try:

            if values['stock'] <= 0 and values['codigo'] == 'C':
                cursor.execute(sql % (account, idivisa, symbol))
                conn.commit()
            else:
                if (values['cantidad'] < 0) and values['codigo'] == 'C':
                    book, ix = select_booktrading(accion='select*', account=account, idivisa=idivisa, symbol=symbol)

                    if book:
                        acum = values['cantidad']
                        for keys in book:
                            if keys[ix.index('codigo')] == 'O':
                                acum += keys[ix.index('stock')]
                                if acum <= 0:
                                    cursor.execute(qry % (account, idivisa, symbol, keys[ix.index('idtrans')]))
                                else:
                                    break
                        conn.commit()

        except conn.ProgrammingError as error:
            print("[Mysql:: insert_booktrading()]: {}".format(error))

    def found_booktrading():
        if values['categoria'] == 'Stock':
            xlist = select_booktrading(accion='valida', account=account, idivisa=idivisa,
                                                    idtrans=idtrans, symbol=symbol)

        if values['categoria'] == 'Crypto':
            xlist = select_booktrading(accion='Trade', account=account, idivisa=idivisa,
                                        fecha=values['fechahora'], idtrans=values['idtrans'], symbol=symbol)

        found = True if len(xlist) == 1 else False
        return found, xlist

    conn = connect_dbase("insert.booktrading")
    cursor = conn.cursor()
    valuesins = list()
    qry = ' '
    try:
        account = values['cuenta']
        idivisa = values['divisa']
        idtrans = values['idtrans']

        (found, xlist) = found_booktrading()
        if not found:
            print('not found==',xlist)
            nw_producto, ubasico, ustock, usec, uid = 0, 0, 0, 0, 0
            utrading = select_booktrading(accion='last', account=account, idivisa=idivisa, symbol=symbol)
            if utrading:
                nw_producto = utrading[0]['basico'] * utrading[0]['stock']
                ubasico = utrading[0]['basico']
                ustock = utrading[0]['stock']
                usec = utrading[0]['sec']

            qry = "INSERT INTO booktrading ("

            if values['cantidad'] > 0:
                stock = values['cantidad'] + ustock
                """
                @ para obtener el basico se debe recalcular el nuevo producto entregado select utrading y 
                @ entre el nuevo stock
                """
                basico = (values['preciotrans'] * values['cantidad'] + values['tarifacomision'] + nw_producto) / stock
                gpreal = Decimal(0.00)
                codigo = 'O'
                mtmgp = 0.00
                values.update({'activa': 'Y'})
            else:
                basico = ubasico
                stock = values['cantidad'] + ustock
                codigo = 'C'
                mtmgp = values['preciotrans'] - basico
                gpreal = mtmgp * abs(values['cantidad'])

            if 'mtmgp' not in values.keys():
                values.update({'mtmgp': 0})

            values.update({'split': 1})
            values.update({'activa': 'Y'})
            values.update({'stock': stock})
            values.update({'mtmgp': mtmgp})
            values.update({'basico': basico})
            values.update({'codigo': codigo})
            values.update({'gprealizadas': gpreal})
            values.update({'sec': int(usec) + 1})

            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry = qry + "simbolo) VALUES ({});".format(",".join('%s' for _ in range(len(valuesins))))
            cursor.execute(qry, tuple(valuesins))
            """
            @ actualiza precio basico en tabla crypto_activos
            @ actualiza indicador activa en booktrading, cuando sea una venta (cantidad <0)
            """
            cvalues = dict()
            cvalues.update({'avgcost': basico})
            cvalues.update({'fecupdate': values['fechahora']})
            update_crypto(values=cvalues, symbol=symbol)

            conn.commit()
            update_indicador_activa()

    except conn.ProgrammingError as error:
        print("[Mysql:: found_booktrading()]: {}".format(error))

    cursor.close()


def min_fec_booktrading(list_asset=None, account=None, idivisa=None) -> dict:
    """
    @param list_asset: lista de simbolos
    @param account: idcuenta
    @param idivisa: divisa
    @return: de booktrading fecha minima para los simbolos de la cuenta
    """
    conn = connect_dbase("select.booktrading")
    cursor = conn.cursor()
    try:
        inicio = dict()
        ifecha = datetime.now()
        for ticket in list_asset:
            utrading = select_booktrading(accion='low', account=account, idivisa=idivisa, symbol=ticket)
            if utrading:
                if ifecha > utrading[0]['fechahora']:
                    ifecha = utrading[0]['fechahora']

            inicio.update({'asset': ticket, 'ifecha': ifecha})
        return inicio

    except ValueError:
        return dict()


def select_performa_inversion(account=None, vehiculo=None, accion=None, referencia=None) -> list:
    """
    @param account: id cuenta de inversion
    @param vehiculo:  tipo de inversión acciones, Crypto
    @param accion: tipo de consulta
    @param referencia:  que índice acompaña el vehículo de inversión
    @return:  entrega lista de filas según parámetros de entrada
    """

    conn = connect_dbase("select.performa_inversion")
    cursor = conn.cursor()
    qry, sql, ix = ' ', list(), list()
    try:
        if is_none(accion) and is_none(referencia):
            qry = """SELECT  fechaclose, p_referencia, p_vehiculo, nr_gyp, value, costo_base FROM performa_inversion 
                     WHERE idcuenta = '%s'  AND vehiculo = '%s' ORDER by fechaclose ASC;"""
            cursor.execute(qry % (account, vehiculo))
            sql = cursor.fetchall()

        if not is_none(accion) and not is_none(referencia):
            qry = """SELECT * FROM performa_inversion WHERE idcuenta = '%s'  AND vehiculo = '%s' 
                                                        AND fechaclose ='%s' AND referencia = '%s';"""
            cursor.execute(qry % (account, vehiculo, accion, referencia))
            sql = cursor.fetchone()

        if accion == 'last':
            qry = """SELECT fechaclose, p_referencia, p_vehiculo FROM performa_inversion a
                     WHERE fechaclose = (SElECT max(fechaclose)  FROM performa_inversion
                                         WHERE idcuenta = a.idcuenta AND vehiculo = a.vehiculo)
                       AND idcuenta = '%s' AND vehiculo = '%s';"""
            cursor.execute(qry % (account, vehiculo))
            sql = cursor.fetchone()

        if accion == 'first':
            qry = """SELECT min(fechaclose) FROM performa_inversion 
                                            WHERE idcuenta = '%s' AND vehiculo = '%s';"""
            cursor.execute(qry % (account, vehiculo))
            sql = cursor.fetchone()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_performa_inversion()]: {}".format(error))

    if sql:
        ix = [columna[0] for columna in cursor.description]

    return sql, ix


def insert_performa_inversion(values=None):
    """
    @param values: de campos a actualizar en tabla performa_inversiones
    @return: insert de registros en performa_inversiones
    """
    conn = connect_dbase("insert.performa_inversion")
    cursor = conn.cursor()
    valuesins = list()
    qry = ' '
    try:

        qry = "INSERT INTO performa_inversion ("

        for keys, vals in values.items():
            qry = qry + keys + ", "
            valuesins.append(vals)

        valuesins.append(datetime.now())

        valuesupd = tuple(valuesins)
        qry = qry + " timestamp) VALUES ({});".format(",".join('%s' for _ in range(len(valuesins))))
        cursor.execute(qry, valuesupd)

    except conn.ProgrammingError as error:
        print("[Mysql:: insert_performa_inversion()]: {}".format(error))

    conn.commit()
    cursor.close()


def insert_split(symbol=None, values=None):
    """
    @param symbol:
    @param values:  dict() con información de campos a actualizar
    @return:
    """
    conn = connect_dbase("select.split")
    cursor = conn.cursor()
    sql = "SELECT * FROM split Where ticket='%s' and date='%s';"
    valuesins = list()
    qry, found = ' ', False

    try:
        cursor.execute(sql % (symbol, values['date']))
        found = cursor.fetchone()
        if not found:

            qry = "INSERT INTO split ("

            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry = qry + "ticket) VALUES ({});".format(",".join("'%s'" for _ in range(len(valuesins))))
            cursor.execute(qry, tuple(valuesins))

    except conn.ProgrammingError as error:
        print("[Mysql:: insert_split()]: {}".format(error))

    conn.commit()
    cursor.close()


def select_split(symbol='all') -> list:
    """
    @param symbol:
    @return:
    """
    conn = connect_dbase("select.split")
    cursor = conn.cursor()
    sql, ix, found = ' ', list(), False

    try:
        if symbol == 'all':
            sql = """SELECT * FROM split Where aplicado ='N';"""
            cursor.execute(sql)
        else:
            sql = """SELECT * FROM split Where aplicado ='N' AND ticket = '%s';"""
            cursor.execute(sql % symbol)

    except EncodingWarning as error:
        print("[Mysql:: select_split()]: {}".format(error))

    found = cursor.fetchall()
    ix = [columna[0] for columna in cursor.description]
    return found, ix


def select_market(account=None, tipo=None, symbol=None, country=None, sector=None, name=None) -> list:
    """
    @param account: id de cuenta inversionista
    @param tipo: tipo de inversion: Dividends  y crecimiento
    @param symbol: activo a consultar
    @param country: pais a consultar
    @param sector: sector productivo a consultar
    @param name: busca por shortname y entrega lista
    @return: lista de activos con alto rendimiento y/o mejor momento e inversión
    """
    conn = connect_dbase("select.market")
    cursor = conn.cursor()
    qry, sql, ix = ' ', list(), list()
    try:

        if not is_none(symbol) and is_none(name):
            qry = """SELECT * FROM market WHERE account= '%s' AND symbol = '%s';"""
            cursor.execute(qry % (account, symbol))
            sql = cursor.fetchall()

        if not is_none(symbol) and not is_none(name):

            qry = """SELECT * FROM market WHERE account= '%s' AND shortname LIKE '%s' OR symbol = '%s';"""
            key = name + '%'
            cursor.execute(qry % (account, key.upper(), symbol.upper()))
            sql = cursor.fetchall()

        if is_none(symbol) and is_none(name) and is_none(country) and is_none(sector):
            qry = """SELECT  * FROM market WHERE account= '%s' AND tipo = '%s';"""
            cursor.execute(qry % (account, tipo))
            sql = cursor.fetchall()

        if is_none(symbol) and is_none(name) and not is_none(country) and is_none(sector):
            qry = """SELECT  * FROM market WHERE account= '%s' AND country = '%s';"""
            cursor.execute(qry % (account, country))
            sql = cursor.fetchall()

        if is_none(symbol) and is_none(name) and is_none(country) and not is_none(sector):
            qry = """SELECT  * FROM market WHERE account= '%s' AND sector = '%s';"""
            cursor.execute(qry % (account, sector))
            sql = cursor.fetchall()

    except conn.ProgrammingError as error:
        print("[Mysql:: select_market]: {}".format(error))

    if sql:
        ix = [columna[0] for columna in cursor.description]
    return sql, ix


def insert_market(cursor=None, upd=None, val=None, symbol=None):
    """
    @param cursor:  market cursor donde es llamada la rutina
    @param upd:  list() de campos para insertar en market
    @param val:  list() de valores que acompañan a upd
    @param symbol: symbol o ticket que se inserta en market
    @return:  Agrega fila a partir de symbol y campos pasados como parameter
    """

    try:
        listvalues = list()
        cursor.execute("SELECT MAX(id) FROM market")
        row = cursor.fetchone()
        listvalues.append(row[0] + 1 if not is_none(row[0]) else 0)

        qry = "INSERT INTO market (id, "

        for i in range(len(val)):
            if not is_none(val[i]):

                if upd[i] in ('lastFiscalYearEnd', 'trazaDividends', 'exDividendDate', 'firstTradeDateEpochUtc'):
                    listvalues.append(val[i])

                else:
                    if is_numeric(val[i]):
                        listvalues.append(float(val[i]))
                    else:
                        listvalues.append(val[i])
                qry = qry + upd[i] + ", "

        listvalues.append(datetime.now())
        listvalues.append(symbol)
        valuesins = tuple(listvalues)
        qry = qry + "timestamp, symbol) VALUES ({});".format(", ".join("'%s'" for _ in range(len(valuesins))))

        cursor.execute(qry % valuesins)

    except EncodingWarning as error:
        print("[Mysql::insert_market()]: {}".format(error))


def select_diaria_performance(accion=None, account=None, date=None, symbol=None) -> list:
    """
    @param accion: parametro indicativo para seleccionar last o firth de la diaria
    @param account: id de cuenta inversionista
    @param date: fecha de consulta
    @param symbol: ticket a consultar
    @return: lista de activos y rendimiento por fecha
    """
    conn = connect_dbase("select.traza.performa")
    cursor = conn.cursor()
    qry, sql, ix = ' ', list(), list()
    try:

        if not is_none(symbol) and is_none(date) and is_none(accion):
            qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND symbol = '%s';"""
            cursor.execute(qry % (account, symbol))
            sql = cursor.fetchall()

        if not is_none(symbol) and is_none(date) and (accion == 'last'):
            qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND symbol = '%s' AND
                                   Date = (SELECT max(Date) FROM diaria_performance 
                                            WHERE account= '%s' AND symbol = '%s');"""
            cursor.execute(qry % (account, symbol, account, symbol))
            sql = cursor.fetchone()

        if not is_none(symbol) and not is_none(date) and is_none(accion):

            qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date = '%s' AND symbol = '%s';"""
            cursor.execute(qry % (account, symbol, date))
            sql = cursor.fetchall()

        if is_none(symbol) and not is_none(date) and is_none(accion):
            qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date = '%s';"""
            cursor.execute(qry % (account, date))
            sql = cursor.fetchall()

        if is_none(symbol) and not is_none(date) and (accion == 'desde'):
            qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date >= '%s';"""
            cursor.execute(qry % (account, date))
            sql = cursor.fetchall()

        if is_none(symbol) and is_none(date) and is_none(accion):
            qry = """SELECT * FROM diaria_performance WHERE account= '%s' ORDER by date ASC;"""
            cursor.execute(qry % account)
            sql = cursor.fetchall()

        ix = [columna[0] for columna in cursor.description]
        sql = sql if not is_none(sql) else []
        return sql, ix

    except conn.ProgrammingError as error:
        print("[Mysql:: select_diaria_performance]: {}".format(error))



def insert_diaria_performance(values=None,  symbol='SPX'):
    """

    @param values:   lista de valores de campos a insertar
    @param symbol: ticket a consultar en booktrading
    @return:
    """

    conn = connect_dbase("insert.diaria_performance")
    cursor = conn.cursor()
    valuesins = list()
    qry = ' '
    try:

        qry = "INSERT INTO diaria_performance ("
        for keys, vals in values.items():
            qry = qry + keys + ", "
            valuesins.append(vals)

        valuesins.append(symbol)
        qry = qry + "symbol) VALUES ({});".format(",".join('%s' for _ in range(len(valuesins))))
        cursor.execute(qry, tuple(valuesins))
        conn.commit()

    except conn.ProgrammingError as error:
        print("[Mysql:: insert_diaria_performance()]: {}".format(error))

    cursor.close()

