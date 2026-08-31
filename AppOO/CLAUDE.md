# AppOO — Convenciones específicas del proyecto

## ⚙️ Protocolo Obligatorio

**Al inicio de CADA SESIÓN y cuando hay CONFLICTO de decisión:**
- Leer `FEEDBACK.md` (18 patrones validados) — vive en el directorio de memoria
  (`~/.claude/projects/c--Users-InversionesWildaga-Documents-MyPython/memory/FEEDBACK.md`),
  visible desde el vault como `10-Memoria/FEEDBACK.md`. **No está en la raíz del repo.**
- Consultar si ya existe solución para el problema
- Evitar duplicar enfoques ya resueltos

**Motivo:** Asegurar consistencia sesión a sesión. FEEDBACK.md es fuente de verdad para patrones de trabajo.

---

## Visión de plataforma — principios arquitectónicos

AppOO es una plataforma de automatización de inversiones con visión de evolucionar de herramienta personal a servicio para terceros. La arquitectura debe soportar ese camino sin reescrituras.

### Principios que Claude debe verificar antes de proponer cualquier diseño

1. **Portabilidad**: ¿Este componente corre igual en localhost, en un VPS o en Venezuela con internet inestable? Si no → rediseñar.
2. **Account-first**: Toda lógica y dato debe estar aislado por `account`. Hoy es 1 usuario, mañana pueden ser N clientes.
3. **Resiliencia**: Servicios deben sobrevivir reinicios sin pérdida de estado. Usar `persist=True` en agentes, JSON en `tmp/` para estado crítico.
4. **Broker-agnóstico**: La lógica de negocio no debe acoplarse a IB o Binance directamente. Solo `Class_ApiIBrks` y `Class_ApiBinnace` tocan los brokers. Todo lo demás consume MySQL o DataHub.
5. **Automatización primero**: Si una tarea se hace manualmente más de una vez, debe tener ruta de automatización.
6. **API-first**: Toda funcionalidad nueva debe ser accesible vía API (no solo desde la UI). Habilita terceros, Claude y acceso remoto.

### Lo que NO puede cambiar sin revisión explícita
- IB Gateway corre local (restricción del broker) — no intentar moverlo a cloud sin análisis
- Datos financieros propios nunca en servicios de terceros — MySQL propio siempre
- `account` como parámetro en toda función que toque datos de cartera — sin excepciones

## Screener — columnas scrollables (orden fijo)

El orden de `_COL_DEFS` en `Class_Screener.py` y los valores en `insert_treeview` deben estar **siempre sincronizados** (posición a posición).

Orden acordado (después de las 4 fijas: Symbol, Name, Status, Cart):

| # | Campo DB | Header |
|---|----------|--------|
| 1 | lastPrice | Last |
| 2 | rotacion | Rotación |
| 3 | inst_score | Inst Score |
| 4 | inst_ownership_pct | Inst % |
| 5 | fh_count | **13F Inst** |
| 6 | fh_buy_ratio | 13F Buy% |
| 7 | fh_sell_ratio | 13F Sell% |
| 8 | fh_total_value | 13F Value |
| 9 | volume | Volume |
| 10 | averageVolume | Avg Vol |
| … | … country, sector, industry … | |
| … | grossMargins | Gross M |
| … | ebitdaMargins | EBITDA M |
| … | operatingMargins | **Op M** ← va después de EBITDA M |
| … | inst_top_holder | Top Holder |
| … | website | Website |

**NOTA:** `inst_funds` (Yahoo) eliminado del Screener — datos inconsistentes. Solo usar `fh_count` (EDGAR).

## Nomenclatura homologada (Screener ↔ Consenso)

- `fh_count` → siempre **"13F Inst"** — única fuente de conteo institucional
- `inst_funds` → NO mostrar en UI (datos Yahoo inconsistentes)
- Ambas pantallas deben usar los mismos nombres de columna para los mismos conceptos

## Consenso popup — columnas fijas

`_FIXED_COLS = ("Symbol", "Div", "Nombre", "13F Inst", "Inst %")`

`13F Inst` usa `fh_count` (pipeline EDGAR propio).

## Autonomía del usuario

- **Nunca ejecutar scripts ni procesos largos en background sin que el usuario lo pida.**
- Siempre entregar el comando listo y dejar que el usuario decida cuándo correrlo.
- El usuario quiere mantener control y aprender del proceso.

## Panel Debugging — Class_SystemStatus.py

El tab "Debugging" en `self.debugging` debe ser **siempre interactivo**: el usuario puede cambiar niveles de logger en tiempo real desde la UI sin reiniciar la app.

Patrón implementado en `debugging_system()`:

| Acción | Comportamiento |
|--------|----------------|
| Doble-click en fila | Toggle rápido WARNING ↔ ERROR |
| Clic derecho | Menú completo: DEBUG / INFO / WARNING / ERROR / CRITICAL |
| Botón "Reset All → WARNING" | Regresa todos los loggers a WARNING |

- Colores por nivel: DEBUG=azul, INFO=verde, WARNING=naranja, ERROR=rojo, CRITICAL=rojo oscuro
- Los cambios se aplican a `DataHub.logger[key].setLevel(...)` en tiempo real
- La fuente de verdad es siempre `DataHub.logger` (dict registrado en `Class_debugging.py`)

**Persistencia entre sesiones:**
- Cada cambio de nivel llama `_save_levels()` → escribe `tmp/logger_levels.json` con `write_json_tmp`
- `Debugging.__init__()` llama `_apply_saved_levels()` al final → lee el JSON y sobreescribe defaults
- Si el JSON no existe (primera vez) → `read_json_tmp` devuelve `{}` y se usan los defaults sin error

**Objetivo de uso:** elevar loggers ruidosos a ERROR para que no ensucien el log rotativo; bajar a DEBUG para diagnóstico puntual.

## Patrón para agregar un nuevo agente

Un agente vive en `Class_AgentManager.py` (si es infraestructura/lento) o en `Class_DashBot.py` (si es trading/mercado).

### Checklist — 3 pasos mínimos

**1. Lógica de negocio** → en la clase dueña del dominio (no en el agente).

**2. Método agente** — con `desc` y `nivel` en el decorador para auto-registro:
```python
@wait_rate(86400, persist=True, desc="Descripción corta (intervalo)", nivel=1)
def Agente_NombreNuevo(self):
    try:
        result = self.ClaseDominio.metodo_logica()
        self._log_infra.warning(f"Agente_NombreNuevo: {result}")
    except Exception as e:
        self._log_infra.error(f"Agente_NombreNuevo(): {e}")
```
`desc` + `nivel` → `wait_rate` auto-registra en `AGENTES_SCHEDULE`. **No tocar `Modulos_Utilitarios.py`.**

**3. Si es en AgentManager** → agregar a `register_threads()`:
```python
("Agente_NombreNuevo", self.Agente_NombreNuevo, 300),
```

**4. Logger** (si emite logs propios) → registrar en `Class_debugging.py` junto a los otros loggers.

### Lo que hace `wait_rate` automáticamente
- `persist=True` → sobrevive reinicios (guarda último run en `../tmp/agents_schedule.json`)
- `desc` presente → se auto-registra en `AGENTES_SCHEDULE` al importar el módulo
- Sin `desc` → no aparece en el panel de schedule (invisible)
- `ventana=(desde, hasta)` → restringe la ejecución a esa franja horaria

### Franja horaria: usar `ventana`, nunca una guarda dentro del agente

Si un agente solo debe correr de madrugada, va en el decorador:

```python
@wait_rate(2592000, persist=True, ventana=(0, 6), desc="...", nivel=2)
def Agente_Nocturno(self):
    ...
```

**No** poner `if not (0 <= datetime.now().hour < 6): return` dentro del método. El decorador
marca `last_run` apenas invoca la función, así que un `return` temprano **consume el turno sin
hacer trabajo** y reinicia el reloj del intervalo. Con intervalos largos el agente puede no
correr nunca: el rescate `_overdue` mide `intervalo * 1.5`, umbral inalcanzable si cada intento
devuelve el contador a cero. Corregido 2026-08-22 en los 6 agentes que tenían ese patrón.

`ventana` se evalúa **antes** de llamar a la función y no toca `last_run` — el turno queda
pendiente. `forced` y `_overdue` se saltan la ventana a propósito.

---

## Base de datos — MySQL 8.x (schema: bdinv)

### Configuración optimizada (my.ini — aplicada 2026-03-30)
```ini
innodb_buffer_pool_size         = 2G
innodb_buffer_pool_instances    = 2
innodb_log_file_size            = 512M
innodb_flush_log_at_trx_commit  = 2
join_buffer_size                = 4M
sort_buffer_size                = 4M
tmp_table_size                  = 256M
max_heap_table_size             = 256M
slow_query_log                  = ON
long_query_time                 = 1
log_queries_not_using_indexes   = ON
```

### Índices críticos (creados o verificados 2026-03-30)
| Tabla | Índice | Columnas | Motivo |
|-------|--------|----------|--------|
| booktrading | idx_hash_id | hash_id | Búsqueda por hash — sin índice era full scan de 3K filas |
| oportunidadesbuysell | idx_hash_id | hash_id | Igual que booktrading |
| trazaplan | idx_idcuenta | idcuenta | Filtro frecuente sin índice |
| fund_holdings | idx_cusip | cusip | Crítico — sin índice: 782K filas, 18 min por query |
| fund_holdings | idx_fund_date | fund_id, report_date | Filtro combinado frecuente |
| fund_holdings | idx_report_date | report_date | Filtro por fecha solo |
| market | idx_symbol | symbol | Tabla sin índices secundarios |
| market | idx_cusip | cusip | JOIN frecuente con fund_holdings |
| funds | idx_cik | cik | Tabla sin índices secundarios |
| diaria_cnv | idx_fecha_cod | fecha, codCAFCI | Filtro compuesto |
| performa_inversion | idx_idcuenta_vehiculo | idcuenta, vehiculo | Filtro compuesto |
| order_trader | idx_account_symbol | account, symbol | Filtro compuesto |

### Columnas con semántica propia

| Tabla | Columna | Qué significa |
|-------|---------|---------------|
| market | `timestamp` | Última modificación de la fila **por cualquier motivo** (precio incluido). No sirve para saber cuándo se recalculó algo puntual |
| market | `inst_update` | Última actualización del pipeline 13F |
| market | `categoria_update` | Última vez que se recalculó `categoriaActivo` (creada 2026-08-25) |
| order_trader | `sync_broker` | Si podemos creerle a la fila — **independiente de `status`** (creada 2026-08-29) |
| symbol_decision_history | `veces` / `primera_vez` | Repeticiones consecutivas colapsadas en la fila y arranque de esa corrida — `timestamp` es la última (creadas 2026-08-31) |
| diaria_performance | `Dividends` | Dividendo devengado en **fecha ex**, no cobrado. No cuadra contra el extracto IB del mismo mes |
| symbol_decision_history | `dedup_key` | Parte estable de la decisión. **NULL = evento único, nunca se agrupa** (creada 2026-08-31) |

**`categoria_update` — por qué existe.** `Agente_DividendStatusScreener` ordenaba los ex-cartera por
`lastPrice DESC` con `LIMIT 150`, así que repetía siempre los mismos 150 símbolos más caros y dejaba
~1170 sin recalcular nunca. Caso testigo: `C` (Citigroup) quedó en `'I'` con la traza congelada en
2024 (precio 57.67) mientras cotizaba a 132.95, donde corresponde `'S'`. Ahora la selección ordena por
`categoria_update ASC` (NULL primero) y el agente corre cada 3 días → los ~1320 ex-cartera rotan
completos en ~27 días. La sellan los dos caminos que escriben categoría:
`sync_dividend_status_screener()` (ex-cartera) y `dividends_en_market_stock()` (en cartera).
El comentario de la columna en MySQL repite este motivo — `SHOW FULL COLUMNS FROM market`.

**Regla: una descarga vacía nunca degrada `categoriaActivo`.** Ambos caminos reescribían la categoría
en cada corrida y bajaban a `'N'` cuando Yahoo no devolvía dividendos, mandando activos `'I'`/`'S'` al
universo de GainsCapture (que solo debe tomar `'N'`). Hoy la categoría solo se escribe si hay dato
real; si no lo hay se conserva la vigente y solo se asigna `'N'` a símbolos que aún no tienen ninguna.
`trailing_annual == 0` sí escribe `'N'`: es un hallazgo, no un fallo de descarga.
La fecha, en cambio, se sella **siempre** — un símbolo que falla debe irse al final de la cola o los
fallos repetidos bloquean la rotación.

**`order_trader.sync_broker` — status dice qué contestó el broker, sync_broker si le llegamos a preguntar.**
Son dos preguntas distintas y estaban en una sola columna. `status` traduce al broker
(`Submitted`/`Filled`/`CANCELED`); `sync_broker` dice si la fila refleja algo confirmado.

| Valor | Qué pasó | Cómo lo trata el gate |
|---|---|---|
| `OK` | El broker devolvió `id_order` — la fila es fiable | Según `status`, como siempre |
| `SIN_CONFIRMAR` | La orden salió pero el broker no devolvió `id_order` | **Cuenta como comprometida**, sin mirar `status` |
| `HUERFANA` | Se buscó en el broker y no apareció tras el plazo de gracia | Deja de contar |

Existe por el gate cruzado H5. `qty_comprometida_sell()` suma las SELL vivas de `order_trader` antes
de que Preservation o GainsCapture emitan, así que la tabla tiene que ser el censo completo de lo
comprometido. No lo era: el camino `[STATE-PRESERVED]` de `_preservation_run_vehiculo()` manda el STOP
a IB **antes** de escribir la fila, y cuando el `order_id` no volvía no escribía nada. El STOP quedaba
vivo en el broker e invisible para el sistema — un fantasma que el gate no veía y contra el que
GainsCapture podía vender las mismas acciones.

No se resolvió con `status` para no mezclar dos semánticas: un `status` inventado ("PENDIENTE") mentiría
sobre lo que dijo el broker, que es justamente lo único que `status` debe decir.

`SIN_CONFIRMAR` cuenta como comprometida a propósito: ante la duda el gate bloquea de más, nunca de
menos — perder una venta es barato, comprometer acciones que no existen es lo que H5 existe para evitar.
`resolve_unconfirmed_orders()` (`Modulos_Mysql.py`, llamada desde `Agente_SyncOrders` cada 300s) la
resuelve contra IB. No puede cruzar por `clientOrderId` — ese es el dato que falta, y por eso
`sync_orders_from_ib()` nunca la encuentra —, así que cruza por símbolo y precio de stop, igual que el
reintento `[RETRY-OK]`; `price` guarda el límite (`stop * 0.99`) y el stop se reconstruye antes de
comparar. Tras una hora sin aparecer la marca `HUERFANA`: IB publica la orden en live orders apenas la
acepta, así que no estar significa que nunca entró **o** que ya se ejecutó. Los dos casos no se
distinguen sin consultar ejecuciones y para el gate dan lo mismo — en ninguno quedan acciones
comprometidas hacia adelante. Se loguea a ERROR porque el segundo caso sí importa para la auditoría.

El comentario de la columna en MySQL repite este motivo — `SHOW FULL COLUMNS FROM order_trader`.

**`diaria_performance.Dividends` es devengo en fecha ex, el extracto IB es caja.** Los dos números
son correctos y no cuadran entre sí: comparar el mes contra el mes da ~40% de desvío y parece un
agujero de datos. Medido sobre julio 2026 — ex-dividendos de julio **123,56**, pago IB de julio
**204,41**; ex-dividendos de **junio** **209,14** contra ese mismo pago: **2,3%**. El desfasaje es el
lag ex-date→payment, típicamente el mes siguiente.

La fecha ex es la que corresponde acá: yfinance la devuelve así y es donde cae el precio. Acreditar el
dividendo en fecha de pago dejaría la serie con un pozo sin contrapartida el día ex y un salto
injustificado semanas después — el retorno total del período quedaría igual, pero ninguno de los dos
días diría la verdad.

**No se reconcilia contra el extracto sin desplazar el mes.** Una purga y reconstrucción completa del
tramo (`AppTest/run_rebuild_diaria_cartera.py`, `accion="cartera"`) devolvió exactamente los mismos
123,56: no había nada roto que arreglar. El residuo de 4,73 sobre el mes desplazado queda sin
atribuir — candidatos: retención en origen de los ADR (TU, BABA, ABEV, PBR) o un ex-date de junio que
paga en agosto. Se cierra con el detalle por símbolo del extracto, no con más reconstrucciones.

**`symbol_decision_history.veces` — la tabla contaba turnos del agente, no hechos.** En modo
`SUPERVISADO` GainsCapture propone y espera autorización, así que repite la misma recomendación
en cada turno: 16 de las 64 filas acumuladas eran "vender clase 100%" sobre ADAUSDT del mismo
día. Consolidando, quedaron **9 filas**.

`dedup_key` la arma el que llama con la parte estable de la decisión (`accion|escenario`,
`stop|urgencia`) porque el `mensaje` trae el ROI del momento y la prosa de Claude, que cambian
siempre. Los tags de acción real (`ENVIADA`, `FILLED`, `EXIT`, `CANCELLED`) no la pasan: cada
orden es un hecho único.

Una corrida se cierra cuando cambia la decisión **o cuando aparece una orden nueva en
`order_trader`, la haya emitido el agente o no** — BTG se vendió a mano el 25/08 mientras el
agente seguía recomendando vender, y sin ese corte la fecha "hasta" se estira por encima de una
decisión ya tomada. Los comentarios de las columnas en MySQL repiten este motivo.

**`inversion.divisa` / `inversion.factor_cambio` — son el recibo, no el pendiente.** La tabla
`inversion` guarda **siempre USD**, para todos los vehículos. Los KPI del panel (Total dGyP, Total
Inversión, UnP&L, Deuda) suman entre vehículos sin mirar la moneda, así que un vehículo que
escribiera en moneda nativa contaminaría el consolidado sin que nada lo detecte.

`divisa` y `factor_cambio` registran la conversión **ya aplicada** — sirven para reconstruir el valor
nativo cuando la UI lo necesita (la pestaña Ars multiplica por `factor_cambio` para mostrar pesos).
**No** son "lo que falta aplicar": multiplicar de nuevo al consumir duplica la conversión.

La conversión vive en `posicion_a_usd()` (`Modulos_Utilitarios.py`), que cada `struct_positions_*`
llama antes de devolver la posición. Antes cada vehículo dividía por su factor a mano — BBVA.ARS lo
hacía bien, pero nada obligaba a que un vehículo nuevo se acordara. `factor_cambio = 0` marca una
fila que quedó en moneda nativa por falta de tasa (queda loggeada, no pasa silenciosa).

**`inversion.dgyp` es siempre el total diario de la posición** (corregido 2026-08-26). Hasta ese
día BBVA.ARS escribía el delta **por unidad** — `struct_positions_fci()` hacía `mrkprice - open` sin
multiplicar por `position` — mientras Stock y Crypto escribían el total. Con eso `SUM(dgyp)` →
`total_ganancia_dia` de `get_totales_inversiones()` sumaba dólares con dólares-por-cuotaparte y no
significaba nada; el consumidor es `Class_Analisis.py:1411`. El panel KPI no se veía afectado porque
usa `DataHub.manager_GyP[vehiculo]["dGyP"]` y el camino ARS multiplicaba por `position` en
`change_a_ARS()` antes de publicarlo.

Hoy `struct_positions_fci()` devuelve `(mrkprice - open) * position` y `change_a_ARS()` acumula
`keys["dgyp"]` directo. Efecto visible: la cabecera de la pestaña Ars muestra el dGyP total en pesos,
no la suma de deltas por cuotaparte. Las filas viejas se corrigen solas — `update_FCI_en_positions()`
reconstruye la posición en cada ciclo.

### Script de monitoreo
`SchemasSQL/mysql_index_analyzer.py` — analiza schema, índices sin uso, full scans y configuración InnoDB.

### Tarea recurrente
Cada lunes 8am → reporte HTML por Gmail (configurado en Claude Scheduled).

---

## Procedimiento de release

Antes de taggear un release, siempre actualizar `version.py`:

```python
VERSION = "10.x.x"
RELEASE_DATE = "YYYY-MM-DD"
```

Luego el flujo completo:
1. Actualizar `version.py` → commit
2. `git tag -a vX.X.X -m "vX.X.X — descripción"`
3. `git push && git push --tags`
4. `gh release create vX.X.X --title "AppOO vX.X.X" --notes "..." --repo gutierrezw/MyPython`
5. `buildExe.bat` → genera el binario
6. `AppTest\export_hijo.bat` → empaqueta versión hijo (genera `deploy\setup_hijo\` y `deploy\AppOO_hijo\`)
7. `gh release upload vX.X.X <archivos> --repo gutierrezw/MyPython --clobber`

### Contenido obligatorio de cada release

**GitHub release notes** deben incluir (con los ajustes de la versión actual):
- Sección `### Novedades` — cambios de esta versión
- Sección `## Instalacion — Version Hijo` — pasos completos: MySQL, BD, profiles, credenciales, Binance, TradingView

**Assets a subir** (generados por `export_hijo.bat`):
- `AppOO_hijo.zip`
- `README.txt` (actualizar URL y sección Novedades antes de correr export_hijo.bat)
- `hijo_estructura.sql`
- `hijo_datos.sql`
- `config_import.json.template`
- `run_binance_import.py`
- `tv_panel.js`

**`AppTest\README.txt`** — actualizar antes de cada release:
- URL del release (sección 0)
- Sección `NOVEDADES vX.X.X` al pie

**Tablas nuevas** — si se creó alguna tabla nueva en el release, verificar que esté incluida
en el `mysqldump` de `export_hijo.bat` (paso `[3/4] Exportando estructura BD`).

---

## Obsidian — flujo de co-work

Vault: `C:\Users\InversionesWildaga\Documents\MyObsidian\AppOO\`
- `10-Memoria/` → junction a `.claude/.../memory/` (mismos archivos que Claude lee/escribe)
- `20-Proyecto/` → junction a `AppOO/Doc/`

### Checklist al INICIAR sesión

Claude debe ejecutar estos pasos antes de responder al primer mensaje de trabajo:

1. Leer `00-Home.md` → verificar estado actual de módulos y links relevantes
2. Leer `10-Memoria/MEMORY.md` → ya cargado como contexto automático, confirmar que es coherente con lo anterior
3. Antes de editar un repo que puede tener otra sesión Claude trabajando en paralelo (AppOO, vault Obsidian, `MyNode/server-api`) → correr `git log -3` / `git status` en ese repo primero. Si hay commits recientes que esta sesión no generó, revisar qué cambió antes de seguir editando — evita duplicar trabajo o pisar cambios. Repetir el chequeo cada vez que la sesión pasa a tocar un repo distinto, no solo al inicio. Caso real: 2026-07-12, una sesión VS Code comiteó cambios de OAuth junto con la implementación de `get_schema_health`/`get_slow_queries` que esta sesión acababa de escribir en `MyNode/server-api` — sin pérdida, pero por casualidad de timing, no por chequeo previo.

### Checklist al COMITEAR

Se ejecuta en **cada `git commit`**, no al final de la sesión — una sesión puede tener
varios commits y el último no es más importante que el primero.

1. **¿El commit cambia el comportamiento descrito en algún doc?** → actualizar el doc en el
   MISMO commit lógico (ver mapa abajo). Un doc que describe código que ya no existe es peor
   que no tener doc: las decisiones de subir a PROD se leen desde ahí.
2. ¿Quedó algún acuerdo de UI/columnas sin registrar?
3. ¿Hay ideas o decisiones relevantes para guardar en MEMORY/FEEDBACK?
4. ¿Todos los cambios de código tienen su contraparte en datos (header + valor en mismo orden)?
5. ¿Se documentaron nuevos índices o cambios en la BD?
6. Si `00-Home.md` quedó desactualizado → actualizarlo (módulos nuevos, estado cambiado)

**Regla de oro del punto 1:** si un hallazgo previo quedó registrado como *resuelto* y este
commit lo revierte o lo cambia de enfoque, **anotar la reversión con el motivo**, no borrar la
entrada. Sin eso, la próxima lectura parece una regresión.

#### Mapa código → doc

Si el commit toca el código de la izquierda, revisar el doc de la derecha antes de cerrar:

| Código | Doc a revisar |
|---|---|
| `_gains_capture_run`, `maximiza_sell_lotes`, `lotesGain*` | `20-Proyecto/design-gains-capture.md` |
| `_preservation_run_vehiculo`, `preservation_*` | `20-Proyecto/design-preservation.md` |
| `readCSV_sell`, `get_top_sell`, `csv_OptionSales_write`, `oportunidades_*` | `20-Proyecto/ref-oportunidades.md` |
| `DataHub` (class vars, config, `gains_config`) | `20-Proyecto/ref-datahub.md` |
| `Class_Screener`, consenso, votos | `20-Proyecto/ref-consenso.md` + tabla de columnas en este archivo |
| `Class_tradingBot`, `Class_BotCryptoUI` | `20-Proyecto/spec-botcrypto.md` |
| Agentes nuevos / `AGENTES_SCHEDULE` | sección "Patrón para agregar un nuevo agente" en este archivo |
| Cualquier hallazgo de la revisión Opus (H1–H10) | `30-Gestion/resultado-revision-opus-preservation-gainscapture.md` + `30-Gestion/BACKLOG.md` |

Los docs viven en `AppOO/Doc/` (= `20-Proyecto/` del vault vía junction) y se comitean en el
repo del vault, aparte del commit de código. Que sean dos repos no los hace dos tareas.
