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
)
from Modulos_Utilitarios import (
    is_none,
    valida_meses_consecutivos,
    sort_positions,
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
            dict con campos: id, modelo, Nombre, paramts, documents, define_modelo, timestamp
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
        documents: bytes = None,
        tipo_modelo: str = None,
        define_modelo: str = None,
    ) -> bool:
        """
        Inserta un nuevo modelo IA.

        Args:
            modelo: Identificador único del modelo (PK)
            nombre: Nombre descriptivo del modelo
            paramts: Parámetros del modelo (blob serializado)
            documents: Documentación/metadata (blob serializado)
            define_modelo: Definición/tipo del modelo

        Returns:
            True si se insertó correctamente, False en caso de error
        """
        try:
            conn = BDsystem.connect_dbase("insert.define_modelosia", False)
            cursor = conn.cursor()

            sql = """
                INSERT INTO bdinv.modelos_ia
                (modelo, Nombre, paramts, documents, define_modelo, tipo_modelo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (modelo, nombre, paramts, documents, define_modelo, tipo_modelo))
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
        documents: bytes = None,
        define_modelo: str = None,
        tipo_modelo: str = None,
    ) -> bool:
        """
        Actualiza un modelo IA existente.

        Args:
            modelo: Identificador del modelo a actualizar (PK)
            nombre: Nuevo nombre (opcional)
            paramts: Nuevos parámetros (opcional)
            documents: Nueva documentación (opcional)
            define_modelo: Nueva definición (opcional)

        Returns:
            True si se actualizó correctamente, False en caso de error
        """
        try:
            conn = BDsystem.connect_dbase("update.define_modelosia", False)
            cursor = conn.cursor()

            # Construir query dinámicamente según campos proporcionados
            updates = []
            values = []

            if nombre is not None:
                updates.append("Nombre = %s")
                values.append(nombre)
            if paramts is not None:
                updates.append("paramts = %s")
                values.append(paramts)
            if documents is not None:
                updates.append("documents = %s")
                values.append(documents)
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
        conn = self._conectar(tabla="insert.diaria_performance")
        try:
            cursor = conn.cursor()
            valuesins = list()

            qry = "INSERT INTO diaria_performance ("
            for keys, vals in values.items():
                qry = qry + keys + ", "
                valuesins.append(vals)

            valuesins.append(symbol)
            qry += "symbol) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
            cursor.execute(qry, tuple(valuesins))
        except (Exception, EncodingWarning, connect.Error) as error:
            print(f"Mysql:: insert_diaria_performance()]: {error} {qry}={tuple(valuesins)}")
        finally:
            conn.commit()
            cursor.close()


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

            if last:
                u_fecha = last[0].strftime("%Y-%m-%d")
            return u_fecha
        except (Exception, EncodingWarning, connect.Error) as error:
            print("[Mysql:: last_insert_CNV(): {}]".format(error))

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
                                ON a.estrategia = b.estrategia;""".format(
                    ivehiculo
                )

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
                "fh_count, fh_total_value, analyst_rec, analyst_mean, analyst_count, categoriaActivo, "
                "sharesOutstanding, volume, insider_ownership_pct, website "
                "FROM market WHERE account = %s AND encartera = 'Y' "
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

    def mark_booktrading_delisted(self, symbol, account) -> int:
        """Marca delisted=1 en todos los registros de booktrading para symbol+account."""
        try:
            conn = self._conectar(tabla="update.booktrading")
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE booktrading SET delisted = 1, updateStamp = %s "
                "WHERE simbolo = %s AND cuenta = %s",
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
                "SELECT DISTINCT cusip, symbol FROM fund_holdings "
                "WHERE cusip IS NOT NULL AND symbol IS NOT NULL"
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
                chunk = funds_list[i:i + _CHUNK]
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

    def load_all_funds_with_cik(self) -> list:
        """Retorna lista completa de (fund_name, cik) con CIK asignado."""
        conn = self._conectar(tabla="select.market")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT fund_name, cik FROM funds WHERE cik IS NOT NULL")
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
            cursor.execute("SELECT COUNT(*) FROM fund_filings WHERE processed = 0")
            pendientes = cursor.fetchone()[0] or 0

            cursor.execute(
                "SELECT COUNT(*) FROM fund_filings "
                "WHERE filing_date <= DATE_SUB(CURDATE(), INTERVAL 70 DAY)"
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
                "SELECT COUNT(*) FROM market "
                "WHERE account = %s AND cusip IS NULL AND encartera = 'Y'",
                (account,),
            )
            market_sin_cusip = cursor.fetchone()[0] or 0

            return {
                "pendientes"      : pendientes,
                "por_renovar"     : por_renovar,
                "fh_sin_symbol"   : fh_sin_symbol,
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

    def save_fund_filing(self, filename: str, cik: str, fund_name: str,
                         filing_date: str, accession: str) -> None:
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

    def upsert_fund_holding(self, fund_name: str, symbol: str, shares: int, report_date,
                            value: int = None, cusip: str = None, option_type: str = None) -> None:
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
                    (fund_id, symbol, shares, shares_prev, shares_delta, pct_change, operation,
                     report_date, value, cusip, option_type,
                     shares, shares_prev, shares_delta, pct_change, operation, value),
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
                    SUM(CASE WHEN fh.option_type = 'STK'  THEN fh.shares ELSE 0 END) AS fh_total_shares
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
                (symbol, fh_count, fh_total_value, fh_buy_ratio, fh_sell_ratio,
                 fh_call_count, fh_put_count, fh_call_shares, fh_put_shares,
                 fh_total_shares) = row
                result[symbol] = {
                    "fh_count"        : int(fh_count) if fh_count else 0,
                    "fh_total_value"  : int(fh_total_value) if fh_total_value else None,
                    "fh_buy_ratio"    : float(fh_buy_ratio) if fh_buy_ratio else 0.0,
                    "fh_sell_ratio"   : float(fh_sell_ratio) if fh_sell_ratio else 0.0,
                    "fh_call_count"   : int(fh_call_count) if fh_call_count else 0,
                    "fh_put_count"    : int(fh_put_count) if fh_put_count else 0,
                    "fh_call_shares"  : int(fh_call_shares) if fh_call_shares else 0,
                    "fh_put_shares"   : int(fh_put_shares) if fh_put_shares else 0,
                    "fh_total_shares" : int(fh_total_shares) if fh_total_shares else 0,
                }
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
            chunk = records[i:i + chunk_size]
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
                    "inst_ownership_pct" : row[1],
                    "floatShares"        : row[2],
                    "sharesOutstanding"  : row[3],
                }
                for row in cursor.fetchall()
            }
        except (Exception, connect.Error) as error:
            _logger.error(f"[Mysql::load_market_inst_fields]: {error}")
            return {}
        finally:
            cursor.close()
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
            acierre, id_next = 0.0, 1
            uextract = self.select_extracto(account=account, extract="last")
            if len(uextract) == 1:
                acierre = uextract[0]["navcierre"]

            listvalues = []

            # valida que extracto a ingresar sea consecutivo al ultimo extracto
            if uextract and bool(values):
                if valida_meses_consecutivos(inicio=uextract[0]["extracto"], fin=values["extracto"]):
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

    def insert_otros_activos(self, symbol=None, values=None, cuenta="B0000001"):
        """
        @param symbol: ticket a consultar en crypto
        @param cuenta: cuenta destino (default B0000001, BotCrypto usa B0000002)
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

                ticket = yf.Ticker(symbol.replace("USDT", "-USD"))
                name = ticket.info["name"] if "name" in ticket.info else " "
                avg = ticket.info["previousClose"] if "previousClose" in ticket.info else 0
                h52w = ticket.info["fiftyTwoWeekHigh"] if "fiftyTwoWeekHigh" in ticket.info else 0

                qry = "INSERT INTO otros_activos ("

                # equivalente CONV(substr(SHA2(ticket, 256),1,15), 16, 10) mysql
                conidHex = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
                conid = int(conidHex[:15], 16)

                values.update({"cuenta": cuenta})
                values.update({"idcrypto": conid})
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
                qry += "symbol) VALUES ({});".format(",".join("%s" for _ in range(len(valuesins))))
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
            "indicadores": row.get("Datostecnicos") or {},
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
                                                    tarifacomision, idtrans, position_inversion, factor_cambio
                                            FROM booktrading WHERE cuenta = '%s' AND divisa = '%s'
                                                                AND simbolo = '%s' AND activa = 'Y'
                                                                AND delisted = 0) AS a
                            ORDER BY fechahora DESC, sec DESC;"""
                    cursor.execute(qry % (account, idivisa, symbol))
                    sql = cursor.fetchone()

                # ultima diaria registrada
                if symbol is None:
                    qry = """SELECT a.* FROM (SELECT sec, fechahora, stock, basico, gprealizadas, cantidad,
                                                    tarifacomision, idtrans, position_inversion FROM booktrading
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
                            row[ix.index("cantidad")] <= 0 and row[ix.index("fechahora")].date() > desde.date()
                        ):

                            if inicio_qry:
                                concatena = """ AND ((simbolo, fechahora) = ('%s', '%s')""" % (
                                    row[ix.index("simbolo")],
                                    row[ix.index("fechahora")],
                                )
                                inicio_qry = False
                            else:
                                concatena = """ OR (simbolo, fechahora) = ('%s', '%s')""" % (
                                    row[ix.index("simbolo")],
                                    row[ix.index("fechahora")],
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
                               tarifacomision, idtrans, position_inversion, factor_cambio
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
                    "position_inversion": position,
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
            cursor.close()

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
                (book, iy) = self.select_booktrading(accion="select*", account=account, idivisa=idivisa, symbol=symbol)
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
            found_hash = self.get_hash_booktrading(accion="valida", values=values, symbol=symbol)
            if found_hash:
                return

            # procede con insert del trader
            hashId = self.get_hash_booktrading(values=values, symbol=symbol)

            # ubica último trader del symbol para obtener basico
            nw_producto, ubasico, ustock = 0.0, 0.0, 0.0
            usec, uid, position = 0.0, 0.0, 0.0

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

            # cuando es compra en largo
            if values["cantidad"] > 0:

                # obtener basico y recalcular el nuevo producto de utrading entre el nuevo stock
                basico = (values["preciotrans"] * values["cantidad"] + values["tarifacomision"] + nw_producto) / stock
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
                (utrading, ix) = self.select_booktrading(accion="low", account=account, idivisa=idivisa, symbol=ticket)
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

