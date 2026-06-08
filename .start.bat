@echo off
:: ------------------------------------------------------------
:: script: Inicio de IGateway IBkrs
:: author: Wilmer Gutierrez
:: date..: 17, Ago, 2025
:: ------------------------------------------------------------

echo ------------------------------------------------------------
echo Iniciando IGateway IBkrs
echo ------------------------------------------------------------

:: Cerrar procesos en puerto 6000
echo Cerrando procesos en puerto 5501...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5501') do (
    taskkill /PID %%a /F 2>nul
)
timeout /t 2 >nul
echo Listo!
echo ------------------------------------------------------------

set CONFIG_PATH=C:\Users\InversionesWildaga\Documents\MyPython\IBGateway\root\
set DIST_PATH=C:\Users\InversionesWildaga\Documents\MyPython\IBGateway\dist\
set BUILD_PATH=C:\Users\InversionesWildaga\Documents\MyPython\IBGateway\build\
set VERTX_PATH=C:\Users\InversionesWildaga\Documents\deploy\.vertx\
set JAVA_PATH=C:\Program Files\Java\jdk\bin

echo Config path  : %CONFIG_PATH%
echo Dist path    : %DIST_PATH%
echo Build path   : %BUILD_PATH%
echo Vertx path   : %VERTX_PATH%
echo ------------------------------------------------------------

echo Limpiando cache Vert.x...
dir "%VERTX_PATH%"
if exist "%VERTX_PATH%" rmdir /S /Q "%VERTX_PATH%"
echo Listo!
echo ------------------------------------------------------------
set RUNTIME_PATH="%CONFIG_PATH%;%DIST_PATH%ibgroup.web.core.iblink.router.clientportal.gw.jar;%BUILD_PATH%lib\runtime\*"

echo "running %verticle% "
echo "runtime path : %RUNTIME_PATH%"

:: Gateway crea su propia subcarpeta logs\ dentro del working dir
if not exist "C:\Users\InversionesWildaga\Documents\deploy" mkdir "C:\Users\InversionesWildaga\Documents\deploy"
cd /d "C:\Users\InversionesWildaga\Documents\deploy"

java -server -Dvertx.disableDnsResolver=true -Djava.net.preferIPv4Stack=true -Dvertx.logger-delegate-factory-class-name=io.vertx.core.logging.SLF4JLogDelegateFactory -Dnologback.statusListenerClass=ch.qos.logback.core.status.OnConsoleStatusListener -Dnolog4j.debug=true -Dnolog4j2.debug=true -classpath %RUNTIME_PATH% ibgroup.web.core.clientportal.gw.GatewayStart
rem optional arguments
rem -conf conf.beta.yaml --nossl

:END