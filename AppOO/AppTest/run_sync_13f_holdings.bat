@echo off
cd /d "c:\Users\InversionesWildaga\Documents\MyPython\AppOO"

set LOGFILE=AppTest\run_sync_13f_holdings.log
echo. > %LOGFILE%
echo ======================================================== >> %LOGFILE%
echo Inicio: %DATE% %TIME% >> %LOGFILE%
echo ======================================================== >> %LOGFILE%

python AppTest\run_sync_13f_holdings.py >> %LOGFILE% 2>&1

echo. >> %LOGFILE%
echo Fin: %DATE% %TIME% >> %LOGFILE%
echo ======================================================== >> %LOGFILE%
