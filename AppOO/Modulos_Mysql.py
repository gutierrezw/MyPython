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
    traceback,
    logging,
    PooledDB,
    pymysql,
)
from Modulos_Utilitarios import (
    is_none,
    valida_meses_consecutivos,
    sort_positions,
    read_json_tmp,
    write_json_tmp,
)

_logger = logging.getLogger("Mysql")


class BDsystem:  # ----------------------------------------------------------------------------------------------------
    """
    clase para manejar accesos genericos a mysql."""

    DB_CONFIG = {
        "user": "root",
        "password": "",
        "host": "localhost",
        "database": "bdinv",
    }
    _pool = None

    @staticmethod
    def configure(db_config: dict):
        BDsystem.DB_CONFIG.update(db_config)
        BDsystem._pool = None  # fuerza recreación del pool con nueva config

    @staticmethod
    def get_sesion_by_vehiculo(vehiculo=None, principal=False) -> dict:
        """
        Obtiene sesión por vehículo.

        Args:
            vehiculo: Tipo de vehículo (Stock, Crypto, etc.)

        Returns:
            dict con todos los campos de la tabla sesion

        Raises:
            ValueError: Si no existe sesión para el vehículo
        """
        conn = BDsystem.connect_dbase("select.sesion", False)
        cursor = None
        try:
            cursor = conn.cursor()
            if not principal:
                sql = "SELECT * FROM sesion WHERE vehiculo = %s"
                cursor.execute(sql, (vehiculo,))

            elif principal:
                sql = "SELECT * FROM sesion WHERE Idcuenta_principal=1"
                cursor.execute(sql)
            qry = cursor.fetchone()

            if not qry:
                raise ValueError(f"No existe sesión para vehículo: {vehiculo}")

            # Construir diccionario con nombres de columnas
            ix = [columna[0] for columna in cursor.description]
            sesion = {}
            for i, nombre_columna in enumerate(ix):
                sesion[nombre_columna] = qry[i]

            return sesion
        except Exception as error:
            print(f"[Mysql::get_sesion_by_vehiculo()]: {error}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def get_vehiculo_by_ticket(ticket: str) -> Optional[dict]:
        """
        Obtiene información del vehículo y presupuesto dado un ticket (símbolo).

        Args:
            ticket: Símbolo del activo (ej: 'AAPL', 'BTC-USD')

        Returns:
            dict con keys: ticket, vehiculo, Pinvertir
            None si no se encuentra el ticket

        Example:
            >>> BDsystem.get_vehiculo_by_ticket('AAPL')
            {'ticket': 'AAPL', 'vehiculo': 'Stock', 'Pinvertir': 10000.0}
        """
        conn = BDsystem.connect_dbase("select.vehiculo_by_ticket", False)
        try:
            cursor = conn.cursor()
            sql = """
                SELECT a.ticket, b.vehiculo, b.Pinvertir
                FROM bdinv.inversion a, bdinv.sesion b
                WHERE a.ticket = %s
                AND b.vehiculo = a.tipoinv
            """
            cursor.execute(sql, (ticket,))
            result = cursor.fetchone()

            if not result:
                return None

            return {"ticket": result[0], "vehiculo": result[1], "Pinvertir": result[2]}
        except Exception as error:
            print(f"[Mysql::get_vehiculo_by_ticket()]: {error}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_fecha_orden(vehiculo: str, fesesion, orcartera: str) -> bool:
        """
        Actualiza fesesion y orcartera de una sesión.

        Args:
            vehiculo: Tipo de vehículo (Stock, Crypto, BotCrypto, etc.)
            fesesion: Fecha de sesión
            orcartera: Orden de cartera

        Returns:
            bool: True si actualización exitosa, False en caso contrario
        """
        sql = "UPDATE sesion SET fesesion=%s, orcartera=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Sesion.Update", False)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fesesion, orcartera, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_fecha_orden()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_environment(vehiculo: str, environment: str) -> bool:
        """
        Actualiza el campo environment de una sesión.

        Args:
            vehiculo: Tipo de vehículo (BotCrypto, Crypto, etc.)
            environment: Ambiente (TESTNET | PRODUCTION)

        Returns:
            bool: True si actualización exitosa, False en caso contrario
        """
        sql = "UPDATE sesion SET environment=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Environment.Update", False)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, (environment, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_environment()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_config(vehiculo: str, config: dict) -> bool:
        """
        Actualiza el campo private_key (JSON config) de una sesión.

        Args:
            vehiculo: Tipo de vehículo (BotCrypto, Crypto, etc.)
            config: Diccionario con la configuración a guardar como JSON

        Returns:
            bool: True si actualización exitosa, False en caso contrario
        """
        import json

        sql = "UPDATE sesion SET private_key=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Config.Update", False)

        try:
            cursor = conn.cursor()
            config_json = json.dumps(config)
            cursor.execute(sql, (config_json, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_config()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_parameters(vehiculo: str, config: dict) -> bool:
        import json

        sql = "UPDATE sesion SET parameters=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Config.Update", False)
        cursor = None
        try:
            cursor = conn.cursor()
            config_json = json.dumps(config)
            cursor.execute(sql, (config_json, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_parameters()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_fecha_fund(vehiculo: str, fecha_fund) -> bool:
        """
        Actualiza fechaFund de una sesión.

        Args:
            vehiculo: Tipo de vehículo (Stock, Crypto, etc.)
            fecha_fund: Fecha fundamental

        Returns:
            bool: True si actualización exitosa, False en caso contrario
        """
        sql = "UPDATE sesion SET fefund=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Fe.fundamental.Update", False)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, (fecha_fund, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_fecha_fund()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def update_sesion_strategy(vehiculo: str, xstrategy: str) -> bool:
        """
        Actualiza xstrategy de una sesión.

        Args:
            vehiculo: Tipo de vehículo (Stock, Crypto, etc.)
            xstrategy: Estrategia a aplicar

        Returns:
            bool: True si actualización exitosa, False en caso contrario
        """
        sql = "UPDATE sesion SET xstrategy=%s WHERE vehiculo=%s"
        conn = BDsystem.connect_dbase("Strategy.Update", False)

        try:
            cursor = conn.cursor()
            cursor.execute(sql, (xstrategy, vehiculo))
            conn.commit()
            return True
        except Exception as error:
            print(f"[Mysql::update_sesion_strategy()]: {error}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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
            if BDsystem._pool is None:
                BDsystem._pool = PooledDB(
                    creator=pymysql,
                    maxconnections=12,
                    mincached=2,
                    maxcached=8,
                    blocking=True,
                    host=BDsystem.DB_CONFIG.get("host"),
                    user=BDsystem.DB_CONFIG.get("user"),
                    passwd=BDsystem.DB_CONFIG.get("password"),
                    db=BDsystem.DB_CONFIG.get("database"),
                )
            conn = BDsystem._pool.connection()
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
            sql = (
                """SELECT * FROM sesion WHERE vehiculo != "DataHub"  ORDER BY Idcuenta_principal DESC, fiscalYear ASC"""
            )
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
                      fefund, Pinvertir, xstrategy, environment, userapi, userpass,
                      private_key, public_key, port,
                      id_transaccion, load_csv, gypPrecio, gainInversion, parameters)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

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
                values.get("environment"),
                values.get("userapi"),
                values.get("userpass"),
                values.get("private_key"),
                values.get("public_key"),
                values.get("port"),
                values.get("id_transaccion", False),
                values.get("load_csv", False),
                values.get("gypPrecio"),
                values.get("gainInversion"),
                values.get("parameters"),
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
                     environment=%s, userapi=%s, userpass=%s, private_key=%s,
                     public_key=%s, port=%s,
                     id_transaccion=%s, load_csv=%s, gypPrecio=%s, gainInversion=%s,
                     parameters=%s
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
                values.get("environment"),
                values.get("userapi"),
                values.get("userpass"),
                values.get("private_key"),
                values.get("public_key"),
                values.get("port"),
                values.get("id_transaccion", False),
                values.get("load_csv", False),
                values.get("gypPrecio"),
                values.get("gainInversion"),
                values.get("parameters"),
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

    # =========================
    # Métodos para define_modelosia
    # =========================
    @staticmethod
    def get_modelo_ia(modelo: str) -> Optional[dict]:
        """
        Obtiene configuración de un modelo IA por nombre.

        Args:
            modelo: Nombre del modelo (ej: 'modelo_sellv01')

        Returns:
            dict con campos: id, modelo, Nombre, paramts, define_modelo, timestamp
            None si no existe
        """
        try:
            conn = BDsystem.connect_dbase("select.define_modelosia", False)
            cursor = conn.cursor()

            sql = "SELECT * FROM bdinv.modelos_ia WHERE modelo = %s"
            cursor.execute(sql, (modelo,))
            result = cursor.fetchone()

            if not result:
                return None

            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, result))
        except Exception as error:
            print(f"[Mysql::get_modelo_ia()]: {error}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def get_all_modelos_ia() -> list:
        """
        Obtiene todos los modelos IA registrados.

        Returns:
            Lista de dicts con la configuración de cada modelo
        """
        try:
            conn = BDsystem.connect_dbase("select.define_modelosia", False)
            cursor = conn.cursor()

            sql = "SELECT * FROM bdinv.modelos_ia ORDER BY modelo"
            cursor.execute(sql)
            results = cursor.fetchall()

            if not results:
                return []

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        except Exception as error:
            print(f"[Mysql::get_all_modelos_ia()]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def insert_modelo_ia(
        modelo: str,
        nombre: str,
        paramts: bytes = None,
        tipo_modelo: str = None,
        define_modelo: str = None,
    ) -> bool:
        try:
            conn = BDsystem.connect_dbase("insert.define_modelosia", False)
            cursor = conn.cursor()

            sql = """
                INSERT INTO bdinv.modelos_ia
                (modelo, Nombre, paramts, define_modelo, tipo_modelo)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (modelo, nombre, paramts, define_modelo, tipo_modelo))
            conn.commit()

            rows_affected = cursor.rowcount
            cursor.close()
            conn.close()
            return rows_affected > 0
        except Exception as error:
            print(f"[Mysql::insert_modelo_ia()]: {error}")
            return False

    @staticmethod
    def update_modelo_ia(
        modelo: str,
        nombre: str = None,
        paramts: bytes = None,
        define_modelo: str = None,
        tipo_modelo: str = None,
    ) -> bool:
        try:
            conn = BDsystem.connect_dbase("update.define_modelosia", False)
            cursor = conn.cursor()

            updates = []
            values = []

            if nombre is not None:
                updates.append("Nombre = %s")
                values.append(nombre)
            if paramts is not None:
                updates.append("paramts = %s")
                values.append(paramts)
            if define_modelo is not None:
                updates.append("define_modelo = %s")
                values.append(define_modelo)
            if tipo_modelo is not None:
                updates.append("tipo_modelo = %s")
                values.append(tipo_modelo)

            if not updates:
                return False

            # Agregar timestamp de actualización
            values.append(modelo)

            sql = f"UPDATE bdinv.modelos_ia SET {', '.join(updates)} WHERE modelo = %s"
            cursor.execute(sql, values)
            conn.commit()

            rows_affected = cursor.rowcount
            cursor.close()
            conn.close()
            return rows_affected > 0
        except Exception as error:
            print(f"[Mysql::update_modelo_ia()]: {error}")
            return False

    @staticmethod
    def delete_modelo_ia(modelo: str) -> bool:
        """
        Elimina un modelo IA.

        Args:
            modelo: Identificador del modelo a eliminar

        Returns:
            True si se eliminó correctamente, False en caso de error
        """
        try:
            conn = BDsystem.connect_dbase("delete.define_modelosia", False)
            cursor = conn.cursor()

            sql = "DELETE FROM bdinv.modelos_ia WHERE modelo = %s"
            cursor.execute(sql, (modelo,))
            conn.commit()

            rows_affected = cursor.rowcount
            cursor.close()
            conn.close()
            return rows_affected > 0
        except Exception as error:
            print(f"[Mysql::delete_modelo_ia()]: {error}")
            return False


class IPerformance(BDsystem):  # ------------------------------------------------------------------------------------
    """
    clase para manejar: select, insert y update sobre Diaria y Performa_inversion."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select_performa_inversion(self, account=None, vehiculo=None, accion=None, referencia=None):
        """
        @param account: id cuenta de inversion
        @param vehiculo: tipo de inversión acciones, Crypto
        @param accion: tipo de consulta
        @param referencia: Qué índice acompaña el vehículo de inversión
        @return: entrega lista de filas según parámetros de entrada."""

        conn = self._conectar(tabla="select.performa_inversion")
        try:
            cursor = conn.cursor()

            # consolida múltiples cuentas por vehículo (FCI: BBVA.ARS = BBVA0001 + SANT0001)
            if is_none(account):
                qry = """SELECT fechaclose,
                                sum(p_referencia) / COUNT(DISTINCT idcuenta) AS p_referencia,
                                sum(p_vehiculo)                               AS p_vehiculo,
                                sum(gyp_dia)                                  AS gyp_dia,
                                sum(nr_gyp)                                   AS nr_gyp,
                                sum(value)                                    AS value,
                                sum(costo_base)                               AS costo_base,
                                sum(dividends)                                AS dividends
                         FROM performa_inversion
                        WHERE vehiculo = '%s'
                        GROUP BY fechaclose
                        ORDER BY fechaclose ASC;"""
                cursor.execute(qry % vehiculo)
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

    def select_resumen_por_vehiculo(self, account=None):
        """Retorna G/P+Div acumulados por vehículo para 30, 60 y 90 días."""
        conn = self._conectar(tabla="select.resumen_por_vehiculo")
        try:
            cursor = conn.cursor()
            qry = """SELECT vehiculo,
                            SUM(CASE WHEN fechaclose >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                                     THEN gyp_dia + dividends ELSE 0 END) AS d30,
                            SUM(CASE WHEN fechaclose >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
                                     THEN gyp_dia + dividends ELSE 0 END) AS d60,
                            SUM(CASE WHEN fechaclose >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                                     THEN gyp_dia + dividends ELSE 0 END) AS d90
                       FROM performa_inversion
                      WHERE fechaclose >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                        {where_account}
                      GROUP BY vehiculo
                      ORDER BY d90 DESC"""
            where = "AND idcuenta = %s" if account else ""
            if account:
                cursor.execute(qry.format(where_account=where), (account,))
            else:
                cursor.execute(qry.format(where_account=where))
            rows = cursor.fetchall()
            ix = [c[0] for c in cursor.description]
            return rows, ix
        except Exception as e:
            print(f"Mysql:: select_resumen_por_vehiculo(): {e}")
            return [], []
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
            qry += " timestamp) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
            cursor.execute(qry, valuesupd)

            conn.commit()
            cursor.close()

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: insert_performa_inversion()]: {}".format(error))

    def select_diaria_performance(self, accion=None, account=None, date=None, symbol=None):
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
        adj = values.get("AdjClose") if values else None
        if adj is None or str(adj).lower() == "nan":
            return
        conn = self._conectar(tabla="insert.diaria_performance")
        try:
            cursor = conn.cursor()
            valuesins = list()

            qry = "INSERT INTO diaria_performance ("
            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            placeholders = ",".join("%s" for _ in range(len(valuesins)))
            cols = [k for k in values.keys()] + ["symbol"]
            update_clause = ", ".join(f"{c}=VALUES({c})" for c in cols)
            qry += f"symbol) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_clause};"
            cursor.execute(qry, tuple(valuesins))
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"Mysql:: insert_diaria_performance()]: {error} {qry}={tuple(valuesins)}")
        finally:
            conn.commit()
            cursor.close()

    def purgar_desde(self, account, vehiculo, desde):
        """Elimina registros de diaria_performance y performa_inversion a partir de una fecha.

        Uso: reparación de datos corruptos — permite que schedule_diario reconstruya
        ambas tablas desde 'desde' en el próximo ciclo.

        Args:
            account:  id de cuenta (ej: 'U4214563')
            vehiculo: tipo de inversión (ej: 'Stock', 'Crypto')
            desde:    date o str 'YYYY-MM-DD' — fecha de inicio de la purga (inclusive)

        Returns:
            dict con claves 'diaria' y 'performa' indicando filas eliminadas en cada tabla.
        """
        conn = self._conectar(tabla="purgar_desde")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM diaria_performance WHERE account = %s AND Date >= %s",
                (account, str(desde)),
            )
            n_diaria = cursor.rowcount
            cursor.execute(
                "DELETE FROM performa_inversion WHERE idcuenta = %s AND vehiculo = %s AND fechaclose >= %s",
                (account, vehiculo, str(desde)),
            )
            n_performa = cursor.rowcount
            conn.commit()
            return {"diaria": n_diaria, "performa": n_performa}
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: IPerformance.purgar_desde()]: {error}")
            conn.rollback()
            return {"diaria": 0, "performa": 0}
        finally:
            cursor.close()
            conn.close()

    def validate_performa(self, account, vehiculo="Stock", threshold=2.0, low_threshold=0.1):
        """Detecta registros en diaria_performance con value_ratio fuera de rango vs día anterior.

        Usa LAG sobre toda la historia del símbolo para calcular value_ratio en los últimos 7 días.
        ratio > threshold  → precio corrupto al alza (ej: ABEV $7230)
        ratio < low_threshold → precio corrupto a la baja (ej: BIL $1.32 en vez de $91)

        Purga quirúrgica: solo elimina los registros del símbolo afectado (no todos los símbolos
        de esa fecha). Performa_inversion se purga desde la fecha mínima afectada para forzar
        reagregación. agents_schedule.json se resetea para que schedule_diario regenere.

        Returns:
            dict con 'anomalias' (list of dicts) y 'purgados' (bool).
        """
        conn = self._conectar(tabla="validate_performa")
        try:
            cursor = conn.cursor()

            # ── 1. Validar diaria_performance.value ───────────────────────────
            cursor.execute(
                """
                SELECT t.Date, t.symbol, t.value, t.value_ayer,
                       t.value / t.value_ayer AS value_ratio
                FROM (
                    SELECT Date, symbol, value,
                           LAG(value) OVER (PARTITION BY account, symbol ORDER BY Date) AS value_ayer
                    FROM diaria_performance
                    WHERE account = %s AND value > 0
                ) t
                WHERE t.value_ayer > 0
                  AND t.Date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                  AND (t.value / t.value_ayer > %s OR t.value / t.value_ayer < %s)
                ORDER BY t.Date ASC
                """,
                (account, threshold, low_threshold),
            )
            anomalias_value = cursor.fetchall()

            # ── 2. Validar diaria_performance.costo_base ──────────────────────
            cursor.execute(
                """
                SELECT t.Date, t.symbol, t.costo_base, t.costo_base_ayer,
                       t.costo_base / t.costo_base_ayer AS ratio
                FROM (
                    SELECT Date, symbol, costo_base,
                           LAG(costo_base) OVER (PARTITION BY account, symbol ORDER BY Date) AS costo_base_ayer
                    FROM diaria_performance
                    WHERE account = %s AND costo_base > 0
                ) t
                WHERE t.costo_base_ayer > 0
                  AND t.Date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                  AND (t.costo_base / t.costo_base_ayer > %s OR t.costo_base / t.costo_base_ayer < %s)
                ORDER BY t.Date ASC
                """,
                (account, threshold, low_threshold),
            )
            anomalias_cb = cursor.fetchall()

            if not anomalias_value and not anomalias_cb:
                cursor.close()
                conn.close()
                return {"anomalias": [], "purgados": False}

            anomalias = [
                {"fecha": r[0], "symbol": r[1], "value": float(r[2]), "value_ayer": float(r[3]), "ratio": float(r[4])}
                for r in anomalias_value
            ]
            anomalias += [
                {"fecha": r[0], "symbol": r[1], "costo_base": float(r[2]), "costo_base_ayer": float(r[3]), "ratio": float(r[4])}
                for r in anomalias_cb
            ]

            # purga quirúrgica: solo los registros del símbolo afectado
            simbolos_purgados = set()
            for a in anomalias:
                key = (a["symbol"], str(a["fecha"]))
                if key not in simbolos_purgados:
                    cursor.execute(
                        "DELETE FROM diaria_performance WHERE account = %s AND symbol = %s AND Date >= %s",
                        (account, a["symbol"], str(a["fecha"])),
                    )
                    simbolos_purgados.add(key)

            conn.commit()
            cursor.close()
            conn.close()

            # purga performa_inversion desde la fecha mínima afectada (aggregate queda inválido)
            fecha_min = min(a["fecha"] for a in anomalias)
            conn2 = self._conectar(tabla="validate_performa.purga_pi")
            try:
                cur2 = conn2.cursor()
                cur2.execute(
                    "DELETE FROM performa_inversion WHERE idcuenta = %s AND vehiculo = %s AND fechaclose >= %s",
                    (account, vehiculo, str(fecha_min)),
                )
                conn2.commit()
            finally:
                cur2.close()
                conn2.close()

            # ── validación adicional: costo_base en performa_inversion ────────
            # Detecta filas donde costo_base colapsa (ej: 313 vs 43K del día anterior)
            # sin que diaria_performance lo haya capturado
            conn3 = self._conectar(tabla="validate_performa.costo_base")
            try:
                cur3 = conn3.cursor()
                cur3.execute(
                    """
                    SELECT t.fechaclose, t.costo_base, t.costo_base_ayer,
                           t.costo_base / t.costo_base_ayer AS ratio
                    FROM (
                        SELECT fechaclose, costo_base,
                               LAG(costo_base) OVER (
                                   PARTITION BY idcuenta, vehiculo ORDER BY fechaclose
                               ) AS costo_base_ayer
                        FROM performa_inversion
                        WHERE idcuenta = %s AND vehiculo = %s AND costo_base > 0
                    ) t
                    WHERE t.costo_base_ayer > 0
                      AND t.fechaclose >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                      AND (t.costo_base / t.costo_base_ayer > %s
                           OR t.costo_base / t.costo_base_ayer < %s)
                    ORDER BY t.fechaclose ASC
                    """,
                    (account, vehiculo, threshold, low_threshold),
                )
                cb_anomalias = cur3.fetchall()
                if cb_anomalias:
                    fecha_cb_min = cb_anomalias[0][0]
                    cur3.execute(
                        "DELETE FROM performa_inversion WHERE idcuenta = %s AND vehiculo = %s AND fechaclose >= %s",
                        (account, vehiculo, str(fecha_cb_min)),
                    )
                    conn3.commit()
                    for row in cb_anomalias:
                        print(
                            f"[validate_performa] costo_base ANOMALIA — "
                            f"fechaclose={row[0]} costo_base={row[1]:.2f} "
                            f"ayer={row[2]:.2f} ratio={row[3]:.4f} → purgado desde {fecha_cb_min}"
                        )
                    # resetear schedule para que reagrege desde fecha_cb_min
                    key = f"diaria_{vehiculo}"
                    desde_reset = (fecha_cb_min - timedelta(days=1)).strftime("%Y-%m-%d")
                    data = read_json_tmp("agents_schedule.json")
                    data[key] = desde_reset
                    write_json_tmp("agents_schedule.json", data)
            finally:
                cur3.close()
                conn3.close()

            # cuarentena: si el mismo símbolo se purga 3+ veces en 6 horas, entra en cuarentena 24h
            _QUARANTINE_LIMIT = 3
            _QUARANTINE_WINDOW = 6 * 3600
            _QUARANTINE_TTL = 24 * 3600
            now = time.time()

            _ch = read_json_tmp("cache_health")
            purge_hist = _ch.get("purge_history", {})
            quarantine = _ch.get("quarantine", {})

            symbols_ok = []
            for a in anomalias:
                sym = a["symbol"]
                recientes = [t for t in purge_hist.get(sym, []) if now - t < _QUARANTINE_WINDOW]
                recientes.append(now)
                purge_hist[sym] = recientes
                if len(recientes) >= _QUARANTINE_LIMIT:
                    quarantine[sym] = now
                    a["quarantined"] = True
                else:
                    a["quarantined"] = False
                    symbols_ok.append(sym)

            write_json_tmp("cache_health", {"purge_history": purge_hist, "quarantine": quarantine})

            # solo resetea el schedule si hay símbolos no cuarentenados con anomalías
            if symbols_ok:
                key = f"diaria_{vehiculo}"
                desde_reset = (fecha_min - timedelta(days=1)).strftime("%Y-%m-%d")
                data = read_json_tmp("agents_schedule.json")
                data[key] = desde_reset
                write_json_tmp("agents_schedule.json", data)

            return {"anomalias": anomalias, "purgados": True}

        except (Exception, connect.Error) as error:
            print(f"[Mysql:: IPerformance.validate_performa()]: {error}")
            return {"anomalias": [], "purgados": False}


class DiariaCNV(BDsystem):  # --------------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert y update sobre tabla diaria_CNV."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select_CNV(self, symbol=None, fecha=None, accion="last"):
        """
        @param symbol: activo a consultar."""

        try:
            conn = self._conectar(tabla="select.diaria_CNV")
            found, columns, sql = False, [], []
            cursor = conn.cursor()
            if fecha is not None:
                last_fecha = self.last_insert_CNV(symbol, fecha)

            elif accion == "last":
                last_fecha = self.last_insert_CNV(symbol)

            if symbol is not None:
                qry = """SELECT * FROM diaria_CNV WHERE codCAFCI='%s' and fecha='%s';"""
                cursor.execute(qry % (symbol, last_fecha))
                sql = cursor.fetchone()
                columns = [columna[0] for columna in cursor.description]
                found = True if sql else False
                return sql, columns, found
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_diaria_CNV(): {}]".format(error))
            return None, [], False

    def last_insert_CNV(self, symbol=None, date=None):
        """@param symbol:  activo a consultar
        @param date: fecha a consultar
        @return: última fecha insertada en diaria_CNV para el activo ticket."""

        try:
            conn = self._conectar(tabla="select.last_insert_CNV")
            cursor = conn.cursor()

            if date is None and symbol is not None:
                query = """SELECT max(fecha) FROM diaria_CNV WHERE codCAFCI='%s';"""
                cursor.execute(query % symbol)

            elif date is None and symbol is None:
                query = """SELECT max(fecha) FROM diaria_CNV;"""
                cursor.execute(query)
            else:
                query = """SELECT fecha FROM diaria_CNV WHERE codCAFCI='%s' and fecha='%s';"""
                cursor.execute(query % (symbol, date))

            last = cursor.fetchone()
            u_fecha = "0001-01-01"

            if last and last[0] is not None:
                u_fecha = last[0].strftime("%Y-%m-%d")
            return u_fecha
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: last_insert_CNV(): {}]".format(error))
            return "0001-01-01"

    def select_CNV_by_precio(self, precio, fecha=None):
        """Busca en diaria_cnv el fondo cuyo valorActual/1000 sea más cercano a precio.
        @param precio: valor cuota parte en ARS (ej: 613.34)
        @param fecha: date — si None usa la fecha más reciente disponible
        @return: (codCAFCI, found)"""
        try:
            conn = self._conectar(tabla="select.diaria_CNV.by_precio")
            cursor = conn.cursor()
            if fecha is not None:
                cursor.execute(
                    """SELECT codCAFCI, valorActual/1000 AS precio_cnv
                       FROM diaria_cnv WHERE DATE(fecha) = %s
                       ORDER BY ABS(valorActual/1000 - %s) LIMIT 1""",
                    (fecha, precio),
                )
            else:
                cursor.execute(
                    """SELECT codCAFCI, valorActual/1000 AS precio_cnv
                       FROM diaria_cnv WHERE fecha = (SELECT MAX(fecha) FROM diaria_cnv)
                       ORDER BY ABS(valorActual/1000 - %s) LIMIT 1""",
                    (precio,),
                )
            row = cursor.fetchone()
            if row:
                return row[0], True
            return None, False
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: select_CNV_by_precio(): {error}]")
            return None, False
        finally:
            cursor.close()
            conn.close()

    def insert_CNV(self, values=None, symbol=None):
        """
        @param values:  lista de valores de campos a insertar
        @param symbol: ticket a consultar en diaria_CNV
        @return: agrega fila  en diaria_CNV."""
        try:
            conn = self._conectar(tabla="insert.diaria_CNV")
            x, y, found = self.select_CNV(symbol=symbol, fecha=values["fecha"])
            if not found:
                cursor = conn.cursor()
                valuesins, qry = [], "INSERT INTO diaria_CNV ("
                for keys, vals in values.items():
                    if keys != "codCAFCI":
                        qry = qry + keys + ", "
                        valuesins.append(vals)

                valuesins.append(symbol)
                qry += "codCAFCI) VALUES ({});".format(",".join("'%s'" for _ in range(len(valuesins))))
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

    def select_fci_rf_candidato(self, cuenta_fci: str) -> dict:
        """Devuelve el fondo RF activo de `cuenta_fci` con menor variacion30dias (más deprimido).
        Busca en inversion (iactiva='Y') los fondos activos de esa cuenta y cruza con
        diaria_cnv para obtener el rendimiento. Excluye fondos de renta variable
        (Acciones / Renta Variable en el nombre).
        @param cuenta_fci: 'BBVA0001' o 'SANT0001'
        @return: dict con fondo, variacion30dias, variacion90dias — vacío si no hay candidato."""
        try:
            conn = self._conectar(tabla="select.diaria_cnv.rf_candidato")
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT d.fondo, d.variacion30dias, d.variacion90dias
                FROM bdinv.otros_activos o
                JOIN bdinv.inversion i ON i.ticket = o.symbol AND i.iactiva = 'Y'
                JOIN bdinv.diaria_cnv d
                  ON d.fondo = i.ticket
                  AND d.fecha = (SELECT MAX(fecha) FROM bdinv.diaria_cnv)
                WHERE o.cuenta = %s
                  AND d.fondo NOT LIKE '%%Acciones%%'
                  AND d.fondo NOT LIKE '%%Renta Variable%%'
                ORDER BY d.variacion30dias ASC
                LIMIT 1
                """,
                (cuenta_fci,),
            )
            row = cursor.fetchone()
            cols = [d[0] for d in cursor.description]
            cursor.close()
            conn.close()
            if row:
                return dict(zip(cols, row))
        except Exception as e:
            _logger.error(f"select_fci_rf_candidato({cuenta_fci}): {e}")
        return {}


class EstrategiaInversion(BDsystem):  # ------------------------------------------------------------------------------
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
                                ON a.estrategia = b.estrategia;""".format(ivehiculo)

            if accion == "tabla":
                qry = """SELECT * FROM estrategia ORDER BY estrategia"""

            if accion == "Select":
                qry = "SELECT objetivo FROM inversion  WHERE ticket ='%s';" % ticket

            if accion == "vehiculo":
                qry = "SELECT * FROM estrategia WHERE vehiculo = '%s';" % ivehiculo

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

                if accion in ("Select", "vehiculo"):
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)

            return xlis
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: Estrategia.Select()]: {}".format(error))

    def _get_pendientes_query(self, qry: str, params: tuple, nombre: str) -> list:
        try:
            conn = self._conectar(tabla=f"select.{nombre}")
            cursor = conn.cursor()
            cursor.execute(qry, params)
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(cols, r)) for r in rows] if rows else []
        except Exception as e:
            print(f"[EstrategiaInversion.{nombre}()]: {e}")
            return []
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    def get_etfs_pendientes(self, account):
        """ETFs, commodities y posiciones con código de esquema viejo pendientes de clasificación."""
        return self._get_pendientes_query(
            """SELECT m.symbol, m.shortName
               FROM market m
               LEFT JOIN inversion i ON i.ticket = m.symbol AND i.useraccount = %s AND i.iactiva = 'Y'
               WHERE m.account = %s AND (
                 (m.categoriaActivo = 'X'
                  AND (i.estrategia IS NULL OR i.estrategia NOT IN ('P01','P02','P03','P04','P05')))
                 OR
                 (m.categoriaActivo IN ('I','S','N') AND m.encartera = 'Y'
                  AND (i.estrategia IS NULL OR i.estrategia = 'P02')
                  AND m.shortName REGEXP 'Gold|Silver|Plata|Oro')
                 OR
                 (i.iactiva = 'Y' AND m.encartera = 'Y'
                  AND i.estrategia IN ('A01','A02','A03','A04','A05','A99','C01','C02'))
               )""",
            (account, account), "get_etfs_pendientes",
        )

    def get_crypto_pendientes(self, account):
        """Crypto activos con estrategia NULL o código viejo pendientes de clasificación."""
        return self._get_pendientes_query(
            """SELECT i.ticket AS symbol, o.descripcion AS shortName
               FROM inversion i
               LEFT JOIN otros_activos o ON o.symbol = i.ticket
               WHERE i.useraccount = %s
                 AND i.tipoinv = 'Crypto'
                 AND i.iactiva = 'Y'
                 AND (i.estrategia IS NULL
                      OR i.estrategia IN ('A01','A02','A03','A04','A05','A99','C01','C02'))""",
            (account,), "get_crypto_pendientes",
        )

    def get_exchange_pendientes(self, account):
        """Assets con descripción 'Exchange' (categoría legacy) pendientes de reclasificación como Crypto."""
        return self._get_pendientes_query(
            """SELECT i.ticket AS symbol, COALESCE(o.descripcion, i.ticket) AS shortName
               FROM inversion i
               LEFT JOIN otros_activos o ON o.symbol = i.ticket
               LEFT JOIN estrategia e ON i.estrategia = e.estrategia
               WHERE i.useraccount = %s
                 AND i.iactiva = 'Y'
                 AND e.descripcion = 'Exchange'""",
            (account,), "get_exchange_pendientes",
        )

    def update_estrategia_etf(self, ticket, account, estrategia):
        """Actualiza estrategia en inversion para un ETF clasificado. Write-once."""
        try:
            conn = self._conectar(tabla="update.etf_estrategia")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inversion SET estrategia = %s WHERE ticket = %s AND useraccount = %s",
                (estrategia, ticket, account),
            )
            conn.commit()
        except Exception as e:
            print(f"[EstrategiaInversion.update_estrategia_etf({ticket})]: {e}")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass


class MarketScreen(BDsystem):  # -------------------------------------------------------------------------------------
    """
    clase para manejar operaciones: select, insert y update sobre tabla Market."""

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        conn = BDsystem.connect_dbase(tabla, display=self.display)
        return conn

    def select(self, account=None, tipo=None, symbol=None, country=None, sector=None, name=None):
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

            if is_none(symbol) and is_none(name) and not is_none(country) and not is_none(sector):
                qry = """SELECT  * FROM market WHERE account= '%s' AND country = '%s' AND sector = '%s';"""
                cursor.execute(qry % (account, country, sector))
                sql = cursor.fetchall()

            ix = [columna[0] for columna in cursor.description]
            return sql, ix
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: select_market]: {}".format(error))
            return [], []

    def select_all(self, account):
        """Retorna todas las filas de market para la cuenta sin filtro de tipo."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM market WHERE account = %s", (account,))
            sql = cursor.fetchall()
            ix = [c[0] for c in cursor.description]
            return sql, ix
        except (Exception, connect.Error) as e:
            print(f"[MarketScreen.select_all]: {e}")
            return [], []

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

            # Agregar categoriaActivo con valor por defecto 'N' si no está en los parámetros
            if "categoriaActivo" not in upd:
                listvalues.append("N")
                qry = qry + "categoriaActivo, "

            listvalues.append(datetime.now())
            listvalues.append(symbol)
            valuesins = tuple(listvalues)
            # Usar parametrización segura sin comillas - el driver maneja NULL correctamente
            qry += "timestamp, symbol) VALUES ({});".format(", ".join("%s" for _ in range(len(valuesins))))
            cursor.execute(qry, valuesins)  # Parametrización segura
            conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql::insert_market()]: {}".format(error))

    def sync_sector_to_inversion(self, account: str) -> int:
        """Propaga market.sector → inversion.sector para todos los símbolos en cartera."""
        try:
            conn = self._conectar(tabla="update.market")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE inversion i "
                "JOIN market m ON m.symbol = i.ticket AND m.account = %s "
                "SET i.sector = m.sector "
                "WHERE m.sector IS NOT NULL AND m.sector != '' AND i.tipoinv = 'Stock'",
                (account,),
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"sync_sector_to_inversion(): {error}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def update(self, upd=None, val=None, symbol=None, account=None):
        """
        @param upd:     list() de campos para actualizar en market
        @param val:     list() de valores que acompañan a upd
        @param symbol:  symbol que se actualiza en market
        @param account: filtra por account si se provee
        @return:  True si se afectó al menos una fila, False en caso contrario
        """
        try:
            conn = self._conectar(tabla="update.market")
            cursor = conn.cursor()
            listvalues = []
            qry = "UPDATE market SET "

            for i, value in enumerate(val):
                if upd[i] in ("sector", "country"):
                    listvalues.append("SV" if value == "None" else value)
                else:
                    listvalues.append(value)
                qry = qry + upd[i] + "=%s,"

            listvalues.append(datetime.now())
            listvalues.append(symbol)
            qry += "timestamp=%s WHERE symbol=%s"
            if account:
                qry += " AND account=%s"
                listvalues.append(account)
            qry += ";"
            cursor.execute(qry, tuple(listvalues))
            conn.commit()
            return cursor.rowcount > 0
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql::update()]: {}".format(error))
            return False

    def load_symbols(self, account):
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT symbol, categoriaActivo FROM market WHERE account = %s", (account,))
            return {row[0]: row[1] for row in cursor.fetchall()}
        except (Exception, connect.Error) as error:
            print("[Mysql::load_symbols()]: {}".format(error))
            return {}

    def delete(self, symbol, account):
        """Elimina un símbolo de fund_holdings y luego de market."""
        try:
            conn = self._conectar(tabla="delete.market")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM fund_holdings WHERE symbol = %s", (symbol,))
            cursor.execute("DELETE FROM market WHERE symbol = %s AND account = %s", (symbol, account))
            conn.commit()
            cursor.close()
            conn.close()
        except (Exception, connect.Error) as error:
            print(f"[Mysql::delete_market({symbol})]: {error}")

    def rename_symbol(self, old_symbol: str, new_symbol: str, account: str) -> dict:
        """Renombra un ticker en todas las tablas que lo referencian.

        Tablas actualizadas: market, booktrading (simbolo), oportunidadesbuysell,
        order_trader, trazaplan, youtube_candidatos, ia_trace (simbolo).
        Devuelve dict {tabla: filas_afectadas} para log.
        """
        conn = self._conectar(tabla="rename.market")
        cursor = conn.cursor()
        result = {}
        ops = [
            ("market",               "UPDATE market SET symbol=%s WHERE symbol=%s AND account=%s",        (new_symbol, old_symbol, account)),
            ("booktrading",          "UPDATE booktrading SET simbolo=%s WHERE simbolo=%s AND cuenta=%s",  (new_symbol, old_symbol, account)),
            ("oportunidadesbuysell", "UPDATE oportunidadesbuysell SET symbol=%s WHERE symbol=%s",        (new_symbol, old_symbol)),
            ("order_trader",         "UPDATE order_trader SET symbol=%s WHERE symbol=%s AND account=%s", (new_symbol, old_symbol, account)),
            ("trazaplan",            "UPDATE trazaplan SET symbol=%s WHERE symbol=%s AND idcuenta=%s",    (new_symbol, old_symbol, account)),
            ("youtube_candidatos",   "UPDATE youtube_candidatos SET symbol=%s WHERE symbol=%s",           (new_symbol, old_symbol)),
            ("ia_trace",             "UPDATE ia_trace SET simbolo=%s WHERE simbolo=%s",                   (new_symbol, old_symbol)),
        ]
        try:
            for tabla, sql, params in ops:
                cursor.execute(sql, params)
                result[tabla] = cursor.rowcount
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"rename_symbol({old_symbol}→{new_symbol}): {error}")
        finally:
            cursor.close()
            conn.close()
        return result

    def load_cartera_symbols(self, account) -> list:
        """Retorna lista de dicts {symbol, shortName, lastPrice, categoriaActivo} para activos encartera='Y'."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT symbol, shortName, lastPrice, categoriaActivo "
                "FROM market WHERE account = %s AND encartera = 'Y' "
                "ORDER BY symbol",
                (account,),
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"load_cartera_symbols({account}): {error}")
            return []
        finally:
            conn.close()

    def load_cartera_inst(self, account) -> list:
        """Retorna lista de dicts con campos institucionales para activos en cartera (encartera='Y')."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT symbol, shortName, lastPrice, inst_ownership_pct, inst_score, "
                "fh_count, fh_total_value, fh_buy_ratio, fh_sell_ratio, "
                "fh_call_shares, fh_put_shares, new_entrants, full_exits, "
                "delta_call_shares, delta_put_shares, "
                "analyst_rec, analyst_mean, analyst_count, categoriaActivo, "
                "floatShares, sharesOutstanding, volume, insider_ownership_pct, website "
                "FROM market WHERE account = %s AND encartera = 'Y' AND categoriaActivo != 'X' "
                "ORDER BY inst_score DESC",
                (account,),
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"load_cartera_inst({account}): {error}")
            return []
        finally:
            conn.close()

    def mark_booktrading_delisted(self, symbol, account, fecha_deliste=None) -> int:
        """Marca delisted=1 en todos los registros de booktrading para symbol+account.
        fecha_deliste: date en que dejó de cotizar; detalle_book procesa hasta esa fecha.
        """
        try:
            conn = self._conectar(tabla="update.booktrading")
            cursor = conn.cursor()
            if fecha_deliste is not None:
                cursor.execute(
                    "UPDATE booktrading SET delisted = 1, fecha_deliste = %s, updateStamp = %s "
                    "WHERE simbolo = %s AND cuenta = %s",
                    (fecha_deliste, datetime.now(), symbol, account),
                )
            else:
                cursor.execute(
                    "UPDATE booktrading SET delisted = 1, updateStamp = %s " "WHERE simbolo = %s AND cuenta = %s",
                    (datetime.now(), symbol, account),
                )
            conn.commit()
            affected = cursor.rowcount
            cursor.close()
            conn.close()
            return affected
        except (Exception, connect.Error) as error:
            _logger.error(f"mark_booktrading_delisted({symbol}): {error}")
            return 0

    def load_symbols_needing_fundamentals(self, account) -> list:
        """Retorna símbolos activos con cualquier campo fundamental NULL o vacío."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT symbol FROM market
                WHERE account = %s
                  AND categoriaActivo NOT IN ('I','S','X')
                  AND (
                    country       IS NULL OR country       = ''  OR
                    sector        IS NULL OR sector        = ''  OR
                    shortName     IS NULL OR shortName     = ''  OR
                    website       IS NULL OR website       = ''  OR
                    targetMeanPrice     IS NULL OR
                    returnOnEquity      IS NULL OR
                    returnOnAssets      IS NULL OR
                    pegRatio            IS NULL OR
                    priceToBook         IS NULL OR
                    earningsGrowth      IS NULL OR
                    revenueGrowth       IS NULL OR
                    freeCashflow        IS NULL OR
                    grossMargins        IS NULL OR
                    ebitdaMargins       IS NULL OR
                    operatingMargins    IS NULL OR
                    lastFiscalYearEnd   IS NULL OR
                    analyst_rec      IS NULL OR analyst_rec   = ''  OR
                    analyst_mean     IS NULL OR
                    analyst_count    IS NULL OR
                    sharesOutstanding IS NULL OR
                    floatShares       IS NULL
                  )
                """,
                (account,),
            )
            return [row[0] for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"load_symbols_needing_fundamentals({account}): {error}")
            return []
        finally:
            conn.close()

    def select_top_marketcap(self, account, top_n=200) -> list:
        """Retorna lista de symbols ordenados por marketCap DESC, limitados a top_n.
        Excluye categoriaActivo I/S/X y símbolos sin marketCap."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT symbol FROM market WHERE account = %s AND marketCap IS NOT NULL "
                "AND categoriaActivo NOT IN ('I', 'S', 'X') ORDER BY marketCap DESC LIMIT %s",
                (account, top_n),
            )
            return [row[0] for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            print(f"[Mysql::select_top_marketcap()]: {error}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_cusip_map(self, account: str) -> dict:
        """Retorna {cusip: symbol} combinando market + fund_holdings.
        fund_holdings ya tiene el mapeo completo de runs anteriores — evita
        re-llamar OpenFIGI para CUSIPs ya resueltos."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT cusip, symbol FROM market WHERE cusip IS NOT NULL AND account = %s", (account,))
            result = {row[0]: row[1] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT DISTINCT cusip, symbol FROM fund_holdings " "WHERE cusip IS NOT NULL AND symbol IS NOT NULL"
            )
            for cusip, symbol in cursor.fetchall():
                if cusip not in result:
                    result[cusip] = symbol
            return result
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::get_cusip_map()]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def update_market_cusip(self, symbol: str, account: str, cusip: str) -> None:
        """Actualiza el campo cusip en market para un símbolo."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE market SET cusip = %s WHERE symbol = %s AND account = %s",
                (cusip, symbol, account),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_market_cusip({symbol})]: {error}")
        finally:
            cursor.close()
            conn.close()

    def bulk_insert_edgar_funds(self, funds_list: list) -> int:
        """INSERT IGNORE masivo de fondos EDGAR en tabla funds.
        funds_list: lista de (fund_name, cik). No pisa registros existentes.
        Retorna cantidad de filas insertadas."""
        if not funds_list:
            return 0
        _CHUNK = 500
        inserted = 0
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            for i in range(0, len(funds_list), _CHUNK):
                chunk = funds_list[i : i + _CHUNK]
                placeholders = ",".join(["(%s,%s)"] * len(chunk))
                sql = f"INSERT IGNORE INTO funds (fund_name, cik) VALUES {placeholders}"
                flat = [v for row in chunk for v in row]
                cursor.execute(sql, flat)
                inserted += cursor.rowcount
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::bulk_insert_edgar_funds()]: {error}")
        finally:
            cursor.close()
            conn.close()
        return inserted

    def update_fund_cik(self, fund_name: str, cik: str) -> None:
        """Actualiza el CIK de un fondo en tabla funds por nombre."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE funds SET cik = %s WHERE fund_name = %s", (cik, fund_name[:200]))
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_fund_cik({fund_name})]: {error}")
        finally:
            cursor.close()
            conn.close()

    def load_top_funds_with_cik(self, top_n: int = 50) -> list:
        """Retorna lista de (fund_name, cik) con CIK asignado, ordenados por frecuencia desc."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT fund_name, cik FROM funds WHERE cik IS NOT NULL ORDER BY frequency DESC LIMIT %s",
                (top_n,),
            )
            return cursor.fetchall()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_top_funds_with_cik()]: {error}")
            return []

    def load_all_funds_with_cik(self, account: str = None) -> list:
        """Retorna lista de (fund_name, cik) con CIK asignado, ordenada por cik.

        Si se pasa account, filtra solo fondos que tienen holdings en símbolos
        de la tabla market para esa cuenta (Opción B — ~7.7K vs 98K total).
        """
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            if account:
                cursor.execute(
                    "SELECT DISTINCT f.fund_name, f.cik FROM funds f "
                    "INNER JOIN fund_holdings fh ON fh.fund_id = f.id "
                    "INNER JOIN market m ON m.symbol = fh.symbol AND m.account = %s "
                    "WHERE f.cik IS NOT NULL ORDER BY f.cik",
                    (account,),
                )
            else:
                cursor.execute("SELECT fund_name, cik FROM funds WHERE cik IS NOT NULL ORDER BY cik")
            return cursor.fetchall()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_all_funds_with_cik()]: {error}")
            return []
        finally:
            cursor.close()
            conn.close()

    def get_fund_id_by_cik(self, cik: str) -> int | None:
        """Retorna el id del fondo en tabla funds dado su CIK."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM funds WHERE cik = %s", (cik,))
            row = cursor.fetchone()
            return row[0] if row else None
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::get_fund_id_by_cik({cik})]: {error}")
            return None
        finally:
            cursor.close()
            conn.close()

    def load_screener_health(self, account: str) -> dict:
        """Retorna métricas de salud del pipeline 13F para el status bar del Screener:
        - pendientes     : fund_filings con processed=0
        - por_renovar    : fondos con filing_date >= 70 días (próximos al umbral 80d)
        - fh_sin_symbol  : fund_holdings con symbol no en market
        - market_sin_cusip: symbols en market sin cusip (invisibles al pipeline 13F)"""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            # Solo fondos con holdings en símbolos de esta cuenta
            cursor.execute(
                "SELECT COUNT(*) FROM fund_filings ff "
                "JOIN funds f ON f.cik = ff.cik "
                "WHERE ff.processed = 0 "
                "  AND EXISTS ("
                "    SELECT 1 FROM fund_holdings fh "
                "    JOIN market m ON m.symbol = fh.symbol AND m.account = %s "
                "    WHERE fh.fund_id = f.id"
                "  )",
                (account,),
            )
            pendientes = cursor.fetchone()[0] or 0

            cursor.execute(
                "SELECT COUNT(*) FROM funds f "
                "WHERE EXISTS (SELECT 1 FROM fund_filings ff WHERE ff.cik = f.cik) "
                "  AND (SELECT MAX(ff.filing_date) FROM fund_filings ff WHERE ff.cik = f.cik) "
                "      <= DATE_SUB(CURDATE(), INTERVAL 70 DAY) "
                "  AND EXISTS ("
                "    SELECT 1 FROM fund_holdings fh "
                "    JOIN market m ON m.symbol = fh.symbol AND m.account = %s "
                "    WHERE fh.fund_id = f.id"
                "  )",
                (account,),
            )
            por_renovar = cursor.fetchone()[0] or 0

            cursor.execute(
                "SELECT COUNT(DISTINCT fh.symbol) FROM fund_holdings fh "
                "LEFT JOIN market m ON m.symbol = fh.symbol AND m.account = %s "
                "WHERE m.symbol IS NULL",
                (account,),
            )
            fh_sin_symbol = cursor.fetchone()[0] or 0

            cursor.execute(
                "SELECT COUNT(*) FROM market " "WHERE account = %s AND cusip IS NULL AND encartera = 'Y'",
                (account,),
            )
            market_sin_cusip = cursor.fetchone()[0] or 0

            return {
                "pendientes": pendientes,
                "por_renovar": por_renovar,
                "fh_sin_symbol": fh_sin_symbol,
                "market_sin_cusip": market_sin_cusip,
            }
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_screener_health]: {error}")
            return {"pendientes": 0, "por_renovar": 0, "fh_sin_symbol": 0, "market_sin_cusip": 0}
        finally:
            cursor.close()
            conn.close()

    def load_fund_filings_all(self) -> list:
        """Retorna lista de {filename, cik, filing_date} para todos los filings en BD."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT filename, cik, filing_date FROM fund_filings")
            return [
                {"filename": filename, "cik": cik, "filing_date": str(filing_date)}
                for filename, cik, filing_date in cursor.fetchall()
            ]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_fund_filings_all]: {error}")
            return []
        finally:
            cursor.close()
            conn.close()

    def load_fund_filings_cik_meta(self) -> dict:
        """Retorna {cik: {filing_date, accession, filename}} con el filing más reciente
        por fondo. Reemplaza el JSON 13f_metadata temporal."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT cik, filing_date, accession, filename
                FROM fund_filings ff1
                WHERE filing_date = (
                    SELECT MAX(ff2.filing_date) FROM fund_filings ff2 WHERE ff2.cik = ff1.cik
                )
            """)
            return {
                cik: {"filing_date": str(filing_date), "accession": accession, "filename": filename}
                for cik, filing_date, accession, filename in cursor.fetchall()
            }
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_fund_filings_cik_meta]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def load_unprocessed_filings(self) -> list:
        """Retorna lista de {filename, cik, fund_name, filing_date} de filings
        no procesados aún en fund_holdings. Reemplaza holdings_processed.json."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT filename, cik, fund_name, filing_date FROM fund_filings WHERE processed = 0 ORDER BY filing_date ASC"
            )
            return [
                {"filename": fn, "cik": cik, "fund_name": fn_name, "filing_date": str(fd)}
                for fn, cik, fn_name, fd in cursor.fetchall()
            ]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_unprocessed_filings]: {error}")
            return []
        finally:
            cursor.close()
            conn.close()

    def save_fund_filing(self, filename: str, cik: str, fund_name: str, filing_date: str, accession: str) -> None:
        """INSERT IGNORE de un filing en fund_filings."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT IGNORE INTO fund_filings (filename, cik, fund_name, filing_date, accession) "
                "VALUES (%s, %s, %s, %s, %s)",
                (filename, cik, fund_name, filing_date, accession),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::save_fund_filing({filename})]: {error}")
        finally:
            cursor.close()
            conn.close()

    def bulk_save_fund_filings(self, records: list) -> int:
        """INSERT IGNORE masivo de filings en fund_filings.
        records: lista de (filename, cik, fund_name, filing_date, accession)."""
        if not records:
            return 0
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.executemany(
                "INSERT IGNORE INTO fund_filings (filename, cik, fund_name, filing_date, accession) "
                "VALUES (%s, %s, %s, %s, %s)",
                records,
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::bulk_save_fund_filings]: {error}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def mark_filings_processed(self, filenames: list) -> None:
        """Marca como processed=1 los filenames indicados en fund_filings."""
        if not filenames:
            return
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            placeholders = ",".join(["%s"] * len(filenames))
            cursor.execute(
                f"UPDATE fund_filings SET processed = 1 WHERE filename IN ({placeholders})",
                filenames,
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::mark_filings_processed]: {error}")
        finally:
            cursor.close()
            conn.close()

    def upsert_fund_holding(
        self,
        fund_name: str,
        symbol: str,
        shares: int,
        report_date,
        value: int = None,
        cusip: str = None,
        option_type: str = None,
    ) -> None:
        """INSERT o UPDATE en fund_holdings. Calcula operation vs registro anterior.
        Filtra bonos/preferreds: solo acepta símbolos puros de letras con ≤ 5 chars.
        option_type: None=acciones directas, 'CALL'/'PUT'=opciones."""
        if len(symbol) > 5 or not symbol.isalpha():
            return
        for attempt in range(3):
            conn = self._conectar(tabla="update.market")
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM funds WHERE fund_name = %s", (fund_name[:200],))
                row = cursor.fetchone()
                if not row:
                    return
                fund_id = row[0]

                cursor.execute(
                    "SELECT shares FROM fund_holdings WHERE fund_id = %s AND symbol = %s "
                    "AND option_type = %s "
                    "ORDER BY report_date DESC LIMIT 1",
                    (fund_id, symbol, option_type or "STK"),
                )
                prev = cursor.fetchone()
                shares_prev = int(prev[0]) if prev else None

                if shares_prev is None:
                    operation, shares_delta, pct_change = "NEW", None, None
                elif shares > shares_prev:
                    operation = "BUY"
                    shares_delta = shares - shares_prev
                    pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
                elif shares < shares_prev:
                    operation = "SELL"
                    shares_delta = shares - shares_prev
                    pct_change = round(shares_delta / shares_prev, 4) if shares_prev > 0 else None
                else:
                    operation, shares_delta, pct_change = "HOLD", 0, 0.0

                cursor.execute(
                    "INSERT INTO fund_holdings (fund_id, symbol, shares, shares_prev, "
                    "shares_delta, pct_change, operation, report_date, value, cusip, option_type) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE "
                    "shares=%s, shares_prev=%s, shares_delta=%s, "
                    "pct_change=%s, operation=%s, value=%s",
                    (
                        fund_id,
                        symbol,
                        shares,
                        shares_prev,
                        shares_delta,
                        pct_change,
                        operation,
                        report_date,
                        value,
                        cusip,
                        option_type,
                        shares,
                        shares_prev,
                        shares_delta,
                        pct_change,
                        operation,
                        value,
                    ),
                )
                conn.commit()
                return
            except connect.Error as error:
                if error.errno in (1213, 1412) and attempt < 2:  # deadlock / table def changed
                    cursor.close()
                    conn.close()
                    time.sleep(0.5 * (attempt + 1))
                    continue
                _logger.error(f"[Mysql::upsert_fund_holding({fund_name}, {symbol})]: {error}")
                return
            except Exception as error:
                _logger.error(f"[Mysql::upsert_fund_holding({fund_name}, {symbol})]: {error}")
                return
            finally:
                cursor.close()
                conn.close()

    def cleanup_fund_holdings_nulls(self) -> int:
        """Elimina filas con cusip IS NULL cuando ya existe otra fila del mismo (fund_id, symbol) con cusip."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE fh1 FROM fund_holdings fh1 "
                "INNER JOIN fund_holdings fh2 "
                "  ON fh2.fund_id = fh1.fund_id AND fh2.symbol = fh1.symbol AND fh2.cusip IS NOT NULL "
                "WHERE fh1.cusip IS NULL"
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::cleanup_fund_holdings_nulls]: {error}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def load_fund_holdings_stats(self) -> dict:
        """Retorna {symbol: {fh_count, fh_total_value, fh_buy_ratio, fh_sell_ratio,
        fh_call_count, fh_put_count, fh_call_shares, fh_put_shares}} con el último
        filing por fondo y tipo de posición.
        fh_count/buy_ratio/sell_ratio: solo posiciones directas (option_type='STK').
        fh_call_count/fh_put_count: fondos únicos con opciones.
        fh_call_shares/fh_put_shares: acciones totales en posiciones CALL/PUT."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            # Query principal — snapshot del último filing por fondo (igual que antes, probado y rápido)
            cursor.execute("""
                SELECT fh.symbol,
                    COUNT(DISTINCT CASE WHEN fh.option_type = 'STK' THEN fh.fund_id END) AS fh_count,
                    SUM(CASE WHEN fh.option_type = 'STK' THEN fh.value ELSE 0 END) AS fh_total_value,
                    SUM(CASE WHEN fh.option_type = 'STK' AND fh.operation IN ('NEW','BUY') THEN 1 ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN fh.option_type = 'STK' THEN 1 ELSE 0 END), 0) AS fh_buy_ratio,
                    SUM(CASE WHEN fh.option_type = 'STK' AND fh.operation = 'SELL' THEN 1 ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN fh.option_type = 'STK' THEN 1 ELSE 0 END), 0) AS fh_sell_ratio,
                    COUNT(DISTINCT CASE WHEN fh.option_type = 'CALL' THEN fh.fund_id END) AS fh_call_count,
                    COUNT(DISTINCT CASE WHEN fh.option_type = 'PUT'  THEN fh.fund_id END) AS fh_put_count,
                    SUM(CASE WHEN fh.option_type = 'CALL' THEN fh.shares ELSE 0 END) AS fh_call_shares,
                    SUM(CASE WHEN fh.option_type = 'PUT'  THEN fh.shares ELSE 0 END) AS fh_put_shares,
                    SUM(CASE WHEN fh.option_type = 'STK'  THEN fh.shares ELSE 0 END) AS fh_total_shares,
                    COUNT(DISTINCT CASE WHEN fh.option_type = 'STK' AND fh.operation = 'NEW'
                        THEN fh.fund_id END) AS new_entrants,
                    COUNT(DISTINCT CASE WHEN fh.option_type = 'STK' AND fh.operation = 'SELL'
                        AND fh.shares = 0 THEN fh.fund_id END) AS full_exits
                FROM fund_holdings fh
                INNER JOIN (
                    SELECT fund_id, symbol, option_type AS opt_grp,
                        MAX(report_date) AS max_date
                    FROM fund_holdings
                    GROUP BY fund_id, symbol, option_type
                ) latest ON fh.fund_id = latest.fund_id
                    AND fh.symbol = latest.symbol
                    AND fh.option_type = latest.opt_grp
                    AND fh.report_date = latest.max_date
                GROUP BY fh.symbol
            """)
            result = {}
            for row in cursor.fetchall():
                (
                    symbol,
                    fh_count,
                    fh_total_value,
                    fh_buy_ratio,
                    fh_sell_ratio,
                    fh_call_count,
                    fh_put_count,
                    fh_call_shares,
                    fh_put_shares,
                    fh_total_shares,
                    new_entrants,
                    full_exits,
                ) = row
                result[symbol] = {
                    "fh_count": int(fh_count) if fh_count else 0,
                    "fh_total_value": int(fh_total_value) if fh_total_value else None,
                    "fh_buy_ratio": float(fh_buy_ratio) if fh_buy_ratio else 0.0,
                    "fh_sell_ratio": float(fh_sell_ratio) if fh_sell_ratio else 0.0,
                    "fh_call_count": int(fh_call_count) if fh_call_count else 0,
                    "fh_put_count": int(fh_put_count) if fh_put_count else 0,
                    "fh_call_shares": int(fh_call_shares) if fh_call_shares else 0,
                    "fh_put_shares": int(fh_put_shares) if fh_put_shares else 0,
                    "fh_total_shares": int(fh_total_shares) if fh_total_shares else 0,
                    "new_entrants": int(new_entrants) if new_entrants else 0,
                    "full_exits": int(full_exits) if full_exits else 0,
                    "delta_call_shares": None,
                    "delta_put_shares": None,
                }

            # Query full_exits — fondos en Q_anterior que NO aparecen en Q_actual
            # Ventanas calculadas dinámicamente según el calendario 13F (45 días post-quarter end)
            today = datetime.today()
            m, y = today.month, today.year
            if m <= 5:  # Ene-May: Q4 en curso (Dec quarter)
                q_act_start = datetime(y, 1, 1).date()
                q_ant_start = datetime(y - 1, 8, 1).date()
                q_ant_end = datetime(y - 1, 12, 31).date()
            elif m <= 8:  # Jun-Ago: Q1 en curso (Mar quarter)
                q_act_start = datetime(y, 4, 1).date()
                q_ant_start = datetime(y - 1, 11, 1).date()
                q_ant_end = datetime(y, 3, 31).date()
            elif m <= 11:  # Sep-Nov: Q2 en curso (Jun quarter)
                q_act_start = datetime(y, 7, 1).date()
                q_ant_start = datetime(y, 2, 1).date()
                q_ant_end = datetime(y, 6, 30).date()
            else:  # Dic: Q3 en curso (Sep quarter)
                q_act_start = datetime(y, 10, 1).date()
                q_ant_start = datetime(y, 5, 1).date()
                q_ant_end = datetime(y, 9, 30).date()

            cursor.execute(
                """
                SELECT fh_q3.symbol, COUNT(DISTINCT fh_q3.fund_id) AS full_exits
                FROM (
                    SELECT DISTINCT fund_id, symbol FROM fund_holdings
                    WHERE option_type = 'STK'
                      AND report_date BETWEEN %s AND %s
                ) fh_q3
                LEFT JOIN (
                    SELECT DISTINCT fund_id, symbol FROM fund_holdings
                    WHERE option_type = 'STK' AND report_date >= %s
                ) fh_q4 ON fh_q3.fund_id = fh_q4.fund_id AND fh_q3.symbol = fh_q4.symbol
                WHERE fh_q4.fund_id IS NULL
                GROUP BY fh_q3.symbol
            """,
                (q_ant_start, q_ant_end, q_act_start),
            )
            for row in cursor.fetchall():
                sym, full_exits_val = row
                if sym in result:
                    result[sym]["full_exits"] = int(full_exits_val) if full_exits_val else 0

            # Query delta CALL/PUT — Q actual vs Q anterior por símbolo (solo símbolos con 2 trimestres)
            cursor.execute("""
                SELECT symbol,
                    SUM(CASE WHEN es_actual = 1 THEN call_sh ELSE 0 END) -
                    SUM(CASE WHEN es_actual = 0 THEN call_sh ELSE 0 END) AS delta_call,
                    SUM(CASE WHEN es_actual = 1 THEN put_sh ELSE 0 END) -
                    SUM(CASE WHEN es_actual = 0 THEN put_sh ELSE 0 END) AS delta_put
                FROM (
                    SELECT fh.symbol,
                        SUM(CASE WHEN fh.option_type='CALL' THEN fh.shares ELSE 0 END) AS call_sh,
                        SUM(CASE WHEN fh.option_type='PUT'  THEN fh.shares ELSE 0 END) AS put_sh,
                        (fh.report_date = max_dates.max_date) AS es_actual
                    FROM fund_holdings fh
                    INNER JOIN (
                        SELECT symbol,
                            MAX(report_date) AS max_date,
                            MIN(report_date) AS min_date
                        FROM fund_holdings
                        WHERE option_type IN ('CALL','PUT')
                        GROUP BY symbol
                        HAVING COUNT(DISTINCT report_date) >= 2
                    ) max_dates ON fh.symbol = max_dates.symbol
                        AND (fh.report_date = max_dates.max_date
                             OR fh.report_date = max_dates.min_date)
                    WHERE fh.option_type IN ('CALL','PUT')
                    GROUP BY fh.symbol, es_actual
                ) t
                GROUP BY symbol
            """)
            for row in cursor.fetchall():
                sym, delta_call, delta_put = row
                if sym in result:
                    result[sym]["delta_call_shares"] = int(delta_call) if delta_call is not None else None
                    result[sym]["delta_put_shares"] = int(delta_put) if delta_put is not None else None
            return result
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_fund_holdings_stats]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def load_fund_holdings_prev(self) -> dict:
        """Carga el último registro por (fund_id, cusip, option_type) en memoria.
        Retorna {(fund_id, cusip, opt_grp): shares} donde opt_grp='STK' para acciones directas."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT fh.fund_id, fh.cusip, fh.option_type, fh.shares
                FROM fund_holdings fh
                INNER JOIN (
                    SELECT fund_id, cusip, option_type AS opt_grp,
                        MAX(report_date) AS max_date
                    FROM fund_holdings
                    GROUP BY fund_id, cusip, option_type
                ) latest ON fh.fund_id = latest.fund_id
                    AND fh.cusip = latest.cusip
                    AND fh.option_type = latest.opt_grp
                    AND fh.report_date = latest.max_date
            """)
            return {(fund_id, cusip, opt): shares for fund_id, cusip, opt, shares in cursor.fetchall()}
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_fund_holdings_prev]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def bulk_upsert_fund_holdings(self, records: list, chunk_size: int = 5000) -> int:
        """INSERT ... ON DUPLICATE KEY UPDATE masivo usando execute con multi-row VALUES.
        Cada record: (fund_id, symbol, shares, shares_prev, shares_delta, pct_change,
                      operation, report_date, value, cusip, option_type)"""
        if not records:
            return 0
        # Garantizar option_type != NULL — la clave UNIQUE requiere valor explícito
        records = [r[:10] + (r[10] or "STK",) for r in records]
        _SQL_BASE = (
            "INSERT INTO fund_holdings "
            "(fund_id, symbol, shares, shares_prev, shares_delta, pct_change, "
            "operation, report_date, value, cusip, option_type) VALUES "
        )
        _SQL_UPDATE = (
            " ON DUPLICATE KEY UPDATE "
            "shares=VALUES(shares), shares_prev=VALUES(shares_prev), "
            "shares_delta=VALUES(shares_delta), pct_change=VALUES(pct_change), "
            "operation=VALUES(operation), value=VALUES(value)"
        )
        _ROW_PH = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        total = 0
        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]
            sql = _SQL_BASE + ",".join([_ROW_PH] * len(chunk)) + _SQL_UPDATE
            flat = [v for r in chunk for v in r]
            conn = self._conectar(tabla="update.market")
            cursor = conn.cursor()
            try:
                cursor.execute(sql, flat)
                conn.commit()
                total += cursor.rowcount
            except (Exception, connect.Error) as error:
                _logger.error(f"[Mysql::bulk_upsert_fund_holdings chunk {i}]: {error}")
            finally:
                cursor.close()
                conn.close()
        return total

    def load_market_inst_fields(self, account: str) -> dict:
        """Retorna {symbol: {inst_ownership_pct, floatShares, sharesOutstanding}}."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT symbol, inst_ownership_pct, floatShares, sharesOutstanding "
                "FROM market WHERE account = %s AND categoriaActivo != 'X'",
                (account,),
            )
            return {
                row[0]: {
                    "inst_ownership_pct": row[1],
                    "floatShares": row[2],
                    "sharesOutstanding": row[3],
                }
                for row in cursor.fetchall()
            }
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_market_inst_fields]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def bulk_save_sentiment(self, records: list) -> int:
        """INSERT IGNORE de lecturas de sentimiento.
        records: lista de (symbol, fecha_hora, sentimiento, headlines_count, fuente)."""
        if not records:
            return 0
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.executemany(
                "INSERT IGNORE INTO market_sentiment "
                "(symbol, fecha_hora, sentimiento, headlines_count, fuente) "
                "VALUES (%s, %s, %s, %s, %s)",
                records,
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::bulk_save_sentiment]: {error}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def load_latest_sentiment(self, account: str) -> dict:
        """Retorna {symbol: sentimiento} con la lectura más reciente por símbolo de cartera."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT ms.symbol, ms.sentimiento "
                "FROM market_sentiment ms "
                "INNER JOIN ( "
                "    SELECT symbol, MAX(fecha_hora) AS max_fh "
                "    FROM market_sentiment "
                "    GROUP BY symbol "
                ") latest ON ms.symbol = latest.symbol AND ms.fecha_hora = latest.max_fh "
                "WHERE EXISTS ( "
                "    SELECT 1 FROM market m "
                "    WHERE m.symbol = ms.symbol AND m.account = %s AND m.encartera = 'Y' "
                ")",
                (account,),
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_latest_sentiment]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def sentiment_already_run_today(self, account: str) -> bool:
        """True si ya existe al menos una lectura de hoy para símbolos de cartera."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM market_sentiment ms "
                "WHERE DATE(ms.fecha_hora) = CURDATE() "
                "AND EXISTS ( "
                "    SELECT 1 FROM market m "
                "    WHERE m.symbol = ms.symbol AND m.account = %s AND m.encartera = 'Y' "
                ")",
                (account,),
            )
            return (cursor.fetchone()[0] or 0) > 0
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::sentiment_already_run_today]: {error}")
            return False
        finally:
            cursor.close()
            conn.close()

    def load_sentiment_history(self, symbol: str, days: int = 7) -> list:
        """Retorna lecturas de sentimiento de los últimos N días para un símbolo.
        Resultado: lista de dicts {fecha_hora, sentimiento, headlines_count, fuente}."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT fecha_hora, sentimiento, headlines_count, fuente "
                "FROM market_sentiment "
                "WHERE symbol = %s AND fecha_hora >= DATE_SUB(NOW(), INTERVAL %s DAY) "
                "ORDER BY fecha_hora ASC",
                (symbol, days),
            )
            cols = ["fecha_hora", "sentimiento", "headlines_count", "fuente"]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_sentiment_history]: {error}")
            return []
        finally:
            cursor.close()
            conn.close()

    def save_sentiment_analysis(self, symbol: str, fecha, interpretacion: str, patron: str) -> None:
        """Upsert de interpretación diaria de sentimiento para un símbolo."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO market_sentiment_analysis (symbol, fecha, interpretacion, patron) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE interpretacion = VALUES(interpretacion), patron = VALUES(patron)",
                (symbol, fecha, interpretacion, patron),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::save_sentiment_analysis]: {error}")
        finally:
            cursor.close()
            conn.close()

    def load_sentiment_analysis(self, account: str) -> dict:
        """Retorna {symbol: {interpretacion, patron}} con el análisis de hoy para cartera."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT sa.symbol, sa.interpretacion, sa.patron "
                "FROM market_sentiment_analysis sa "
                "WHERE sa.fecha = CURDATE() "
                "AND EXISTS ( "
                "    SELECT 1 FROM market m "
                "    WHERE m.symbol = sa.symbol AND m.account = %s AND m.encartera = 'Y' "
                ")",
                (account,),
            )
            return {row[0]: {"interpretacion": row[1], "patron": row[2]} for row in cursor.fetchall()}
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_sentiment_analysis]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def load_sentiment_features(self, account: str) -> dict:
        """Retorna {symbol: {sentiment_score, sentiment_3d_avg, sentiment_7d_avg, sentiment_patron}}
        para todos los símbolos en cartera. Ventana máxima: 7 días. Fallback 0 cuando sin datos."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT ms.symbol, "
                "    MAX(CASE WHEN ms.fecha_hora = latest.max_fh THEN ms.sentimiento END) AS sentiment_score, "
                "    AVG(CASE WHEN ms.fecha_hora >= DATE_SUB(NOW(), INTERVAL 3 DAY) THEN ms.sentimiento END) AS sentiment_3d_avg, "
                "    AVG(ms.sentimiento) AS sentiment_7d_avg, "
                "    MAX(msa.patron) AS sentiment_patron "
                "FROM market_sentiment ms "
                "INNER JOIN ( "
                "    SELECT symbol, MAX(fecha_hora) AS max_fh "
                "    FROM market_sentiment "
                "    WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "    GROUP BY symbol "
                ") latest ON ms.symbol = latest.symbol "
                "LEFT JOIN market_sentiment_analysis msa ON msa.symbol = ms.symbol AND msa.fecha = CURDATE() "
                "WHERE ms.fecha_hora >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "AND EXISTS ( "
                "    SELECT 1 FROM market m "
                "    WHERE m.symbol = ms.symbol AND m.account = %s AND m.encartera = 'Y' "
                ") "
                "GROUP BY ms.symbol",
                (account,),
            )
            _PATRON_MAP = {"acumulacion": 1.0, "inflexion": 0.5, "neutro": 0.0, "distribucion": -1.0}
            result = {}
            for row in cursor.fetchall():
                sym, score, avg3, avg7, patron = row
                result[sym] = {
                    "sentiment_score": float(score) if score is not None else 0.0,
                    "sentiment_3d_avg": round(float(avg3), 4) if avg3 is not None else 0.0,
                    "sentiment_7d_avg": round(float(avg7), 4) if avg7 is not None else 0.0,
                    "sentiment_patron": _PATRON_MAP.get(patron, 0.0) if patron else 0.0,
                }
            return result
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_sentiment_features]: {error}")
            return {}
        finally:
            cursor.close()
            conn.close()

    def cleanup_sentiment(self, months: int = 6) -> int:
        """Elimina lecturas de market_sentiment y analysis más antiguas de N meses."""
        conn = self._conectar(tabla="update.market")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM market_sentiment WHERE fecha_hora < DATE_SUB(NOW(), INTERVAL %s MONTH)",
                (months,),
            )
            deleted = cursor.rowcount
            cursor.execute(
                "DELETE FROM market_sentiment_analysis WHERE fecha < DATE_SUB(CURDATE(), INTERVAL %s MONTH)",
                (months,),
            )
            deleted += cursor.rowcount
            conn.commit()
            return deleted
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::cleanup_sentiment]: {error}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def load_youtube_canales_all(self) -> list:
        """Retorna todos los canales (activos e inactivos) como lista de dicts para la UI de mantenimiento."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, canal, channel_id, url, active, score, detecciones, validados, last_scan "
                "FROM youtube_canales ORDER BY score DESC, canal ASC"
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_youtube_canales_all]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def insert_youtube_canal(self, canal: str, channel_id: str, url: str, active: int, score: int) -> bool:
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO youtube_canales (canal, channel_id, url, active, score) VALUES (%s, %s, %s, %s, %s)",
                (canal, channel_id, url or None, active, score),
            )
            conn.commit()
            return True
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::insert_youtube_canal]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def update_youtube_canal(
        self, canal_id: int, canal: str, channel_id: str, url: str, active: int, score: int
    ) -> bool:
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE youtube_canales SET canal=%s, channel_id=%s, url=%s, active=%s, score=%s WHERE id=%s",
                (canal, channel_id, url or None, active, score, canal_id),
            )
            conn.commit()
            return True
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_youtube_canal]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def delete_youtube_canal(self, canal_id: int) -> bool:
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM youtube_canales WHERE id=%s", (canal_id,))
            conn.commit()
            return True
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::delete_youtube_canal]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def load_youtube_canales(self) -> dict:
        """Retorna {canal: {channel_id, score}} de canales activos, ordenados por score desc."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT canal, channel_id, score FROM youtube_canales WHERE active = 1 ORDER BY score DESC")
            return {row[0]: {"channel_id": row[1], "score": row[2]} for row in cursor.fetchall()}
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_youtube_canales]: {error}")
            return {}
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def update_youtube_canal_stats(self, channel_id: str, detecciones: int, validados: int) -> None:
        """Actualiza contadores acumulados y last_scan de un canal."""
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE youtube_canales SET "
                "detecciones = detecciones + %s, "
                "validados = validados + %s, "
                "last_scan = NOW() "
                "WHERE channel_id = %s",
                (detecciones, validados, channel_id),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_youtube_canal_stats]: {error}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def upsert_youtube_candidato(
        self, symbol: str, confidence: float, market_cap: int, canal: str, company_name: str = "", website: str = ""
    ) -> None:
        """INSERT nuevo candidato o incrementa apariciones si ya existe (solo si sigue en pending)."""
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT apariciones, canales FROM youtube_candidatos WHERE symbol = %s", (symbol,))
            row = cursor.fetchone()
            hoy = datetime.now().date()
            if row:
                apariciones = row[0] + 1
                canales_set = set((row[1] or "").split(","))
                canales_set.add(canal)
                canales_str = ",".join(sorted(canales_set))
                cursor.execute(
                    "UPDATE youtube_candidatos SET apariciones=%s, confidence=GREATEST(confidence,%s), "
                    "market_cap=%s, canales=%s, ultima_vez=%s, "
                    "company_name=COALESCE(company_name, %s), "
                    "website=COALESCE(website, NULLIF(%s,'')) WHERE symbol=%s AND status='pending'",
                    (
                        apariciones,
                        confidence,
                        market_cap,
                        canales_str,
                        hoy,
                        company_name or None,
                        website or None,
                        symbol,
                    ),
                )
            else:
                cursor.execute(
                    "INSERT INTO youtube_candidatos (symbol, company_name, apariciones, confidence, market_cap, canales, website, primera_vez, ultima_vez) "
                    "VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s)",
                    (symbol, company_name or None, confidence, market_cap, canal, website or None, hoy, hoy),
                )
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::upsert_youtube_candidato]: {error}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def load_youtube_candidatos(self, status: str = "pending") -> list:
        """Retorna candidatos con estado en market: en_market, en_cartera."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT c.symbol, COALESCE(c.company_name, m.shortName) AS company_name, "
                "c.apariciones, c.confidence, c.market_cap, c.canales, "
                "c.primera_vez, c.ultima_vez, c.status, "
                "CASE WHEN m.symbol IS NOT NULL THEN 1 ELSE 0 END AS en_market, "
                "COALESCE(m.encartera, 'N') AS en_cartera, "
                "COALESCE(c.sector, m.sector) AS sector, "
                "COALESCE(m.lastPrice, c.last_price) AS lastPrice, "
                "COALESCE(m.website, c.website) AS website, "
                "COALESCE(m.country, c.country) AS country "
                "FROM youtube_candidatos c "
                "LEFT JOIN market m ON m.symbol = c.symbol "
                "WHERE c.status = %s "
                "ORDER BY c.apariciones DESC, c.confidence DESC",
                (status,),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_youtube_candidatos]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def set_youtube_candidato_status(self, symbol: str, status: str) -> None:
        """Cambia status de un candidato: pending / approved / rejected."""
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE youtube_candidatos SET status=%s WHERE symbol=%s", (status, symbol))
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::set_youtube_candidato_status]: {error}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def load_youtube_candidatos_incomplete(self, limit: int = 5) -> list:
        """Retorna símbolos pending con campos incompletos (website/sector/market_cap nulos)."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT symbol FROM youtube_candidatos "
                "WHERE status = 'pending' "
                "AND (website IS NULL OR sector IS NULL OR market_cap IS NULL OR market_cap = 0 "
                "     OR country IS NULL OR last_price IS NULL OR last_price = 0) "
                "ORDER BY apariciones DESC LIMIT %s",
                (limit,),
            )
            return [row[0] for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_youtube_candidatos_incomplete]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def update_youtube_candidato_fields(
        self,
        symbol: str,
        website: str = None,
        sector: str = None,
        market_cap: int = None,
        company_name: str = None,
        country: str = None,
        last_price: float = None,
    ) -> None:
        """Actualiza solo los campos proporcionados (no pisa valores existentes)."""
        parts = []
        params = []
        if website is not None:
            parts.append("website = COALESCE(website, NULLIF(%s, ''))")
            params.append(website)
        if sector is not None:
            parts.append("sector = COALESCE(sector, NULLIF(%s, ''))")
            params.append(sector)
        if market_cap is not None and market_cap > 0:
            parts.append("market_cap = COALESCE(NULLIF(market_cap, 0), %s)")
            params.append(market_cap)
        if company_name is not None:
            parts.append("company_name = COALESCE(company_name, NULLIF(%s, ''))")
            params.append(company_name)
        if country is not None:
            parts.append("country = COALESCE(country, NULLIF(%s, ''))")
            params.append(country)
        if last_price is not None and last_price > 0:
            parts.append("last_price = COALESCE(NULLIF(last_price, 0), %s)")
            params.append(last_price)
        if not parts:
            return
        params.append(symbol)
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE youtube_candidatos SET {', '.join(parts)} WHERE symbol = %s", params)
            conn.commit()
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_youtube_candidato_fields]: {error}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def cleanup_youtube_candidatos(self) -> int:
        """Rechaza candidatos pendientes que no reaparecer en el tiempo esperado."""
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE youtube_candidatos SET status = 'rejected' "
                "WHERE status = 'pending' AND ("
                "  (apariciones = 1 AND ultima_vez < CURDATE() - INTERVAL 15 DAY) "
                "  OR "
                "  (apariciones < 3 AND ultima_vez < CURDATE() - INTERVAL 30 DAY) "
                ")"
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::cleanup_youtube_candidatos]: {error}")
            return 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def load_youtube_candidatos_symbols(self) -> list:
        """Retorna todos los símbolos de youtube_candidatos con status='pending'."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM youtube_candidatos WHERE status = 'pending'")
            return [row[0] for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_youtube_candidatos_symbols]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def update_prices_batch(self, rows: list) -> int:
        """Actualiza lastPrice y volume en market. rows = [(symbol, account, price, volume), ...]"""
        if not rows:
            return 0
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            now = datetime.now()
            data = [(price, vol if vol else None, now, sym, acc) for sym, acc, price, vol in rows]
            cursor.executemany(
                "UPDATE market SET lastPrice=%s, volume=%s, timestamp=%s " "WHERE symbol=%s AND account=%s",
                data,
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_prices_batch]: {error}")
            return 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def update_youtube_prices(self, prices: dict) -> int:
        """Actualiza last_price en youtube_candidatos. prices = {symbol: price}"""
        if not prices:
            return 0
        conn = self._conectar(tabla="update.market")
        cursor = None
        try:
            cursor = conn.cursor()
            data = [(price, sym) for sym, price in prices.items() if price and price > 0]
            cursor.executemany(
                "UPDATE youtube_candidatos SET last_price=%s WHERE symbol=%s",
                data,
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::update_youtube_prices]: {error}")
            return 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def select_preservation_context(self, symbol: str, account: str) -> dict:
        """Contexto fundamental para evaluación Claude en preservation.
        Junta market (consenso + inst) + market_sentiment_analysis (patron).
        Indicadores técnicos en tiempo real los agrega _build_preservation_context desde DataHub.
        Retorna dict con todos los campos; ausentes quedan como None."""
        conn = self._conectar(tabla="select.market")
        cursor = None
        ctx = {}
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT consenso_tag, consenso_suma, inst_score, inst_ownership_pct, "
                "fh_buy_ratio, analyst_rec, analyst_mean "
                "FROM market WHERE symbol = %s AND account = %s LIMIT 1",
                (symbol, account),
            )
            row = cursor.fetchone()
            if row:
                keys = (
                    "consenso_tag",
                    "consenso_suma",
                    "inst_score",
                    "inst_ownership_pct",
                    "fh_buy_ratio",
                    "analyst_rec",
                    "analyst_mean",
                )
                ctx.update(dict(zip(keys, row)))

            cursor.execute(
                "SELECT patron FROM market_sentiment_analysis msa "
                "WHERE msa.symbol = %s ORDER BY msa.fecha DESC LIMIT 1",
                (symbol,),
            )
            row = cursor.fetchone()
            if row:
                ctx["patron"] = row[0]

        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::select_preservation_context({symbol})]: {error}")
        finally:
            if cursor:
                cursor.close()
            conn.close()
        return ctx

    def select_feed_context(self, symbol: str, account: str) -> dict:
        """Contexto de mercado para la plantilla de decisiones IA. Retorna dict con campos; ausentes como None."""
        conn = self._conectar(tabla="select.market")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT lastPrice, shortName, sector, country, inst_score, inst_ownership_pct, "
                "fh_count, consenso_tag, consenso_suma "
                "FROM market WHERE symbol = %s AND account = %s LIMIT 1",
                (symbol, account),
            )
            row = cursor.fetchone()
            if not row:
                return {}
            keys = (
                "lastPrice",
                "shortName",
                "sector",
                "country",
                "inst_score",
                "inst_ownership_pct",
                "fh_count",
                "consenso_tag",
                "consenso_suma",
            )
            return dict(zip(keys, row))
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::select_feed_context({symbol})]: {error}")
            return {}
        finally:
            conn.close()

    def select_last_position(self, symbol: str, account: str) -> dict:
        """Retorna {'stock': qty, 'basico': costo_promedio} desde booktrading. Dict vacío si no hay posición."""
        conn = self._conectar(tabla="select.booktrading")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stock, basico FROM booktrading "
                "WHERE simbolo = %s AND cuenta = %s "
                "ORDER BY fechahora DESC LIMIT 1",
                (symbol, account),
            )
            row = cursor.fetchone()
            if not row:
                return {}
            return {"stock": float(row[0] or 0), "basico": float(row[1] or 0)}
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::select_last_position({symbol})]: {error}")
            return {}
        finally:
            conn.close()


class PlanInversion(BDsystem):  # ------------------------------------------------------------------------------------
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
                        campos["efectividad"] = (key["tinversion"] - key["vision"]) / key["vision"]
                        campos["trendimiento"] = (key["dividendo"] + key["ccapital"]) / key["tinversion"]

                    inversion = int(inversion / 2)
                    self.update_trazaplan_inversion(idcuenta=idcuenta, meta=key["meta"], values=campos)

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

    def update_variablesplan_item(self, id, ditem, observaciones=""):
        try:
            conn = self._conectar(tabla="update.variablesplan")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE variablesplan SET ditem=%s, observaciones=%s WHERE id=%s",
                (ditem[:50], observaciones[:50], id),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: update_variablesplan_item()]: {error}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def insert_variablesplan_item(self, idcuenta, tipo, ditem, observaciones=""):
        try:
            conn = self._conectar(tabla="insert.variablesplan")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO variablesplan (idcuenta, tipo, codigo, ditem, valor, unidad, observaciones) "
                "VALUES (%s, %s, %s, %s, 0, '', %s)",
                (idcuenta, tipo, tipo[:3].upper(), ditem[:50], observaciones[:50]),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: insert_variablesplan_item()]: {error}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def delete_variablesplan_item(self, id):
        try:
            conn = self._conectar(tabla="delete.variablesplan")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM variablesplan WHERE id=%s", (id,))
            conn.commit()
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: delete_variablesplan_item()]: {error}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def update_plan_proyecto(self, id, proyecto):
        try:
            conn = self._conectar(tabla="update.plan")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE plan SET proyecto=%s WHERE id=%s",
                (proyecto[:200], id),
            )
            conn.commit()
        except (Exception, connect.Error) as error:
            print(f"[Mysql:: update_plan_proyecto()]: {error}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

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
                qry = """SELECT * FROM bdinv.extractos WHERE idcuenta='%s' AND extracto = '%s';"""
                cursor.execute(qry % (account, extract))
                sql = cursor.fetchone()

            if sql:
                columnas = [columna[0] for columna in cursor.description]
                if extract in ("last", "sum", "fiscal"):
                    xlis.append(dict(zip(columnas, sql)))

                elif extract in ("select*", "sum*"):
                    for fila in sql:
                        x = dict(zip(columnas, fila))
                        xlis.append(x)
                else:
                    xlis.append(dict(zip(columnas, sql)))

            return xlis
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: select_extracto()]: {e} {traceback.print_exc()}")

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
            qry += ") VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
            cursor.execute(qry, valuesins)

            conn.commit()
            cursor.close()

        try:
            conn = self._conectar(tabla="select.extracto")
            cursor = conn.cursor()
            acierre, listvalues = 0.0, []

            if is_none(account) or not bool(values):
                return

            # Eliminar registros existentes del mismo (idcuenta, mes/año) — permite re-cierre
            extracto_mes = values["extracto"].strftime("%Y-%m")
            cursor.execute(
                "DELETE FROM extractos WHERE idcuenta=%s AND DATE_FORMAT(extracto, '%%Y-%%m') = %s",
                (account, extracto_mes),
            )
            conn.commit()

            # Obtener el último registro restante (mes anterior real)
            uextract = self.select_extracto(account=account, extract="last")
            if uextract:
                acierre = uextract[0]["navcierre"]
                # Validar que el mes sea consecutivo al anterior
                if not valida_meses_consecutivos(inicio=uextract[0]["extracto"], fin=values["extracto"]):
                    return

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
                                                country = '%s', timestamp = '%s',
                                                estrategia = CASE WHEN estrategia IN ('A01','A02','A03','A04','A05','A99','C01','C02') OR estrategia IS NULL THEN '%s' ELSE estrategia END
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
                Debaja = keys["position"] <= 0 or (1 - keys["retorno"]) < 0.001
                xlistvalues.append("N" if Debaja else "Y")
                if Debaja:
                    cursor.execute(
                        "UPDATE market SET encartera = 'N' WHERE symbol = %s AND account = %s",
                        (ticket, account),
                    )
                xlistvalues.append(keys["empresa"])
                xlistvalues.append(keys["region"] if "region" in keys else "")
                xlistvalues.append(keys["country"] if "country" in keys else "")
                xlistvalues.append(datetime.now())
                xlistvalues.append(keys["estrategia"] if "estrategia" in keys else "")

                xlistvalues.append(ticket)
                xlistvalues.append(account)
                valuesupd = tuple(xlistvalues)
                cursor.execute(qry % valuesupd)
            except Exception as e:
                print("[update_inversion.update({})]: {} - {}={}".format(vehiculo, e, qry, valuesupd))

        def insert(keys, ticket):
            try:
                found = self.select_inversion(tipoin=vehiculo, ticket=ticket)
                if not found:
                    qry = """INSERT INTO inversion (ticket, iactiva, fealta, febaja, estrategia, empresa, costobase, conid, 
                                                            mrkprice, position, sector, exDividendDate, factor_cambio,
                                                            divisa, tipoinv, useraccount, region, country"""
                    fectime = datetime.now()
                    exdiv = keys["exDividendDate"] if "exDividendDate" in keys else "9999-12-31"
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
                    qry += ", timestamp) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
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
            cartera = self.select_inversion(account=account, tipoin=vehiculo, ticket="update")

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

            # posiciones viejas que ya no están en la nueva cartera — dar de baja
            while eof_old is not None:
                if old_position["iactiva"] == "Y":
                    baja(old_position["ticket"])
                eof_old, old_position = next(old, (None, None))

            conn.commit()
            cursor.close()
            conn.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_inversion({})]: {}".format(vehiculo, error))

    def get_totales_inversiones(self, vehiculo=None):
        """
        Obtiene los totales consolidados de todas las inversiones activas.
        @return: dict con total_costo_base, total_mercado, total_ganancia_dia, total_unrealized_pnl
        """
        try:
            conn = self._conectar(tabla="select.inversion")
            cursor = conn.cursor()

            qry = """SELECT
                        SUM(costobase) as total_costo_base,
                        SUM(mrkprice * position) as total_mercado,
                        SUM(dgyp) as total_ganancia_dia,
                        SUM(unrealizedpnl) as total_unrealized_pnl
                     FROM inversion
                     WHERE iactiva = 'Y'"""

            if vehiculo is None:
                qry += ";"
                cursor.execute(qry)
                result = cursor.fetchone()

            elif vehiculo is not None:
                qury += " AND tipoinv = %s;"
                cursor.execute(qry, vehiculo)
                result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                return {
                    "total_costo_base": result[0] or 0.0,
                    "total_mercado": result[1] or 0.0,
                    "total_ganancia_dia": result[2] or 0.0,
                    "total_unrealized_pnl": result[3] or 0.0,
                }
            else:
                return {
                    "total_costo_base": 0.0,
                    "total_mercado": 0.0,
                    "total_ganancia_dia": 0.0,
                    "total_unrealized_pnl": 0.0,
                }

        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: get_totales_inversiones()]: {}".format(error))
            return {
                "total_costo_base": 0.0,
                "total_mercado": 0.0,
                "total_ganancia_dia": 0.0,
                "total_unrealized_pnl": 0.0,
            }

    def get_totales_otros_activos(self, vehiculo=None):
        """
        Obtiene los totales consolidados de todas las inversiones activas asociada al vehiculo y otros activos.
        @return: dict con total_costo_base, total_mercado, total_ganancia_dia, total_unrealized_pnl
        """
        try:
            conn = self._conectar(tabla="select.inversion")
            cursor = conn.cursor()

            qry = """SELECT
                        O.symbol as symbol,
                        I.conid,
                        O.descripcion as asset,
                        I.position as posicion,
                        I.costobase as total_costo_base,
                        (I.mrkprice * I.position) as total_mercado,
                        (I.dgyp) as total_ganancia_dia,
                        (I.unrealizedpnl) as total_unrealized_pnl,
                        I.divisa as divisa,
                        I.factor_cambio as tasa
                     FROM inversion I, otros_activos O
                     WHERE I.iactiva = 'Y'
                     AND   I.ticket = O.symbol"""

            if vehiculo is None:
                qry += ";"

                cursor.execute(qry)
                result = cursor.fetchone()

            elif vehiculo is not None:
                qry += " AND I.tipoinv = %s;"
                cursor.execute(qry, (vehiculo,))
                result = cursor.fetchall()

            cursor.close()
            conn.close()

            if result:
                ix = [columna[0] for columna in cursor.description]
                lista = []
                for keys in result:
                    lista.append(dict(zip(ix, keys)))

                return lista
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: get_totales_otros_activos()]: {}".format(error))
            return []

    def select_otros_activos(
        self,
        symbol=None,
        idSymbol=None,
        account=None,
        descripcion=None,
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

            elif descripcion is not None:
                qry = "SELECT * FROM otros_activos WHERE descripcion LIKE %s LIMIT 1;"
                cursor.execute(qry, (f"%{descripcion}%",))
                sql = cursor.fetchone()

            else:
                qry = "SELECT * FROM otros_activos WHERE symbol = %s;"
                cursor.execute(qry, symbol)
                sql = cursor.fetchone()

            if sql:
                found = True
                ix = [columna[0] for columna in cursor.description]

                if idSymbol is not None or descripcion is not None:
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

    def update_otros_activos(self, account=None, values=None, symbol=None):
        """
        @param values:
        @param symbol:
        @return: actualiza taraba otros_activos."""
        try:
            conn = self._conectar(tabla="update.crypto")
            cursor = conn.cursor()
            valuesins = []
            qry = "UPDATE otros_activos SET "

            found = self.select_otros_activos(account=account, symbol=symbol)
            if found:

                for keys, vals in values.items():

                    qry = qry + keys + "='%s', "
                    valuesins.append(vals)

                valuesins.append(account)
                valuesins.append(symbol)
                qry += "WHERE cuenta='%s' AND symbol='%s';"
                qry = qry.replace(", WHERE", " WHERE")

                valuesupd = tuple(valuesins)
                cursor.execute(qry % valuesupd)
            conn.commit()
            cursor.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: update_otros_activos()]: {}".format(error))

    def update_otros_activos_indicadores(self, symbol, cuenta, data):
        """Actualiza campo indicadores (JSON) en otros_activos."""
        try:
            conn = self._conectar(tabla="update.crypto")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE otros_activos SET indicadores = %s WHERE symbol = %s AND cuenta = %s",
                (json.dumps(data, default=str), symbol, cuenta),
            )
            conn.commit()
            cursor.close()
        except Exception as e:
            self.logger.error(f"update_otros_activos_indicadores({symbol}): {e}")

    def delete_otros_activos(self, symbol=None, cuenta=None):
        """
        Elimina un registro de la tabla otros_activos.
        @param symbol: símbolo a eliminar
        @param cuenta: cuenta específica (opcional)
        @return: True si se eliminó correctamente
        """
        try:
            conn = self._conectar(tabla="delete.otros_activos")
            cursor = conn.cursor()

            if cuenta:
                qry = "DELETE FROM otros_activos WHERE symbol = %s AND cuenta = %s;"
                cursor.execute(qry, (symbol, cuenta))
            else:
                qry = "DELETE FROM otros_activos WHERE symbol = %s;"
                cursor.execute(qry, (symbol,))

            conn.commit()
            deleted = cursor.rowcount > 0
            cursor.close()
            conn.close()
            return deleted
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: delete_otros_activos()]: {}".format(error))
            return False

    # get info from en formato yfinance into otros_activos
    def get_yf_CNV(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None):
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

    def insert_otros_activos(
        self,
        symbol=None,
        values=None,
        cuenta="B0000001",
        avgcost_override=0,
        base_asset=None,
        idcrypto_override=None,
        descripcion=None,
    ):
        """
        @param symbol: ticket (crypto) o nombre del fondo (FCI)
        @param cuenta: cuenta destino
        @param avgcost_override: si >0 usa este valor directo y saltea yfinance (FCI/ARS)
        @param base_asset: asset base override (ej: 'ARS' para fondos FCI)
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
            row, found = self.select_otros_activos(account=cuenta, symbol=symbol)

            # Si existe pero en otra cuenta, permitir insertar para esta cuenta
            if found and row and row[0].get("cuenta") != cuenta:
                found = False

            if not found:

                if avgcost_override > 0:
                    name = descripcion if descripcion else symbol
                    avg = avgcost_override
                    h52w = 0
                else:
                    ticket = yf.Ticker(symbol.replace("USDT", "-USD"))
                    name = ticket.info["name"] if "name" in ticket.info else " "
                    avg = ticket.info["previousClose"] if "previousClose" in ticket.info else 0
                    h52w = ticket.info["fiftyTwoWeekHigh"] if "fiftyTwoWeekHigh" in ticket.info else 0

                qry = "INSERT INTO otros_activos ("

                if idcrypto_override is not None:
                    conid = idcrypto_override
                else:
                    conidHex = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
                    conid = int(conidHex[:15], 16)

                values.update({"cuenta": cuenta})
                values.update({"idcrypto": conid})
                values.update({"descripcion": name})
                values.update({"base_asset": base_asset if base_asset else symbol.replace("USDT", "")})
                values.update({"quote_asset": "ARS" if avgcost_override > 0 else "USDT"})
                values.update({"avgcost": avg})
                values.update({"objetivo": h52w})
                values.update({"fecupdate": datetime.now()})

                for keys, vals in values.items():
                    qry = qry + keys + ", "
                    valuesins.append(vals)

                valuesins.append(symbol)
                qry += "symbol) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
                cursor.execute(qry, tuple(valuesins))
                values.update({"symbol": symbol})
                xlis.append(values)
                found = True

            else:
                xlis = row
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
                qry += "ticket) VALUES ({});".format(",".join("'%s'" for _ in range(len(valuesins))))
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

    def monitor_residual_positions(self) -> list:
        UMBRAL_STOCK = 0.01
        UMBRAL_VALOR_FCI = 5.0

        conn = self._conectar(tabla="monitor_residual_positions")
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT i.ticket, i.useraccount, i.tipoinv,
                       COALESCE(i.position, 0)          AS position,
                       COALESCE(i.mrkprice * i.position, 0) AS mktvalue,
                       COALESCE(b.book_stock, 0)        AS book_stock
                FROM inversion i
                LEFT JOIN (
                    SELECT b1.simbolo, b1.cuenta, b1.stock AS book_stock
                    FROM booktrading b1
                    INNER JOIN (
                        SELECT simbolo, cuenta, MAX(fechahora) AS max_fh
                        FROM booktrading WHERE delisted = 0
                        GROUP BY simbolo, cuenta
                    ) b2 ON b1.simbolo = b2.simbolo
                         AND b1.cuenta  = b2.cuenta
                         AND b1.fechahora = b2.max_fh
                ) b ON i.ticket = b.simbolo AND i.useraccount = b.cuenta
                WHERE i.iactiva = 'Y'
            """)
            rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        alertas = []
        for ticket, account, tipoin, position, mktvalue, book_stock in rows:
            book_stock = float(book_stock or 0)
            mktvalue = float(mktvalue or 0)
            es_fci = tipoin not in ("Stock", "Crypto", "BotCrypto")

            if abs(book_stock) < UMBRAL_STOCK:
                alertas.append(
                    {
                        "symbol": ticket,
                        "account": account,
                        "tipoin": tipoin,
                        "book_stock": book_stock,
                        "mktvalue": mktvalue,
                        "motivo": "book_stock≈0",
                    }
                )
            elif es_fci and 0 < mktvalue < UMBRAL_VALOR_FCI:
                alertas.append(
                    {
                        "symbol": ticket,
                        "account": account,
                        "tipoin": tipoin,
                        "book_stock": book_stock,
                        "mktvalue": mktvalue,
                        "motivo": f"residual_fci ${mktvalue:.2f}",
                    }
                )
        return alertas

    def close_residual_fci(self, account: str, symbol: str) -> bool:
        """Cierra una posición residual de FCI: activa='N' + stock=0 en booktrading, iactiva='N' en inversion."""
        conn = self._conectar(tabla="close_residual_fci")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE booktrading SET activa = 'N', stock = 0 "
                "WHERE cuenta = %s AND simbolo = %s AND divisa = 'ARS' AND delisted = 0",
                (account, symbol),
            )
            cursor.execute(
                "UPDATE inversion SET iactiva = 'N', position = 0, timestamp = %s "
                "WHERE useraccount = %s AND ticket = %s",
                (datetime.now(), account, symbol),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[Mysql:: close_residual_fci({symbol}, {account})]: {e}")
            return False
        finally:
            cursor.close()
            conn.close()


class RepositorioOportunidadesBuySell(PlanInversion):  # -------------------------------------------------------------
    """
    -- Class de oportunidades generadas, acciones y trading realziados."""

    def __init__(self):
        self.display = False
        self.logger = logging.getLogger("RepositorioOportunidades")

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
    def generar_hash_id(account, symbol, option, fecha=None, tipo=None, subtipo=None, recomendado=None):
        try:
            date = fecha if fecha is not None else datetime.now().strftime("%Y-%m-%d")
            hash_id = f"{account}_{symbol}_{option}_{date}_{tipo}_{subtipo}_{recomendado}"
            return hashlib.md5(hash_id.encode()).hexdigest()

        except (Exception, EncodingWarning, connect.Error) as e:
            print(f"evaluar_generar_hash_id(): {e}")

    # Verifica si ya existe una oportunidad con tolerancia en el ROI
    def ya_existe_con_tolerancia(self, symbol, option, fecha, nuevo_roi, tolerancia=0.10):
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
                    diferencia = abs(nuevo_roi - roi_existente) / max(abs(roi_existente), 1e-6)
                    return diferencia <= tolerancia
                return False
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: RepositorioOportunidadesBuySell.ya_existe_con_tolerancia(): {error}]")

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

    def detalle_OportunidadBuy(self, origen, row=None):
        import math

        def _sanitize(v):
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
            if isinstance(v, dict):
                return {k: _sanitize(val) for k, val in v.items()}
            if isinstance(v, list):
                return [_sanitize(i) for i in v]
            return v

        detalle = {
            "ganancia_precio": row.get("ganancia_precio", 0),
            "ganancia_inversion": row.get("ganancia_inversion", 0),
            "dividend_yield": row.get("dividend_yield", 0),
            "score": row.get("score", 0),
            "Confianza": row.get("confianza", 0),
            "monto_sugerido": row.get("monto_sugerido", 0),
            "cantidad_buy": row.get("cantidad_buy", 0),
            "last": row.get("last", 0),
            "avgcost": row.get("avgcost", 0),
            "cantidad_post": row.get("cantidad_post", 0),
            "avgcost_post": row.get("avgcost_post", 0),
            "retorno_post": row.get("retorno_post", 0),
            "objetivo": row.get("objetivo", 0),
            "ex_dividend_date": row.get("ex_dividend_date"),
            "pre_dividendos": row.get("pre_dividendos", 0),
            "post_dividendos": row.get("post_dividendos", 0),
            "pre_costobase": row.get("pre_costobase", 0),
            "post_costobase": row.get("post_costobase", 0),
            "recomendado": row.get("Recomendado"),
            "comentarios": row.get("Comentarios"),
            "indicadores": _sanitize(row.get("Datostecnicos") or {}),
            "otros": {"modelo": origen, "timestamp_local": str(datetime.now())},
        }
        return json.dumps(detalle)

    # Inserta una nueva oportunidad de compra
    def insertar_buy(self, row, tipo="buy", subtipo=None, origen=None):
        try:
            hash_id = self.generar_hash_id(
                row.get("account"),
                row.get("Symbol"),
                row.get("vehiculo"),
                row.get("Fecha"),
                tipo,
                subtipo,
                row.get("Recomendado"),
            )
            detalle = self.detalle_OportunidadBuy(origen, row)

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
                row.get("tipo", ""),
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
            print(f"[Mysql:: RepositorioOportunidadesBuySell.insertar_buy(): {error}]")
            return False

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
    def actualizar_oportunidad(self, hash_id=None, estado=None, origen=None, tipo=None, subtipo=None, row=None):
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
            print(f"[Mysql:: RepositorioOportunidadesBuySell.actualizar_oportunidad(): {error}]")

    # update de una oportunidad de compra existente
    def actualizar_oportunidad_buy(self, hash_id=None, estado=None, origen=None, tipo=None, subtipo=None, row=None):
        try:
            # caso de actualización con hash_id (actualiza oportunidad específica)
            if hash_id is not None:
                sql = """
                    UPDATE oportunidadesbuysell
                    SET json_detalle = %s, timestamp = NOW()
                    WHERE hash_id = %s AND estado = %s
                """
                detalle = self.detalle_OportunidadBuy(origen=origen, row=row)
                datos = (detalle, hash_id, estado)

            # caso de actualización sin hash_id (actualiza la última oportunidad pendiente)
            if hash_id is None:
                sql = """
                    UPDATE oportunidadesbuysell
                    SET json_detalle = %s, timestamp = NOW(), hash_id = %s, fecha = %s
                    WHERE account = %s AND symbol = %s AND vehiculo = %s AND tipo = 'buy' AND estado = 'pendiente'
                """
                account = row.get("account", "")
                symbol = row.get("Symbol", "")
                vehiculo = row.get("vehiculo", "")
                fecha = row.get("Fecha", "")

                # genera nuevo hash_id
                hash_id = self.generar_hash_id(
                    account,
                    symbol,
                    vehiculo,
                    fecha,
                    tipo,
                    subtipo,
                    row.get("Recomendado"),
                )

                detalle = self.detalle_OportunidadBuy(origen=origen, row=row)
                datos = (detalle, hash_id, fecha, account, symbol, vehiculo)

            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, datos)
                rows_afectadas = cursor.rowcount
                conn.commit()

                return True if rows_afectadas > 0 else False

        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: RepositorioOportunidadesBuySell.actualizar_oportunidad_buy(): {error}]")

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
            print(f"[Mysql:: RepositorioOportunidadesBuySell.marcar_oportunidad(): {error}]")

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
            print(f"[Mysql:: RepositorioOportunidadesBuySell.obtener_no_enviadas(): {error}]")

    def marcar_como_enviada(self, hash_id):
        try:
            sql = "UPDATE oportunidadesbuysell SET enviada = TRUE WHERE hash_id = %s"
            with self._conectar(tabla="accionoportunidades") as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (hash_id,))
                conn.commit()
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: RepositorioOportunidadesBuySell.marcar_como_enviada(): {error}]")

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
                                                    tarifacomision, idtrans, factor_cambio, preciocierre
                                            FROM booktrading WHERE cuenta = '%s' AND divisa = '%s'
                                                                AND simbolo = '%s' AND activa = 'Y'
                                                                AND delisted = 0) AS a
                            ORDER BY fechahora DESC, sec DESC;"""
                    cursor.execute(qry % (account, idivisa, symbol))
                    sql = cursor.fetchone()

                # ultima diaria registrada
                if symbol is None:
                    qry = """SELECT a.* FROM (SELECT sec, fechahora, stock, basico, gprealizadas, cantidad,
                                                    tarifacomision, idtrans FROM booktrading
                                            WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y'
                                            AND delisted = 0) AS a
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
                                            AND simbolo = '%s' AND activa = 'Y'
                                            AND delisted = 0) AS a
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
                                WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y'
                                AND delisted = 0) AS a;"""

                cursor.execute(qry % (account, idivisa))
                sql = cursor.fetchone()

            elif accion == "select*":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s'
                                                                    AND simbolo = '%s' AND activa = 'Y'
                                                                    AND delisted = 0) AS a
                                                                    ORDER BY preciotrans ASC, fechahora ASC, sec ASC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # para obtener tasa de cambio mas reciente
            elif accion == "tasa_cambio":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s'
                                                                    AND simbolo = '%s' AND activa = 'Y'
                                                                    AND delisted = 0) AS a
                                                                    ORDER BY fechahora DESC, sec DESC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            elif accion == "cuenta":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading WHERE cuenta = '%s'  AND divisa = '%s') AS a
                                        ORDER BY fechahora ASC, sec ASC;"""

                cursor.execute(qry % (account, idivisa))
                sql = cursor.fetchall()

            elif accion == "hoy":
                qry = """SELECT cuenta, simbolo, codigo, cantidad, basico, gprealizadas, fechahora
                         FROM booktrading
                         WHERE DATE(fechahora) = CURDATE()
                         ORDER BY cuenta, fechahora DESC;"""
                cursor.execute(qry)
                sql = cursor.fetchall()

            elif accion == "performa":
                qry = """SELECT a.* FROM (SELECT DATE(fechahora), basico, stock, gprealizadas, codigo, comisiones
                                        FROM booktrading  WHERE cuenta = '%s'  AND divisa = '%s' 
                                                            AND simbolo = '%s') AS a 
                        ORDER BY DATE(fechahora) ASC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # opción para reconstruir performa de la cartera — sin filtro divisa para incluir CAD, etc.
            elif accion == "cartera":
                qry = """SELECT * FROM booktrading
                        WHERE cuenta = '%s' AND codigo in ('C', 'O')
                        ORDER BY simbolo, fechahora ASC;"""

                cursor.execute(qry % (account,))
                sql = cursor.fetchall()

            # opción para obtener maxima ganancia en Trade de venta
            elif accion == "ganancias":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading
                                        WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y'
                                            AND codigo = 'O'  AND simbolo = '%s'
                                            AND delisted = 0) AS a
                        ORDER BY preciotrans ASC, fechahora DESC, sec DESC;"""

                cursor.execute(qry % (account, idivisa, symbol))
                sql = cursor.fetchall()

            # opción para obtener ganancia en BOTTrade de venta
            elif accion == "bottrader":
                qry = """SELECT a.* FROM (SELECT * FROM booktrading
                                        WHERE cuenta = '%s' AND divisa = '%s' AND activa = 'Y'
                                            AND codigo = 'O'  AND simbolo = '%s'
                                            AND delisted = 0) AS a
                        ORDER BY fechahora DESC, sec DESC;"""

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
                                        FROM bdinv.booktrading  WHERE cuenta = '{account}' and date(fechahora) <= '{f_hasta}'
                                        GROUP by cuenta, simbolo) as a
                        UNION
                        SELECT a.* from (SELECT cuenta, simbolo,  fechahora, sum(cantidad) cantidad
                                        FROM bdinv.booktrading  WHERE cuenta = '{account}' and date(fechahora) <= '{f_hasta}'
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
                            row[ix.index("cantidad")] <= 0 and row[ix.index("fechahora")].date() > desde.date()
                        ):

                            fecha_dia = row[ix.index("fechahora")].strftime("%Y-%m-%d")
                            if inicio_qry:
                                concatena = """ AND ((simbolo, DATE(fechahora)) = ('%s', '%s')""" % (
                                    row[ix.index("simbolo")],
                                    fecha_dia,
                                )
                                inicio_qry = False
                            else:
                                concatena = """ OR (simbolo, DATE(fechahora)) = ('%s', '%s')""" % (
                                    row[ix.index("simbolo")],
                                    fecha_dia,
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

    def insert_bottraderBook(self, values=None, symbol="SPX", object="bottrader"):
        """
        Inserta operación BotTrader en booktrading.
        Calcula basico (precio promedio), ganancias realizadas y stock acumulado.
        @param values: dict con datos de la operación (cuenta, divisa, cantidad, preciotrans, etc.)
        @param symbol: símbolo del activo
        @param object: tipo de consulta para select_booktrading ('bottrader')
        """

        def _last_secbottrader():
            """Obtiene cantidad registros para el vehiculo"""
            qry = """SELECT count(*) as sec FROM booktrading
                        WHERE cuenta = %s AND divisa = %s AND simbolo = %s;"""
            cursor.execute(qry, (account, idivisa, symbol))
            sql = cursor.fetchone()
            return sql[0]

        def _last_bottrader():
            """Obtiene último registro activo de compra para calcular basico"""
            qry = """SELECT a.* FROM (
                        SELECT sec, fechahora, stock, basico, gprealizadas, cantidad,
                               tarifacomision, idtrans, factor_cambio
                        FROM booktrading
                        WHERE cuenta = %s AND divisa = %s AND simbolo = %s AND activa = 'Y'
                     ) AS a ORDER BY fechahora DESC, sec DESC;"""
            cursor.execute(qry, (account, idivisa, symbol))
            sql = cursor.fetchone()
            columnas = [col[0] for col in cursor.description]
            return [dict(zip(columnas, sql))] if sql else [], columnas

        def _update_indicador_activa(idcuenta, divisa, ticket, id_trans, activa, sell, update):
            """Actualiza indicador activa y sell en booktrading"""
            try:
                u_conn = self._conectar(tabla="update.booktrading")
                u_cursor = u_conn.cursor()
                upd = """UPDATE booktrading SET activa = %s, sell = %s, updateStamp = %s
                         WHERE cuenta = %s AND divisa = %s AND simbolo = %s AND idtrans = %s;"""
                u_cursor.execute(upd, (activa, sell, update, idcuenta, divisa, ticket, id_trans))
                u_conn.commit()
            except (Exception, connect.Error) as e:
                self.logger.error(f"_update_indicador_activa(): {e}")

        def _get_importe_sell(c_sell, update):
            """Calcula importe de lotes vendidos y marca como inactivos"""
            try:
                book, iy = self.select_booktrading(accion=object, account=account, idivisa=idivisa, symbol=symbol)
                ebook = enumerate(book)
                eof_book, read = next(ebook, (None, None))

                value, x_stock, ya_sell = 0.0, 0.0, 0.0
                while (eof_book is not None) and (x_stock + c_sell < 0):
                    a_sell = read[iy.index("sell")]
                    cant = read[iy.index("cantidad")] - a_sell
                    prec = read[iy.index("preciotrans")]

                    if (cant + ya_sell + c_sell) <= 0:
                        ya_sell += cant
                        activa = "N"
                        value += cant * prec
                    elif (cant + ya_sell + c_sell) > 0:
                        cant = abs(ya_sell + c_sell)
                        a_sell += cant
                        activa = "Y"
                        value += cant * prec

                    x_stock += cant
                    _update_indicador_activa(
                        read[iy.index("cuenta")],
                        read[iy.index("divisa")],
                        symbol,
                        read[iy.index("idtrans")],
                        activa,
                        a_sell,
                        update,
                    )

                    if x_stock + c_sell >= 0.0:
                        break
                    eof_book, read = next(ebook, (None, None))
                return value
            except (Exception, connect.Error) as e:
                self.logger.error(f"_get_importe_sell(): {e}")
                return 0.0

        def _update_codigo_sell(id_trader, update):
            """Marca como inactivas las ventas anteriores"""
            try:
                book, iy = self.select_booktrading(accion="select*", account=account, idivisa=idivisa, symbol=symbol)
                for _, read in enumerate(book):
                    if read[iy.index("codigo")] == "C" and read[iy.index("idtrans")] != id_trader:
                        _update_indicador_activa(
                            read[iy.index("cuenta")],
                            read[iy.index("divisa")],
                            symbol,
                            read[iy.index("idtrans")],
                            "N",
                            read[iy.index("cantidad")],
                            update,
                        )
            except (Exception, connect.Error) as e:
                self.logger.error(f"_update_codigo_sell(): {e}")

        try:
            conn = self._conectar(tabla="insert.booktrading")
            cursor = conn.cursor()

            account = values["cuenta"]
            idivisa = values["divisa"]
            idtrans = values["idtrans"]

            # Validar duplicado
            if self.get_hash_booktrading(accion="valida", values=values, symbol=symbol):
                return

            hashId = self.get_hash_booktrading(values=values, symbol=symbol)

            # Último registro para calcular basico y stock acumulado
            nw_producto, ustock, usec, costo_avg = 0.0, 0.0, 0.0, 0.0
            utrading, _ = _last_bottrader()
            if utrading:
                last = utrading[0]
                costo_avg = last["basico"]
                ustock = last["stock"]
                usec = _last_secbottrader()

            stock = ustock + values["cantidad"]
            position = 0.0

            # Compra (cantidad > 0)
            if values["cantidad"] > 0:
                basico = (values["producto"] + values["tarifacomision"]) / values["cantidad"]
                gpreal = 0.0
                codigo = "O"
                activa = "Y"
                mtmgp = 0.0

            # Venta (cantidad < 0)
            elif values["cantidad"] < 0:
                basico = costo_avg
                codigo = "C"
                activa = "Y"
                importe = _get_importe_sell(values["cantidad"], values["fechahora"])
                gpreal = values["producto"] - (importe + values["tarifacomision"])
                mtmgp = gpreal / abs(values["cantidad"])
                _update_codigo_sell(idtrans, values["fechahora"])
            else:
                return

            # Completar registro
            values.update(
                {
                    "split": 1,
                    "activa": activa,
                    "stock": stock,
                    "mtmgp": mtmgp,
                    "basico": basico,
                    "codigo": codigo,
                    "gprealizadas": gpreal,
                    "updateStamp": datetime.now(),
                    "hash_id": hashId,
                    "sec": int(usec) + 1,
                }
            )

            # Insert
            columns = list(values.keys()) + ["simbolo"]
            placeholders = ",".join(["%s"] * len(columns))
            qry = f"INSERT INTO booktrading ({','.join(columns)}) VALUES ({placeholders});"
            cursor.execute(qry, tuple(list(values.values()) + [symbol]))
            conn.commit()
            last_id = cursor.lastrowid
            cursor.close()

            # Recalcula stock real desde BD para corregir desfase cuando se insertan
            # múltiples transacciones del mismo símbolo en la misma fecha/hora
            fix_cur = conn.cursor()
            fix_cur.execute(
                """
                UPDATE booktrading b
                JOIN (
                    SELECT SUM(t.cantidad) AS stock_real
                    FROM booktrading t
                    WHERE t.cuenta = %s AND t.simbolo = %s
                      AND (t.fechahora < %s OR (t.fechahora = %s AND t.sec <= %s))
                ) calc ON 1=1
                SET b.stock = calc.stock_real
                WHERE b.id = %s
                """,
                (account, symbol, values["fechahora"], values["fechahora"], values["sec"], last_id),
            )
            conn.commit()
            fix_cur.close()

            # Actualizar costo promedio en otros_activos
            time.sleep(0.4)
            self.update_otros_activos(
                account=account,
                values={"avgcost": basico, "fecupdate": values["fechahora"]},
                symbol=symbol,
            )
        except (Exception, connect.Error) as error:
            self.logger.error(f"insert_bottraderBook({symbol}): {error}")
            traceback.print_exc()

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

                u_cursor.execute(upd % (activa, sell, update, idcuenta, divisa, ticket, id_trans))
                u_conn.commit()
            except (Exception, EncodingWarning, connect.Error) as e:
                print("[Mysql:: update_indicador_activa()]: {}".format(e))

        # aplica a las sell para obtener maxima's ganancias y marcas los códigos = 'O' como inactivo
        def maximiza_ganancias_corto_plazo(c_sell, update):
            try:
                book, iy = self.select_booktrading(accion="ganancias", account=account, idivisa=idivisa, symbol=symbol)
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
                book, iy = self.select_booktrading(accion="select*", account=account, idivisa=idivisa, symbol=symbol)
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
            if len(symbol) > 100:
                print(f"[Mysql:: insert_booktrading()]: símbolo demasiado largo ({len(symbol)} chars) → {symbol[:60]}…")
                return

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
            found_hash = self.get_hash_booktrading(accion="valida", values=values, symbol=symbol)
            if found_hash:
                return

            # procede con insert del trader
            hashId = self.get_hash_booktrading(values=values, symbol=symbol)

            # ubica último trader del symbol para obtener basico
            nw_producto, ubasico, ustock = 0.0, 0.0, 0.0
            usec, uid, position = 0.0, 0.0, 0.0
            costo_avg = 0.0

            utrading, ix = self.select_booktrading(accion="last", account=account, idivisa=idivisa, symbol=symbol)
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
                    inversion[0]["costobase"] * inversion[0]["factor_cambio"] / position if position > 0 else ubasico
                )

            stock = ustock + values["cantidad"]

            # Rechazar venta que generaría posición en corto para stocks/ETFs
            if stock < -0.001 and values["cantidad"] < 0 and values.get("categoria") in ("Stock", "ETF"):
                print(
                    f"[insert_booktrading] SHORT RECHAZADO — {symbol}: "
                    f"stock_actual={ustock:.4f}  venta={values['cantidad']:.4f}  "
                    f"resultado={stock:.4f}. No se permite vender más de lo que se tiene."
                )
                return

            # cuando es compra en largo
            if values["cantidad"] > 0:

                # obtener basico y recalcular el nuevo producto de utrading entre el nuevo stock
                # stock puede ser 0 (cierre de corto) o incluso positivo después de un corto — evitar /0
                if abs(stock) > 0.0001:
                    basico = (values["preciotrans"] * values["cantidad"] + values["tarifacomision"] + nw_producto) / stock
                else:
                    basico = 0.0
                gpreal = 0.0
                codigo = "O"
                mtmgp = 0.00
                values.update({"activa": "Y"})

            # cuando es venta en corto
            elif values["cantidad"] < 0:
                basico = costo_avg
                codigo = "C"

                # rutina para marcar como iactiva='N'
                importe = maximiza_ganancias_corto_plazo(values["cantidad"], values["fechahora"])

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

            values.update({"updateStamp": datetime.now()})
            values.update({"hash_id": hashId})
            values.update({"sec": int(usec) + 1})

            # prepara Query Insert
            qry = "INSERT INTO booktrading ("
            for keys, vals in values.items():
                qry += keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry += "simbolo) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
            cursor.execute(qry, tuple(valuesins))
            conn.commit()
            cursor.close()

            time.sleep(0.4)
            # update basico "otros_activos" e indicador "activa", cuando sea una venta (cantidad <0)
            cvalues = {}
            cvalues.update({"avgcost": basico})
            cvalues.update({"fecupdate": values["fechahora"]})
            self.update_otros_activos(account=account, values=cvalues, symbol=symbol)
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: insert_booktrading()]: {error}")

    def update_preciotrans_fci(self, account, idivisa, symbol, idtrans, preciotrans, cantidad, producto):
        """
        Actualiza precio y cuotapartes de una operación FCI ajustada retroactivamente por el banco.
        Importe ARS fijo → precio ajustado implica cantidad distinta.
        Recalcula stock acumulado del símbolo ya que cantidad cambia.
        """
        try:
            conn = self._conectar(tabla="update.booktrading")
            cursor = conn.cursor()

            cursor.execute(
                """UPDATE booktrading
                   SET preciotrans = %s, preciocierre = %s, cantidad = %s, producto = %s, updateStamp = %s
                   WHERE cuenta = %s AND divisa = %s AND simbolo = %s AND idtrans = %s;""",
                (preciotrans, preciotrans, cantidad, producto, datetime.now(), account, idivisa, symbol, idtrans),
            )
            conn.commit()

            # Recalcula stock corrido para todos los registros del símbolo
            cursor.execute(
                """UPDATE booktrading b
                   JOIN (
                       SELECT id,
                              SUM(cantidad) OVER (
                                  PARTITION BY cuenta, simbolo, divisa
                                  ORDER BY fechahora, sec
                              ) AS stock_real
                       FROM booktrading
                       WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                   ) calc ON b.id = calc.id
                   SET b.stock = calc.stock_real
                   WHERE b.cuenta = %s AND b.simbolo = %s AND b.divisa = %s;""",
                (account, symbol, idivisa, account, symbol, idivisa),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"[Mysql:: update_preciotrans_fci()]: {error}")

    def select_botcrypto_performance(self, account, dias=90):
        """
        Retorna rendimiento diario del BotCrypto desde booktrading (últimos N días).
        Solo registros de venta (codigo='C') que son los que tienen gprealizadas != 0.
        Returns: (rows, columnas)
        """
        try:
            conn = self._conectar(tabla="select.botcrypto.performance")
            cursor = conn.cursor()
            qry = """
                SELECT
                    DATE(fechahora)                                             AS fecha,
                    simbolo,
                    SUM(gprealizadas)                                           AS pnl_dia,
                    COUNT(*)                                                    AS trades,
                    SUM(CASE WHEN gprealizadas > 0 THEN 1 ELSE 0 END)          AS wins,
                    SUM(CASE WHEN gprealizadas <= 0 THEN 1 ELSE 0 END)         AS losses,
                    SUM(tarifacomision)                                         AS comisiones,
                    MAX(gprealizadas)                                           AS mejor_trade,
                    MIN(gprealizadas)                                           AS peor_trade
                FROM booktrading
                WHERE cuenta = %s
                  AND divisa = 'USD'
                  AND codigo = 'C'
                  AND DATE(fechahora) >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY DATE(fechahora), simbolo
                ORDER BY fecha ASC, simbolo ASC;
            """
            cursor.execute(qry, (account, dias))
            rows = cursor.fetchall()
            columnas = [col[0] for col in cursor.description]
            cursor.close()
            return rows or [], columnas
        except Exception as e:
            self.logger.error(f"select_botcrypto_performance({account}): {e}")
            return [], []

    def min_fec_booktrading(self, list_asset=None, account=None, idivisa=None):
        """
        @param list_asset: lista de símbolos
        @param account: idcuenta
        @param idivisa: divisa
        @return: de booktrading fecha minima para los símbolos de la cuenta."""
        try:
            inicio, ifecha = {}, datetime.now()
            for ticket in list_asset:
                utrading, ix = self.select_booktrading(accion="low", account=account, idivisa=idivisa, symbol=ticket)
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
            qry += "symbol) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
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

    def update_order_trader_by_client_id(
        self, client_order_id: str, account: str, status: str, stamp_submit=None
    ) -> bool:
        """Actualiza status (y opcionalmente stampSubmit) en order_trader usando clientOrderId."""
        conn = self._conectar(tabla="insert.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            if stamp_submit:
                cursor.execute(
                    "UPDATE order_trader SET status=%s, stampSubmit=%s WHERE clientOrderId=%s AND account=%s",
                    (status, stamp_submit, client_order_id, account),
                )
            else:
                cursor.execute(
                    "UPDATE order_trader SET status=%s WHERE clientOrderId=%s AND account=%s",
                    (status, client_order_id, account),
                )
            conn.commit()
            return cursor.rowcount > 0
        except (Exception, connect.Error) as error:
            print(f"[Mysql::update_order_trader_by_client_id]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

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

    def select_order_trader_today(self, account: str, vehiculo: str) -> tuple:
        """Retorna órdenes de hoy + cualquier orden activa de días anteriores (ej: STOPs de preservation)."""
        conn = self._conectar(tabla="select.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM order_trader "
                "WHERE account = %s AND vehiculo = %s "
                "AND (DATE(stampPlace) = CURDATE() "
                "     OR status IN ('New','NEW','Submitted','PreSubmitted','PendingSubmit','PARTIALLY_FILLED')) "
                "ORDER BY stampPlace DESC",
                (account, vehiculo),
            )
            rows = cursor.fetchall()
            ix = [col[0] for col in cursor.description]
            return rows, ix
        except (Exception, connect.Error) as error:
            print(f"[Mysql::select_order_trader_today]: {error}")
            return [], []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def select_pending_orders(self, account: str, vehiculo: str) -> tuple:
        """Retorna todas las órdenes pendientes (sin importar fecha) para account/vehiculo."""
        _PENDING = ("New", "NEW", "Submitted", "PreSubmitted", "PendingSubmit", "PARTIALLY_FILLED")
        conn = self._conectar(tabla="select.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            placeholders = ",".join(["%s"] * len(_PENDING))
            cursor.execute(
                f"SELECT * FROM order_trader WHERE account = %s AND vehiculo = %s "
                f"AND status IN ({placeholders}) ORDER BY stampPlace DESC",
                (account, vehiculo, *_PENDING),
            )
            rows = cursor.fetchall()
            ix = [col[0] for col in cursor.description]
            return rows, ix
        except (Exception, connect.Error) as error:
            print(f"[Mysql::select_pending_orders]: {error}")
            return [], []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def sync_orders_from_ib(self, ib_client, account: str) -> int:
        """Sincroniza order_trader con get_live_orders() de IB. Retorna registros actualizados."""
        _STATUS_MAP = {
            "Cancelled": "CANCELED",
            "Filled": "Filled",
            "Submitted": "Submitted",
            "PreSubmitted": "PreSubmitted",
            "Inactive": "Inactive",
            "New": "New",
        }
        try:
            orders = (ib_client.get_live_orders() or {}).get("orders", [])
        except Exception as e:
            _logger.error(f"[sync_orders_from_ib] get_live_orders: {e}")
            return 0
        updated = 0
        for o in orders:
            coid = str(o.get("orderId", ""))
            ib_status = o.get("status", "")
            if not coid or not ib_status:
                continue
            if self.update_order_trader_by_client_id(coid, account, _STATUS_MAP.get(ib_status, ib_status)):
                updated += 1
        if updated:
            _logger.warning(f"sync_orders_from_ib: {updated} actualizadas account={account}")
        return updated

    def sync_orders_from_binance(self, b_client, account: str) -> int:
        """Sincroniza order_trader (Crypto) comparando contra órdenes abiertas en Binance.
        Órdenes que ya no están abiertas → consulta estado real y actualiza BD."""
        _STATUS_MAP = {
            "FILLED": "Filled",
            "CANCELED": "CANCELED",
            "EXPIRED": "CANCELED",
            "NEW": "Submitted",
            "PARTIALLY_FILLED": "Submitted",
        }
        try:
            open_orders = b_client.Myget_open_orders() or []
            open_ids = {str(o.get("orderId", "")) for o in open_orders}
        except Exception as e:
            _logger.error(f"[sync_orders_from_binance] get_open_orders: {e}")
            return 0

        rows, ix = self.select_pending_orders(account, "Crypto")
        pending = [dict(zip(ix, r)) for r in rows]
        updated = 0
        for r in pending:
            binance_order_id = str(r.get("id_order") or "")
            coid = str(r.get("clientOrderId") or "")
            if not binance_order_id or binance_order_id in open_ids:
                continue
            try:
                detail = b_client.get_order_status(symbol=r["symbol"], order_id=int(binance_order_id))
                if not detail:
                    continue
                bn_status = _STATUS_MAP.get(detail.get("status", ""), detail.get("status", ""))
                if self.update_order_trader_by_client_id(coid, account, bn_status):
                    updated += 1
            except Exception as e:
                _logger.warning(f"[sync_orders_from_binance] {r.get('symbol')}: {e}")
        if updated:
            _logger.warning(f"sync_orders_from_binance: {updated} actualizadas account={account}")
        return updated

    def cleanup_order_trader_eod(self, account: str) -> int:
        """Elimina órdenes obsoletas por plazo fijo (sin validación API).
        - Hoy: CANCELED, Inactive.
        - >1d: PendingSubmit.
        - >2d: PreSubmitted, PARTIALLY_FILLED.
        - >7d: todo excepto Filled (last resort)."""
        conn = self._conectar(tabla="insert.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM order_trader WHERE account = %s AND DATE(stampPlace) = CURDATE() "
                "AND status IN ('CANCELED', 'Inactive')",
                (account,),
            )
            d1 = cursor.rowcount
            cursor.execute(
                "DELETE FROM order_trader WHERE account = %s AND DATE(stampPlace) < CURDATE() "
                "AND status IN ('PendingSubmit', 'CANCELED', 'Inactive')",
                (account,),
            )
            d2 = cursor.rowcount
            cursor.execute(
                "DELETE FROM order_trader WHERE account = %s "
                "AND DATE(stampPlace) <= DATE_SUB(CURDATE(), INTERVAL 2 DAY) "
                "AND status IN ('PreSubmitted', 'PARTIALLY_FILLED') "
                "AND orderType NOT LIKE 'STP%%'",
                (account,),
            )
            d3 = cursor.rowcount
            cursor.execute(
                "DELETE FROM order_trader WHERE account = %s "
                "AND DATE(stampPlace) <= DATE_SUB(CURDATE(), INTERVAL 7 DAY) "
                "AND status NOT IN ('Filled', 'FILLED') "
                "AND orderType NOT LIKE 'STP%%'",
                (account,),
            )
            d4 = cursor.rowcount
            conn.commit()
            return d1 + d2 + d3 + d4
        except (Exception, connect.Error) as error:
            print(f"[Mysql::cleanup_order_trader_eod]: {error}")
            return 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_stale_pending_orders(self, account: str, vehiculo: str, days_min: int = 2, days_max: int = 7) -> list:
        """Retorna órdenes NEW/Submitted entre days_min y days_max días, con id_order válido."""
        conn = self._conectar(tabla="select.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, symbol, status, id_order, clientOrderId "
                "FROM order_trader "
                "WHERE account = %s AND vehiculo = %s "
                "AND status IN ('NEW', 'New', 'Submitted') "
                "AND DATE(stampPlace) <= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
                "AND DATE(stampPlace) > DATE_SUB(CURDATE(), INTERVAL %s DAY) "
                "AND id_order IS NOT NULL AND id_order != '' "
                "AND orderType NOT LIKE 'STP%%'",
                (account, vehiculo, days_min, days_max),
            )
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as error:
            print(f"[Mysql::get_stale_pending_orders]: {error}")
            return []
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def delete_order_trader_by_id(self, record_id: int, account: str) -> bool:
        """Elimina un registro de order_trader por su id (PK)."""
        conn = self._conectar(tabla="insert.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM order_trader WHERE id = %s AND account = %s", (record_id, account))
            conn.commit()
            return cursor.rowcount > 0
        except (Exception, connect.Error) as error:
            print(f"[Mysql::delete_order_trader_by_id]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def validate_stale_crypto_orders(self, account: str, b_client, days_min: int = 2, days_max: int = 7) -> int:
        """Valida con Binance órdenes NEW/Submitted de days_min-days_max días.
        Actualiza status o elimina registros huérfanos según respuesta de la API."""
        _STATUS_MAP = {"FILLED": "Filled", "CANCELED": "CANCELED", "EXPIRED": "CANCELED"}
        candidates = self.get_stale_pending_orders(account, "Crypto", days_min, days_max)
        if not candidates:
            return 0
        try:
            open_ids = {str(o.get("orderId", "")) for o in (b_client.Myget_open_orders() or [])}
        except Exception as e:
            _logger.error(f"[validate_stale_crypto_orders] get_open_orders: {e}")
            return 0
        resolved = 0
        for row in candidates:
            order_id = str(row.get("id_order", ""))
            if order_id in open_ids:
                continue
            try:
                detail = b_client.get_order_status(symbol=row["symbol"], order_id=int(order_id))
                bn_raw = (detail or {}).get("status", "")
                new_status = _STATUS_MAP.get(bn_raw)
                if bn_raw == "NEW":
                    continue  # activa en Binance → no tocar
                if new_status:
                    coid = str(row.get("clientOrderId") or "")
                    if coid and self.update_order_trader_by_client_id(coid, account, new_status):
                        resolved += 1
                else:
                    if self.delete_order_trader_by_id(row["id"], account):
                        resolved += 1
            except Exception as e:
                err = str(e)
                if "-2011" in err or "Unknown order" in err:
                    if self.delete_order_trader_by_id(row["id"], account):
                        resolved += 1
                        _logger.warning(
                            f"[validate_stale_crypto_orders] {row['symbol']} id={order_id} no existe en Binance → eliminado"
                        )
                else:
                    _logger.warning(f"[validate_stale_crypto_orders] {row['symbol']}: {e}")
        if resolved:
            _logger.warning(f"validate_stale_crypto_orders: {resolved} resueltas account={account}")
        return resolved

    def validate_stale_stock_orders(self, account: str, ib_client, days_min: int = 2, days_max: int = 7) -> int:
        """Valida con IB órdenes Submitted de days_min-days_max días.
        Las no encontradas en live orders se eliminan (registros huérfanos)."""
        candidates = self.get_stale_pending_orders(account, "Stock", days_min, days_max)
        if not candidates:
            return 0
        try:
            orders = (ib_client.get_live_orders() or {}).get("orders", [])
            live_coids = {str(o.get("orderId", "")) for o in orders}
        except Exception as e:
            _logger.error(f"[validate_stale_stock_orders] get_live_orders: {e}")
            return 0
        resolved = 0
        for row in candidates:
            coid = str(row.get("clientOrderId") or "")
            if coid and coid in live_coids:
                continue
            if self.delete_order_trader_by_id(row["id"], account):
                resolved += 1
                _logger.warning(
                    f"[validate_stale_stock_orders] {row['symbol']} coid={coid} no está en IB live → eliminado"
                )
        if resolved:
            _logger.warning(f"validate_stale_stock_orders: {resolved} eliminadas account={account}")
        return resolved

    def sync_splits(self, account="U4214563"):
        """Detecta splits via yfinance para posiciones abiertas (stock>0), registra en bdinv.split
        solo splits ocurridos después de la primera compra del símbolo, y aplica pendientes.
        Returns dict {nuevos, aplicados, residuos}."""
        nuevos, aplicados, residuos = 0, 0, 0
        try:
            conn = self._conectar(tabla="sync_splits.symbols")
            cursor = conn.cursor()
            cursor.execute(
                """SELECT b.simbolo, MIN(b.fechahora) AS primera_compra
                   FROM booktrading b
                   JOIN (
                       SELECT cuenta, simbolo, MAX(sec) AS max_sec
                       FROM booktrading WHERE cuenta=%s AND delisted=0 GROUP BY cuenta, simbolo
                   ) m ON b.cuenta=m.cuenta AND b.simbolo=m.simbolo AND b.sec=m.max_sec
                   WHERE b.stock > 0
                   GROUP BY b.simbolo""",
                (account,),
            )
            positions = {r[0]: r[1] for r in cursor.fetchall()}
            cursor.close()
            conn.close()
        except (Exception, connect.Error) as e:
            _logger.error(f"sync_splits(): {e}")
            return {"nuevos": 0, "aplicados": 0, "residuos": 0}

        for symbol, primera_compra in positions.items():
            try:
                splits = yf.Ticker(symbol).splits
                if splits.empty:
                    continue
                ts = pd.Timestamp(primera_compra)
                if splits.index.tz is not None and ts.tzinfo is None:
                    ts = ts.tz_localize(splits.index.tz)
                relevantes = splits[splits.index >= ts]
                for split_date, ratio in relevantes.items():
                    if ratio <= 0 or ratio == 1.0:
                        continue
                    self.insert_split(
                        symbol=symbol,
                        values={"date": split_date, "split": float(ratio), "preciocantidad": "A", "aplicado": "N"},
                    )
                    nuevos += 1
            except Exception as e:
                _logger.error(f"sync_splits detect {symbol}: {e}")

        try:
            pending, ix = self.select_split(symbol="all")
        except Exception as e:
            _logger.error(f"sync_splits select_split(): {e}")
            return {"nuevos": nuevos, "aplicados": 0, "residuos": 0}

        for row in pending:
            rec = dict(zip(ix, row))
            symbol = rec["ticket"]
            split_date = rec["date"]
            ratio = float(rec["split"])
            pc = rec.get("preciocantidad") or "A"
            split_id = rec["id"]
            if ratio <= 0 or ratio == 1.0:
                continue
            try:
                conn = self._conectar(tabla="sync_splits.apply")
                cursor = conn.cursor()
                if pc in ("A", None):
                    cursor.execute(
                        """UPDATE booktrading
                           SET cantidad=cantidad*%s, stock=stock*%s,
                               basico=basico/%s, preciotrans=preciotrans/%s, preciocierre=preciocierre/%s,
                               split=split*%s
                           WHERE cuenta=%s AND simbolo=%s AND fechahora<%s""",
                        (ratio, ratio, ratio, ratio, ratio, ratio, account, symbol, split_date),
                    )
                elif pc == "C":
                    cursor.execute(
                        """UPDATE booktrading
                           SET cantidad=cantidad*%s, stock=stock*%s, split=split*%s
                           WHERE cuenta=%s AND simbolo=%s AND fechahora<%s""",
                        (ratio, ratio, ratio, account, symbol, split_date),
                    )
                elif pc == "P":
                    cursor.execute(
                        """UPDATE booktrading
                           SET basico=basico/%s, preciotrans=preciotrans/%s, preciocierre=preciocierre/%s,
                               split=split*%s
                           WHERE cuenta=%s AND simbolo=%s AND fechahora<%s""",
                        (ratio, ratio, ratio, ratio, account, symbol, split_date),
                    )
                aplicados += cursor.rowcount
                cursor.execute("UPDATE split SET aplicado='Y' WHERE id=%s", (split_id,))
                conn.commit()
                cursor.close()
                conn.close()
            except (Exception, connect.Error) as e:
                _logger.error(f"sync_splits apply {symbol} {split_date}: {e}")

        try:
            conn = self._conectar(tabla="sync_splits.residuos")
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE booktrading b
                   JOIN (
                       SELECT cuenta, simbolo, MAX(sec) AS max_sec
                       FROM booktrading WHERE cuenta=%s GROUP BY cuenta, simbolo
                   ) m ON b.cuenta=m.cuenta AND b.simbolo=m.simbolo AND b.sec=m.max_sec
                   SET b.stock=0
                   WHERE ABS(b.stock) < 0.01 AND b.stock != 0""",
                (account,),
            )
            residuos = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
        except (Exception, connect.Error) as e:
            _logger.error(f"sync_splits residuos: {e}")

        return {"nuevos": nuevos, "aplicados": aplicados, "residuos": residuos}

    def insert_preservation_order(
        self,
        account: str,
        vehiculo: str,
        symbol: str,
        conid: str,
        order_id: str,
        stop_price: float,
        qty: float,
        json_detalle: str,
    ) -> bool:
        """Registra una orden STOP de preservation en order_trader con json_detalle."""
        conn = self._conectar(tabla="insert.order_trader")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO order_trader "
                "(account, vehiculo, symbol, conid, clientOrderId, side, orderType, "
                "price, quantity, status, json_detalle, stampPlace) "
                "VALUES (%s, %s, %s, %s, %s, 'SELL', 'STP LMT', %s, %s, 'New', %s, NOW())",
                (account, vehiculo, symbol, conid, order_id, stop_price, qty, json_detalle),
            )
            conn.commit()
            return True
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::insert_preservation_order({symbol})]: {error}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()


    def recalculate_stock_chain(self, account: str, symbol: str, divisa: str) -> int:
        """
        Recalcula el campo stock de TODOS los registros del símbolo usando
        SUM(cantidad) acumulada ordenada por (fechahora, sec).
        Retorna la cantidad de filas actualizadas.
        """
        conn = self._conectar(tabla="update.booktrading.recalc")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE booktrading b
                   JOIN (
                       SELECT id,
                              SUM(cantidad) OVER (
                                  PARTITION BY cuenta, simbolo, divisa
                                  ORDER BY fechahora, sec
                              ) AS stock_real
                       FROM booktrading
                       WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                   ) calc ON b.id = calc.id
                   SET b.stock = calc.stock_real
                   WHERE b.cuenta = %s AND b.simbolo = %s AND b.divisa = %s""",
                (account, symbol, divisa, account, symbol, divisa),
            )
            conn.commit()
            return cursor.rowcount
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: recalculate_stock_chain()]: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def exists_bt_trade(self, account: str, symbol: str, divisa: str,
                        fechahora, cantidad: float, precio: float) -> bool:
        """True si existe un registro en booktrading que coincida en fecha/qty/precio."""
        conn = self._conectar(tabla="select.booktrading.exists")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 1 FROM booktrading
                   WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                     AND DATE(fechahora) = DATE(%s)
                     AND ABS(cantidad - %s) < 0.001
                     AND ABS(preciotrans - %s) < 0.001
                   LIMIT 1""",
                (account, symbol, divisa, fechahora, cantidad, precio),
            )
            return cursor.fetchone() is not None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: exists_bt_trade()]: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def exists_bt_trade_by_idtrans(self, account: str, symbol: str, divisa: str, idtrans: str) -> bool:
        """True si existe un registro en booktrading con ese idtrans (match exacto — Flex format)."""
        conn = self._conectar(tabla="select.booktrading.exists_idtrans")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 1 FROM booktrading
                   WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                     AND idtrans = %s
                   LIMIT 1""",
                (account, symbol, divisa, idtrans),
            )
            return cursor.fetchone() is not None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: exists_bt_trade_by_idtrans()]: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def raw_insert_bt_trade(self, account: str, symbol: str, divisa: str,
                            fechahora, cantidad: float, precio: float,
                            commission: float, categoria: str = "Stock",
                            idtrans: str = None) -> bool:
        """
        Inserta un trade faltante en booktrading SIN calcular stock/basico.
        El campo stock queda en 0 — debe llamarse recalculate_stock_chain() después.
        idtrans: si se pasa (Flex format), se usa el TransactionID real de IB.
                 Si no, se genera un ID sintético basado en hash.
        """
        conn = self._conectar(tabla="insert.booktrading.raw")
        cursor = None
        try:
            cursor = conn.cursor()
            codigo = "O" if cantidad > 0 else "C"
            sec_next = 0
            cursor.execute(
                "SELECT COALESCE(MAX(sec),0)+1 FROM booktrading WHERE cuenta=%s AND simbolo=%s AND divisa=%s",
                (account, symbol, divisa),
            )
            row = cursor.fetchone()
            if row:
                sec_next = int(row[0])

            import hashlib as _hl
            import datetime as _dt
            if not idtrans:
                idtrans = _hl.md5(
                    f"IB_FLEX_{symbol}_{fechahora}_{cantidad}_{precio}".encode()
                ).hexdigest()[:24]
            cursor.execute(
                """INSERT INTO booktrading
                   (cuenta, simbolo, divisa, categoria, fechahora, cantidad,
                    preciotrans, preciocierre, tarifacomision, producto, codigo,
                    activa, stock, basico, gprealizadas, sec, split, idtrans, updateStamp)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Y',0,%s,0,%s,1,%s,%s)""",
                (account, symbol, divisa, categoria, fechahora, cantidad,
                 precio, precio, commission, round(precio * abs(cantidad), 4),
                 codigo, precio, sec_next, str(idtrans), _dt.datetime.now()),
            )
            conn.commit()
            return True
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: raw_insert_bt_trade()]: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_bt_stock_before(self, account: str, symbol: str, divisa: str, date: str):
        """Stock más reciente en booktrading estrictamente antes de la fecha dada (cualquier activa)."""
        conn = self._conectar(tabla="reconcile.bt_stock_before")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT stock FROM booktrading
                   WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                     AND fechahora < %s AND delisted = 0
                   ORDER BY fechahora DESC, sec DESC
                   LIMIT 1""",
                (account, symbol, divisa, date),
            )
            row = cursor.fetchone()
            return float(row[0]) if row else None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: get_bt_stock_before()]: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_bt_latest_stock(self, account: str, symbol: str, divisa: str):
        """Retorna (id, stock) del último registro activo para el símbolo."""
        conn = self._conectar(tabla="reconcile.bt_latest_stock")
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, stock FROM booktrading
                   WHERE cuenta = %s AND simbolo = %s AND divisa = %s
                     AND activa = 'Y' AND delisted = 0
                   ORDER BY fechahora DESC, sec DESC
                   LIMIT 1""",
                (account, symbol, divisa),
            )
            row = cursor.fetchone()
            return (int(row[0]), float(row[1])) if row else (None, None)
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: get_bt_latest_stock()]: {e}")
            return (None, None)
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def get_ib_trades(self, account_id: str, date_from: str, date_to: str = None) -> list:
        """
        Retorna trades de ib_flex_trades para el período dado.
        date_from / date_to : 'YYYY-MM-DD'
        Retorna lista de dicts con las columnas de la tabla.
        """
        conn = cursor = None
        try:
            conn = self._conectar(tabla="select.ib_flex_trades")
            cursor = conn.cursor()
            sql = """SELECT transaction_id, symbol, currency, trade_datetime,
                            trade_date, quantity, price, commission, buy_sell
                       FROM ib_flex_trades
                      WHERE account_id = %s AND trade_date >= %s"""
            params = [account_id, date_from]
            if date_to:
                sql += " AND trade_date <= %s"
                params.append(date_to)
            sql += " ORDER BY trade_datetime"
            cursor.execute(sql, params)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: get_ib_trades()]: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_ib_trades_net(self, account_id: str, date_from: str, date_to: str = None) -> list:
        """
        Retorna neto de qty por symbol+currency en el período.
        Retorna lista de dicts: {symbol, currency, ib_net}
        """
        conn = cursor = None
        try:
            conn = self._conectar(tabla="select.ib_flex_trades.net")
            cursor = conn.cursor()
            sql = """SELECT symbol, currency, SUM(quantity) AS ib_net
                       FROM ib_flex_trades
                      WHERE account_id = %s AND trade_date >= %s"""
            params = [account_id, date_from]
            if date_to:
                sql += " AND trade_date <= %s"
                params.append(date_to)
            sql += " GROUP BY symbol, currency"
            cursor.execute(sql, params)
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: get_ib_trades_net()]: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def count_ib_trades(self, account_id: str) -> dict:
        """Retorna {total, date_min, date_max} de ib_flex_trades para la cuenta."""
        conn = cursor = None
        try:
            conn = self._conectar(tabla="select.ib_flex_trades.count")
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*), MIN(trade_date), MAX(trade_date)
                     FROM ib_flex_trades WHERE account_id = %s""",
                (account_id,),
            )
            row = cursor.fetchone()
            return {"total": row[0], "date_min": str(row[1] or ""), "date_max": str(row[2] or "")}
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: count_ib_trades()]: {e}")
            return {"total": 0, "date_min": "", "date_max": ""}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class FinanceScreen(BDsystem):  # -------------------------------------------------------------------------------------
    """
    Operaciones DB para el módulo de Finanzas Personales.
    Tablas: fin_accounts, fin_banks, fin_transactions, fin_categories, fin_import_rules.
    """

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        return BDsystem.connect_dbase(tabla, display=self.display)

    def get_bank_credentials(self, bank_name: str) -> dict | None:
        """Retorna {login_user, login_pass} para el banco indicado (ej: 'BBVA', 'Santander')."""
        conn = self._conectar("fin_banks.select")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT login_user, login_pass FROM fin_banks WHERE name = %s AND is_active = 1",
                (bank_name,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                return {"login_user": row[0], "login_pass": row[1] or ""}
            return None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_bank_credentials({bank_name})]: {e}")
            return None
        finally:
            conn.close()

    def get_accounts(self) -> list[tuple]:
        """Retorna lista de cuentas activas: (label, account_id, bank_name, account_name, short_name)."""
        conn = self._conectar("fin_accounts.select")
        try:
            cursor = conn.cursor()
            cursor.execute("""SELECT CONCAT(b.name, ' — ', a.name), a.id, b.name, a.name, a.short_name
                   FROM fin_accounts a
                   JOIN fin_banks b ON b.id = a.bank_id
                   WHERE a.is_active = 1
                   ORDER BY b.name, a.name""")
            return cursor.fetchall()
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_accounts()]: {e}")
            return []
        finally:
            conn.close()

    def get_account_id(self, label: str) -> int | None:
        """Resuelve account_id a partir del label 'Banco — Cuenta'."""
        parts = label.split(" — ", 1)
        if len(parts) != 2:
            return None
        conn = self._conectar("fin_accounts.select")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT a.id FROM fin_accounts a
                   JOIN fin_banks b ON b.id = a.bank_id
                   WHERE b.name = %s AND a.name = %s""",
                (parts[0], parts[1]),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_account_id()]: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def _ids_clause(account_ids: list[int] | None) -> tuple[str, list]:
        """Helper: genera cláusula WHERE y params para filtro por lista de account_ids."""
        if not account_ids:
            return "", []
        placeholders = ",".join(["%s"] * len(account_ids))
        return f"AND t.account_id IN ({placeholders})", list(account_ids)

    def sync_binance_investment(self, year: int, month: int) -> dict:
        """
        Calcula el USDT neto retenido en Binance para el mes dado y hace upsert
        de una transacción sintética (classified_by='synthetic') con category_type='investment'.
        Fórmula: Compra USDT − Venta USDT USD − Remesa VES − Remesa Pay.
        Llama automáticamente desde load() de C2C y Pay, y desde save_rule() si afecta USDT.
        """
        from calendar import monthrange
        from datetime import date as _date
        from decimal import Decimal

        last_day = monthrange(year, month)[1]
        date_from = _date(year, month, 1)
        date_to = _date(year, month, last_day)
        comprobante = f"BINANCE-INV-{year:04d}-{month:02d}"

        conn = self._conectar("sync_binance_investment")
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM fin_accounts WHERE account_ref='BINANCE-USDT' AND is_active=1")
            row = cur.fetchone()
            if not row:
                return {"net_usdt": 0, "action": "no_account"}
            account_id = row[0]

            cur.execute("SELECT id FROM fin_categories WHERE name='Retención USDT'")
            row = cur.fetchone()
            if not row:
                return {"net_usdt": 0, "action": "no_category"}
            retention_cat_id = row[0]

            cur.execute(
                """SELECT
                       COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0)
                   FROM fin_transactions
                   WHERE account_id=%s AND currency='USDT'
                     AND date BETWEEN %s AND %s
                     AND (classified_by IS NULL OR classified_by != 'synthetic')""",
                (account_id, date_from, date_to),
            )
            income, expense = cur.fetchone()
            net = round(float(income) - float(expense), 8)

            cur.execute(
                "SELECT id FROM fin_transactions WHERE comprobante=%s AND account_id=%s",
                (comprobante, account_id),
            )
            existing = cur.fetchone()

            if net <= 0:
                if existing:
                    cur.execute("DELETE FROM fin_transactions WHERE id=%s", (existing[0],))
                    conn.commit()
                return {"net_usdt": net, "action": "deleted"}

            if existing:
                cur.execute(
                    "UPDATE fin_transactions SET amount=%s, amount_usdt=%s, date=%s, category_id=%s " "WHERE id=%s",
                    (Decimal(str(net)), Decimal(str(net)), date_to, retention_cat_id, existing[0]),
                )
                action = "updated"
            else:
                cur.execute(
                    """INSERT INTO fin_transactions
                           (date, type, amount, currency, amount_usdt, category_id, account_id,
                            description, raw_description, raw_description_detail,
                            comprobante, classified_by)
                       VALUES (%s,'expense',%s,'USDT',%s,%s,%s,%s,%s,'',%s,'synthetic')""",
                    (
                        date_to,
                        Decimal(str(net)),
                        Decimal(str(net)),
                        retention_cat_id,
                        account_id,
                        f"USDT retenido {year}-{month:02d}",
                        "BINANCE RETENCION USDT",
                        comprobante,
                    ),
                )
                action = "inserted"

            conn.commit()
            cur.close()
            return {"net_usdt": net, "action": action}
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.sync_binance_investment()]: {e}")
            return {"net_usdt": 0, "action": "error"}
        finally:
            conn.close()

    def get_kpis(self, date_from: str, date_to: str, account_ids: list[int] | None = None) -> dict:
        """
        Retorna KPIs del período para moneda ARS:
          ingresos, gastos, ing_usdt, gas_usdt, total_txns.
        account_ids: None=todas, []=ninguna, [1,2,...]=filtro.
        """
        clause, extra = self._ids_clause(account_ids)
        params = [date_from, date_to] + extra

        conn = self._conectar("fin_transactions.kpis")
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT
                       COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense') = 'income'      THEN t.amount_usdt ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense') = 'expense'     THEN t.amount_usdt ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN t.currency='ARS' AND COALESCE(c.category_type,'expense') = 'income'     THEN t.amount ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN t.currency='ARS' AND COALESCE(c.category_type,'expense') = 'expense'    THEN t.amount ELSE 0 END), 0),
                       COUNT(*),
                       COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense') = 'investment'  THEN t.amount_usdt ELSE 0 END), 0),
                       COALESCE(SUM(CASE WHEN t.currency='ARS' AND COALESCE(c.category_type,'expense') = 'investment' THEN t.amount ELSE 0 END), 0)
                   FROM fin_transactions t
                   LEFT JOIN fin_categories c ON c.id = t.category_id
                   WHERE t.date BETWEEN %s AND %s {clause}""",
                params,
            )
            row = cursor.fetchone()
            if row:
                return {
                    "ingresos": float(row[0]),  # USD equivalente — coincide con categorías
                    "gastos": float(row[1]),  # USD equivalente — coincide con categorías
                    "ingresos_ars": float(row[2]),  # subtotal ARS pesos
                    "gastos_ars": float(row[3]),  # subtotal ARS pesos
                    "total_txns": int(row[4]),
                    "invertido": float(row[5]),  # USD equivalente
                    "invertido_ars": float(row[6]),  # subtotal ARS pesos
                }
            return {}
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_kpis()]: {e}")
            return {}
        finally:
            conn.close()

    def _get_categories_by_type(
        self, cat_type: str, date_from: str, date_to: str, account_ids: list[int] | None = None
    ) -> list[dict]:
        """Agrupa transacciones por categoría filtrando por category_type de la categoría."""
        clause, extra = self._ids_clause(account_ids)
        params = [cat_type, date_from, date_to] + extra

        conn = self._conectar("fin_transactions.categories")
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT
                       COALESCE(c.name, 'Sin categoría'),
                       COALESCE(SUM(t.amount_usdt), SUM(t.amount)) AS total_usdt
                   FROM fin_transactions t
                   LEFT JOIN fin_categories c ON c.id = t.category_id
                   WHERE COALESCE(c.category_type, 'expense') = %s
                     AND t.date BETWEEN %s AND %s {clause}
                   GROUP BY c.name
                   ORDER BY total_usdt DESC""",
                params,
            )
            rows = cursor.fetchall()
            total = sum(float(r[1]) for r in rows) or 1
            return [{"name": r[0], "total": float(r[1]), "pct": float(r[1]) / total * 100} for r in rows]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen._get_categories_by_type({cat_type})]: {e}")
            return []
        finally:
            conn.close()

    def get_categories_expense(self, date_from: str, date_to: str, account_ids: list[int] | None = None) -> list[dict]:
        return self._get_categories_by_type("expense", date_from, date_to, account_ids)

    def get_categories_income(self, date_from: str, date_to: str, account_ids: list[int] | None = None) -> list[dict]:
        return self._get_categories_by_type("income", date_from, date_to, account_ids)

    def get_categories_transfer(self, date_from: str, date_to: str, account_ids: list[int] | None = None) -> list[dict]:
        return self._get_categories_by_type("transfer", date_from, date_to, account_ids)

    def get_categories_investment(
        self, date_from: str, date_to: str, account_ids: list[int] | None = None
    ) -> list[dict]:
        return self._get_categories_by_type("investment", date_from, date_to, account_ids)

    def get_monthly_evolution(self, months: int = 6, account_ids: list[int] | None = None) -> list[dict]:
        """Retorna los últimos N meses con totales de ingresos, gastos e inversiones en USD."""
        clause, extra = self._ids_clause(account_ids)
        conn = self._conectar("fin_transactions.evolution")
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT
                        YEAR(t.date)  AS yr,
                        MONTH(t.date) AS mo,
                        COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense')='income'     THEN t.amount_usdt ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense')='expense'    THEN t.amount_usdt ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN COALESCE(c.category_type,'expense')='investment' THEN t.amount_usdt ELSE 0 END), 0)
                    FROM fin_transactions t
                    LEFT JOIN fin_categories c ON c.id = t.category_id
                    WHERE t.date >= DATE_SUB(CURDATE(), INTERVAL %s MONTH) {clause}
                    GROUP BY yr, mo
                    ORDER BY yr, mo""",
                [months] + extra,
            )
            _MESES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            return [
                {
                    "year": int(r[0]),
                    "month": int(r[1]),
                    "label": _MESES[int(r[1])],
                    "ingresos": float(r[2]),
                    "gastos": float(r[3]),
                    "invertido": float(r[4]),
                }
                for r in cursor.fetchall()
            ]
        except (Exception, connect.Error) as e:
            print(f"[Mysql::FinanceScreen.get_monthly_evolution()]: {e}")
            return []
        finally:
            conn.close()

    def get_transactions(
        self, date_from: str, date_to: str, account_ids: list[int] | None = None, limit: int = 200
    ) -> list[dict]:
        """
        Retorna últimas transacciones del período.
        Resultado: [{"date", "type", "amount", "currency", "description", "category", "account"}, ...]
        """
        clause, extra = self._ids_clause(account_ids)
        params = [date_from, date_to] + extra + [limit]

        conn = self._conectar("fin_transactions.select")
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""SELECT
                       t.id, t.date, t.type, t.amount, t.currency,
                       COALESCE(t.description, t.raw_description),
                       COALESCE(c.name, 'Sin categoría'),
                       t.category_id,
                       CONCAT(a.name,
                              IF(a.account_number_last4 IS NOT NULL,
                                 CONCAT(' ****', a.account_number_last4), ''))
                   FROM fin_transactions t
                   LEFT JOIN fin_categories c ON c.id = t.category_id
                   LEFT JOIN fin_accounts   a ON a.id = t.account_id
                   LEFT JOIN fin_banks      b ON b.id = a.bank_id
                   WHERE t.date BETWEEN %s AND %s {clause}
                   ORDER BY t.date DESC
                   LIMIT %s""",
                params,
            )
            return [
                {
                    "txn_id": r[0],
                    "date": str(r[1]),
                    "type": r[2],
                    "amount": float(r[3]),
                    "currency": r[4],
                    "description": r[5],
                    "category": r[6],
                    "category_id": r[7],
                    "account": r[8],
                }
                for r in cursor.fetchall()
            ]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_transactions()]: {e}")
            return []
        finally:
            conn.close()

    def get_categories(self) -> list[tuple]:
        """Retorna todas las categorías activas: [(id, name, category_type), ...]."""
        conn = self._conectar("fin_categories.select")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, category_type FROM fin_categories ORDER BY name")
            return cursor.fetchall()
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_categories()]: {e}")
            return []
        finally:
            conn.close()

    def add_category(self, name: str, category_type: str) -> tuple[bool, str]:
        """Inserta una nueva categoría. Retorna (ok, mensaje)."""
        name = name.strip()
        if not name:
            return False, "El nombre no puede estar vacío."
        conn = self._conectar("fin_categories.insert")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO fin_categories (name, category_type) VALUES (%s, %s)",
                (name, category_type),
            )
            conn.commit()
            return True, f"Categoría '{name}' creada."
        except (Exception, connect.Error) as e:
            return False, str(e)
        finally:
            conn.close()

    def delete_category(self, cat_id: int) -> tuple[bool, str]:
        """Elimina categoría si no tiene transacciones asociadas. Retorna (ok, mensaje)."""
        conn = self._conectar("fin_categories.delete")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fin_transactions WHERE category_id=%s", (cat_id,))
            count = cursor.fetchone()[0]
            if count > 0:
                return (
                    False,
                    f"No se puede eliminar: tiene {count} transacción{'es' if count > 1 else ''} asignada{'s' if count > 1 else ''}.",
                )
            cursor.execute("DELETE FROM fin_categories WHERE id=%s", (cat_id,))
            conn.commit()
            return True, "Categoría eliminada."
        except (Exception, connect.Error) as e:
            return False, str(e)
        finally:
            conn.close()

    def get_last_loaded_period(self) -> tuple[int, int]:
        """Retorna (mes, año) del último mes con transacciones cargadas (sin fechas futuras)."""
        conn = self._conectar("fin_transactions.last_period")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT YEAR(MAX(date)), MONTH(MAX(date)) FROM fin_transactions WHERE date <= CURDATE()")
            row = cursor.fetchone()
            if row and row[0]:
                return int(row[1]), int(row[0])
        except (Exception, connect.Error):
            pass
        finally:
            conn.close()
        from datetime import datetime as _dt

        now = _dt.now()
        return now.month, now.year

    def get_tasa(self, currency: str, fecha) -> float | None:
        """Devuelve tasa fiat→USDT más cercana a fecha desde booktrading.
        USD → 1.0 directo. ARS/VES → busca en booktrading por categoria."""
        if currency == "USD":
            return 1.0
        categoria = {"ARS": "ARS", "VES": "VES"}.get(currency)
        if not categoria:
            return None
        conn = self._conectar("booktrading.tasa")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT preciotrans FROM booktrading
                   WHERE categoria=%s AND simbolo='USDT' AND preciotrans > 0
                   ORDER BY ABS(TIMESTAMPDIFF(SECOND, fechahora, %s))
                   LIMIT 1""",
                (categoria, fecha),
            )
            row = cursor.fetchone()
            return float(row[0]) if row else None
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.get_tasa()]: {e}")
            return None
        finally:
            conn.close()

    def update_txn_category(self, txn_id: int, category_id: int | None) -> bool:
        """Actualiza la categoría de una transacción. Retorna True si tuvo efecto."""
        conn = self._conectar("fin_transactions.update")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE fin_transactions SET category_id=%s, classified_by='manual' WHERE id=%s",
                (category_id, txn_id),
            )
            conn.commit()
            return cursor.rowcount == 1
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.update_txn_category()]: {e}")
            return False
        finally:
            conn.close()

    def update_txn_date(self, txn_id: int, new_date: str) -> bool:
        """Corrige la fecha de una transacción (desfase banco vs operación). Retorna True si tuvo efecto."""
        conn = self._conectar("fin_transactions.update_date")
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE fin_transactions SET date=%s WHERE id=%s", (new_date, txn_id))
            conn.commit()
            return cursor.rowcount == 1
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.update_txn_date()]: {e}")
            return False
        finally:
            conn.close()

    def save_rule(self, pattern: str, match_type: str, category_id: int, priority: int = 50) -> bool:
        """
        Inserta o actualiza una regla en fin_import_rules (creada por el usuario).
        priority=50 → reglas de usuario tienen mayor precedencia que las del sistema (100).
        Luego aplica retroactivamente la regla a todas las transacciones sin categoría
        que coincidan, para que el aprendizaje tenga efecto inmediato en el historial.
        Retorna True si se insertó o actualizó.
        """
        import re as _re

        conn = self._conectar("fin_import_rules.upsert")
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO fin_import_rules
                       (pattern, match_type, category_id, priority, created_by)
                   VALUES (%s, %s, %s, %s, 'user')
                   ON DUPLICATE KEY UPDATE
                       category_id = VALUES(category_id),
                       priority    = VALUES(priority),
                       is_active   = 1,
                       created_by  = 'user'""",
                (pattern.strip(), match_type, category_id, priority),
            )
            conn.commit()
            inserted = cursor.rowcount >= 1

            # ── aplicación retroactiva ────────────────────────────────────────
            # Cargar txns sin categoría O auto-clasificadas por regla (no manual)
            cursor.execute(
                "SELECT id, COALESCE(raw_description, description) FROM fin_transactions "
                "WHERE classified_by IS NULL OR classified_by = 'rule'"
            )
            candidates = cursor.fetchall()

            p = pattern.strip()
            p_upper = p.upper()
            matched_ids = []
            for txn_id, desc in candidates:
                if not desc:
                    continue
                d = desc.upper()
                hit = False
                if match_type == "exact":
                    hit = d == p_upper
                elif match_type == "contains":
                    hit = p_upper in d
                elif match_type == "startswith":
                    hit = d.startswith(p_upper)
                elif match_type == "regex":
                    hit = bool(_re.search(p, desc, _re.IGNORECASE))
                if hit:
                    matched_ids.append(txn_id)

            if matched_ids:
                placeholders = ",".join(["%s"] * len(matched_ids))
                cursor.execute(
                    f"UPDATE fin_transactions SET category_id=%s, classified_by='rule' "
                    f"WHERE id IN ({placeholders}) AND classified_by != 'manual'",
                    [category_id] + matched_ids,
                )
                conn.commit()

                # Si alguna transacción USDT fue afectada, recalcular inversión por mes
                id_pl = ",".join(["%s"] * len(matched_ids))
                cursor.execute(
                    f"SELECT DISTINCT YEAR(date), MONTH(date) FROM fin_transactions "
                    f"WHERE id IN ({id_pl}) AND currency='USDT'",
                    matched_ids,
                )
                usdt_months = cursor.fetchall()

            for year, month in (usdt_months if matched_ids else []):
                self.sync_binance_investment(year, month)

            return inserted
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.save_rule()]: {e}")
            return False
        finally:
            conn.close()

    def save_rule_count_retro(self, pattern: str, match_type: str) -> int:
        """
        Cuenta cuántas transacciones sin categoría coincidirían con el patrón.
        Útil para mostrar un preview en el popup antes de confirmar.
        """
        import re as _re

        conn = self._conectar("fin_import_rules.preview")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, COALESCE(raw_description, description) FROM fin_transactions "
                "WHERE classified_by IS NULL OR classified_by = 'rule'"
            )
            rows = cursor.fetchall()
            p = pattern.strip()
            p_upper = p.upper()
            count = 0
            for _, desc in rows:
                if not desc:
                    continue
                d = desc.upper()
                if match_type == "exact":
                    count += d == p_upper
                elif match_type == "contains":
                    count += p_upper in d
                elif match_type == "startswith":
                    count += d.startswith(p_upper)
                elif match_type == "regex":
                    count += bool(_re.search(p, desc, _re.IGNORECASE))
            return count
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: FinanceScreen.save_rule_count_retro()]: {e}")
            return 0
        finally:
            conn.close()


class IaTraceScreen(BDsystem):  # ---------------------------------------------------------------------------------

    def __init__(self):
        self.display = False

    def _conectar(self, tabla=None):
        return BDsystem.connect_dbase(tabla, display=self.display)

    def insert_trace(
        self, vehiculo: str, simbolo: str, decision: str, monto: float, motivo: str, gates_ok: dict
    ) -> int | None:
        conn = self._conectar(tabla="ia_trace.insert")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ia_trace (vehiculo, simbolo, decision, monto, motivo, gates_ok) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (vehiculo, (simbolo or "")[:100], decision, monto or 0, motivo or "", json.dumps(gates_ok or {})),
            )
            conn.commit()
            return cursor.lastrowid
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.insert_trace()]: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def update_trace_estado(self, trace_id: int, estado: str, telegram_id: str = None):
        conn = self._conectar(tabla="ia_trace.update")
        try:
            cursor = conn.cursor()
            if telegram_id:
                cursor.execute(
                    "UPDATE ia_trace SET estado = %s, telegram_id = %s WHERE id = %s",
                    (estado, telegram_id, trace_id),
                )
            else:
                cursor.execute(
                    "UPDATE ia_trace SET estado = %s WHERE id = %s",
                    (estado, trace_id),
                )
            conn.commit()
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.update_trace_estado()]: {e}")
        finally:
            cursor.close()
            conn.close()

    def select_trace(self, limit: int = 100) -> list:
        conn = self._conectar(tabla="ia_trace.select")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, vehiculo, simbolo, decision, monto, motivo, estado, gates_ok "
                "FROM ia_trace ORDER BY timestamp DESC LIMIT %s",
                (limit,),
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.select_trace()]: {e}")
            return []
        finally:
            conn.close()

    def insert_mejora(
        self, categoria: str, titulo: str, descripcion: str, impacto: str = "medio", origen: str = None
    ) -> bool:
        conn = self._conectar(tabla="ia_mejoras.insert")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM ia_mejoras WHERE titulo = %s AND estado = 'pendiente' LIMIT 1",
                (titulo,),
            )
            if cursor.fetchone():
                return False
            cursor.execute(
                "INSERT INTO ia_mejoras (categoria, titulo, descripcion, impacto, origen) "
                "VALUES (%s, %s, %s, %s, %s)",
                (categoria, titulo, descripcion or "", impacto, origen or ""),
            )
            conn.commit()
            return True
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.insert_mejora()]: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def select_mejoras(self, estado: str = "pendiente") -> list:
        conn = self._conectar(tabla="ia_mejoras.select")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, categoria, titulo, descripcion, impacto, estado "
                "FROM ia_mejoras WHERE estado = %s ORDER BY timestamp DESC",
                (estado,),
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.select_mejoras()]: {e}")
            return []
        finally:
            conn.close()

    def select_candidatos_ia(self, account: str, consenso_min: int = 4) -> list:
        """Activos con buen consenso que NO están en cartera — candidatos de entrada."""
        conn = self._conectar(tabla="ia_trace.candidatos")
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT symbol, shortName, lastPrice, consenso_tag, consenso_suma, "
                "inst_score, inst_ownership_pct, dividendYield, categoriaActivo "
                "FROM market "
                "WHERE account = %s AND consenso_suma >= %s "
                "AND (encartera IS NULL OR encartera != 'Y') "
                "AND categoriaActivo NOT IN ('X') "
                "ORDER BY consenso_suma DESC, inst_score DESC "
                "LIMIT 10",
                (account, consenso_min),
            )
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except (Exception, connect.Error) as e:
            print(f"[Mysql:: IaTraceScreen.select_candidatos_ia()]: {e}")
            return []
        finally:
            conn.close()
