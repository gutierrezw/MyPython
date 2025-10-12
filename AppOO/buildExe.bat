@echo off
echo ======================================================
echo == INICIANDO CONSTRUCCION DE EJECUTABLE (PYINSTALLER) ==
echo ======================================================

:: 1. Limpia las carpetas de construccion anteriores
::    (Esto es crucial para evitar errores de caches)
echo.
echo Limpiando entorno anterior...
rmdir /s /q build
del /q DashMainV9_ia.py.spec

:: 2. Define la ruta de la base de datos y otros archivos de datos
::    ASUME que tu base de datos y/o archivos de configuracion estan en una carpeta 'data/' o similar.
::    MODIFICA ESTAS LINEAS si tus archivos estan en otro lugar.
:: set DB_FILE="data\mi_base_de_datos.db"
:: set CONFIG_FILE="config\settings.json"
:: set IMAGENES_DIR="images"

echo.
echo Ejecutando PyInstaller con opciones avanzadas...

:: 3. EL COMANDO PRINCIPAL DE PYINSTALLER
:: pyinstaller --onefile --windowed ^
::    --name "DashApp_Trading" ^
::    --icon "ruta\a\tu\icono.ico" ^
::    --hidden-import "schedule" ^
::    --hidden-import "asyncio" ^
::    --hidden-import "pandas" ^
::    --hidden-import "matplotlib" ^
::    --add-data %DB_FILE%;. ^
::    --add-data %CONFIG_FILE%;. ^
::    --add-data %IMAGENES_DIR%;images ^
::    DashMainV9_ia.py
pyinstaller --onefile --windowed DashMainV9_ia.py

echo.
echo ======================================================
echo == PROCESO TERMINADO ==
echo == Revisa la carpeta 'dist' para el ejecutable. ==
echo ======================================================

pause