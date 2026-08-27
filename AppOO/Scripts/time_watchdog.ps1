<#
    time_watchdog.ps1 — vigila la deriva del reloj y fuerza resincronizacion.

    Motivo: esta maquina deriva ~690 ppm (~59 s/dia), muy por encima de lo que
    W32Time puede corregir por slew. Sin resync forzado periodico el reloj cruza
    el recvWindow de Binance en ~1.5 h y las ordenes firmadas empiezan a fallar
    con -1021 INVALID_TIMESTAMP.

    Corre como NT AUTHORITY\SYSTEM desde el Programador de tareas (/resync exige
    elevacion). Ver Scripts/README_time_watchdog.md para el registro de la tarea.
#>
[CmdletBinding()]
param(
    [double]   $UmbralSeg  = 0.25,
    [int]      $Muestras   = 4,
    # tmp de la app: mismo directorio que agents_schedule.json y demas estado runtime.
    # APPOO_TMP tiene prioridad, igual que define_FileCache() en Modulos_Utilitarios.py.
    # Ojo: la tarea corre como SYSTEM, que solo ve variables de ambito Machine.
    [string]   $LogPath    = $(if ($env:APPOO_TMP) { Join-Path $env:APPOO_TMP "time_watchdog.csv" }
                              else { "C:\Users\InversionesWildaga\Documents\deploy\tmp\time_watchdog.csv" }),
    [string[]] $Servidores = @("216.239.35.0", "162.159.200.1", "129.6.15.28")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


function Get-OffsetServidor {
    # Devuelve la mediana de offsets contra un servidor, o $null si no responde.
    param([string] $Servidor, [int] $Samples)

    $salida = & w32tm /stripchart /computer:$Servidor /samples:$Samples /dataonly 2>&1
    $vals = @()
    foreach ($linea in $salida) {
        if ("$linea" -match ',\s*([+-]?\d+[.,]\d+)s') {
            $vals += [double](($matches[1]) -replace ',', '.')
        }
    }
    if ($vals.Count -eq 0) { return $null }
    $ord = $vals | Sort-Object
    return $ord[[int]([math]::Floor($ord.Count / 2))]
}

function Get-OffsetConsenso {
    # Consulta todos los servidores y devuelve la mediana entre los que responden.
    param([string[]] $Lista, [int] $Samples)

    $medidas = @()
    foreach ($srv in $Lista) {
        try {
            $o = Get-OffsetServidor -Servidor $srv -Samples $Samples
            if ($null -ne $o) { $medidas += $o }
        } catch {
            # servidor caido o sin ruta: se ignora, el consenso usa los que quedan
        }
    }
    if ($medidas.Count -eq 0) { return $null }
    $ord = $medidas | Sort-Object
    return [pscustomobject]@{
        Offset = $ord[[int]([math]::Floor($ord.Count / 2))]
        Fuentes = $medidas.Count
    }
}

function Write-Fila {
    # Append CSV con cabecera automatica la primera vez.
    param([string] $Ruta, [hashtable] $Datos)

    $dir = Split-Path -Parent $Ruta
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    # .NET resuelve rutas relativas contra su propio cwd, no el de PowerShell.
    $Ruta = Join-Path (Resolve-Path $dir) (Split-Path -Leaf $Ruta)

    # UTF8Encoding($false) = sin BOM. Out-File -Encoding utf8 en PS 5.1 siempre lo
    # antepone y ensucia el nombre de la primera columna al parsear el CSV.
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $cols = @("fecha", "offset_antes", "fuentes", "accion", "offset_despues", "resultado")
    if (-not (Test-Path $Ruta)) {
        [System.IO.File]::WriteAllText($Ruta, ($cols -join ";") + [Environment]::NewLine, $utf8)
    }
    $fila = ($cols | ForEach-Object { "$($Datos[$_])" }) -join ";"
    [System.IO.File]::AppendAllText($Ruta, $fila + [Environment]::NewLine, $utf8)
}


$fecha = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
$antes = Get-OffsetConsenso -Lista $Servidores -Samples $Muestras

if ($null -eq $antes) {
    Write-Fila -Ruta $LogPath -Datos @{
        fecha = $fecha; offset_antes = ""; fuentes = 0
        accion = "SIN_RED"; offset_despues = ""; resultado = "ningun servidor NTP respondio"
    }
    Write-Output "SIN_RED - ningun servidor NTP respondio"
    exit 0
}

if ([math]::Abs($antes.Offset) -le $UmbralSeg) {
    Write-Fila -Ruta $LogPath -Datos @{
        fecha = $fecha; offset_antes = $antes.Offset; fuentes = $antes.Fuentes
        accion = "OK"; offset_despues = $antes.Offset; resultado = "dentro de umbral $UmbralSeg s"
    }
    Write-Output ("OK - offset {0:N4}s dentro de umbral {1}s" -f $antes.Offset, $UmbralSeg)
    exit 0
}

# Fuera de umbral: reiniciar el servicio limpia el backoff de DNS/peer y luego forzar resync.
$resultado = ""
try {
    & w32tm /resync /rediscover 2>&1 | Out-String -OutVariable r | Out-Null
    $resultado = ($r -replace '\s+', ' ').Trim()
    if ($LASTEXITCODE -ne 0) {
        Restart-Service W32Time -Force
        Start-Sleep -Seconds 5
        & w32tm /resync /rediscover 2>&1 | Out-String -OutVariable r2 | Out-Null
        $resultado = "reinicio W32Time + " + ($r2 -replace '\s+', ' ').Trim()
    }
} catch {
    $resultado = "EXCEPCION: $($_.Exception.Message)"
}

Start-Sleep -Seconds 3
$despues = Get-OffsetConsenso -Lista $Servidores -Samples $Muestras

Write-Fila -Ruta $LogPath -Datos @{
    fecha = $fecha; offset_antes = $antes.Offset; fuentes = $antes.Fuentes
    accion = "RESYNC"
    offset_despues = $(if ($null -ne $despues) { $despues.Offset } else { "" })
    resultado = $resultado
}
Write-Output ("RESYNC - antes {0:N4}s -> despues {1}" -f $antes.Offset,
    $(if ($null -ne $despues) { "{0:N4}s" -f $despues.Offset } else { "sin medida" }))
