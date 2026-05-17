@echo off
cd /d "%~dp0"
echo ======================================================
echo == INICIANDO CONSTRUCCION DE EJECUTABLE (PYINSTALLER) ==
echo ======================================================

set PYENV=C:\Users\InversionesWildaga\Documents\MyPython\.venv\Scripts
set DEPLOY=C:\Users\InversionesWildaga\Documents\deploy

echo.
echo IMPORTANTE: Cerrar el Explorador de Windows apuntando a deploy\AppOO\
echo            y cerrar AppOO.exe si esta corriendo.
echo.
pause

echo Creando estructura deploy si no existe...
if not exist "%DEPLOY%" mkdir "%DEPLOY%"
if not exist "%DEPLOY%\tmp" mkdir "%DEPLOY%\tmp"
if not exist "%DEPLOY%\logs" mkdir "%DEPLOY%\logs"

echo.
echo Limpiando AppOO anterior...
rmdir /s /q build 2>nul
rmdir /s /q "%DEPLOY%\AppOO" 2>nul

echo.
echo Ejecutando PyInstaller...

%PYENV%\pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --paths "." ^
    --paths "AppValuations" ^
    --name "AppOO" ^
    --distpath "%DEPLOY%" ^
    --add-data "profiles;profiles" ^
    --hidden-import "pymysql" ^
    --hidden-import "schedule" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "ta" ^
    --hidden-import "yfinance" ^
    --hidden-import "syncio" ^
    --hidden-import "edgar_13f" ^
    --hidden-import "Class_debugging" ^
    --hidden-import "Class_DataFrame" ^
    --hidden-import "Class_ApiIBrks" ^
    --hidden-import "Class_ApiBinnace" ^
    --hidden-import "Class_gestion" ^
    --hidden-import "Class_FondosInversion" ^
    --hidden-import "Class_Screener" ^
    --hidden-import "Class_DashBot" ^
    --hidden-import "Class_IA_modelos" ^
    --hidden-import "Class_SystemStatus" ^
    --hidden-import "Class_BotCryptoUI" ^
    --hidden-import "Class_BrowserBridge" ^
    --hidden-import "Class_Finance" ^
    --hidden-import "Class_customer" ^
    --hidden-import "Modulos_Mysql" ^
    --hidden-import "Modulos_Utilitarios" ^
    --hidden-import "Modulos_python" ^
    --collect-all "binance" ^
    DashMain.py

echo.
echo Copiando profiles al deploy...
xcopy /s /e /i /y profiles "%DEPLOY%\AppOO\profiles" >nul

echo.
echo ======================================================
echo == PROCESO TERMINADO                                 ==
echo == Ejecutable: %DEPLOY%\AppOO\AppOO.exe
echo == Para distribuir al hijo: AppTest\export_hijo.bat
echo ======================================================

start explorer "%DEPLOY%\AppOO"
pause
