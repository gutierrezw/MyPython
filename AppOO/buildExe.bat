@echo off
cls
cd /d "%~dp0"

set PYENV=C:\Users\InversionesWildaga\Documents\MyPython\.venv\Scripts
set DEPLOY=C:\Users\InversionesWildaga\Documents\deploy

:: --- Leer version.py --------------------------------------------------
set APP_VERSION=unknown
set APP_DATE=unknown
for /f "tokens=3 delims== " %%a in ('findstr /r "^VERSION" version.py 2^>nul') do set APP_VERSION=%%~a
for /f "tokens=3 delims== " %%a in ('findstr /r "^RELEASE_DATE" version.py 2^>nul') do set APP_DATE=%%~a
set APP_VERSION=%APP_VERSION:"=%
set APP_DATE=%APP_DATE:"=%

:: --- Log fijo (se sobreescribe en cada build) --------------------------
set LOGDIR=%~dp0build_logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set LOGFILE=%LOGDIR%\build.log

echo ======================================================
echo == AppOO v%APP_VERSION%  (%APP_DATE%)
echo == Log: %LOGFILE%
echo ======================================================
echo.

:: --- PRE-BUILD: AppOO.exe corriendo? ----------------------------------
echo [1/5] Verificando procesos...
tasklist /fi "imagename eq AppOO.exe" 2>nul | findstr /i "AppOO.exe" >nul
if not errorlevel 1 (
    echo.
    echo ERROR: AppOO.exe esta corriendo. Cerralo y vuelve a ejecutar.
    goto :error
)
echo       OK - AppOO.exe no esta en ejecucion.

:: --- PRE-BUILD: .venv existe? -----------------------------------------
echo [2/5] Verificando entorno virtual...
if not exist "%PYENV%\pyinstaller.exe" (
    echo.
    echo ERROR: PyInstaller no encontrado en: %PYENV%
    goto :error
)
echo       OK - PyInstaller encontrado.

:: --- Estructura deploy ------------------------------------------------
echo [3/5] Preparando directorios deploy...
if not exist "%DEPLOY%" mkdir "%DEPLOY%"
if not exist "%DEPLOY%\tmp" mkdir "%DEPLOY%\tmp"
if not exist "%DEPLOY%\logs" mkdir "%DEPLOY%\logs"
if not exist "%DEPLOY%\setup" mkdir "%DEPLOY%\setup"
rmdir /s /q build 2>nul
echo       OK

:: --- PYINSTALLER ------------------------------------------------------
echo [4/5] Ejecutando PyInstaller (ver log para detalle)...
echo.

set ICON=C:\Users\InversionesWildaga\Documents\MyPython\Iconos\Systems\WGM_icon.ico
set ICON_FLAG=
if exist "%ICON%" set ICON_FLAG=--icon "%ICON%"

%PYENV%\pyinstaller --noconfirm --onefile --windowed %ICON_FLAG% ^
    --paths "." --paths "AppValuations" --paths "ConvergIA" ^
    --name "AppOO" --distpath "%DEPLOY%" ^
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
    --hidden-import "ConvergIA.ThemeMapper" ^
    --hidden-import "feedparser" ^
    --hidden-import "anthropic" ^
    --collect-all "binance" ^
    --collect-all "tkinter" ^
    DashMain.py >> "%LOGFILE%" 2>&1

if %ERRORLEVEL% neq 0 goto :error

:: --- POST-BUILD: verificar exe ----------------------------------------
echo [5/5] Verificando ejecutable generado...
if not exist "%DEPLOY%\AppOO.exe" (
    echo ERROR: AppOO.exe no encontrado en %DEPLOY%
    goto :error
)
for %%A in ("%DEPLOY%\AppOO.exe") do set EXE_SIZE=%%~zA
set /a EXE_MB=%EXE_SIZE% / 1048576
echo       OK - AppOO.exe  %EXE_MB% MB

:: --- Copiar profiles --------------------------------------------------
xcopy /s /e /i /y profiles "%DEPLOY%\profiles" >nul
if %ERRORLEVEL% neq 0 goto :error
xcopy /s /e /i /y profiles "%DEPLOY%\setup\profiles" >nul
if %ERRORLEVEL% neq 0 goto :error

:: --- RESULTADO --------------------------------------------------------
echo.
echo ======================================================
echo == BUILD EXITOSO
echo == Ejecutable : %DEPLOY%\AppOO.exe  (%EXE_MB% MB)
echo == Version    : v%APP_VERSION%  (%APP_DATE%)
echo == Log        : %LOGFILE%
echo ======================================================
echo.

:: set /p DO_TAG=Crear git tag v%APP_VERSION% y push? (s/n):
:: if /i "%DO_TAG%"=="s" (
::     git tag -a "v%APP_VERSION%" -m "v%APP_VERSION% -- %APP_DATE%"
::     if %ERRORLEVEL% neq 0 (
::         echo AVISO: git tag fallo. Puede que el tag ya exista.
::     ) else (
::         git push
::         git push --tags
::         echo Tag v%APP_VERSION% publicado.
::     )
:: )

cd /d "%DEPLOY%"
pause
exit /b 0

:error
echo.
echo BUILD FALLIDO - revisa el log: %LOGFILE%
cd /d "%~dp0"
pause
exit /b 1
