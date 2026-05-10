@echo off
echo ======================================================
echo == CONSTRUCCION EJECUTABLE PERFIL: HIJO             ==
echo ======================================================

set PYENV=C:\Users\InversionesWildaga\Documents\MyPython\.venv\Scripts

echo.
echo Limpiando entorno anterior...
rmdir /s /q build 2>nul
if exist "dist\AppOO_hijo.exe" del /f /q "dist\AppOO_hijo.exe"

echo.
echo Ejecutando PyInstaller...

%PYENV%\pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --paths "." ^
    --paths "AppValuations" ^
    --name "AppOO_hijo" ^
    --distpath "dist" ^
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
    DashMain_hijo.py

echo.
echo ======================================================
echo == PROCESO TERMINADO                                 ==
echo == Ejecutable: dist\AppOO_hijo.exe                  ==
echo ======================================================

pause
