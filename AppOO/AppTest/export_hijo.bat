@echo off
cd /d "%~dp0.."
echo ======================================================
echo == EXPORTAR PAQUETE HIJO                            ==
echo ======================================================

set DEPLOY=%~dp0..\deploy
set DEST=%DEPLOY%\AppOO_hijo

:: ── 1. Empaquetar ejecutable ──────────────────────────────────────────────────
echo.
echo [1/3] Copiando ejecutable a AppOO_hijo...
rmdir /s /q "%DEST%" 2>nul
xcopy /s /e /i /y "%DEPLOY%\AppOO" "%DEST%" >nul

echo Configurando perfil hijo como main...
copy /y "%DEST%\profiles\hijo.json" "%DEST%\profiles\main.json" >nul
del /f /q "%DEST%\profiles\hijo.json" 2>nul

:: ── 2. Exportar schema BD ────────────────────────────────────────────────────
set USER=root
set HOST=localhost
set DB=bdinv
set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.0\bin

echo.
echo [2/3] Exportando estructura BD (tablas vacias)...
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
    > "%~dp0hijo_estructura.sql"

echo.
echo [3/3] Exportando datos de referencia...
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
    > "%~dp0hijo_datos.sql"

echo.
echo ======================================================
echo == LISTO                                            ==
echo == Ejecutable: %DEST%\AppOO.exe
echo == BD:         %~dp0hijo_estructura.sql
echo ==             %~dp0hijo_datos.sql
echo.
echo En la maquina del hijo ejecutar en orden:
echo   1. mysql -u root -p -e "CREATE DATABASE bdinv CHARACTER SET utf8mb4;"
echo   2. mysql -u root -p bdinv ^< hijo_estructura.sql
echo   3. mysql -u root -p bdinv ^< hijo_datos.sql
echo ======================================================

pause
