@echo off
cd /d "%~dp0.."
echo ======================================================
echo == EXPORTAR PAQUETE HIJO                            ==
echo ======================================================

set DEPLOY=%~dp0..\deploy
set DEST=%DEPLOY%\AppOO_hijo
set SETUP=%DEPLOY%\setup_hijo

:: ── 1. Empaquetar ejecutable ──────────────────────────────────────────────────
echo.
echo [1/4] Copiando ejecutable a AppOO_hijo...
rmdir /s /q "%DEST%" 2>nul
xcopy /s /e /i /y "%DEPLOY%\AppOO" "%DEST%" >nul

echo Configurando perfil hijo como main...
copy /y "%DEST%\profiles\hijo.json" "%DEST%\profiles\main.json" >nul
del /f /q "%DEST%\profiles\hijo.json" 2>nul

:: ── 2. Preparar carpeta setup ─────────────────────────────────────────────────
echo.
echo [2/4] Preparando carpeta setup_hijo...
if exist "%SETUP%" rmdir /s /q "%SETUP%"
mkdir "%SETUP%"

copy /y "%~dp0README.txt"                  "%SETUP%\" >nul
copy /y "%~dp0config_import.json.template" "%SETUP%\" >nul
copy /y "%~dp0run_binance_import.py"       "%SETUP%\" >nul

:: ── 3. Exportar schema BD ────────────────────────────────────────────────────
set USER=root
set HOST=localhost
set DB=bdinv
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.0\bin

echo.
echo [3/4] Exportando estructura BD (tablas vacias)...
"%MYSQL_BIN%\mysqldump" -u %USER% -p --no-data --skip-triggers %DB% ^
    booktrading ^
    inversion ^
    oportunidadesbuysell ^
    order_trader ^
    diaria_performance ^
    performa_inversion ^
    otros_activos ^
    extractos ^
    sesion ^
    trazaplan ^
    fin_accounts ^
    fin_exchange_rates ^
    fin_statement_imports ^
    fin_transactions ^
    market ^
    funds ^
    fund_filings ^
    fund_holdings ^
    > "%SETUP%\hijo_estructura.sql"

echo.
echo [4/4] Exportando datos de referencia...
"%MYSQL_BIN%\mysqldump" -u %USER% -p --no-create-info --skip-triggers %DB% ^
    sys_objeto ^
    split ^
    diaria_cnv ^
    estrategia ^
    plan ^
    variablesplan ^
    modelos_ia ^
    fin_banks ^
    fin_categories ^
    fin_import_rules ^
    > "%SETUP%\hijo_datos.sql"

echo.
echo ======================================================
echo == LISTO                                            ==
echo ==                                                  ==
echo == App:   %DEST%\AppOO.exe
echo == Setup: %SETUP%\
echo ==        - README.txt
echo ==        - config_import.json.template
echo ==        - run_binance_import.py
echo ==        - hijo_estructura.sql
echo ==        - hijo_datos.sql
echo ==                                                  ==
echo == Pasar al hijo las dos carpetas:                  ==
echo ==   AppOO_hijo\  +  setup_hijo\                   ==
echo ======================================================

pause
