================================================================================
  SETUP COMPLETO — AppOO + Binance + TradingView
================================================================================


0. DESCARGAR LA APLICACION
---------------------------
Ir al release en GitHub:
  https://github.com/gutierrezw/MyPython/releases/tag/v10.1.0

Descargar:
  - AppOO_hijo.zip  -> descomprimir en cualquier carpeta (ej: C:\AppOO)
  - README.txt, hijo_estructura.sql, hijo_datos.sql, config_import.json.template,
    run_binance_import.py, tv_panel.js  -> guardarlos en una carpeta aparte (ej: C:\AppOO\setup)

La app se ejecuta desde:  AppOO_hijo\AppOO.exe  (no requiere instalar nada)


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

Luego importar los archivos de esta carpeta (desde cmd):

  mysql -u root -p bdinv < hijo_estructura.sql
  mysql -u root -p bdinv < hijo_datos.sql


3. CONFIGURAR LA APP (AppOO.exe)
----------------------------------
Abrir el archivo:  AppOO_hijo\profiles\main.json

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

Ejecutar la app: AppOO_hijo\AppOO.exe


4. INSTALAR PYTHON (para importar operaciones Binance)
-------------------------------------------------------
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


7. SETUP TRADINGVIEW
---------------------
Crear cuenta gratuita en: https://www.tradingview.com


7.1 Agregar los indicadores
  En TradingView abrir un grafico -> click en "Indicators" (arriba).
  Buscar por autor: GutierrezW

  Agregar los dos indicadores:
    - EMA/MACD cross {dual 4 EMA (V2.0)}   <- medias moviles en el grafico
    - RSI Cross + VIX + Volume (v5.1)       <- panel debajo del grafico

  Hacer click en la estrella para agregarlos a Favoritos.


7.2 Instalar el panel de la app (tv_panel.js)
  El panel conecta TradingView con AppOO para ver datos de cartera
  directamente en el grafico. Requiere que AppOO este corriendo.

  Paso 1 - Instalar Tampermonkey (extension del browser):
    Chrome:  https://chrome.google.com/webstore/detail/tampermonkey
    Firefox: https://addons.mozilla.org/firefox/addon/tampermonkey
    Instalar y activar la extension.

  Paso 2 - Instalar el script:
    - Abrir Tampermonkey -> Dashboard
    - Click en el icono "+" (nuevo script)
    - Borrar todo el contenido que aparece por defecto
    - Pegar el contenido del archivo tv_panel.js (de esta carpeta)
    - Guardar (Ctrl+S)

  Paso 3 - Verificar:
    - Abrir TradingView en el browser
    - Debe aparecer un panel flotante con datos de la cartera
    - Si no aparece: verificar que Tampermonkey este activado
    - La app AppOO debe estar abierta (se comunica por puerto 5050)


================================================================================
