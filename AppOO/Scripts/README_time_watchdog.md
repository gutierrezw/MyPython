# Time Watchdog — sincronización de reloj para trading

## Por qué existe

Medición del 2026-08-27 contra tres servidores NTP independientes (Google
`216.239.35.0`, Cloudflare `162.159.200.1`, NIST `129.6.15.28`) — los tres
coinciden dentro de 5 ms, así que el offset es real y no jitter de red:

| Hora     | Offset      | Δ vs anterior      |
|----------|-------------|--------------------|
| 06:06:26 | −0.1645 s   | —                  |
| 06:08:19 | −0.2424 s   | −78 ms en 113 s    |
| 06:09:59 | −0.3118 s   | −69 ms en 100 s    |
| 06:10:24 | −0.3245 s   | —                  |

**Deriva sostenida ≈ 690 ppm ≈ 59 segundos/día.** Un PC sano deriva 10–30 ppm.

### Por qué tunear W32Time nunca alcanzó

La configuración ya estaba bien afinada de intentos anteriores
(`MinPollInterval = MaxPollInterval = 6` → sondeo cada 64 s, `SpecialPollInterval = 64`,
dos servidores buenos). El problema es otro: **W32Time corrige por *slew*
(acelerar/frenar el reloj), y su tasa máxima de slew ronda los 500 ppm. Con 690 ppm
de deriva el servicio no puede alcanzar el error ni aunque sondee cada 64 segundos.**
Por eso el reloj se va aunque todo "esté configurado".

Evidencia adicional en el registro de eventos:

- **Evento 134 (25/8 06:50:47)** — falla de DNS para *ambos* servidores al arrancar:
  `Host desconocido (0x80072AF9)`. W32Time entra en backoff de 15 min que **se duplica
  en cada reintento** (`ResolvePeerBackoffMinutes = 15`) → tras un arranque o un corte de
  internet la máquina puede quedar horas sin fuente de hora.
- **`SynchronizeTime` (tarea nativa de Windows)** — último resultado `1056`
  (`ERROR_SERVICE_ALREADY_RUNNING`), y es **semanal**. Inútil a 59 s/día.
- **`VMICTimeProvider` habilitado** en hardware que no es invitado Hyper-V: arranca y se
  detiene en loop (evento 158, 4 veces el 25/8). Ruido, y un proveedor compitiendo de más.

### Impacto en trading

Binance rechaza toda request firmada cuyo `timestamp` caiga fuera de `recvWindow`
(error `-1021 INVALID_TIMESTAMP`). En este repo `recvWindow` va entre 5000 y 8000 ms
(`Class_ApiBinnace.py:419`, `Class_customer.py:3137`, `DashMain.py:1382`).

A 690 ppm: **~1 segundo de deriva cada 24 minutos → el recvWindow se cruza en 1.5–2 horas**
desde la última sincronización buena. De ahí que las operaciones se corten por completo.

---

## Paso 1 — Endurecer la configuración de W32Time (una sola vez, como admin)

Abrí una PowerShell **como administrador** y pegá el bloque completo:

```powershell
# 1a. Peers con IPs literales primero: si el DNS falla, igual hay fuente de hora.
w32tm /config /update /syncfromflags:manual /manualpeerlist:"216.239.35.0,0x1 162.159.200.1,0x1 129.6.15.28,0x1 time.google.com,0x1 time.cloudflare.com,0x1"

$np = 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient'
$cf = 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\Config'

# 1b. Backoff de DNS: 15 min que se duplican -> 2 min, tope 3 reintentos.
Set-ItemProperty $np -Name ResolvePeerBackoffMinutes  -Value 2 -Type DWord
Set-ItemProperty $np -Name ResolvePeerBackoffMaxTimes -Value 3 -Type DWord

# 1c. Corregir SIEMPRE por salto, nunca por slew. A 690 ppm el slew no alcanza.
Set-ItemProperty $cf -Name MaxAllowedPhaseOffset -Value 0 -Type DWord

# 1d. Apagar el proveedor Hyper-V, que no aplica en esta máquina.
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\VMICTimeProvider' -Name Enabled -Value 0 -Type DWord

# 1e. Arranque retrasado: evita la carrera contra el stack de red que dispara el evento 134.
Set-Service W32Time -StartupType AutomaticDelayedStart

Restart-Service W32Time -Force
Start-Sleep 5
w32tm /resync /rediscover
w32tm /query /status
```

`MaxAllowedPhaseOffset = 0` (paso 1c) es la clave: obliga a W32Time a **saltar** el reloj
a la hora correcta en vez de intentar alcanzarla acelerándolo.

## Paso 2 — Registrar el watchdog (una sola vez, como admin)

La definición vive en `Scripts\AppOO-TimeWatchdog.xml`. Corre como `NT AUTHORITY\SYSTEM`
(`S-1-5-18`) porque `w32tm /resync` exige elevación.

```powershell
Register-ScheduledTask -TaskName "AppOO-TimeWatchdog" -Force `
    -Xml (Get-Content "C:\Users\InversionesWildaga\Documents\MyPython\AppOO\Scripts\AppOO-TimeWatchdog.xml" -Raw)
```

### Por qué XML y no los cmdlets `New-ScheduledTask*`

Porque **"repetir indefinidamente" no se puede expresar con los cmdlets.** En el schema del
Task Scheduler eso se declara **omitiendo** `<Duration>` dentro de `<Repetition>`, y los
cmdlets no tienen forma de omitir ese parámetro.

El camino intuitivo — `-RepetitionDuration ([TimeSpan]::MaxValue)` — falla al registrar:

```text
Register-ScheduledTask : El archivo XML de tarea contiene un valor con formato
incorrecto o que está fuera de intervalo. (10,42):Duration:P99999999DT23H59M59S
```

`[TimeSpan]::MaxValue` se serializa como `P99999999DT23H59M59S`, que el schema rechaza por
fuera de rango. No hay valor "suficientemente grande" que funcione: la ausencia del
elemento es semánticamente distinta de cualquier duración.

Los dos disparadores del XML:

| Disparador     | Cuándo                                                  |
|----------------|---------------------------------------------------------|
| `TimeTrigger`  | Cada 10 min, indefinidamente (`PT10M` sin `<Duration>`) |
| `BootTrigger`  | Al arrancar, con 2 min de gracia (`PT2M`) para la red   |

Cada 10 min porque a 690 ppm el offset entre corridas no supera ~0.42 s.

Si editás el XML, ojo con dos cosas: **no** agregar declaración `<?xml ... ?>` (choca con la
codificación al pasarlo como string a `-Xml`), y **no** reordenar los hijos de `<Settings>`
— el orden es el que exporta Windows y el schema lo valida.

## Paso 3 — Verificar

```powershell
& schtasks.exe /Run /TN "AppOO-TimeWatchdog"
Start-Sleep -Seconds 20
Get-ScheduledTaskInfo -TaskName "AppOO-TimeWatchdog" | Select-Object LastRunTime, LastTaskResult, NextRunTime
& cmd /c "type C:\Users\InversionesWildaga\Documents\deploy\tmp\time_watchdog.csv"
```

`LastTaskResult` debe dar `0`. Si da `267011` (`0x00041303` = `SCHED_S_TASK_HAS_NOT_RUN`)
con `LastRunTime` en `30/11/1999`, la tarea está registrada pero nunca corrió — no es un
fallo, es el valor centinela.

El `&` inicial no es decorativo: la consola de esta máquina se come el primer carácter al
pegar. Con `& comando` el texto sigue siendo válido tanto si el `&` sobrevive como si no;
con `Start-ScheduledTask` a secas queda `tart-ScheduledTask` y falla.

### Resultado observado — 2026-08-27

Primera corrida real, disparada por el propio `TimeTrigger`:

```text
fecha;offset_antes;fuentes;accion;offset_despues;resultado
2026-08-27 07:00:01;-0.0469954;3;OK;-0.0469954;dentro de umbral 0.25 s
```

**47 ms, no los ~400 ms que este documento anticipaba.** La diferencia importa, así que
queda la cuenta:

| Magnitud                          | Valor                     |
|-----------------------------------|---------------------------|
| Deriva del hardware               | 690 ppm = 0.69 ms/s       |
| Intervalo de sondeo (Paso 1c)     | 64 s                      |
| Error acumulado entre sondeos     | 0.69 x 64 = **44 ms**     |
| Medido                            | **47 ms**                 |

La deriva no cambió. Lo que cambió es que con `MaxAllowedPhaseOffset = 0` el W32Time
**corrige por salto cada 64 segundos** en vez de intentar frenar el reloj: el error sube
hasta ~44 ms, salta a cero y vuelve a empezar. Un diente de sierra de 44 ms de amplitud,
no una rampa.

Contra el `recvWindow` de Binance (5000-8000 ms) eso es 0.6% del presupuesto.

### Seguimiento de la deriva

El CSV (`fecha;offset_antes;fuentes;accion;offset_despues;resultado`) es el registro
histórico de la deriva. Sirve para dos cosas: confirmar que el watchdog está haciendo su
trabajo, y detectar si la deriva empeora.

```powershell
Import-Csv C:\Users\InversionesWildaga\Documents\deploy\tmp\time_watchdog.csv -Delimiter ';' |
    Select-Object -Last 20 | Format-Table -AutoSize
```

Acciones posibles: `OK` (dentro de umbral), `RESYNC` (corrigió), `SIN_RED`
(ningún servidor NTP respondió — no es un fallo del reloj).

El CSV se escribe **sin BOM**, vía `System.IO.File` con `UTF8Encoding($false)`. No es
cosmética: `Out-File -Encoding utf8` en PowerShell 5.1 siempre antepone el BOM, y eso
convierte el nombre de la primera columna en `<BOM>fecha`, con lo que `Import-Csv` deja de
poder seleccionar `fecha`. Si tenés un CSV viejo con BOM, borralo y dejá que el script lo
recree con la cabecera limpia:

```powershell
Remove-Item C:\Users\InversionesWildaga\Documents\deploy\tmp\time_watchdog.csv -ErrorAction SilentlyContinue
& schtasks.exe /Run /TN "AppOO-TimeWatchdog"
```

### Dónde se escribe el CSV

En `Documents/deploy/tmp/`, el mismo directorio donde la app deja `agents_schedule.json`
y el resto del estado de runtime. **Un solo lugar para el estado, no uno por proceso**:
si cada componente elige su propia carpeta, no hay forma de saber qué escribe qué.

Ese directorio está en `.gitignore`, así que el CSV no ensucia el repo.

`APPOO_TMP` tiene prioridad sobre el default, igual que en `define_FileCache()`
(`Modulos_Utilitarios.py`). Con una salvedad: **la tarea corre como SYSTEM, que solo ve
variables de ambito Machine** — una `APPOO_TMP` de usuario la app la respeta y el watchdog
no, y el log se partiría en dos lugares sin aviso. Hoy no está definida en ningún ambito.

Verificado que SYSTEM tiene `FullControl` sobre ese directorio; si no lo tuviera, el
script fallaría en silencio y `LastTaskResult` seguiría dando `0`.

### Parámetros

| Parámetro       | Default                                                              | Para qué                                              |
|-----------------|----------------------------------------------------------------------|-------------------------------------------------------|
| `-UmbralSeg`    | `0.25`                                                               | Offset en segundos a partir del cual fuerza resync    |
| `-Muestras`     | `4`                                                                  | Muestras NTP por servidor (se toma la mediana)        |
| `-LogPath`      | `C:\Users\InversionesWildaga\Documents\deploy\tmp\time_watchdog.csv` | Destino del CSV                                       |
| `-Servidores`   | 3 IPs literales                                                      | IPs literales, no hostnames: inmune a fallas de DNS   |

---

## Lo que este watchdog NO resuelve

**El watchdog acota la ventana de daño, no la elimina.** Si la máquina queda sin
internet la deriva corre libre a 59 s/día sin nada que la frene, y si el servicio W32Time
se detiene, otro tanto.

> **Corrección 2026-08-27.** Este párrafo decía que "entre dos corridas el reloj se va
> hasta ~0.42 s". Esa cuenta suponía que el watchdog era el único corrector, y la medición
> de las 07:00 mostró que no lo es: con el Paso 1 aplicado, W32Time corrige por salto cada
> 64 s y el error nunca pasa de ~44 ms. **Eso cambia el rol del watchdog**: no es quien
> compensa la deriva, es la red de seguridad para cuando W32Time falle — DNS caído al
> arrancar, internet cortado, servicio detenido. Con un umbral de 0.25 s contra un pico
> esperado de 44 ms hay 5x de margen, así que **una fila `RESYNC` en el CSV significa un
> fallo real, no ruido normal**. El umbral se deja donde está justamente por eso.

Por eso la app dejó de depender del reloj del SO (capa A, ya implementada), y queda
abierta la causa de raíz en el hardware (capa B).

### A. La app ya no depende del reloj del SO — `BinanceTime` (implementado)

`Class_ApiBinnace.BinanceTime` mantiene un offset contra `GET /api/v3/time` y lo suma al
timestamp de **toda** request firmada. Aunque Windows esté 30 s corrido, las órdenes se
firman con la hora del exchange.

- **Offset por `base_url`** — PRODUCTION y TESTNET son servidores distintos, no comparten reloj.
- **Round-trip descontado** — `offset = serverTime − (t0 + t1) / 2`, no `serverTime − t0`.
- **Refresco cada 300 s** (`REFRESCO_SEG`), perezoso: se remide al firmar, no por agente.
  A 690 ppm eso son ~0.21 s de deriva acumulada entre mediciones, contra un `recvWindow`
  de 5000–8000 ms.
- **Nunca lanza** — si la medición falla (sin internet) se conserva el último offset
  conocido, que sigue siendo mejor que el reloj local.
- **Backoff de 30 s ante fallo** (`REINTENTO_SEG`) — sin esto, estando sin red **cada firma**
  reintentaría la medición y pagaría el timeout completo de 5 s.
- **Autocorrección ante `-1021`** — `handle_binance_exceptions` invalida el offset al ver
  un `INVALID_TIMESTAMP`, así la firma siguiente remide en vez de repetir el error.
- **Thread-safe** — `threading.Lock`, porque los agentes firman desde hilos distintos. La
  medición HTTP se hace **fuera** del lock: bloquear 320 ms a todos los hilos que firman
  sale más caro que la medición redundante que dos hilos puedan hacer a la vez.

#### Costo medido

`binance_time` es un singleton de módulo: **todos** los clientes lo comparten, así que el
refresco es uno por `base_url` cada 300 s, no uno por instancia. Como mucho hay 2
`base_url` en juego (PRODUCTION + TESTNET).

| Concepto                                       | Medido                                       |
|------------------------------------------------|----------------------------------------------|
| Firma con offset cacheado (99.9% de los casos) | **0.76 µs** — aritmética, sin red            |
| Refresco (1 cada 300 s por `base_url`)         | **321 ms**                                   |
| Requests a Binance                             | 12/h por `base_url` = 0.2/min                |
| Presupuesto de rate limit consumido            | ~0.003% (`/api/v3/time` pesa 1 de 6000/min)  |
| Tráfico                                        | ~300 KB/día (respuesta de 28 bytes)          |
| 1000 firmas estando sin red                    | **0.6 ms** total, gracias al backoff         |

La `requests.Session` importa: sin reuso de conexión el refresco medía **807 ms**, porque
cada uno rehacía el handshake TLS. Con Session baja a 321 ms, que ya es el RTT puro hasta
Binance desde acá.

Puntos de firma cubiertos, todos vía `binance_time.timestamp_ms(base_url)`:

| Sitio                                    | Cubre                                                        |
|------------------------------------------|--------------------------------------------------------------|
| `BinanceSpot.signature_spot_message`     | REST manual: órdenes, cancelaciones, préstamos, earn         |
| `BinanceSpot.sign_request` (override)    | Todo método heredado de `Spot`: trades, open orders, margin  |
| `BinanceClient.signature_message`        | WebSocket API: `session.logon`, `account.status`             |
| `BinanceClient._sign_rest`               | Binance Pay (`/sapi/v1/pay/transactions`)                    |
| `BinanceWSApiClient.login` / `my_Orders` | Autenticación y consulta de órdenes por WS                   |

El override de `sign_request` replica el cuerpo de `binance.api.API.sign_request` cambiando
solo la fuente del timestamp. Está acoplado a esa firma —
`(self, http_method, url_path, payload=None)`, verificada contra la versión instalada, y
ningún call site de la librería usa un cuarto argumento. **Si se actualiza
`binance-connector`, revisar que la firma siga igual.**

`my_allOrders` conserva `int(time.time() * 1000)` a propósito: arma ventanas de días para
consultas históricas, no firma nada.

### B. Por qué el hardware deriva 690 ppm

690 ppm no es un cristal normal envejecido. Causas candidatas, en orden de probabilidad:
pila CMOS agotada, gestión de energía / C-states afectando el temporizador, o un HPET
defectuoso (se fuerza con `bcdedit /set useplatformclock true`). Sin resolver esto el
watchdog es permanente, no transitorio.

---

## Estado — en observación

Ambas capas están cerradas y verificadas en vivo. Lo que sigue abierto es la **causa
física** de los 690 ppm (sección B): hoy está compensada, no resuelta.

Seguimiento en `30-Gestion/BACKLOG.md` ítem **#84**. Criterio de revisión a 1-2 semanas:

- **CSV todo `OK`** → la capa 1 se sostiene sola; la causa física queda como deuda
  conocida y el watchdog como seguro permanente.
- **`RESYNC` recurrentes** → W32Time está fallando de verdad; escalar al hardware.
