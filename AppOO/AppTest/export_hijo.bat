@echo off
cd /d "%~dp0.."
echo.
echo [1/4] Copiando ejecutable a AppOO_hijo...
set DEPLOY=%~dp0..\..\deploy
set DEST=%DEPLOY%\AppOO_hijo
set SETUP=%DEPLOY%\setup_hijo
xcopy /e /i /y "%DEPLOY%\AppOO" "%DEST%" >nul
echo Configurando perfil hijo como main...
copy /y "%DEST%\profiles\hijo.json" "%DEST%\profiles\main.json" >nul
if exist "%DEST%\profiles\hijo.json" del "%DEST%\profiles\hijo.json"
echo.
echo [2/4] Preparando carpeta setup_hijo...
if not exist "%SETUP%" mkdir "%SETUP%"
copy /y "%~dp0README.txt" "%SETUP%\" >nul
copy /y "%~dp0config_import.json.template" "%SETUP%\" >nul
copy /y "%~dp0run_binance_import.py" "%SETUP%\" >nul
echo.
set DBUSER=root
set DB=bdinv
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.0\bin
echo [3/4] Exportando estructura BD...
"%MYSQL_BIN%\mysqldump" -u %DBUSER% -p --no-data --skip-triggers %DB% booktrading inversion oportunidadesbuysell order_trader diaria_performance performa_inversion otros_activos extractos sesion trazaplan fin_accounts fin_exchange_rates fin_statement_imports fin_transactions market funds fund_filings fund_holdings > "%SETUP%\hijo_estructura.sql"
echo.
echo [4/4] Exportando datos de referencia...
"%MYSQL_BIN%\mysqldump" -u %DBUSER% -p --no-create-info --skip-triggers %DB% sys_objeto split diaria_cnv estrategia plan variablesplan modelos_ia fin_banks fin_categories fin_import_rules > "%SETUP%\hijo_datos.sql"
echo.
echo Listo!
echo App:   %DEST%\AppOO.exe
echo Setup: %SETUP%
pause
