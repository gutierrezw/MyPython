================================================================================
  SETUP COMPLETO — AppOO + Importacion Binance
================================================================================


1. INSTALAR MYSQL
-----------------
Descargar MySQL Community Server:
  https://dev.mysql.com/downloads/mysql/

Elegir "MySQL Installer for Windows" -> opcion "Server Only"

Durante la instalacion:
  - Authentication Method -> "Use Legacy Authentication Method"
  - Root password -> puede dejarlo vacio o poner una contrasena (anotarla)
  - Puerto por defecto: 3306 (no cambiar)


2. CREAR LA BASE DE DATOS E IMPORTAR
-------------------------------------
Abrir "MySQL Command Line Client" (se instala con MySQL) y ejecutar:

  CREATE DATABASE bdinv CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

Luego importar los archivos que te paso (desde cmd):

  mysql -u root -p bdinv < schema_bdinv.sql
  mysql -u root -p bdinv < datos_referencia.sql


3. CONFIGURAR LA APP (AppOO.exe)
----------------------------------
Abrir el archivo:  profiles\main.json

Completar el campo "password" con la contrasena elegida en el paso 1:

  {
      "db": {
          "host": "localhost",
          "user": "root",
          "password": "TU_PASSWORD",
          "database": "bdinv"
      }
  }

Si dejaste la contrasena vacia en MySQL, dejar "password": ""


4. INSTALAR PYTHON
-------------------
Descargar Python 3.11 o superior:
  https://www.python.org/downloads/

IMPORTANTE: durante la instalacion marcar "Add Python to PATH"

Luego instalar las dependencias (abrir cmd y ejecutar):

  pip install binance-connector pymysql


5. CONFIGURAR EL SCRIPT DE IMPORTACION BINANCE
------------------------------------------------
Copiar el template:
  config_import.json.template  ->  config_import.json  (misma carpeta)

Abrir config_import.json y completar:
  - api_key / api_secret: obtenerlos desde tu cuenta Binance -> Gestion de API
  - password: la misma contrasena de MySQL del paso 1

  {
      "api_key": "TU_API_KEY_BINANCE",
      "api_secret": "TU_API_SECRET_BINANCE",
      "account": "B0000001",
      "vehiculo": "Crypto",
      "db": {
          "host": "localhost",
          "user": "root",
          "password": "TU_PASSWORD",
          "database": "bdinv"
      }
  }


6. IMPORTAR OPERACIONES BINANCE
---------------------------------
Primer run (verifica sin insertar nada):

  python run_binance_import.py --desde 2024-01-01 --dry-run

Si todo se ve bien, importar definitivo:

  python run_binance_import.py --desde 2024-01-01

Opciones disponibles:
  --desde     Fecha de inicio obligatoria (formato YYYY-MM-DD)
  --simbolos  Simbolos especificos, ej: --simbolos BTC ETH BNB
              (si no se indica, se detectan automaticamente desde el balance)
  --dry-run   Muestra las operaciones sin insertar en la base de datos


================================================================================
