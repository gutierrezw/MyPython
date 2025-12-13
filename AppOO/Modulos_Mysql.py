from Modulos_python import (
    pd,
    np,
    yf,
    datetime,
    Image,
    ImageTk,
    io,
    time,
    timedelta,
    hashlib,
    json,
    connect,
    Error,
    Optional,
    create_engine,
)
from Modulos_Utilitarios import (
    is_none,
    valida_meses_consecutivos,
    sort_positions,
)


class BDsystem:  # ----------------------------------------------------------------------------------------------------
    """
    clase para manejar accesos genericos a mysql."""

    DB_CONFIG = {
        "user": "root",
        "password": "Daga2004",
        "host": "localhost",
        "database": "bdinv",
    }

    def select_sesion(
        fecha,
        orden='{"RetS": "ASC"}',
        accion=False,
        invertir=0,
        filtro=None,
        vehiculo="Stock",
    ) -> dict:
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
        conn = BDsystem.connect_dbase("select.sesion", False)
        try:
            cursor = conn.cursor()
            cursor.execute(sql % vehiculo)
            qry = cursor.fetchone()
            ix = [columna[0] for columna in cursor.description]

            fesesion = qry[ix.index("fesesion")]
            or_cartera = qry[ix.index("orcartera")]
            pinvertir = qry[ix.index("Pinvertir")]
            xstrategy = qry[ix.index("xstrategy")]

            sesion = dict.fromkeys(ix, 0)
            sesion["fefund"] = qry[ix.index("fefund")]

            if accion == "update":
                upd = """UPDATE sesion SET fesesion='%s', orcartera='%s' WHERE vehiculo='%s';"""
                fesesion = fecha
                conn = BDsystem.connect_dbase("Sesion.Update", False)
                cursor = conn.cursor()
                cursor.execute(upd % (fesesion, orden, vehiculo))
                conn.commit()

                sesion["fectime"] = fesesion
                sesion["fesesion"] = fesesion
                sesion["orcartera"] = orden
                sesion["Pinvertir"] = invertir

            if accion == "select":
                sesion["fectime"] = fecha
                sesion["fesesion"] = fesesion
                sesion["orcartera"] = or_cartera
                sesion["Pinvertir"] = pinvertir
                sesion["xstrategy"] = xstrategy

            if accion == "updateFun":
                upd = """UPDATE sesion SET fechaFund='%s' WHERE vehiculo='%s';"""
                sesion["fefund"] = fecha
                conn = BDsystem.connect_dbase("Fe.fundamental.Update", False)
                cursor = conn.cursor()
                cursor.execute(upd % (fecha, vehiculo))
                conn.commit()

            if accion == "updatexstrategy":
                if filtro:
                    upd = """UPDATE sesion SET xstrategy='%s' WHERE vehiculo='%s';"""
                    sesion["xstrategy"] = filtro
                    conn = BDsystem.connect_dbase("Strategy.Update", False)
                    cursor = conn.cursor()
                    cursor.execute(upd % (filtro, vehiculo))
                    conn.commit()

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_sesion()]: {}".format(error))

        cursor.close()
        sesion["id"] = qry[ix.index("id")]
        sesion["iduser"] = qry[ix.index("iduser")]
        sesion["idcuenta"] = qry[ix.index("idcuenta")]
        sesion["userapi"] = qry[ix.index("userapi")]
        sesion["userpass"] = qry[ix.index("userpass")]
        sesion["private_key"] = qry[ix.index("private_key")]
        sesion["vehiculo"] = qry[ix.index("vehiculo")]
        sesion["Pinvertir"] = qry[ix.index("Pinvertir")]
        sesion["fiscalYear"] = qry[ix.index("fiscalYear")]

        return sesion

    # cagar imagen desde sys_objetos

    def select_image(idd=None, size=(20, 20)):
        imagen0, xlis = BDsystem.select_objeto(codigo=idd)
        imagen = Image.open(io.BytesIO(imagen0))
        imagen = imagen.resize(size, Image.ADAPTIVE)
        imagen_tk = ImageTk.PhotoImage(imagen)
        return imagen_tk

    def select_objeto(codigo=None, usamodo=None) -> object:
        """
        @param codigo: id del registro a seleccionar
        @param usamodo: grupo de registros a seleccionar
        @return: lista de objetos."""
        try:
            conn = BDsystem.connect_dbase("select.sys_objeto")
            cursor = conn.cursor()
            listvalues, qry, sql, objeto, xlis = [], None, None, None, []

            if codigo is not None:
                qry = "SELECT objeto FROM sys_objeto WHERE id = '%s';"
                listvalues = [codigo]
            elif usamodo is not None:
                qry = "SELECT id, descripcion FROM sys_objeto WHERE usamodulo = %s;"
                listvalues = [usamodo]

            cursor.execute(qry, tuple(listvalues))
            ix = [columna[0] for columna in cursor.description]

            if codigo is not None:
                sql = cursor.fetchone()

            elif usamodo is not None:
                sql = cursor.fetchall()

            if sql:
                if usamodo is not None:
                    for fila in sql:
                        x = dict(zip(ix, fila))
                        xlis.append(x)
                else:
                    objeto = sql[ix.index("objeto")]
                    xlis.append({"id": codigo})

            return objeto, xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_objeto()]: {}".format(error))

    # conector a BaseDatos
    def connect_dbase(tabla, display=False) -> object:
        try:
            conn = None
            conn = connect(
                host=BDsystem.DB_CONFIG.get("host"),
                user=BDsystem.DB_CONFIG.get("user"),
                password=BDsystem.DB_CONFIG.get("password"),
                database=BDsystem.DB_CONFIG.get("database"),
            )
            if display:
                print("[Message]: connect a Mysql: " + tabla)

            return conn
        except (Exception, EncodingWarning, connect.Error) as e:
            print("[MySql:: connect_dbase()] ", e)

    @staticmethod
    def select_all_sesion():
        """Obtiene todos los registros de sesión ordenados por fecha ascendente"""
        try:
            conn = BDsystem.connect_dbase("select.all_sesion", False)
            cursor = conn.cursor()
            sql = "SELECT * FROM sesion ORDER BY fiscalYear ASC"
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            sessions = []
            for row in rows:
                sessions.append(dict(zip(columns, row)))

            cursor.close()
            conn.close()
            return sessions
        except Exception as error:
            print(f"[Mysql::select_all_sesion()]: {error}")
            return []

    @staticmethod
    def insert_sesion(values):
        """Inserta nuevo registro de sesión"""
        try:
            conn = BDsystem.connect_dbase("insert.sesion", False)
            cursor = conn.cursor()

            sql = """INSERT INTO sesion
                     (vehiculo, fesesion, iduser, idcuenta, orcartera, fiscalYear,
                      fefund, Pinvertir, xstrategy, userapi, userpass,
                      private_key, public_key, port)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

            data = (
                values.get("vehiculo"),
                values.get("fesesion"),
                values.get("iduser"),
                values.get("idcuenta"),
                values.get("orcartera"),
                values.get("fiscalYear"),
                values.get("fefund"),
                values.get("Pinvertir"),
                values.get("xstrategy"),
                values.get("userapi"),
                values.get("userpass"),
                values.get("private_key"),
                values.get("public_key"),
                values.get("port"),
            )

            cursor.execute(sql, data)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as error:
            print(f"[Mysql::insert_sesion()]: {error}")
            return False

    @staticmethod
    def update_sesion(session_id, vehiculo, values):
        """Actualiza registro de sesión existente"""
        try:
            conn = BDsystem.connect_dbase("update.sesion", False)
            cursor = conn.cursor()

            sql = """UPDATE sesion SET
                     fesesion=%s, iduser=%s, idcuenta=%s, orcartera=%s,
                     fiscalYear=%s, fefund=%s, Pinvertir=%s, xstrategy=%s,
                     userapi=%s, userpass=%s, private_key=%s, public_key=%s, port=%s
                     WHERE id=%s AND vehiculo=%s"""

            data = (
                values.get("fesesion"),
                values.get("iduser"),
                values.get("idcuenta"),
                values.get("orcartera"),
                values.get("fiscalYear"),
                values.get("fefund"),
                values.get("Pinvertir"),
                values.get("xstrategy"),
                values.get("userapi"),
                values.get("userpass"),
                values.get("private_key"),
                values.get("public_key"),
                values.get("port"),
                session_id,
                vehiculo,
            )

            cursor.execute(sql, data)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion()]: {error}")
            return False

    @staticmethod
    def delete_sesion(session_id, vehiculo):
        """Elimina registro de sesión"""
        try:
            conn = BDsystem.connect_dbase("delete.sesion", False)
            cursor = conn.cursor()

            sql = "DELETE FROM sesion WHERE id=%s AND vehiculo=%s"
            cursor.execute(sql, (session_id, vehiculo))
            conn.commit()

            rows_affected = cursor.rowcount
            cursor.close()
            conn.close()
            return rows_affected > 0
        except Exception as error:
            print(f"[Mysql::delete_sesion()]: {error}")
            return False


class IPerformance(
    BDsystem
):  # ------------------------------------------------------------------------------------
    """
    clase para manejar: select, insert y update sobre Diaria y Performa_inversion."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select_performa_inversion(
        self, account=None, vehiculo=None, accion=None, referencia=None
    ):
        """
        @param account: id cuenta de inversion
        @param vehiculo: tipo de inversión acciones, Crypto
        @param accion: tipo de consulta
        @param referencia: Qué índice acompaña el vehículo de inversión
        @return: entrega lista de filas según parámetros de entrada."""

        conn = self._conectar(tabla="select.performa_inversion")
        try:
            cursor = conn.cursor()

            # exclusivo para sumar valores por vehiculo (caso: BBVA.ARS)
            if is_none(account):
                qry = """SELECT fechaclose, p_referencia, 
                                sum(p_vehiculo) p_vehiculo, 
                                sum(nr_gyp) nr_gyp, 
                                sum(value) value, 
                                sum(costo_base) 
                         FROM performa_inversion 
                        WHERE vehiculo = '%s' 
                        GROUP BY fechaclose, p_referencia
                        ORDER by fechaclose ASC;"""
                cursor.execute(qry % (vehiculo))
                sql = cursor.fetchall()

            # uso mas frecuente para sumar valores por account y vehiculo
            elif is_none(accion) and is_none(referencia):
                qry = """SELECT fechaclose, p_referencia, p_vehiculo, nr_gyp, value, costo_base FROM performa_inversion 
                        WHERE idcuenta = '%s'  AND vehiculo = '%s' ORDER by fechaclose ASC;"""
                cursor.execute(qry % (account, vehiculo))
                sql = cursor.fetchall()

            # consulta por acción y referencia específica
            elif not is_none(accion) and not is_none(referencia):
                qry = """SELECT * FROM performa_inversion WHERE idcuenta = '%s'  AND vehiculo = '%s' 
                                                            AND fechaclose ='%s' AND referencia = '%s';"""
                cursor.execute(qry % (account, vehiculo, accion, referencia))
                sql = cursor.fetchone()

            elif accion == "last":
                qry = """SELECT fechaclose, p_referencia, p_vehiculo FROM performa_inversion a
                        WHERE fechaclose = (SElECT max(fechaclose)  FROM performa_inversion
                                            WHERE idcuenta = a.idcuenta AND vehiculo = a.vehiculo)
                        AND idcuenta = '%s' AND vehiculo = '%s';"""
                cursor.execute(qry % (account, vehiculo))
                sql = cursor.fetchone()

            elif accion == "first":
                qry = """SELECT min(fechaclose) FROM performa_inversion 
                                                WHERE idcuenta = '%s' AND vehiculo = '%s';"""
                cursor.execute(qry % (account, vehiculo))
                sql = cursor.fetchone()
            else:
                qry = """SELECT * FROM performa_inversion 
                                WHERE idcuenta = '%s' AND vehiculo = '%s';"""
                cursor.execute(qry % (account, vehiculo))
                sql = cursor.fetchall()

            ix = [columna[0] for columna in cursor.description]
            return sql, ix
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"Mysql:: select_performa_inversion(): {error}")
        finally:
            cursor.close()
            conn.close()

    def insert_performa_inversion(self, values=None):
        """
        @param values: de campos a actualizar en tabla performa_inversiones
        @return: insert de registros en performa_inversiones
        """
        try:
            conn = self._conectar(tabla="insert.performa_inversion")
            cursor = conn.cursor()
            valuesins = list()
            qry = "INSERT INTO performa_inversion ("

            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(datetime.now())

            valuesupd = tuple(valuesins)
            qry += " timestamp) VALUES ({});".format(
                ",".join("%s" for _ in range(len(valuesins)))
            )
            cursor.execute(qry, valuesupd)

            conn.commit()
            cursor.close()

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: insert_performa_inversion()]: {}".format(error))

    def select_diaria_performance(
        self, accion=None, account=None, date=None, symbol=None
    ):
        """
        @param accion: parametro indicativo para seleccionar last o firth de la diaria
        @param account: id de cuenta inversionista
        @param date: fecha de consulta
        @param symbol: ticket a consultar
        @return: lista de activos y rendimiento por fecha
        """
        try:
            conn = self._conectar(tabla="select.traza.performa")
            cursor = conn.cursor()
            qry, sql, ix = " ", list(), list()

            if not is_none(symbol) and is_none(date) and is_none(accion):
                qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND symbol = '%s';"""
                cursor.execute(qry % (account, symbol))
                sql = cursor.fetchall()

            elif not is_none(symbol) and is_none(date) and (accion == "last"):
                qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND symbol = '%s' AND
                                    Date = (SELECT max(Date) FROM diaria_performance 
                                                WHERE account= '%s' AND symbol = '%s');"""
                cursor.execute(qry % (account, symbol, account, symbol))
                sql = cursor.fetchone()

            elif not is_none(symbol) and not is_none(date) and is_none(accion):

                qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date = '%s' AND symbol = '%s';"""
                cursor.execute(qry % (account, symbol, date))
                sql = cursor.fetchall()

            # Query para extraer perfromace global en 3 o 6 ultimos meses
            elif symbol == "all" and not is_none(date) and (accion == "hasta"):
                qry = """SELECT * FROM diaria_performance WHERE Date >= '%s' 
                        ORDER BY Date DESC;"""
                cursor.execute(qry % (date))
                sql = cursor.fetchall()

            elif is_none(symbol) and not is_none(date) and is_none(accion):
                qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date = '%s';"""
                cursor.execute(qry % (account, date))
                sql = cursor.fetchall()

            elif is_none(symbol) and not is_none(date) and (accion == "desde"):
                qry = """SELECT * FROM diaria_performance WHERE account= '%s' AND Date >= '%s';"""
                cursor.execute(qry % (account, date))
                sql = cursor.fetchall()

            elif is_none(symbol) and is_none(date) and is_none(accion):
                qry = """SELECT * FROM diaria_performance WHERE account= '%s' ORDER by date ASC;"""
                cursor.execute(qry % account)
                sql = cursor.fetchall()

            ix = [columna[0] for columna in cursor.description]
            sql = sql if not is_none(sql) else []
            return sql, ix

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_diaria_performance]: {}".format(error))

    def insert_diaria_performance(self, values=None, symbol="SPX"):
        """@param values:   lista de valores de campos a insertar
        @param symbol: ticket a consultar en booktrading
        @return:
        """
        conn = self._conectar(tabla="insert.diaria_performance")
        try:
            cursor = conn.cursor()
            valuesins = list()

            qry = "INSERT INTO diaria_performance ("
            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry += "symbol) VALUES ({});".format(
                ",".join("%s" for _ in range(len(valuesins)))
            )
            cursor.execute(qry, tuple(valuesins))
        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"Mysql:: insert_diaria_performance()]: {error} {qry}={tuple(valuesins)}"
            )
        finally:
            conn.commit()
            cursor.close()


class DiariaCNV(
    BDsystem
):  # --------------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert y update sobre tabla diaria_CNV."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select(self, symbol=None, fecha=None, accion="last"):
        """
        @param symbol: activo a consultar."""

        def last_insert(ticket, date=None):

            if date is None:
                query = """SELECT max(fecha) FROM diaria_CNV WHERE codCAFCI='%s';"""
                cursor.execute(query % ticket)
            else:
                query = """SELECT fecha FROM diaria_CNV WHERE codCAFCI='%s' and fecha='%s';"""
                cursor.execute(query % (ticket, date))

            last = cursor.fetchone()
            u_fecha = "0001-01-01"
            if last:
                u_fecha = last[0].strftime("%Y-%m-%d")
            return u_fecha

        try:
            conn = self._conectar(tabla="select.diaria_CNV")
            found, columns, sql = False, [], []
            cursor = conn.cursor()
            if fecha is not None:
                last_fecha = last_insert(symbol, fecha)

            elif accion == "last":
                last_fecha = last_insert(symbol)

            if symbol is not None:
                qry = """SELECT * FROM diaria_CNV WHERE codCAFCI='%s' and fecha='%s';"""
                cursor.execute(qry % (symbol, last_fecha))
                sql = cursor.fetchone()
                columns = [columna[0] for columna in cursor.description]
                found = True if sql else False

            return sql, columns, found
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_diaria_CNV(): {}]".format(error))

    def insert(self, values=None, symbol=None):
        """
        @param values:  lista de valores de campos a insertar
        @param symbol: ticket a consultar en diaria_CNV
        @return: agrega fila  en diaria_CNV."""
        try:
            conn = self._conectar(tabla="insert.diaria_CNV")
            x, y, found = self.select(symbol=symbol, fecha=values["fecha"])
            if not found:
                cursor = conn.cursor()
                valuesins, qry = [], "INSERT INTO diaria_CNV ("
                for keys, vals in values.items():
                    if keys != "codCAFCI":
                        qry = qry + keys + ", "
                        valuesins.append(vals)

                valuesins.append(symbol)
                qry += "codCAFCI) VALUES ({});".format(
                    ",".join("'%s'" for _ in range(len(valuesins)))
                )
                cursor.execute(qry % tuple(valuesins))
                conn.commit()
                cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: insert_diaria_CNV()]: {}".format(error))

    def update(self, values=None, symbol=None):
        """
        @param values: diccionario con atributos a actualizar
        @param symbol: identificador del activo
        @return: modifica fila tabla diaria_CNV."""
        try:
            conn = self._conectar(tabla="insert.diaria_CNV")
            cursor = conn.cursor()
            valuesins, qry = [], "UPDATE diaria_CNV SET "

            x, y, found = self.select(symbol=symbol, fecha=values["fecha"])
            if found:
                for keys, vals in values.items():
                    if keys != "codCAFCI":
                        qry = qry + keys + "='%s', "
                        valuesins.append(vals)

                valuesins.append(symbol)
                valuesins.append(values["fecha"])

                qry += "WHERE codCAFCI='%s' and fecha = '%s'"
                qry = qry.replace(", WHERE", " WHERE")

                cursor.execute(qry % tuple(valuesins))
                conn.commit()
                cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_diaria_CNV()]: {}".format(error))


class EstrategiaInversion(
    BDsystem
):  # ------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert, read y update sobre tabla Estrategia.
    """

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def read(self):
        """
        @return: construye estructura con a partir JOIN entre inversion y estrategia"""
        try:
            conn = self._conectar(tabla="select.estrategia")
            cursor = conn.cursor()
            estrategia = {}
            qry = """SELECT b.estrategia, b.descripcion, ticket, empresa, peso, costobase, 
                            dividendo, unrealizedpnl, sector, deuda, country, region 
                     FROM (SELECT * FROM inversion WHERE iactiva = 'Y') a 
                     LEFT JOIN  estrategia b ON a.estrategia = b.estrategia
                     ORDER BY a.estrategia;"""

            cursor.execute(qry)
            ix = [column[0] for column in cursor.description]
            sql = cursor.fetchall()
            if sql:
                ebook = enumerate(sql)
                eof_book, read = next(ebook, (None, None))
                xlist, clave = [], read[ix.index("descripcion")]

                while eof_book is not None:
                    if clave != read[ix.index("descripcion")]:
                        estrategia.update({clave: xlist})
                        clave = read[ix.index("descripcion")]
                        xlist = []

                    rows = {
                        "symbol": read[ix.index("ticket")],
                        "empresa": read[ix.index("empresa")],
                        "peso": read[ix.index("peso")],
                        "costobase": read[ix.index("costobase")],
                        "dividendo": read[ix.index("dividendo")],
                        "unrealizedpnl": read[ix.index("unrealizedpnl")],
                        "sector": read[ix.index("sector")],
                        "deuda": read[ix.index("deuda")],
                        "country": read[ix.index("country")],
                        "region": read[ix.index("region")],
                    }
                    xlist.append(rows)

                    eof_book, read = next(ebook, (None, None))

                # por eof()
                if eof_book is None:
                    estrategia.update({clave: xlist})

            cursor.close()
            conn.close()
            return estrategia
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: Estrategia.read()]: {}".format(error))

    def select(self, accion=None, ticket=None, ivehiculo=None):
        """
        @param accion: que es solicitado a la función: Delete, Estrategia, Tabla, Select
        @param ticket: nombre del symbol
        @param ivehiculo: tipo de inversión
        @return: lista de registros de la tabla estrategia JOIN inversión."""
        try:
            conn = self._conectar(tabla="select.inversion")
            cursor = conn.cursor()
            qry, sql, xlis = None, None, []

            if accion == "detalle":
                qry = """SELECT * FROM inversion WHERE iactiva="Y" ORDER BY ticket"""

            if accion == "estrategia":
                qry = """SELECT a.*, b.descripcion FROM (SELECT DISTINCT estrategia 
                                                         FROM bdinv.inversion where iactiva = 'Y')
                                a JOIN  (SELECT * FROM estrategia WHERE vehiculo = '{}') b 
                                ON a.estrategia = b.estrategia;""".format(
                    ivehiculo
                )

            if accion == "tabla":
                qry = """SELECT * FROM estrategia ORDER BY estrategia"""

            if accion == "Select":
                qry = "SELECT objetivo FROM inversion  WHERE ticket ='%s';" % ticket

            cursor.execute(qry)
            sql = cursor.fetchall()
            columnas = [columna[0] for columna in cursor.description]

            if sql:
                if accion == "detalle":
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)

                if accion == "tabla":
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)

                if accion == "estrategia":
                    for fila in sql:
                        xlis.append(fila[0] + " - " + fila[1])

                if accion == "Select":
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)

            return xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: Estrategia.Select()]: {}".format(error))


class MarketScreen(
    BDsystem
):  # -------------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert y update sobre tabla Market."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select(
        self, account=None, tipo=None, symbol=None, country=None, sector=None, name=None
    ):
        """@param account: id de cuenta inversionista
        @param tipo: tipo de inversion: Dividends y crecimiento
        @param symbol: activo a consultar
        @param country: pais a consultar
        @param sector: sector productivo a consultar
        @param name: busca por shortname y entrega lista
        @return: de activos con alto rendimiento y/o mejor momento e inversión."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        qry, sql, ix = " ", [], []
        try:

            if not is_none(symbol) and is_none(name):
                qry = """SELECT * FROM market WHERE account= '%s' AND symbol = '%s';"""
                cursor.execute(qry % (account, symbol))
                sql = cursor.fetchall()

            if not is_none(symbol) and not is_none(name):

                qry = """SELECT * FROM market WHERE account= '%s' AND shortname LIKE '%s' OR symbol = '%s';"""
                key = name + "%"
                cursor.execute(qry % (account, key.upper(), symbol.upper()))
                sql = cursor.fetchall()

            if (
                is_none(symbol)
                and is_none(name)
                and is_none(country)
                and is_none(sector)
            ):
                qry = """SELECT  * FROM market WHERE account= '%s' AND tipo = '%s';"""
                cursor.execute(qry % (account, tipo))
                sql = cursor.fetchall()

            if (
                is_none(symbol)
                and is_none(name)
                and not is_none(country)
                and is_none(sector)
            ):
                qry = (
                    """SELECT  * FROM market WHERE account= '%s' AND country = '%s';"""
                )
                cursor.execute(qry % (account, country))
                sql = cursor.fetchall()

            if (
                is_none(symbol)
                and is_none(name)
                and is_none(country)
                and not is_none(sector)
            ):
                qry = """SELECT  * FROM market WHERE account= '%s' AND sector = '%s';"""
                cursor.execute(qry % (account, sector))
                sql = cursor.fetchall()

            ix = [columna[0] for columna in cursor.description]
            return sql, ix
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_market]: {}".format(error))

    def insert(self, upd=None, val=None, symbol=None):
        """
        @param upd:  list() de campos para insertar en market
        @param val:  list() de valores que acompañan a upd
        @param symbol: symbol o ticket que se inserta en market
        @return:  Agrega fila a partir de symbol y campos pasados como parameter
        """
        try:
            conn = self._conectar(tabla="insert.market")
            cursor = conn.cursor()
            listvalues = []
            cursor.execute("SELECT MAX(id) FROM market")
            row = cursor.fetchone()
            listvalues.append(row[0] + 1 if not is_none(row[0]) else 0)

            qry = "INSERT INTO market (id, "

            for i, value in enumerate(val):
                if upd[i] in ("sector", "country"):
                    if value == "None":
                        listvalues.append("SV")
                    else:
                        listvalues.append(value)
                else:
                    listvalues.append(value)
                qry = qry + upd[i] + ", "

            listvalues.append(datetime.now())
            listvalues.append(symbol)
            valuesins = tuple(listvalues)
            qry += "timestamp, symbol) VALUES ({});".format(
                ", ".join("'%s'" for _ in range(len(valuesins)))
            )
            cursor.execute(qry % valuesins)
            conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql::insert_market()]: {} {}".format(error, qry % valuesins))

    def update(self, upd=None, val=None, symbol=None):
        """
        @param upd:  list() de campos para insertar en market
        @param val:  list() de valores que acompañan a upd
        @param symbol: symbol o ticket que se inserta en market
        @return:  Agrega fila a partir de symbol y campos pasados como parameter
        """
        try:
            conn = self._conectar(tabla="update.market")
            cursor = conn.cursor()
            listvalues = []
            cursor.execute("SELECT MAX(id) FROM market")
            row = cursor.fetchone()
            qry = "UPDATE market SET "

            for i, value in enumerate(val):
                if upd[i] in ("sector", "country"):
                    if value == "None":
                        listvalues.append("SV")
                    else:
                        listvalues.append(value)
                else:
                    listvalues.append(value)

                qry = qry + upd[i] + "='%s',"

            listvalues.append(datetime.now())
            listvalues.append(symbol)
            valuesins = tuple(listvalues)
            qry += "timestamp='%s' WHERE symbol ='%s';"
            cursor.execute(qry % valuesins)
            conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql::insert_market()]: {}".format(error))


class PlanInversion(
    BDsystem
):  # ------------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert y update sobre tabla Plan, TrazaPlan y VariablesPlan.
    """

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select_plan(self, idcuenta=None):
        """
        @param idcuenta: cuenta ID de inversor
        @return: estructura de plan de inversiones."""
        try:
            conn = self._conectar(tabla="select_plan")
            cursor = conn.cursor()
            xlis = []
            qry = """SELECT * from plan WHERE idcuenta = '%s';"""
            cursor.execute(qry % idcuenta)
            sql = cursor.fetchall()
            if sql:
                columnas = [columna[0] for columna in cursor.description]
                for fila in sql:
                    x = dict(zip(columnas, fila))
                    xlis.append(x)
            return xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_plan()]: {}".format(error))

    def select_trazaplan(self, idcuenta=None, orden="ASC"):
        """
        @param idcuenta: cuenta ID de inversor
        @param orden: que orden se entregan los datos
        @return: estructura de plan de inversiones"""
        try:
            conn = self._conectar(tabla="select.trazaplan")
            cursor = conn.cursor()
            qry = """SELECT * from trazaplan WHERE idcuenta = '%s' 
                      ORDER BY meta %s;"""
            cursor.execute(qry % (idcuenta, orden))
            sql, xlis = cursor.fetchall(), []
            if sql:
                columnas = [columna[0] for columna in cursor.description]
                for fila in sql:
                    x = dict(zip(columnas, fila))
                    xlis.append(x)
            return xlis
        except (Exception, EncodingWarning) as error:
            print("[Mysql:: select_trazaplan()]: {}".format(error))

    def update_plan_inversion(self, idcuenta=None, vision="deseada", values=None):
        """
        @param idcuenta: cuenta ID de inversor
        @param vision: tipo de visión a actualizar para el plan
        @param values: dict() con información para actualizar."""

        def update_traza():
            traza = self.select_trazaplan(idcuenta, orden="DESC")

            if traza:
                inversion, campos = values["Financiera"], {}

                for i, key in enumerate(traza):
                    campos["vision"] = inversion
                    campos["efectividad"] = 0.0
                    campos["trendimiento"] = 0.0

                    if key["tinversion"] > 0:
                        campos["efectividad"] = (
                            key["tinversion"] - key["vision"]
                        ) / key["vision"]
                        campos["trendimiento"] = (
                            key["dividendo"] + key["ccapital"]
                        ) / key["tinversion"]

                    inversion = int(inversion / 2)
                    self.update_trazaplan_inversion(
                        idcuenta=idcuenta, meta=key["meta"], values=campos
                    )

        try:
            conn = self._conectar(tabla="update.trazaplan")
            cursor = conn.cursor()

            # actualiza deseada o actual de la cuenta de inversión
            if vision == "deseada":
                qry = """UPDATE plan SET deseada = '%s', timestamp = '%s' WHERE idcuenta = '%s' AND vision = '%s';"""

            if vision == "actual":
                qry = """UPDATE plan SET actual = '%s', timestamp = '%s' WHERE idcuenta = '%s' AND vision = '%s';"""

            found = self.select_plan(idcuenta=idcuenta)
            if found:
                for keys, val in values.items():
                    valuesupd = [val, datetime.now(), idcuenta, keys]
                    cursor.execute(qry % tuple(valuesupd))

                # si es deseada ajusta trazaplan
                if vision == "deseada":
                    update_traza()

                conn.commit()
                cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_plan_inversion()]: {}".format(error))

    def update_trazaplan_inversion(self, idcuenta=None, meta=None, values=None):
        """
        @param idcuenta: cuenta ID de inversor
        @param meta: Identificación de registro a modificar
        @param values: dict() con información para actualizar."""
        try:
            conn = self._conectar(tabla="update.trazaplan")
            cursor = conn.cursor()
            qry = """UPDATE trazaplan SET """
            valuesupd = []
            for keys, val in values.items():
                qry = qry + keys + "='%s', "
                valuesupd.append(val)

            valuesupd.append(datetime.now())
            valuesupd.append(idcuenta)
            valuesupd.append(meta)
            qry += "timestamp='%s' WHERE idcuenta ='%s' AND meta = '%s';"

            cursor.execute(qry % tuple(valuesupd))
            conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_trazaplan_inversion()]: {}".format(error))

    def select_variablesplan(self, idcuenta):
        """
        @param idcuenta: cuenta ID de inversor
        @return: retornas las variables asociadas al plan."""
        try:
            conn = self._conectar(tabla="select_variablesplan")
            cursor = conn.cursor()
            xlis, sql, qry = (
                [],
                None,
                """SELECT * from variablesplan WHERE idcuenta = '%s';""",
            )
            cursor.execute(qry % idcuenta)
            sql = cursor.fetchall()
            if sql:
                columnas = [columna[0] for columna in cursor.description]
                for fila in sql:
                    x = dict(zip(columnas, fila))
                    xlis.append(x)
            return xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_variablesplan()]: {}".format(error))

    def select_extracto(self, account=None, extract="last") -> dict:
        """
        @param account: id de cuenta de inversión
        @param extract: fecha o extract de extracto a consultar
        @return: lista de registros seleccionados."""
        try:
            conn = self._conectar(tabla="select.extracto")
            cursor = conn.cursor()
            xlis = []

            if extract == "last":
                qry = """SELECT * FROM extractos WHERE idcuenta='%s' ORDER BY extracto DESC;"""
                cursor.execute(qry % account)
                sql = cursor.fetchone()

            elif extract == "sum":
                qry = """SELECT sum(depositos), sum(retiros), sum(crecimiento), sum(dividendos), sum(perdidas),
                                sum(fee), sum(comisiones), sum(tax), sum(idevengo), sum(imargen)
                         FROM extractos WHERE idcuenta='%s'
                                          AND year(extracto) = (SELECT MAX(year(extracto)) FROM extractos);"""
                cursor.execute(qry % account)
                sql = cursor.fetchone()

            elif extract == "fiscal":
                hasta = datetime.now().date()
                year = hasta.year - 1
                desde = datetime.strptime(str(year) + "-08-31", "%Y-%m-%d").date()
                qry = """SELECT sum(depositos), sum(retiros), sum(crecimiento), sum(dividendos), sum(perdidas),
                                sum(fee), sum(comisiones), sum(tax), sum(idevengo), sum(imargen), avg(cierreanterior)
                         FROM extractos WHERE idcuenta='%s'
                                          AND extracto >= '%s' and extracto <= '%s';"""
                cursor.execute(qry % (account, desde, hasta))
                sql = cursor.fetchone()

            elif extract == "select*":
                qry = """SELECT * FROM extractos WHERE idcuenta='%s' ORDER BY extracto DESC;"""
                cursor.execute(qry % account)
                sql = cursor.fetchall()

            elif extract == "sum*":
                qry = """SELECT extracto, sum(depositos) depositos, sum(retiros) retiros, sum(crecimiento) crecimiento, 
                                          sum(dividendos) dividendos, sum(perdidas) perdidas, sum(fee) fee, 
                                          sum(comisiones) comisiones, sum(tax) tax, sum(cierreanterior) cierreanterior,
                                          sum(idevengo) idevengo, sum(navcierre) navcierre, sum(costobase) costobase, 
                                          sum(imargen) imargen
                           FROM bdinv.extractos GROUP BY extracto 
                                                ORDER BY extracto DESC;"""
                cursor.execute(qry)
                sql = cursor.fetchall()

            else:
                # if extract not in ('last', 'sum', 'fiscal', 'select*'):
                qry = """SELECT * FROM extractos WHERE idcuenta='%s' AND extracto = '%s';"""
                cursor.execute(qry % (account, extract))
                sql = cursor.fetchone()

            if sql:
                columnas = [columna[0] for columna in cursor.description]
                if extract in ("last", "sum", "fiscal"):
                    xlis.append(dict(zip(columnas, sql)))
                else:
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)
            return xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_extracto()]: {}".format(error))

    def insert_extracto(self, account=None, values=None):
        """
        @param account: id de cuenta de inversión
        @param values:   lista de valores de campos a insertar
        @return:"""

        def insert_account_exists():

            qry = "INSERT INTO extractos (idcuenta, cierreanterior,"
            listvalues.append(account)
            listvalues.append(acierre)
            long = len(values)

            for i, (key, valor) in enumerate(values.items()):
                if key not in ("id", "idcuenta", "cierreanterior"):
                    listvalues.append(valor)
                    if i < long - 1:
                        qry += key + ", "
                    else:
                        qry += key

            valuesins = tuple(listvalues)
            qry += ") VALUES ({});".format(
                ",".join("%s" for _ in range(len(valuesins)))
            )
            cursor.execute(qry, valuesins)

            conn.commit()
            cursor.close()

        try:
            conn = self._conectar(tabla="select.extracto")
            cursor = conn.cursor()
            acierre, id_next = 0.0, 1
            uextract = self.select_extracto(account=account, extract="last")
            if len(uextract) == 1:
                acierre = uextract[0]["navcierre"]

            listvalues = []

            # valida que extracto a ingresar sea consecutivo al ultimo extracto
            if uextract and bool(values):
                if valida_meses_consecutivos(
                    inicio=uextract[0]["extracto"], fin=values["extracto"]
                ):
                    insert_account_exists()
            else:
                # caso cuando la account no tenga extractos previos
                if not is_none(account) and bool(values):
                    insert_account_exists()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: insert_extracto()]: {}".format(error))

    def select_inversion(self, account=None, tipoin: str = "Stock", ticket="all"):
        """
        @param account: id account para el vehículo
        @param tipoin: se indica el tipo de activo
        @param ticket: simbolo específico a consultar
        @return: Lista de activos de la cartera asociada al tipoin, incluye el last - precio
        """
        try:
            conn = self._conectar(tabla="select.inversion")
            cursor = conn.cursor()
            xlis, curs = [], []

            if (account == "selectIA") and (tipoin is None):
                qry = """SELECT *, mrkprice * position as mktvalue FROM inversion 
                        WHERE nivelIA ='01' AND  iactiva = 'Y' AND ticket = '%s';"""
                cursor.execute(qry % ticket)
                curs = cursor.fetchone()

            elif (ticket == "all") and (tipoin == "activo"):
                qry = """SELECT *, mrkprice * position as mktvalue, descripcion as tipoActivo FROM inversion a, estrategia b 
                        WHERE iactiva = 'Y' AND a.estrategia = b.estrategia;"""
                cursor.execute(qry)
                curs = cursor.fetchall()

            elif ticket == "update":
                qry = """SELECT * FROM inversion 
                        WHERE useraccount = '%s' AND tipoinv ='%s';"""
                cursor.execute(qry % (account, tipoin))
                curs = cursor.fetchall()

            elif ticket == "all":
                qry = """SELECT *, mrkprice * position as mktvalue FROM inversion 
                        WHERE tipoinv ='%s' AND  iactiva = '%s';"""
                cursor.execute(qry % (tipoin, "Y"))
                curs = cursor.fetchall()

            elif ticket == "all*":
                qry = """SELECT *, mrkprice * position as mktvalue FROM inversion 
                        WHERE tipoinv ='%s' AND  iactiva = '%s';"""
                cursor.execute(qry % (tipoin, "Y"))
                curs = cursor.fetchall()

            elif ticket == "hist":
                qry = """SELECT *, mrkprice * position as mktvalue FROM inversion 
                        WHERE tipoinv ='%s';"""
                cursor.execute(qry % tipoin)

                curs = cursor.fetchall()
            else:
                qry = """SELECT  * FROM inversion WHERE tipoinv ='%s' AND ticket = '%s';"""
                cursor.execute(qry % (tipoin, ticket))
                curs = cursor.fetchone()

            ix = [column[0] for column in cursor.description]
            if curs:
                if ticket in ("all", "hist", "update"):
                    for row in curs:
                        x = dict(zip(ix, row))
                        xlis.append(x)
                    return xlis

                elif ticket == "all*":
                    return curs[0], ix

                else:
                    xlis.append(dict(zip(ix, curs)))
                    return xlis

            cursor.close()
            conn.close()
            return []
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_inversion()]: {}".format(error))

    # actualiza tabla de cartera
    def update_inversion(self, vehiculo=None, account=None, positions=None):
        """
        @param vehiculo: tipo de cartera "Stock", "Crypto"
        @param account:
        @param positions: cartera activa que se actualiza en inversiones
        @return: actualiza lo que hay positions en inversiones
        """

        def update(keys, ticket):
            try:
                xlistvalues = []
                qry = """UPDATE inversion  SET  position = '%s', peso = '%s', costobase = '%s', conid = '%s', 
                                                sector = '%s', dividendo = '%s', objetivo = '%s', retorno = '%s', 
                                                unrealizedpnl = '%s', dividendYield = '%s', exDividendDate = '%s', 
                                                factor_cambio = '%s', deuda = '%s',  mrkprice = '%s', open = '%s', 
                                                dgyp = '%s', iactiva = '%s', empresa = '%s', region = '%s',
                                                country = '%s', timestamp = '%s' 
                        WHERE ticket ='%s' AND useraccount ='%s';"""

                factor = keys["factor_cambio"] if "factor_cambio" in keys else 1
                xlistvalues.append(keys["position"])
                xlistvalues.append(keys["peso"])
                xlistvalues.append(keys["costobase"])
                xlistvalues.append(keys["conid"])
                xlistvalues.append(keys["sector"])

                if vehiculo == "Stock":
                    xlistvalues.append(keys["dividendo"] * keys["position"])
                elif vehiculo == "Crypto":
                    xlistvalues.append(keys["dividendo"])
                else:
                    xlistvalues.append(keys["dividendo"])

                xlistvalues.append(keys["objetivo"])
                xlistvalues.append(keys["retorno"])
                xlistvalues.append(keys["unrealizedpnl"])
                xlistvalues.append(keys["dividendYield"])
                xlistvalues.append(keys["exDividendDate"])
                xlistvalues.append(factor)
                xlistvalues.append(keys["deuda"])
                xlistvalues.append(keys["mrkprice"])
                xlistvalues.append(keys["open"])
                xlistvalues.append(keys["dgyp"])

                # da baja si position == 0 or retorno < .001
                Debaja = keys["position"] == 0 or (1 - keys["retorno"]) < 0.001
                xlistvalues.append("N" if Debaja else "Y")
                xlistvalues.append(keys["empresa"])
                xlistvalues.append(keys["region"] if "region" in keys else "")
                xlistvalues.append(keys["country"] if "country" in keys else "")
                xlistvalues.append(datetime.now())

                xlistvalues.append(ticket)
                xlistvalues.append(account)
                valuesupd = tuple(xlistvalues)
                cursor.execute(qry % valuesupd)
            except Exception as e:
                print(
                    "[update_inversion.update({})]: {} - {}={}".format(
                        vehiculo, e, qry, valuesupd
                    )
                )

        def insert(keys, ticket):
            try:
                found = self.select_inversion(tipoin=vehiculo, ticket=ticket)
                if not found:
                    qry = """INSERT INTO inversion (ticket, iactiva, fealta, febaja, estrategia, empresa, costobase, conid, 
                                                            mrkprice, position, sector, exDividendDate, factor_cambio,
                                                            divisa, tipoinv, useraccount, region, country"""
                    fectime = datetime.now()
                    exdiv = (
                        keys["exDividendDate"]
                        if "exDividendDate" in keys
                        else "9999-12-31"
                    )
                    factor = keys["factor_cambio"] if "factor_cambio" in keys else 1
                    divisa = keys["divisa"] if "divisa" in keys else "USD"
                    region = keys["region"] if "region" in keys else ""
                    country = keys["country"] if "country" in keys else ""
                    ylistvalues = [
                        ticket,
                        "Y",
                        fectime.date(),
                        "9999-12-31",
                        keys["estrategia"],
                        keys["empresa"],
                        keys["costobase"],
                        keys["conid"],
                        keys["mrkprice"],
                        keys["position"],
                        keys["sector"],
                        exdiv,
                        factor,
                        divisa,
                        vehiculo,
                        account,
                        region,
                        country,
                        str(datetime.now()),
                    ]

                    valuesins = tuple(ylistvalues)
                    qry += ", timestamp) VALUES ({});".format(
                        ",".join("%s" for _ in range(len(valuesins)))
                    )
                    cursor.execute(qry, valuesins)

            except Exception as e:
                print("[update_inversion.insert({})]: {}".format(vehiculo, e))

        def baja(keys):
            try:
                xlistvalues = []
                qry = """UPDATE inversion  SET  iactiva = '%s', timestamp = '%s' 
                        WHERE ticket ='%s' AND useraccount ='%s';"""

                xlistvalues.append("N")
                xlistvalues.append(datetime.now())

                xlistvalues.append(keys)
                xlistvalues.append(account)
                valuesupd = tuple(xlistvalues)
                cursor.execute(qry % valuesupd)
            except Exception as e:
                print("[update_inversion.baja({})]: {}".format(vehiculo, e))

        try:
            conn = self._conectar(tabla="update.inversion")
            cursor = conn.cursor()

            # recupera cartera actual
            cartera = self.select_inversion(
                account=account, tipoin=vehiculo, ticket="update"
            )

            # enumera new positions para el apareamiento
            orden = [{"ticket": "ticket"}, "ASC"]
            in_cartera = sort_positions(cartera, orden)

            old = enumerate(in_cartera)
            eof_old, old_position = next(old, (None, None))

            # enumera new positions para el apareamiento
            orden = [{"ticket": "ticket"}, "ASC"]
            in_positions = sort_positions(positions, orden)

            new = enumerate(in_positions)
            eof_new, new_position = next(new, (None, None))

            # aparea positions y assets para construir positions actualizada
            while (eof_old is not None) and (eof_new is not None):

                # actualiza position
                if old_position["ticket"] == new_position["ticket"]:

                    update(new_position, new_position["ticket"])
                    eof_old, old_position = next(old, (None, None))
                    eof_new, new_position = next(new, (None, None))
                else:
                    # inserta position
                    if old_position["ticket"] > new_position["ticket"]:

                        insert(new_position, new_position["ticket"])
                        eof_new, new_position = next(new, (None, None))
                    else:
                        # inactiva position
                        if old_position["iactiva"] == "Y":
                            baja(old_position["ticket"])

                        eof_old, old_position = next(old, (None, None))

            # cuando sea nueva cartera y no tenga historia
            if eof_new is not None:
                while eof_new is not None:
                    insert(new_position, new_position["ticket"])
                    eof_new, new_position = next(new, (None, None))

            conn.commit()
            cursor.close()
            conn.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_inversion({})]: {}".format(vehiculo, error))

    def select_otros_activos(
        self,
        symbol=None,
        idSymbol=None,
        account=None,
    ):
        """
        @param symbol:
        @param account:
        @return: retorna list() de asset."""
        try:
            conn = self._conectar(tabla="select.otros_activos")
            cursor = conn.cursor()
            qry, sql, found, desc, xlis = None, None, False, None, []

            if symbol == "all" and account is None:
                qry = "SELECT * FROM otros_activos;"
                cursor.execute(qry)
                sql = cursor.fetchall()

            elif symbol == "all" and account is not None:
                qry = "SELECT * FROM otros_activos where cuenta = '%s';"
                cursor.execute(qry % account)
                sql = cursor.fetchall()

            elif idSymbol is not None:
                qry = "SELECT * FROM otros_activos WHERE idcrypto = %s;"
                cursor.execute(qry, idSymbol)
                sql = cursor.fetchone()

            else:
                qry = "SELECT * FROM otros_activos WHERE symbol = %s;"
                cursor.execute(qry, symbol)
                sql = cursor.fetchone()

            if sql:
                found = True
                ix = [columna[0] for columna in cursor.description]

                if idSymbol is not None:
                    xlis.append(dict(zip(ix, sql)))

                elif symbol != "all":
                    xlis.append(dict(zip(ix, sql)))

                elif symbol == "all":
                    for keys in sql:
                        xlis.append(dict(zip(ix, keys)))

            return xlis, found
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_otros_activos()]: {}".format(error))
        finally:
            cursor.close()
            conn.close()

    def update_otros_activos(self, values=None, symbol=None):
        """
        @param values:
        @param symbol:
        @return: actualiza taraba otros_activos."""
        try:
            conn = self._conectar(tabla="update.crypto")
            cursor = conn.cursor()
            valuesins = []
            qry = "UPDATE otros_activos SET "

            found = self.select_otros_activos(symbol=symbol)
            if found:

                for keys, vals in values.items():

                    qry = qry + keys + "='%s', "
                    valuesins.append(vals)

                valuesins.append(symbol)
                qry += "WHERE symbol='%s';"
                qry = qry.replace(", WHERE", " WHERE")

                valuesupd = tuple(valuesins)
                cursor.execute(qry % valuesupd)
            conn.commit()
            cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_otros_activos()]: {}".format(error))

    # get info from en formato yfinance into otros_activos
    def get_yf_CNV(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None
    ):
        """
        Simula la función yf.download, extrayendo datos de rendimiento y volumen
        calculado de la tabla 'diaria_cnv' de MySQL.

        Args:
            symbol (str): El codCAFCI (ej. 'FCI001').
            start (str, opcional): Fecha de inicio para el filtro (YYYY-MM-DD).
            end (str, opcional): Fecha de fin para el filtro (YYYY-MM-DD).

        Returns:
            pd.DataFrame: DataFrame con las columnas 'Close' y 'Volume',
                        indexado por 'Date'.
        """

        # obtiene idcrypto desde tabla otros_activos
        OtrActivos, found = self.select_otros_activos(symbol=symbol)

        # 1. Construir la consulta SQL con los cálculos y el filtro principal
        sql_query = f"""
        SELECT
            fecha AS Date,
            valorAnterior/1000 Open, 
            GREATEST(valorAnterior, valoractual)/1000 High , 
            LEAST(valorAnterior, valoractual)/1000 Low, 
            valorActual / 1000 AS Close,
            TRUNCATE(patrimonioActual / valorActual, 0) AS Volume
        FROM
            diaria_cnv
        WHERE
            codCAFCI = '{OtrActivos[0]["idcrypto"]}'
        """

        # 2. Añadir filtros de fecha si se proporcionan
        if start:
            sql_query += f" AND fecha >= '{start}'"

        elif start is None:
            inicio = datetime.now() - timedelta(days=365)
            desde = inicio.strftime("%Y-%m-%d")
            sql_query += f" AND fecha >= '{desde}'"

        if end:
            sql_query += f" AND fecha <= '{end}'"
        elif end is None:
            sql_query += f" AND fecha <= CURDATE()"

        sql_query += " ORDER BY fecha ASC"  # Es buena práctica ordenar por fecha

        # 3. Conexión y ejecución (Bloque robusto try...except)
        try:
            # Intentar establecer la conexión
            db_uri = f"mysql+pymysql://{BDsystem.DB_CONFIG.get("user")}:{BDsystem.DB_CONFIG.get("password")}"
            db_uri += f"@{BDsystem.DB_CONFIG.get("host")}/{BDsystem.DB_CONFIG.get("database")}"

            # Usar pd.read_sql_query para ejecutar el query y obtener el DataFrame directamente
            df = pd.read_sql_query(sql_query, db_uri)

            # 4. Formatear la salida (como un resultado de yfinance)
            if not df.empty:
                df.set_index("Date", inplace=True)
                df.index = pd.to_datetime(df.index)

            return df

        except (Exception, EncodingWarning, connect.Error) as e:
            print(f"get_yf_CNV(): {e}")
            return pd.DataFrame()  # Devolver DataFrame vacío en caso de error

    def insert_otros_activos(self, symbol=None, values=None):
        """
        @param symbol: ticket a consultar en crypto
        @return: agrega symbol en tabla otros_activos."""
        try:
            conn = self._conectar(tabla="insert.otros_activos")
            cursor = conn.cursor()
            valuesins = list()
            qry, values, xlis, found = " ", dict(), list(), False
            ix = (
                "cuenta",
                "idcrypto",
                "descripcion",
                "base_asset",
                "quote_asset",
                "objetivo",
                "fecupdate",
            )
            row, found = self.select_otros_activos(symbol=symbol)

            if not found:

                ticket = yf.Ticker(symbol.replace("USDT", "-USD"))
                name = ticket.info["name"] if "name" in ticket.info else " "
                avg = (
                    ticket.info["previousClose"]
                    if "previousClose" in ticket.info
                    else 0
                )
                h52w = (
                    ticket.info["fiftyTwoWeekHigh"]
                    if "fiftyTwoWeekHigh" in ticket.info
                    else 0
                )

                qry = "INSERT INTO otros_activos ("

                values.update({"cuenta": "B0000001"})
                values.update({"idcrypto": np.random.randint(1, 10000001)})
                values.update({"descripcion": name})
                values.update({"base_asset": symbol.replace("USDT", "")})
                values.update({"quote_asset": "USDT"})
                values.update({"avgcost": avg})
                values.update({"objetivo": h52w})
                values.update({"fecupdate": datetime.now()})

                for keys, vals in values.items():
                    qry = qry + keys + ", "
                    valuesins.append(vals)

                valuesins.append(symbol)
                qry += "symbol) VALUES ({});".format(
                    ",".join("%s" for _ in range(len(valuesins)))
                )
                cursor.execute(qry, tuple(valuesins))
                xlis.append(values)

            else:
                xlis.append(dict(zip(ix, row))["cuenta"])
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql::  insert_otros_activos()]: {}".format(error))

        conn.commit()
        cursor.close()
        return xlis, found

    def insert_split(self, symbol=None, values=None):
        """
        @param symbol:
        @param values: dict() con información de campos a actualizar
        @return:"""
        try:
            conn = self._conectar(tabla="select.split")
            cursor = conn.cursor()
            sql = "SELECT * FROM split Where ticket='%s' and date='%s';"
            valuesins = list()
            qry, found = " ", False

            cursor.execute(sql % (symbol, values["date"]))
            found = cursor.fetchone()
            if not found:

                qry = "INSERT INTO split ("

                for keys, vals in values.items():
                    qry = qry + keys + ", "
                    valuesins.append(vals)

                valuesins.append(symbol)
                qry += "ticket) VALUES ({});".format(
                    ",".join("'%s'" for _ in range(len(valuesins)))
                )
                cursor.execute(qry, tuple(valuesins))

            conn.commit()
            cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: insert_split()]: {}".format(error))

    def select_split(self, symbol="all") -> list:
        """
        @param symbol:
        @return:"""
        try:
            conn = self._conectar(tabla="select.split")
            cursor = conn.cursor()
            sql, ix, found = " ", list(), False

            if symbol == "all":
                sql = """SELECT * FROM split Where aplicado ='N';"""
                cursor.execute(sql)
            else:
                sql = """SELECT * FROM split Where aplicado ='N' AND ticket = '%s';"""
                cursor.execute(sql % symbol)

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_split()]: {}".format(error))

        found = cursor.fetchall()
        ix = [columna[0] for columna in cursor.description]
        return found, ix


class RepositorioOportunidadesBuySell(
    PlanInversion
):  # -------------------------------------------------------------
    """
    -- Class de oportunidades generadas, acciones y trading realziados."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None) -> object:
        try:
            conn = BDsystem.connect_dbase(tabla, display=self.display)
            return conn
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: RepositorioOportunidadesBuySell_conectar(): {error}]")

    # consulta oportunidades por tipo, subtipo y estado
    def obtener_por_tipo(self, tipo="sell", subtipo=None, estado=None):
        sql = "SELECT * FROM oportunidadesbuysell WHERE tipo = %s"
        params = [tipo]
        if subtipo:
            sql += " AND subtipo = %s"
            params.append(subtipo)

        if estado:
            sql += " AND estado = %s"
            params.append(estado)

        with self._conectar(tabla="oportunidadesbuysell") as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            return cursor.fetchall(), columns

    # consulta oportunidades por symbol
    def obtener_por_symbol(self, symbol):
        sql = "SELECT * FROM oportunidadesbuysell WHERE symbol = %s"
        with self._conectar(tabla="oportunidadesbuysell") as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (symbol,))
            return cursor.fetchall()

    # Elimina oportunidades por hash_id
    def eliminar_por_hash(self, hash_id):
        sql = "DELETE FROM oportunidadesbuysell WHERE hash_id = %s"
        with self._conectar(tabla="oportunidadesbuysell") as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (hash_id,))
            conn.commit()

    # Elimina por inciio de sesión, tipo y subtipo
    def eliminar_por_estado(self, estado, tipo, subtipo):
        sql = "DELETE FROM oportunidadesbuysell WHERE estado = %s AND tipo = %s AND subtipo = %s"
        with self._conectar(tabla="oportunidadesbuysell") as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (estado, tipo, subtipo))
            conn.commit()

    @staticmethod
    def generar_hash_id(
        account, symbol, option, fecha=None, tipo=None, subtipo=None, recomendado=None
    ):
        try:
            date = fecha if fecha is not None else datetime.now().strftime("%Y-%m-%d")
            hash_id = (
                f"{account}_{symbol}_{option}_{date}_{tipo}_{subtipo}_{recomendado}"
            )
            return hashlib.md5(hash_id.encode()).hexdigest()

        except (Exception, EncodingWarning, connect.Error) as e:
            print(f"evaluar_generar_hash_id(): {e}")

    # Verifica si ya existe una oportunidad con tolerancia en el ROI
    def ya_existe_con_tolerancia(
        self, symbol, option, fecha, nuevo_roi, tolerancia=0.10
    ):
        try:
            sql = """
                SELECT json_detalle->>'$.roi' AS roi
                FROM oportunidadesbuysell
                WHERE symbol = %s AND opcion = %s AND fecha = %s AND tipo = 'sell' AND estado = 'pendiente' AND enviada < 2
                ORDER BY timestamp DESC
                LIMIT 1
            """
            with self._conectar(tabla="oportunidadesbuysell") as conn:
                # cursor = conn.cursor(dictionary=True)
                cursor = conn.cursor()
                cursor.execute(sql, (symbol, option, fecha))
                resultado = cursor.fetchone()

                # Si hay un resultado, verifica la tolerancia del ROI
                if resultado and resultado[0]:
                    roi_existente = float(resultado[0])
                    diferencia = abs(nuevo_roi - roi_existente) / max(
                        abs(roi_existente), 1e-6
                    )
                    return diferencia <= tolerancia
                return False
        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"[Mysql:: RepositorioOportunidadesBuySell.ya_existe_con_tolerancia(): {error}]"
            )

    # Detalle de oportunidad de venta
    def detalle_OportunidadSell(self, origen, grafico_url=None, row=None):

        detalle = {
            "profit": row.get("Profit"),
            "roi": row.get("%Roi"),
            "Confianza": row.get("confianza", 0),
            "Nro_lotes": row.get("NroLotes"),
            "cantidad_sell": row.get("CantidadSell"),
            "price_market": row.get("PriceMarket"),
            "costo_acumulado": row.get("CostoCum"),
            "costo_base": row.get("CostoBase"),
            "position": row.get("Position"),
            "Disponible": row.get("Disponible"),
            "Pos_AvgCost": row.get("PosAvgCost"),
            "Pos_Position": row.get("PosPosition"),
            "Pos_CostBase": row.get("PosCostobase"),
            "recomendado": row.get("Recomendado"),
            "comentarios": row.get("Comentarios"),
            "indicadores": row.get("Datostecnicos") or {},
            "grafico_url": grafico_url,
            "otros": {"modelo": origen, "timestamp_local": str(datetime.now())},
        }
        return json.dumps(detalle)

    # Inserta una nueva oportunidad en la base de datos
    def insertar_sell(
        self,
        row,
        grafico_url=None,
        tipo="sell",
        subtipo=None,
        origen=None,
        tolerancia_roi=0.10,
    ):

        try:
            if tipo == "sell" and self.ya_existe_con_tolerancia(
                row["Symbol"], row["Opcion"], row["Fecha"], row["%Roi"], tolerancia_roi
            ):
                return False

            hash_id = self.generar_hash_id(
                row.get("account"),
                row.get("Symbol"),
                row.get("Opcion"),
                row.get("Fecha"),
                tipo,
                subtipo,
                row.get("Recomendado"),
            )
            detalle = self.detalle_OportunidadSell(origen, grafico_url, row)

            sql = """
                    INSERT IGNORE INTO oportunidadesbuysell
                    (symbol, account, vehiculo, opcion, tipo, subtipo, origen, hash_id, 
                    recomendado, estado, fecha, nota, json_detalle)
                    VALUES (%s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s)
                """

            datos = (
                row["Symbol"],
                row["account"],
                row["vehiculo"],
                row["Opcion"],
                tipo,
                subtipo,
                origen,
                hash_id,
                row.get("Recomendado"),
                "pendiente",
                row["Fecha"],
                row.get("Comentarios"),
                detalle,
            )

            with self._conectar(tabla="insert.oportunidadesbuysell") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, datos)
                conn.commit()
                return True
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: RepositorioOportunidadesBuySell.insert(): {error}]")
            return False

    # update de una oportunidad existente
    def actualizar_oportunidad(
        self, hash_id=None, estado=None, origen=None, tipo=None, subtipo=None, row=None
    ):
        try:
            # caso de actualización con hash_id (actualiza oportunidad específica)
            if hash_id is not None:
                sql = """
                    UPDATE oportunidadesbuysell
                    SET json_detalle = %s, timestamp = NOW()
                    WHERE hash_id = %s AND estado = %s
                """
                detalle = self.detalle_OportunidadSell(origen=origen, row=row)
                datos = (detalle, hash_id, estado)

            # caso de actualización sin hash_id (actualiza la última oportunidad pendiente)
            if hash_id is None:
                sql = """
                    UPDATE oportunidadesbuysell
                    SET json_detalle = %s, timestamp = NOW(), hash_id = %s, fecha = %s
                    WHERE account = %s AND symbol = %s AND opcion = %s AND estado = 'pendiente'
                """
                account = row.get("account", "")
                symbol = row.get("Symbol", "")
                opcion = row.get("Opcion", "")
                fecha = row.get("Fecha", "")

                # genera nuevo hash_id
                hash_id = self.generar_hash_id(
                    account,
                    symbol,
                    opcion,
                    fecha,
                    tipo,
                    subtipo,
                    row.get("Recomendado"),
                )

                detalle = self.detalle_OportunidadSell(origen=origen, row=row)
                datos = (detalle, hash_id, fecha, account, symbol, opcion)

            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, datos)
                rows_afectadas = cursor.rowcount
                conn.commit()

                # True si se actualizó al menos una fila, False si no se encontró la oportunidad
                return True if rows_afectadas > 0 else False

        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"[Mysql:: RepositorioOportunidadesBuySell.actualizar_oportunidad(): {error}]"
            )

    # establec enlace entre oportunidad y buySell
    def registrar_venta(self, recom_id, precio_venta, ganancia_real, comentario=""):
        sql = """
            INSERT INTO accionoportunidades (recom_id, precio_venta, ganancia_real, comentario)
            VALUES (%s, %s, %s, %s)
        """
        with self._conectar(tabla="accionoportunidades") as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (recom_id, precio_venta, ganancia_real, comentario))
            conn.commit()

    def obtener_id_por_hash(self, hash_id):
        sql = """SELECT O.*, conid, mrkprice FROM oportunidadesbuysell as O, inversion 
                  WHERE hash_id = %s AND useraccount = account  AND tipoinv = vehiculo AND ticket = symbol;"""

        with self._conectar(tabla="accionoportunidades") as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (hash_id,))
            row = cursor.fetchone()
            ix = [columna[0] for columna in cursor.description]
            return row, ix if row else None

    # marca una oportunidad como rechazada
    def marcar_oportunidad(
        self,
        hash_id,
        recomendado=-1,
        estado="rechazada",
        razon="Rechazada manualmente.",
    ):
        try:
            sql = """
                UPDATE oportunidadesbuysell
                SET recomendado = %s,
                    estado = %s,
                    enviada = 2,
                    nota = %s,
                    json_detalle = JSON_SET(
                        json_detalle,
                        '$.recomendado', %s
                    )
                WHERE hash_id = %s
            """
            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (recomendado, estado, razon, recomendado, hash_id))
                conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"[Mysql:: RepositorioOportunidadesBuySell.marcar_oportunidad(): {error}]"
            )

    def obtener_no_enviadas(self, limite=15):
        try:
            sql = """
                SELECT id, hash_id, symbol, opcion, origen, json_detalle
                FROM oportunidadesbuysell
                WHERE enviada = FALSE AND estado = 'pendiente'
                ORDER BY timestamp
                LIMIT %s
            """
            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (limite,))
                ix = [columna[0] for columna in cursor.description]

                return cursor.fetchall(), ix
        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"[Mysql:: RepositorioOportunidadesBuySell.obtener_no_enviadas(): {error}]"
            )

    def marcar_como_enviada(self, hash_id):
        try:
            sql = "UPDATE oportunidadesbuysell SET enviada = TRUE WHERE hash_id = %s"
            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (hash_id,))
                conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print(
                f"[Mysql:: RepositorioOportunidadesBuySell.marcar_como_enviada(): {error}]"
            )

    # return: lista de registros seleccionados
    def select_booktrading(
        self,
        accion="last",
        account="B0000001",
        idivisa="USD",
        idtrans=None,
        fecha=None,
        hasta=None,
        symbol=None,
        hash_id=None,
    ):
        """@param accion: tipo de consultar
        @param account: id cuenta de inversion
        @param idivisa: ticket a consultar en booktrading
        @param fecha: fecha de consults
        @param symbol: ticket a consultar en booktrading
        @param idtrans: Nro de transaction
        @param fecha: fecha de transaction
        @param hasta: fecha hasta de transaction
        @param hash_id: identificador unico
        @return: lista de registros seleccionados."""

        try:
            conn = self._conectar(tabla="select.booktrading")
            cursor = conn.cursor()
            xlist, sql = list(), None
            if accion == "inc_BTC":
                qry = """SELECT min(fecha_hora) FROM booktrading;"""
                cursor.execute(qry)
                sql = cursor.fetchone()

            # cálculo de precio medio solo se toma stock y basico de última operación suma(producto, comisiones)
            elif accion == "last":

                # ultima diaria para un determinado symbol
                if symbol is not None:
                    qry = """SELECT a.* FROM (SELECT sec, fechahora, stock, basico, gprealizadas, cantidad, 
                                                    tarifacomision, idtrans, position_inversion, factor_cambio
                                            FROM booktrading WHERE cuenta = '%s' AND divisa = '%s' 
                                                                AND simbolo = '%s' AND activa = 'Y') AS a
                            ORDER BY fechahora DESC, sec DESC;"""
                    cursor.execute(qry % (account, idivisa, symbol))
                    sql = cursor.fetchone()

                # ultima diaria registrada
                if symbol is None:
                    qry = """SELECT a.* FROM (SELECT sec, fechahora, stock, basico, gprealizadas, cantidad, 
                                                    tarifacomision, idtrans, position_inversion FROM booktrading 
                                            WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y') AS a
                            ORDER BY fechahora DESC, sec DESC;"""
                    cursor.execute(qry % (account, idivisa))
                    sql = cursor.fetchone()

            elif accion == "low":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading  WHERE cuenta = '%s'  
                                                                    AND divisa = '%s' AND simbolo = '%s') AS a 
                                                                    ORDER BY fechahora ASC, sec ASC;"""
                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchone()

            elif accion == "valida":
                qry = """SELECT * FROM booktrading as x WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' 
                                                        AND idtrans = '%s';"""

                cursor.execute(qry % (account, idivisa, symbol, idtrans))
                sql = cursor.fetchone()

            elif accion == "select":
                qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock, gprealizadas, sec FROM booktrading  
                                        WHERE cuenta = '%s'  AND divisa = '%s' 
                                            AND simbolo = '%s' AND activa = 'Y') AS a
                                            ORDER BY DATE(fechahora) ASC, sec ASC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            elif accion == "fecha":
                istamp = pd.to_datetime(fecha)
                estamp = istamp + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
                qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock  FROM booktrading  
                                        WHERE cuenta = '%s'  AND divisa = '%s' AND simbolo = '%s' AND codigo = 'O'
                                            AND fechahora >= '%s' AND fechahora <= '%s') AS a
                                        ORDER BY  DATE(fechahora) ASC;"""
                cursor.execute(qry % (account, idivisa, symbol, istamp, estamp))
                sql = cursor.fetchall()

            elif accion == "desde_hasta":
                qry = """SELECT * FROM booktrading 
                        WHERE cuenta = '%s'  AND divisa = '%s' AND codigo in ('C', 'O')
                            AND Date(fechahora) >= '%s' AND Date(fechahora) <= '%s' 
                        ORDER BY simbolo, fechahora ASC, sec ASC;"""
                cursor.execute(qry % (account, idivisa, fecha, hasta))
                sql = cursor.fetchall()

            elif accion == "Trade":
                istamp = pd.to_datetime(fecha)
                qry = """SELECT * FROM booktrading  WHERE cuenta = '%s' AND divisa = '%s' 
                                                    AND simbolo ='%s' AND fechahora = '%s' AND idtrans = '%s';"""
                cursor.execute(qry % (account, idivisa, symbol, istamp, idtrans))
                sql = cursor.fetchall()

            elif accion == "timestamp":
                qry = """SELECT max(a.fechahora) as fechahora FROM 
                                (SELECT fechahora FROM booktrading  
                                WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y') AS a;"""

                cursor.execute(qry % (account, idivisa))
                sql = cursor.fetchone()

            elif accion == "select*":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s' 
                                                                    AND simbolo = '%s' AND activa = 'Y') AS a 
                                                                    ORDER BY preciotrans ASC, fechahora ASC, sec ASC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # para obtener tasa de cambio mas reciente
            elif accion == "tasa_cambio":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s' 
                                                                    AND simbolo = '%s' AND activa = 'Y') AS a 
                                                                    ORDER BY fechahora DESC, sec DESC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            elif accion == "cuenta":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s') AS a 
                                        ORDER BY fechahora ASC, sec ASC;"""

                cursor.execute(qry % (account, idivisa))
                sql = cursor.fetchall()

            elif accion == "performa":
                qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock, gprealizadas, codigo, comisiones
                                        FROM booktrading  WHERE cuenta = '%s'  AND divisa = '%s' 
                                                            AND simbolo = '%s') AS a 
                        ORDER BY DATE(fechahora) ASC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # opción para reconstruir performa de la cartera
            elif accion == "cartera":
                qry = """SELECT * FROM booktrading 
                        WHERE cuenta = '%s' AND divisa = '%s' AND codigo in ('C', 'O')
                        ORDER BY simbolo, fechahora ASC;"""

                cursor.execute(qry % (account, idivisa))
                sql = cursor.fetchall()

            # opción para obtener maxima ganancia en Trade de venta
            elif accion == "ganancias":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading  
                                        WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y'
                                            AND codigo = 'O'  AND simbolo = '%s') AS a 
                        ORDER BY preciotrans ASC, fechahora DESC, sec DESC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # opción para obtener última fecha de operaciones para el cálculo de la diaria
            elif accion == "diaria":
                qrq = """SELECT cuenta, simbolo,  max(fechahora) fechahora FROM bdinv.booktrading 
                        WHERE cuenta = '%s' GROUP by cuenta, simbolo  
                                            ORDER by fechahora ASC;"""
                cursor.execute(qrq % account)
                ix = [columna[0] for columna in cursor.description]
                sqx = cursor.fetchall()

                if sqx:
                    desde = sqx[0][ix.index("fechahora")]
                    qry = """SELECT * FROM bdinv.booktrading  
                            WHERE cuenta = '%s' AND fechahora >= '%s' ORDER by simbolo, fechahora ASC;"""

                    cursor.execute(qry % (account, desde))
                    sql = cursor.fetchall()

            elif accion == "diaria_app":
                hasta = datetime.now() - timedelta(days=1)
                desde = datetime.now() - timedelta(days=10)
                f_hasta = hasta.strftime("%Y-%m-%d")
                hasta_mes = hasta.month
                hasta_año = hasta.year

                qrq = f"""
                        SELECT X.cuenta, X.simbolo,  X.fechahora, sum(cantidad) as cantidad
                        FROM
                        (SELECT a.* from (SELECT cuenta, simbolo,  max(fechahora) fechahora, sum(cantidad) cantidad
                                        FROM bdinv.booktrading  WHERE cuenta = '{account}' and date(fechahora) < '{f_hasta}'
                                        GROUP by cuenta, simbolo) as a  
                        UNION 
                        SELECT a.* from (SELECT cuenta, simbolo,  fechahora, sum(cantidad) cantidad
                                        FROM bdinv.booktrading  WHERE cuenta = '{account}' and date(fechahora) < '{f_hasta}' 
                                                                  and month(fechahora) = {hasta_mes} and year(fechahora) = {hasta_año}
                                        GROUP by cuenta, simbolo, fechahora) as a) as X
                        GROUP by X.cuenta, X.simbolo, X.fechahora 
                        ORDER by simbolo, fechahora ASC;
                      """
                cursor.execute(qrq)
                ix = [columna[0] for columna in cursor.description]
                sqx = cursor.fetchall()

                # construye query con todos los activos para obtener el last record
                if sqx:

                    inicio_qry, qry = (
                        True,
                        """SELECT * FROM bdinv.booktrading WHERE cuenta = '%s'""",
                    )

                    for i, row in enumerate(sqx):

                        # condicion que deja pasar las posiciones liquidadas más recientes (10 días atrás)
                        if (row[ix.index("cantidad")] > 0.0001) or (
                            row[ix.index("cantidad")] <= 0
                            and row[ix.index("fechahora")].date() > desde.date()
                        ):

                            if inicio_qry:
                                concatena = (
                                    """ AND ((simbolo, fechahora) = ('%s', '%s')"""
                                    % (
                                        row[ix.index("simbolo")],
                                        row[ix.index("fechahora")],
                                    )
                                )
                                inicio_qry = False
                            else:
                                concatena = (
                                    """ OR (simbolo, fechahora) = ('%s', '%s')"""
                                    % (
                                        row[ix.index("simbolo")],
                                        row[ix.index("fechahora")],
                                    )
                                )
                            qry += concatena

                    qry += ") ORDER by simbolo, fechahora ASC;" ""
                    cursor.execute(qry % account)
                    sql = cursor.fetchall()

            # cosulta por hash_id
            elif accion == "hash":
                qry = "SELECT * FROM booktrading WHERE hash_id = '%s';"
                cursor.execute(qry % hash_id)
                sql = cursor.fetchone()

            xlis, columnas = list(), [columna[0] for columna in cursor.description]
            if sql:
                if accion in ("last", "low", "valida", "timestamp", "id", "Trade"):
                    xlis.append(dict(zip(columnas, sql)))
                else:
                    xlis = sql

            cursor.close()
            return xlis, columnas
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_booktrading()]: {}".format(error))

    def get_hash_booktrading(self, accion=None, values=None, symbol=None):
        """
        Genera un hash único para una operación en booktrading.
        Usa campos clave para asegurar unicidad.
        """
        # Puedes ajustar los campos según tu modelo de unicidad
        idtran = values.get("idtrans", "")
        idtran = str(idtran) if isinstance(idtran, int) else idtran

        campos = [
            values.get("cuenta", ""),
            values.get("divisa", ""),
            symbol,
            idtran,
            str(values.get("fechahora", "")),
            str(values.get("cantidad", "")),
            str(values.get("preciotrans", "")),
        ]
        hash_str = "_".join(campos)
        hashId = hashlib.md5(hash_str.encode()).hexdigest()

        if accion is None:
            return hashId

        # valida hashId en booktrading
        last, ix = self.select_booktrading(accion="hash", hash_id=hashId)
        return False if len(last) == 0 else True

    # inserta operaciones buy-sell en booktrading
    def insert_booktrading(self, values=None, symbol="SPX"):

        # return: Mantiene indicador activa, en función de las sesiones de venta
        def update_indicador_activa(
            idcuenta=None,
            divisa=None,
            ticket=None,
            id_trans=None,
            activa=None,
            sell=None,
            update=None,
        ):
            try:
                u_conn = self._conectar(tabla="update.booktrading")
                u_cursor = u_conn.cursor()
                upd = """UPDATE booktrading SET activa = '%s', sell = '%s', updateStamp = '%s' 
                        WHERE cuenta = '%s' AND divisa = '%s' AND simbolo = '%s' and idtrans = '%s';"""

                u_cursor.execute(
                    upd % (activa, sell, update, idcuenta, divisa, ticket, id_trans)
                )
                u_conn.commit()
            except (Exception, EncodingWarning, connect.Error) as e:
                print("[Mysql:: update_indicador_activa()]: {}".format(e))

        # aplica a las sell para obtener maxima's ganancias y marcas los códigos = 'O' como inactivo
        def maximiza_ganancias_corto_plazo(c_sell, update):
            try:
                (book, iy) = self.select_booktrading(
                    accion="ganancias", account=account, idivisa=idivisa, symbol=symbol
                )
                ebook = enumerate(book)
                eof_book, read = next(ebook, (None, None))

                value, x_stock, ya_sell = 0.0, 0.0, 0.0
                while (eof_book is not None) and (x_stock + c_sell < 0):

                    a_sell = read[iy.index("sell")]
                    cant = read[iy.index("cantidad")] - a_sell
                    prec = read[iy.index("preciotrans")]

                    # recalcula la cantidad que es vendida para los casos que toma más de un lote
                    if (cant + ya_sell + c_sell) <= 0:
                        ya_sell += cant
                        activa = "N"

                        # se acumula el importe total del lote
                        value += cant * prec

                    elif (cant + ya_sell + c_sell) > 0:
                        cant = abs(ya_sell + c_sell)
                        a_sell += cant
                        activa = "Y"

                        # se acumula el importe parcial del lote, en función de la cantidad vendida del lote
                        value += cant * prec

                    x_stock += cant

                    update_indicador_activa(
                        idcuenta=read[iy.index("cuenta")],
                        divisa=read[iy.index("divisa")],
                        ticket=symbol,
                        id_trans=read[iy.index("idtrans")],
                        activa=activa,
                        sell=a_sell,
                        update=update,
                    )

                    if x_stock + c_sell >= 0.0:
                        break

                    eof_book, read = next(ebook, (None, None))
                return value
            except (Exception, EncodingWarning, connect.Error) as e:
                print("[Mysql:: maximiza_ganancias_corto_plazo()]: {}".format(e))

        # Objetivo es dejar solo como activa la venta más reciente
        def update_codigo_sell(id_trader=None, update=None):
            try:
                (book, iy) = self.select_booktrading(
                    accion="select*", account=account, idivisa=idivisa, symbol=symbol
                )
                ebook = enumerate(book)

                eof_book, read = next(ebook, (None, None))
                while eof_book is not None:

                    if (
                        (read[iy.index("codigo")] == "C")
                        and (read[iy.index("idtrans")] != id_trader)
                        and (read[iy.index("idtrans")] == "Y")
                    ):

                        update_indicador_activa(
                            idcuenta=read[iy.index("cuenta")],
                            divisa=read[iy.index("divisa")],
                            ticket=symbol,
                            id_trans=read[iy.index("idtrans")],
                            activa="N",
                            sell=read[iy.index("cantidad")],
                            update=update,
                        )

                    eof_book, read = next(ebook, (None, None))
            except (Exception, EncodingWarning, connect.Error) as e:
                print("[Mysql:: update_codigo_sell()]: {}".format(e))

        try:
            conn = self._conectar(tabla="insert.booktrading")
            cursor = conn.cursor()
            valuesins = []
            stock, basico, gpreal = 0.0, 0.0, 0.0
            mtmgp, codigo, qry = 0.0, "", ""

            account = values["cuenta"]
            idivisa = values["divisa"]
            idtrans = values["idtrans"]
            categoria = values["categoria"]

            # crea hashID y valida su existencia
            found_hash = self.get_hash_booktrading(
                accion="valida", values=values, symbol=symbol
            )
            if found_hash:
                return

            # procede con insert del trader
            hashId = self.get_hash_booktrading(values=values, symbol=symbol)

            # ubica último trader del symbol para obtener basico
            nw_producto, ubasico, ustock = 0.0, 0.0, 0.0
            usec, uid, position = 0.0, 0.0, 0.0

            utrading, ix = self.select_booktrading(
                accion="last", account=account, idivisa=idivisa, symbol=symbol
            )
            if utrading:
                nw_producto = utrading[0]["basico"] * utrading[0]["stock"]
                costo_avg = utrading[0]["basico"]
                ubasico = utrading[0]["basico"]
                ustock = utrading[0]["stock"]
                usec = utrading[0]["sec"]

            # ubica costobase para mejorar el precio medio
            inversion = self.select_inversion(tipoin=categoria, ticket=symbol)
            if inversion:
                position = inversion[0]["position"] if inversion else 0
                costo_avg = (
                    inversion[0]["costobase"] * inversion[0]["factor_cambio"] / position
                    if position > 0
                    else ubasico
                )

            stock = ustock + values["cantidad"]

            # cuando es compra en largo
            if values["cantidad"] > 0:

                # obtener basico y recalcular el nuevo producto de utrading entre el nuevo stock
                basico = (
                    values["preciotrans"] * values["cantidad"]
                    + values["tarifacomision"]
                    + nw_producto
                ) / stock
                gpreal = 0.0
                codigo = "O"
                mtmgp = 0.00
                values.update({"activa": "Y"})
                stock = stock if stock > position else position

            # cuando es venta en corto
            elif values["cantidad"] < 0:
                basico = costo_avg
                codigo = "C"

                # rutina para marcar como iactiva='N'
                importe = maximiza_ganancias_corto_plazo(
                    values["cantidad"], values["fechahora"]
                )

                gpreal = values["producto"] - (importe + values["tarifacomision"])
                mtmgp = gpreal / abs(values["cantidad"])

                # coloca inactiva todas las sell anteriores y en caso de ser la última actuliza sellc
                update_codigo_sell(id_trader=idtrans, update=values["fechahora"])

            # complementa para actualizar información de la operación
            values.update({"split": 1})
            values.update({"activa": "Y"})
            values.update({"stock": stock})
            values.update({"mtmgp": mtmgp})
            values.update({"basico": basico})
            values.update({"codigo": codigo})
            values.update({"gprealizadas": gpreal})
            values.update({"position_inversion": position})
            values.update({"updateStamp": datetime.now()})
            values.update({"hash_id": hashId})
            values.update({"sec": int(usec) + 1})

            # prepara Query Insert
            qry = "INSERT INTO booktrading ("
            for keys, vals in values.items():
                qry += keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry += "simbolo) VALUES ({});".format(
                ",".join("%s" for _ in range(len(valuesins)))
            )
            cursor.execute(qry, tuple(valuesins))
            conn.commit()
            cursor.close()

            time.sleep(0.4)
            # update basico "otros_activos" e indicador "activa", cuando sea una venta (cantidad <0)
            cvalues = {}
            cvalues.update({"avgcost": basico})
            cvalues.update({"fecupdate": values["fechahora"]})
            self.update_otros_activos(values=cvalues, symbol=symbol)
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: insert_booktrading()]: {error}")

    def min_fec_booktrading(self, list_asset=None, account=None, idivisa=None):
        """
        @param list_asset: lista de símbolos
        @param account: idcuenta
        @param idivisa: divisa
        @return: de booktrading fecha minima para los símbolos de la cuenta."""
        try:
            inicio, ifecha = {}, datetime.now()
            for ticket in list_asset:
                (utrading, ix) = self.select_booktrading(
                    accion="low", account=account, idivisa=idivisa, symbol=ticket
                )
                if utrading:
                    if ifecha > utrading[0]["fechahora"]:
                        ifecha = utrading[0]["fechahora"]

                inicio.update({"asset": ticket, "ifecha": ifecha})
            return inicio
        except (Exception, EncodingWarning, connect.Error):
            return {}

    def insert_order_trader(self, values=None, symbol=None):
        """
        @param values:  lista de valores de campos a insertar
        @param symbol: ticket a consultar en Order
        @return: agrega fila  en order_trader."""

        conn = self._conectar(tabla="insert.order_trader")
        cursor = conn.cursor()
        valuesins = list()
        qry = " "
        try:
            qry = "INSERT INTO order_trader ("
            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry += "symbol) VALUES ({});".format(
                ",".join("%s" for _ in range(len(valuesins)))
            )
            cursor.execute(qry, tuple(valuesins))
            conn.commit()
            cursor.close()
        except (ValueError, Exception, EncodingWarning) as error:
            print("[Mysql:: insert_order_trader()]: {}".format(error))

    def update_order_trader(self, account=None, values=None, symbol=None, orderid=None):
        """
        @param account: cuenta id del vehículo Crypto
        @param values: diccionario con atributos a actualizar
        @param symbol: identificador del activo
        @param orderid: identificador de la orden
        @return:
        """
        conn = self._conectar(tabla="insert.order_trader")
        cursor = conn.cursor()
        valuesins = []
        qry = "UPDATE order_trader SET "

        try:
            for keys, vals in values.items():

                qry = qry + keys + "='%s', "
                valuesins.append(vals)

            valuesins.append(account)
            valuesins.append(symbol)
            valuesins.append(orderid)

            qry += "WHERE account='%s' AND symbol='%s' AND id_order='%s';"
            qry = qry.replace(", WHERE", " WHERE")

            valuesupd = tuple(valuesins)
            cursor.execute(qry % valuesupd)
            conn.commit()
            cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_order_trader()]: {}".format(error))

    def select_order_trader(self, account=None, vehiculo=None, symbol=None, conid=None):
        """
        @param account: id de cuenta inversionista
        @param vehículo: tipo de inversión
        @param conid: activo a consultar
        @param symbol: activo a consultar
        """
        conn = self._conectar(tabla="select.order_trader")
        cursor = conn.cursor()
        qry, sql, ix = " ", list(), list()
        try:

            if account == "all":
                desde = datetime.now() - timedelta(days=7)
                qry = """SELECT * FROM order_trader WHERE date(stampPlace) >= '%s'
                         ORDER BY stampPlace DESC;"""
                cursor.execute(qry % (desde.date()))
                sql = cursor.fetchall()

            elif not is_none(symbol):
                qry = """SELECT * FROM order_trader WHERE account= '%s' AND vehiculo = '%s' AND symbol = '%s';"""
                cursor.execute(qry % (account, vehiculo, symbol))
                sql = cursor.fetchall()

            elif not is_none(conid):
                qry = """SELECT * FROM order_trader WHERE account= '%s' AND vehiculo = '%s' AND conid = '%s';"""
                cursor.execute(qry % (account, vehiculo, conid))
                sql = cursor.fetchall()

            ix = [columna[0] for columna in cursor.description]
            return sql, ix
        except conn.ProgrammingError as error:
            print("[Mysql:: select_order_trader({})]: {}".format(vehiculo, error))
