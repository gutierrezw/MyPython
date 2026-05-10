@echo off
:: Exporta schema de bdinv para perfil hijo
:: Uso: export_hijo.bat
:: Resultado: hijo_schema.sql (tablas vacias) + hijo_data.sql (tablas de referencia)

set USER=root
set HOST=localhost
set DB=bdinv
set OUT_DIR=%~dp0

echo Exportando estructura (tablas vacias)...
mysqldump -u %USER% -p --no-data --skip-triggers %DB% ^
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
    > "%OUT_DIR%hijo_estructura.sql"

echo Exportando datos de referencia...
mysqldump -u %USER% -p --no-create-info --skip-triggers %DB% ^
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
    > "%OUT_DIR%hijo_datos.sql"

echo.
echo Listo. Archivos generados:
echo   %OUT_DIR%hijo_estructura.sql
echo   %OUT_DIR%hijo_datos.sql
echo.
echo En la maquina del hijo ejecutar en orden:
echo   1. mysql -u root -p -e "CREATE DATABASE bdinv CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
echo   2. mysql -u root -p bdinv < hijo_estructura.sql
echo   3. mysql -u root -p bdinv < hijo_datos.sql
echo.
pause
