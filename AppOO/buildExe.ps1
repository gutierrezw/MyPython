#Requires -Version 5.1
<#
.SYNOPSIS
    Compila AppOO.exe con PyInstaller.
    Equivalente PowerShell de buildExe.bat
#>

Set-Location $PSScriptRoot

$PYENV  = "C:\Users\InversionesWildaga\Documents\MyPython\.venv\Scripts"
$DEPLOY = "C:\Users\InversionesWildaga\Documents\deploy"
$ICON   = "C:\Users\InversionesWildaga\Documents\MyPython\Iconos\Systems\WGM_icon.ico"
$LOGDIR = Join-Path $PSScriptRoot "build_logs"
$LOGFILE = Join-Path $LOGDIR "build.log"

# --- Leer version.py -------------------------------------------------------
$versionContent = if (Test-Path "version.py") { Get-Content "version.py" -Raw } else { "" }
$APP_VERSION = if ($versionContent -match '(?m)^VERSION\s*=\s*"(.+)"')     { $Matches[1] } else { "unknown" }
$APP_DATE    = if ($versionContent -match '(?m)^RELEASE_DATE\s*=\s*"(.+)"') { $Matches[1] } else { "unknown" }

if (-not (Test-Path $LOGDIR)) { New-Item -ItemType Directory -Path $LOGDIR | Out-Null }

Write-Host ""
Write-Host "======================================================"
Write-Host "== AppOO v$APP_VERSION  ($APP_DATE)"
Write-Host "== Log: $LOGFILE"
Write-Host "======================================================"
Write-Host ""

# [1/5] AppOO corriendo? ----------------------------------------------------
Write-Host "[1/5] Verificando procesos..."
$proc = Get-Process -Name "AppOO" -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host ""
    Write-Host "ERROR: AppOO.exe esta corriendo. Cerralo y vuelve a ejecutar."
    exit 1
}
Write-Host "      OK - AppOO.exe no esta en ejecucion."

# [2/5] PyInstaller existe? -------------------------------------------------
Write-Host "[2/5] Verificando entorno virtual..."
$pyinstaller = Join-Path $PYENV "pyinstaller.exe"
if (-not (Test-Path $pyinstaller)) {
    Write-Host ""
    Write-Host "ERROR: PyInstaller no encontrado en: $PYENV"
    exit 1
}
Write-Host "      OK - PyInstaller encontrado."

# [3/5] Directorios deploy --------------------------------------------------
Write-Host "[3/5] Preparando directorios deploy..."
foreach ($dir in @($DEPLOY, "$DEPLOY\tmp", "$DEPLOY\logs", "$DEPLOY\setup")) {
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
}
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
Write-Host "      OK"

# [4/5] PyInstaller ---------------------------------------------------------
Write-Host "[4/5] Ejecutando PyInstaller (ver log para detalle)..."
Write-Host ""

$iconFlag = if (Test-Path $ICON) { @("--icon", $ICON) } else { @() }

$pyArgs = @(
    "--noconfirm", "--onefile", "--windowed"
) + $iconFlag + @(
    "--paths", "."
    "--paths", "AppValuations"
    "--paths", "ConvergIA"
    "--name", "AppOO"
    "--distpath", $DEPLOY
    "--add-data", "profiles;profiles"
    "--hidden-import", "pymysql"
    "--hidden-import", "schedule"
    "--hidden-import", "PIL._tkinter_finder"
    "--hidden-import", "ta"
    "--hidden-import", "yfinance"
    "--hidden-import", "syncio"
    "--hidden-import", "edgar_13f"
    "--hidden-import", "Class_debugging"
    "--hidden-import", "Class_DataFrame"
    "--hidden-import", "Class_ApiIBrks"
    "--hidden-import", "Class_ApiBinnace"
    "--hidden-import", "Class_gestion"
    "--hidden-import", "Class_FondosInversion"
    "--hidden-import", "Class_Screener"
    "--hidden-import", "Class_DashBot"
    "--hidden-import", "Class_IA_modelos"
    "--hidden-import", "Class_SystemStatus"
    "--hidden-import", "Class_BotCryptoUI"
    "--hidden-import", "Class_BrowserBridge"
    "--hidden-import", "Class_Finance"
    "--hidden-import", "Class_customer"
    "--hidden-import", "Modulos_Mysql"
    "--hidden-import", "Modulos_Utilitarios"
    "--hidden-import", "Modulos_python"
    "--hidden-import", "ConvergIA.ThemeMapper"
    "--hidden-import", "feedparser"
    "--hidden-import", "anthropic"
    "--collect-all", "binance"
    "--collect-all", "tkinter"
    "DashMain.py"
)

$logStdout = Join-Path $LOGDIR "build_stdout.log"
$logStderr = Join-Path $LOGDIR "build_stderr.log"

$proc = Start-Process -FilePath $pyinstaller `
    -ArgumentList $pyArgs `
    -Wait -PassThru -NoNewWindow `
    -RedirectStandardOutput $logStdout `
    -RedirectStandardError  $logStderr

# Unificar en build.log
Add-Content -Path $LOGFILE -Value (Get-Content $logStdout -Raw -ErrorAction SilentlyContinue)
Add-Content -Path $LOGFILE -Value (Get-Content $logStderr -Raw -ErrorAction SilentlyContinue)

if ($proc.ExitCode -ne 0) {
    Write-Host ""
    Write-Host "BUILD FALLIDO - revisa el log: $LOGFILE"
    exit 1
}

# [5/5] Verificar exe -------------------------------------------------------
Write-Host "[5/5] Verificando ejecutable generado..."
$exePath = Join-Path $DEPLOY "AppOO.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "ERROR: AppOO.exe no encontrado en $DEPLOY"
    exit 1
}
$exeMB = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
Write-Host "      OK - AppOO.exe  $exeMB MB"

# Copiar profiles -----------------------------------------------------------
Copy-Item -Path "profiles" -Destination "$DEPLOY\profiles" -Recurse -Force
Copy-Item -Path "profiles" -Destination "$DEPLOY\setup\profiles" -Recurse -Force

# Resultado -----------------------------------------------------------------
Write-Host ""
Write-Host "======================================================"
Write-Host "== BUILD EXITOSO"
Write-Host "== Ejecutable : $exePath  ($exeMB MB)"
Write-Host "== Version    : v$APP_VERSION  ($APP_DATE)"
Write-Host "== Log        : $LOGFILE"
Write-Host "======================================================"
Write-Host ""

Set-Location $DEPLOY
Read-Host "Presiona Enter para cerrar"
