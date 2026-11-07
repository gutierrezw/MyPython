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

- El concepto sigue siendo **Consenso**; la etiqueta visible es **"Señal"** (Telegram, Screener, popups y
  panel de decisión). Donde convive con el voto institucional —ventana de cartera— son **`Inst Señal`**
  (voto institucional) y **`App Señal`** (los 7 votos), para que no se lean como lo mismo
- `fh_count` → siempre **"13F Inst"** — única fuente de conteo institucional
- `inst_funds` → NO mostrar en UI (datos Yahoo inconsistentes)
- Ambas pantallas deben usar los mismos nombres de columna para los mismos conceptos

## Consenso popup — columnas fijas

`_FIXED_COLS = ("Symbol", "Div", "Nombre", "13F Inst", "Inst %")`

`13F Inst` usa `fh_count` (pipeline EDGAR propio).

## Precio objetivo — fuente única (2026-11-06)

El número que el panel muestra en la columna **Objetivo** y las columnas `Tgt Mean / Tgt High / Tgt Low`
del Screener salen **de la misma tabla**: `market`. Antes eran dos descargas independientes del mismo
dato de Yahoo — el Screener persistía en `market`, el panel llamaba `ts_yfinance_symbol` y aplicaba su
propia cascada en memoria. Medido sobre las 41 posiciones activas: 31 idénticos, 6 con diferencia bajo
el 1% (momentos de descarga distintos, no fórmulas distintas) y 4 que solo tenía el panel.

`MarketScreen.load_target_prices(account)` (`Modulos_Mysql.py`) devuelve `{symbol: {objetivo, origen}}`
con la cascada `targetMeanPrice → targetHighPrice → targetLowPrice → fiftyTwoWeekHigh`.
`api_vehiculo_iteractive` la carga **una vez por ciclo**, antes del lazo de posiciones.

**No hizo falta columna nueva.** `market` ya tiene `fiftyTwoWeekHigh`, así que la cascada completa
resuelve dentro de la tabla y el origen es derivable: si el valor salió de `targetMean/High/Low` es
`analistas`; si cayó al máximo de 52 semanas es `52w`. Medido: 345 de 1320 símbolos del universo y
3 de la cartera (CTRM, NNDM, PHYS) muestran un 52w, que es historia, no proyección.

**ETF: siempre el máximo de 52 semanas, y siempre de Yahoo.** No es una excepción cosmética —
`audit_portfolio` **borra los ETF de `market`** por diseño (la posición vive en `inversion`/`booktrading`),
así que para un ETF no hay fila que leer. Por eso la regla vive en el panel, el único punto donde el
`quoteType` está en memoria. Caso testigo: TLT, cuya ausencia de `market` parecía un hueco de datos.

**El criterio es `quoteType in _ETF_TYPES` más la lista `_ETF_SYMBOLS`, nunca el nombre**
(cerrado 2026-11-07). Las dos listas viven en `Class_Screener.py` y las comparten el panel, el
Screener y `audit_portfolio` — un solo lugar donde decidir si algo es fondo.

`_ETF_NAME_KEYWORDS` **se eliminó**: incluía `"trust"` y `"fund"`, que sobre `market` marcan **125
filas** — entre ellas los REITs **DLR** (Digital Realty Trust) y **MPT** (Medical Properties Trust),
con cobertura real de analistas, y 7 bancos operativos (NTRS, TRMK, TRST, WASH, WTFC, CTBI, HTB). El
desvío de objetivo sería material: MPT 3,67 → 6,47 y DLR 224,22 → 208,14. El criterio estaba vivo
desde el 2026-05-30 (`1e88496`) y `audit_portfolio` **borraba las tres filas de `market`** en cada
corrida mensual, con su `cusip` y su `fh_count`; el panel las reinsertaba en el ciclo siguiente como
`categoriaActivo='N'` y el pipeline del Screener volvía a poblarlas. Un lazo que churneaba el dato
sin que nada lo reportara.

`_ETF_SYMBOLS = {"PHYS"}` es el override por símbolo para lo que Yahoo tipa mal: reporta PHYS
(Sprott Physical Gold Trust) como `EQUITY`, así que ni `_ETF_TYPES` lo atrapaba ni la cascada lo
sacaba del Screener — figuraba con `fh_count` 764 y entraba al Consenso como si fuera una acción.
El override cierra los tres caminos a la vez: `audit_portfolio` lo borra de `market`,
`dividends_en_market_stock` ya no lo reinserta, y el panel le da el 52w directo.

`inversion.objetivo` queda como **espejo histórico, no como fuente** — lo escribe el panel con el valor
ya resuelto.

### Crypto — el objetivo era el 52w del día del alta, congelado

Lo de arriba es Stock. En Crypto el objetivo vive en `otros_activos.objetivo` y **la fuente nunca
estuvo mal: estaba congelada.** `insert_otros_activos` lo escribe con el `fiftyTwoWeekHigh` de Yahoo
dentro de la rama `if not found` — o sea **una sola vez, en el alta del par** — y ningún camino lo
vuelve a tocar: el único `UPDATE` de la columna en `Modulos_Mysql.py` es ese insert, y las cuatro
llamadas a `update_otros_activos` nunca pasan `objetivo`.

Medido el 2026-11-06 sobre los 12 pares activos: todos traían el máximo vigente el día del alta.
Los dados de alta en 2021 llevaban el pico de ese ciclo —**ADA 3,00 contra un precio de 0,186; DOT
53,00 contra 0,917**— que ningún escenario alcanza, así que el `gypp` del panel (`position *
objetivo - costobase`) era una proyección muerta. Lo que cierra el diagnóstico es el caso inverso:
**FIL (3,88334) e ICP (9,74224) en B0000002 coinciden al decimal con el Yahoo de hoy** — son altas
recientes.

**`fecupdate` no fecha el objetivo.** La mueve el costo: `recalculate_cost_chain` la sella con la
fecha de la última fila de la cadena. ADA tiene `fecupdate` 2026-06-05 con un objetivo de 2021.

**La fuente son las klines de Binance, no Yahoo.** No es preferencia: `POL-USD` y `MATIC-USD`
devuelven `None` en Yahoo (`quoteType` NONE) y el ticker real es **`POL28321-USD`**, que no se
deriva del par. Binance lo resuelve nativo — `POLUSDT` tiene su propia historia post-rename, así que
tampoco arrastra el objetivo de MATIC. Y son las klines **que el panel ya descarga**:
`ServiciosCrypto.sync_objetivo_cartera()` llama `get_yfinance(ticket, vehiculo="Crypto")` sin
`desde`/`hasta`, exactamente como `ts_yfinance_symbol`, así que comparte la entrada de `CacheHut` y
la corrida **no agrega descargas**. Pasar un `desde` propio perdería la caché.

**Se persiste, no se calcula en el panel.** `DashMain.py:250` es el websocket de Crypto: relee
`otros_activos` en cada tick. Un valor que viviera solo en memoria quedaría pisado por el viejo en
el mensaje siguiente y el objetivo oscilaría. Lo refresca `Agente_ObjetivoCrypto` (24h).

**Punto de atención — la ventana se vacía en noviembre.** Los 12 máximos caen entre el 2025-11-06 y
el 2025-11-12: el pico del ciclo está justo en el borde de la ventana. Medido cuánto baja el
objetivo **solo por el paso del tiempo**, sin que el mercado se mueva: a 30 días FIL −57%, ICP −51%,
DOT −32%; a 90 días FIL −67%, ICP −58%, ADA −48%, DOT −50%. Esto invierte la pregunta de la ventana:
**una ventana más corta no endurece el objetivo, lo ablanda** — en tendencia bajista el 52w rodante
persigue al precio hacia abajo. Se eligen 52 semanas igual, por el mismo criterio que el ETF, y se
deja anotado el escalón para que los objetivos más bajos de diciembre no se lean como un defecto.

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
- Si el agente ya tiene entrada estática en `AGENTES_SCHEDULE` (`Modulos_Utilitarios.py`), esa entrada manda: el
  decorador solo registra nombres que no están, así que su `desc` se ignora. Caso `Agente_ExtractosWatcher`: su
  decorador va sin `desc` y el panel muestra la de la entrada estática

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

### Tipos de columna — la convención es `float`

Medido sobre `AppTest/hijo_estructura.sql`: **111 columnas `float`** contra 10 `decimal`. Toda columna
numérica nueva va en `float` salvo motivo escrito; el resto de la tabla manda sobre cualquier criterio
teórico de precisión.

**Un `MODIFY COLUMN` copia el tipo de `SHOW CREATE TABLE`, nunca lo infiere.** MySQL no permite cambiar
solo el comentario de una columna: `MODIFY` obliga a repetir la definición entera, así que un tipo
adivinado **convierte los datos en silencio**. Caso real del 2026-09-21: para ponerle el `COMMENT` a
`inversion.deuda` se emitió `DECIMAL(18,8) NOT NULL` sobre una columna que era `float` nullable →
7 warnings 1265 (redondeo en la 8ª decimal de las 114 filas) y la columna con un tipo distinto al del
resto de la tabla. El valor no se dañó de forma material, pero el `ALTER` de reversión no estaba
planificado. La secuencia correcta es: `SHOW CREATE TABLE` primero, copiar la definición literal,
agregarle el `COMMENT`, y recién entonces ejecutar.

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
| market | uq_market_account_symbol | account, symbol (**UNIQUE**) | Nada impedía dos filas del mismo símbolo — caso FIRY, 2026-11-07. Reemplaza al `idx_market_account_symbol` no único |
| funds | idx_cik | cik | Tabla sin índices secundarios |
| funds | uq_funds_cik | cik (**UNIQUE**) | `bulk_insert_edgar_funds` emitía `INSERT IGNORE` sin nada que ignorar — 22 copias de cada fondo, 2026-11-07 |
| diaria_cnv | idx_fecha_cod | fecha, codCAFCI | Filtro compuesto |
| performa_inversion | idx_idcuenta_vehiculo | idcuenta, vehiculo | Filtro compuesto |
| order_trader | idx_account_symbol | account, symbol | Filtro compuesto |

**`market` admitía dos filas del mismo símbolo, y la duplicada quedaba invisible** (2026-11-07).
Medido: FIRY era el único caso sobre 1.360 filas — ids 1466 y 1807, idénticas salvo `cusip`,
`sharesOutstanding`, `floatShares` y `lastDividendValue`, que solo traía la vieja.

**La columna `account` es original de la tabla; lo que faltaba era pasarla.** `insert()` arma la lista
de columnas desde `upd`, así que un llamador que no la incluya produce una fila con `account` NULL
aunque la columna exista desde el día uno. No es un agujero nuevo: en el snapshot más viejo del repo
(`68c45a6`, 2025-10-26) el insert de `dividends_en_market_stock` ya iba sin `account`. Una fila sin
cuenta es invisible para `load_symbols(account)` y `select(account=...)`, así que la fase 1 del
Screener la inserta de nuevo.

**Hay un segundo camino y no se puede decidir cuál disparó.** `select()` devuelve `[], []` cuando
falla, y `update_tabla_market` lee eso como "no existe" → inserta: un error transitorio de BD durante
el `select` genera la fila duplicada sin dejar rastro. El orden de los ids favorece este segundo
camino — la fila **vieja** (1466) es la que tiene `cusip` y `floatShares`, que los escriben caminos
filtrados por `account`; si la huérfana hubiera nacido primero, esos datos habrían caído en la nueva.

Nada lo impedía en ningún caso: el índice `(account, symbol)` existía pero **no era único**. Eso es
lo que cubre las dos vías.

Y quedaba invisible porque `update()` **sin `account` arma `WHERE symbol=%s`**, que pisa las dos
filas: por eso las dos traían el mismo `timestamp` al microsegundo y el mismo `inst_score`. El
duplicado no se notaba porque algo lo mantenía sincronizado.

Hoy `insert()` recibe `account` y `dividends_en_market_stock` lo pasa en el insert y en el update.
Se conserva la fila **con `cusip`** — sin cusip la posición 13F se descarta al cargar.

**El segundo camino quedó cerrado el 2026-11-07, y no con "update primero, insert si no actualizó":
`update()` tenía la misma confusión.** Devolvía `False` tanto si la fila no existía como si la BD
falló, así que mover la decisión sin separar los dos casos solo movía el defecto de método. Hoy
`update()` devuelve **`True` / `False` / `None` en error** y `update_tabla_market` corta en `None`
sin insertar nada.

La existencia la decide el **rowcount del UPDATE**, no un `SELECT` previo: `update()` siempre escribe
`timestamp` con `datetime.now()`, así que **rowcount ≥ 1 cuando la fila existe** → rowcount 0 solo
puede ser "no existe". El `select()` desapareció del camino, que ahora hace **una consulta menos por
símbolo**.

Devolver `None` es seguro porque de los 8 llamadores de `update()` **solo `Class_InstitucionalScore.py:141`
lee el retorno** (`if ok: updated += 1`), y `None` es falsy exactamente como el viejo `False`. El
contrato `[], []` de `select()` **se dejó intacto a propósito**: tiene 11 llamadores y hacerlo `raise`
o devolver `None, None` los rompe a todos. Lo que sí cambió es que los tres `except` de `MarketScreen`
pasaron de `print()` a `_logger.error`, así que un fallo de BD deja rastro en el log rotativo
(el logger `Mysql` está en ERROR, que es justo el nivel que llega).

**`funds` tenía 188.823 filas basura: el `INSERT IGNORE` no tenía nada que ignorar** (2026-11-07).
`bulk_insert_edgar_funds` reinserta el padrón EDGAR completo en cada corrida de `sync_edgar_funds`
—mensual— y la tabla no tenía clave única, así que acumuló **22 copias de cada uno de los 8.992
fondos**: 197.815 filas, un solo nombre por cik (reinserción pura, no renames).

No corrompía nada. `get_fund_id_by_cik` hace `SELECT id FROM funds WHERE cik = %s` + `fetchone()` sin
`ORDER BY`, y en la práctica devolvía siempre el `id` más bajo: los 7.887 `fund_id` que usa
`fund_holdings` eran **todos** el `MIN(id)` de su cik, así que el borrado quedó sin huérfanos.
Saneado a 8.992 filas y cerrado con `uq_funds_cik`, que es el arreglo de código — el `INSERT IGNORE`
ya estaba bien escrito, le faltaba contra qué colisionar.

**`sys_objeto` ids 8 y 9 eran el mismo blob de icono** (60.797 bytes, `usamodulo='globales.py'`).
Borrado el 9. Inocuo, se registra para no volver a investigarlo.

### Columnas con semántica propia

| Tabla | Columna | Qué significa |
|-------|---------|---------------|
| market | `timestamp` | Última modificación de la fila **por cualquier motivo** (precio incluido). No sirve para saber cuándo se recalculó algo puntual |
| market | `inst_update` | Última corrida de `sync_13f_scores` que escribió la fila. **Columna muerta hasta el 2026-11-07** — existía en la BD y ningún código la tocaba. Solo se sella cuando hay dato real; los `skipped` quedan en NULL |
| market | `inst_ownership_pct` | % del float en manos institucionales, **de Yahoo** (`heldPercentInstitutions`). Dueño único: `sync_institutional`. Puede pasar de 1 por desfase float/holdings — la UI lo acota a 100% |
| market | `inst_score` | Score institucional compuesto. Dueño único: `sync_13f_scores`. **No tiene techo** — el término `log(fh_count)` solo ya vale 1,68 con 4.482 fondos |
| market | `categoria_update` | Última vez que se recalculó `categoriaActivo` (creada 2026-08-25) |
| fund_filings | `processed` | `0` en cola, `1` cargado en `fund_holdings`, **`2` no cargable — no reintentar**: el XML no está en disco o el fondo no está registrado. Sin el 2 el filing se recorre en cada corrida sin avanzar nunca, porque `sync_fund_filings` solo reintenta la accession más reciente de cada fondo. Medido 2026-11-06: **4.152 filings atascados** así (creada la semántica 2026-11-07) |
| order_trader | `sync_broker` | Si podemos creerle a la fila — **independiente de `status`** (creada 2026-08-29) |
| symbol_decision_history | `veces` / `primera_vez` | Repeticiones consecutivas colapsadas en la fila y arranque de esa corrida — `timestamp` es la última (creadas 2026-08-31) |
| diaria_performance | `Dividends` | Dividendo devengado en **fecha ex**, no cobrado. No cuadra contra el extracto IB del mismo mes |
| trazaplan | `costobase` | **Columna muerta** — se inserta en 0 y nada la actualiza. El costo base real es `tinversion` |
| symbol_decision_history | `dedup_key` | Parte estable de la decisión. **NULL = evento único, nunca se agrupa** (creada 2026-08-31) |
| incidencias | `dedup_key` / `veces` / `primera_vez` | Mismo mecanismo que `symbol_decision_history`, aplicado a las alertas. **`leida` es el borde del grupo** (creadas 2026-09-06) |
| incidencias | `notificado` | Último envío real a Telegram — el reloj de `renotify`, **independiente de la agrupación**: la fila sigue siendo una. **NULL = silencio infinito → notifica** (creada 2026-11-04) |
| fin_categories | `expense_class` | Clase del gasto: `fixed` + `variable` = costo de vida base del número de libertad financiera, `extraordinary` se promedia aparte. **NULL si la categoría no es gasto** (creada 2026-09-13) |
| fin_transactions | `billing_date` | Cierre del resumen que cobra la fila. Los KPIs agrupan por `COALESCE(billing_date, date)`, nunca por `date` sola. **NULL = la fecha del movimiento ya es la del cobro** (creada 2026-09-16) |
| fin_accounts | `tracked_since` | Desde cuándo la cuenta cuenta en el histórico de Finanzas: antes de esa fecha un mes vacío no es hueco de carga. **Default 2026-01-01 = piso del módulo**, no la apertura de la cuenta (creada 2026-09-16) |
| inversion | `conid` | Listado de IB (bolsa) donde **la cuenta** operó el ticker; se conserva tras la baja. **No es "el" conid del ticker**: el mismo ticker cotiza en varias bolsas (ENB en NYSE y TSE) |
| inversion | `deuda` | Deuda de **Binance para esa posición** (`debit USDT`). Stock y FCI escriben 0, así que `SUM(deuda)` **no es la deuda de la cartera** |
| ib_flex_trades | `exec_id` | execID de TWS — el **único** identificador que cruza contra `booktrading.idtrans`, y solo desde **2024-04-02** (creada 2026-09-21) |
| booktrading | `basico` | Costo medio de la posición **después** de ese hecho, calculado **solo con datos del libro**: el divisor es su propio `stock` y el total del que se descuenta es `basico * stock` de la fila anterior. El costo del broker no entra (corregido 2026-10-29). Solo lo consume Crypto manual; Stock lee el costo de IB |
| booktrading | `sell` | Cuánto del lote ya se consumió. **`cantidad - sell` es lo vivo solo si `activa = 'Y'`** — toda query que lea la columna filtra por `activa` (corregido 2026-10-30) |

**`inst_ownership_pct` e `inst_score` tenían dos escritores cada una, y ganaba el que corría último**
(2026-11-07). `sync_institutional` (Yahoo, 24h) y `sync_13f_scores` (13F, 24h) escribían las dos columnas
con significados distintos: `inst_ownership_pct` era el `heldPercentInstitutions` de Yahoo (0–1) o el ratio
propio `fh_total_shares / floatShares` (sin techo), e `inst_score` era el porcentaje de Yahoo o la fórmula
de 4 términos. Medido antes del arreglo: 1.152 filas con el ratio 13F, 133 con el porcentaje de Yahoo.

**El ratio propio se eliminó porque el numerador está mal, no el divisor.** El 13F agregado duplica
acciones —co-filers y custodios reportan las mismas— y no se puede deduplicar desde los filings. Medido:
GS sumaba 566,6M de acciones entre 3.375 fondos contra ~295M existentes → ratio **1,92** contra el
**0,765** real de Yahoo; PEO daba **18,95** contra 0,386. No es antigüedad de los filings (3.314 de los
3.375 fondos de GS filearon en 2026, aportan 566,3M de los 566,6M) ni duplicados de carga (0 filas
duplicadas en `fund_holdings`). Con el `floatShares` correcto de Yahoo —298.213.315— el ratio queda en
1,90: igual de absurdo.

Hoy `sync_13f_scores` **lee** `inst_ownership_pct` de la fila para su término del 40% y no la escribe;
`sync_institutional` dejó de escribir `inst_score`. Efecto: el score baja en los 46 símbolos donde el
ratio pasaba de 100%. **El orden importa** — `sync_institutional` primero, `sync_13f_scores` después,
o el 40% calcula en cero.

`floatShares` sigue descargándose para la Rotación del Screener, pero **ya no es divisor de nada**: está
poblado en solo 30 de 1.361 filas de `market` y 1.241 caen al `sharesOutstanding`.

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

**`trazaplan.costobase` no se usa — el costo base del paso es `tinversion`.** `insert_trazaplan()`
la escribe literalmente en `0` y ningún camino la actualiza después; los valores que traen las filas
viejas vienen de un camino que ya no existe (meta 5 y meta 6 comparten el mismo 43984.9). El dato vivo
lo escribe `update_plan()` en `tinversion`.

Importa porque dos consumidores la usaban como "¿esta fila tiene datos?": la tabla del plan
(`Class_gestion.py`) y `chart_trazaplan()`. Con eso el paso en `Ejecucion` —el año fiscal en curso—
se veía vacío y sin barra en el gráfico **los doce meses**, aunque `update_plan()` le estuviera
acumulando el extracto en cada cierre. Corregido 2026-09-02: ambos filtran por `tinversion`.

No se borró la columna: las filas `Cumplido` históricas la traen con dato y nadie verificó qué
significaba ese número. Se marca muerta y no se lee.

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
resuelve contra el broker del vehículo. No puede cruzar por `clientOrderId` — ese es el dato que falta,
y por eso `sync_orders_from_ib()` nunca la encuentra —, así que cruza por símbolo y precio de disparo,
igual que el reintento `[RETRY-OK]`. Tras una hora sin aparecer la marca `HUERFANA`: el broker publica
la orden apenas la acepta, así que no estar significa que nunca entró **o** que ya se ejecutó. Los dos
casos no se distinguen sin consultar ejecuciones y para el gate dan lo mismo — en ninguno quedan
acciones comprometidas hacia adelante. Se loguea a ERROR porque el segundo caso sí importa para la
auditoría.

**Corregido el 2026-09-07 — antes solo servía a Stock.** Se documentaba que el método "resuelve contra
IB" y que el disparo se reconstruía desde `price` como `stop * 0.99`. Las dos cosas dejaron de valer:

- Consultaba `ib_client.get_preservation_stops()` en duro y se lo llamaba **solo desde la rama IB** de
  `Agente_SyncOrders`, con la `account` de Stock. Una fila de Crypto ni siquiera entraba en el
  `SELECT`: no se confirmaba, no llegaba a `HUERFANA`, y el símbolo quedaba comprometido de forma
  permanente para Preservation y para GainsCapture. Hoy `Class_ApiBinnace` implementa el mismo
  `get_preservation_stops()` que IB —{symbol, order_id, stop_price, status}— y el método recibe
  `client` y `vehiculo`, sin saber contra qué broker cruza.
- La reconstrucción `price / 0.99` daba por hecha una holgura fija. Con `stop_limit_pct` configurable
  por vehículo (`parameters.preservation`) el cálculo queda mal apenas se afina el parámetro, y mal
  hacia atrás para las filas ya escritas. El disparo sale ahora de `json_detalle.resultado.stop_final`,
  que es el valor exacto que se envió; las filas viejas sin ese dato caen al cálculo anterior. La
  tolerancia pasó a relativa (0,5%) — un margen fijo de centavos no significa lo mismo en una acción
  de 700 que en una cripto de 0,0004.

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

**`incidencias` — el panel de Alertas estaba inutilizado, no solo ruidoso.** Medido el 2026-09-06:
1870 filas, **1794 pendientes**, ~30 por día. `⚠️ IB Gateway caído — reconectando en 30s` sola era
**1238 (66%)**. Como `get_incidencias` lee `LIMIT 200`, **181 de las 200 filas visibles eran esa
línea**: se veían 5 hechos distintos y ~1594 incidencias pendientes no se renderizaban nunca.
Consolidando quedaron **72 pendientes** — 6 agrupadas y 66 hechos únicos que antes estaban tapados.

`dedup_key` la arma el emisor con la parte estable del hecho (`ib_gateway_down`, `ntp_drift`,
`fci_blocked`). El `msg` no sirve de clave: lleva el dato del momento —los ms de deriva NTP iban en
el texto y habrían generado 30+ grupos para un solo hecho—, así que el mensaje que se conserva es el
**último**, no el primero: qué banco está bloqueado hoy dice más que cuál lo estaba en julio.

**`leida = 0` es la condición de agrupamiento, y por eso `leida` es el borde del grupo.** Marcar la
fila leída cierra la corrida: la próxima aparición abre fila nueva y **vuelve a notificar por
Telegram**. Es lo que hace que "leída" signifique *ya me hice cargo* y no *no me lo muestres más*.
Mientras la fila sigue pendiente, la repetición suma en `veces` y **no se reenvía a Telegram** —
`add_alert()` corta antes de encolar; el estado ya está reportado. **Matizado el 2026-11-04:** eso
vale mientras el emisor no pase `renotify`, que sigue siendo el default; con `renotify` el aviso
vuelve a salir pasado el plazo y sin abrir fila nueva (ver abajo).

El único punto de entrada es `DataHub.add_alert()` → `BDsystem.insert_incidencia()`, que devuelve
`(id, veces, notificar)`. Un hecho único —una orden, un repago— va sin clave y nunca se agrupa.

**`add_alert(registrar=False)` manda el mensaje y no deja fila** (2026-09-22). Es para reescribir en
el chat un hecho **ya registrado** cuyo texto cambió — el refresco de una propuesta de GainsCapture,
que reemite el precio del momento. `dedup_key` no sirve para eso: agrupa bien en la tabla pero corta
el envío cuando `veces > 1`, que es justamente lo que hay que actualizar. Consecuencia a tener
presente al contar filas: un mensaje del chat puede no tener incidencia propia.

**`renotify` separa notificar de agrupar** (2026-11-04). El agrupamiento arregló el panel y dejó muda
la alerta: `ib_sso_expired` quedó pendiente desde el 2026-10-23 y acumuló **862 caídas con un solo
aviso**; `ib_gateway_down` 516 desde el 08-09; `fci_blocked` 1195 desde el 24-07. Reiniciar la app no
reabre el canal — el reenvío del arranque busca `enviado_tg=0` y esas filas ya estaban en 1 —, así
que el silencio sobrevivía a todo menos a marcarlas leídas a mano. Para un estado que va y vuelve
*"ya te avisé"* no es la pregunta; la pregunta es *"¿hace cuánto?"*.

Con `renotify=<segundos>` la repetición sigue siendo **una sola fila** y sigue sumando en `veces`,
pero vuelve a salir por Telegram si el último envío real fue hace más de ese plazo. El plazo se mide
contra `notificado`, que vive en la BD: a diferencia del throttle en memoria que tenía `DashMain.py`
—eliminado en el mismo commit— **sobrevive al reinicio**. `notificado IS NULL` cuenta como silencio
infinito y notifica: ante la duda se avisa de más, nunca de menos. Lo mide `TIMESTAMPDIFF` **dentro
de MySQL**, no restando `datetime.now()` — el servicio corría en UTC−4 (Venezuela) con Windows ya en
UTC−3, así que mezclar relojes regalaba 3600 s exactos y `renotify=3600` habría renotificado siempre.
El desfase se cerró el mismo día (`SET PERSIST time_zone='-03:00'`, desvío 3600,9 s → 0,4 s), pero la
regla queda: **el que sella la fecha y el que la mide tienen que ser el mismo reloj.**

**Y habilitó `dedup_key` donde antes no se podía poner.** La propuesta de GainsCapture se emitía sin
clave a propósito: agrupar cortaba el envío y el usuario tiene que poder autorizarla. Con `renotify`
esa objeción desaparece — FIRY había abierto **41 filas** entre el 22-09 y el 03-11 por re-evaluarse
~1 vez por día, todas el mismo hecho.

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

**`inversion.conid` es el mercado donde operó la cuenta, no una propiedad del ticker** (2026-09-16). La
compra de un símbolo fuera de cartera tomaba el primer resultado de la búsqueda de IB, que es difusa y no
trae `currency`: ENB salió en Toronto (TSE, en CAD) antes que en NYSE, y BIL devolvía BHP antes que el ETF.
El filtro anterior por `currency == "USD"` nunca coincidía por eso mismo. Hoy la compra lista los mercados
con el ticker exacto (`IB.get_listings()`, EE.UU. primero) y el usuario elige; el `conid` guardado para esa
cuenta va primero, marcado "— ya operado" (`_conid_guardado()` en `Class_customer.py`), aunque IB ya no lo
liste con ese ticker (MPW hoy es MPT). Por eso `select_inversion()` filtra por `account` cuando la recibe:
sin cuenta devolvía la fila de cualquier cuenta. La orden (`place_OrderStock`) usa el mismo `conid` guardado
antes de ir a buscar a IB.

**Matizado el 2026-10-14 — en FCI `conid` es el `codCAFCI`.** Las 16 filas `BBVA.ARS` lo traen poblado y 15
coinciden con `otros_activos.idcrypto`; no hay bolsa ni listado de por medio. Importa porque el padrón CNV
**renombra fondos manteniendo el código**: cafci 816 fue `FBA Renta Fija Plus - Clase A` hasta el 2026-06-08
y `FBA Renta Fija Pesos Plus I - Clase A` desde el 2026-06-09. El nombre es inestable por diseño del padrón,
el código es la identidad. `booktrading` no tiene columna equivalente — ahí el fondo se identifica por
`simbolo`, el nombre que manda el banco, así que un rename parte la cadena de costo en dos símbolos y nada
lo detecta. Detalle en `10-Memoria/state-bbva-ars.md`.

**`inversion.deuda` es el `debit USDT` de esa posición en Binance — no la deuda de la cartera** (2026-09-21). La
escribe `update_inversion()` desde `keys["deuda"]`, y el único camino que le pone algo distinto de 0 es el de Crypto
(`on_message_binance_websocket()` y el ciclo de posiciones, ambos en `DashMain.py`). El de Stock
(`api_vehiculo_iteractive()`) escribe `0` y FCI también, así que **el margen de IB no figura en ninguna fila**.

Importa porque `SUM(deuda)` parece la deuda total y no lo es: el bloque PROGRESO de Finanzas restaba esos 411 USD
cuando la deuda real era 6.900 (IB 6.462 + Binance 410), inflando el capital propio en ~6.500. La deuda consolidada
se lee de `DataHub.manager_GyP[vehiculo]["Debit"]`, la fuente de la barra `Deuda Total`, que `kpi_snapshot` persiste
cada 30s en `stock_debit` y `crypto_debit` para que el valor sobreviva a que el broker esté fuera de línea.

**`ib_flex_trades.exec_id` — `transaction_id` y `exec_id` son dos numeraciones de IB para el mismo trade, y
solo una cruza.** `booktrading.idtrans` guarda el execID de TWS (`0000febb.5f50b86f.01.01`); el Flex además
trae su `TransactionID` (11 dígitos), que no deriva del otro. Medido 2026-09-21 sobre los 7 CSV: por
`transaction_id` cruzan **4 filas de 1813**, por `exec_id` **971**.

El corte es **2024-04-02 12:27**: antes de esa fecha la app inventaba un número de 9 dígitos, así que las
754 filas de 2020-2023 no tienen contra qué cruzar y dependen del match difuso. Abril 2024 es el único mes
mezclado.

**El cruce no filtra por símbolo ni divisa** (`exists_bt_trade_by_idtrans`): el execID ya identifica la
ejecución y agregarlos solo resta — cuenta+idtrans cruza 971, sumando símbolo 883, sumando divisa 877. Las 94
que se pierden son los renames (SKLZ, MPW, GOEV, NEP, SUP) y VRLA, que cotiza en EUR y el libro guarda en USD.

**Matizado el 2026-10-10 — el metodo acepta `symbol` opcional.** Binance numera el tradeId **por par**, no por
cuenta: sin el filtro el tradeId de un par puede chocar con el de otro y descartar un trade real. La medicion de
arriba sigue valiendo para IB, que lo llama sin `symbol` porque su execID es global.

La tabla entera se convirtió a `utf8mb4_0900_ai_ci` en el mismo trabajo: estaba en `utf8mb4_unicode_ci` y
**todo** JOIN contra booktrading moría con error 1267, no solo el de `exec_id`. Detalle en
`10-Memoria/ref-ib-reconcile.md`.

**`fin_categories` — el grupo lo decide `category_type`, la clase `expense_class`.** `category_type`
(`expense` / `income` / `transfer` / `investment`) es lo que leen los KPIs de Finanzas (`_SQL_GRUPO`); las
transferencias no cuentan ni como ingreso ni como gasto. La columna `type` se borró el 2026-09-13: nada la
leía y la clave única `(name, type)` permitía dos categorías con el mismo nombre — hoy `uq_cat_name (name)`.
`parent_id` sigue existiendo pero está en NULL en todas: el mapa es plano a propósito.

`expense_class` existe para el número de libertad financiera: el costo de vida base es `fixed` + `variable`;
`extraordinary` (tecnología, viajes, mantenimiento, cancelación de préstamo) no es un gasto de todos los meses
y se promedia aparte. El mapa vigente y el motivo de cada fusión están en `20-Proyecto/spec-finanzas.md`
§ "Mapa de categorías". El comentario de la columna en MySQL repite la regla.

**`fin_transactions.billing_date` — la cuota se cobra en el resumen donde aparece, no en el mes de la compra.**
Sin esto un plan de 6 cuotas cae entero en un solo mes: el gasto de ese mes queda inflado y los siguientes vacíos.
**No se resuelve moviendo `date`**: `uq_tx` es `(account_id, date, amount, raw_description)`, así que reescribirla
puede colisionar con otra cuota del mismo plan, pierde la fecha real de la compra y una reimportación del resumen
vuelve a insertar con la fecha vieja. La sella `_set_billing_dates()` (`Class_Finance.py`) al cerrar el import.
Todo consumidor nuevo de `fin_transactions` que agrupe por período debe usar `FinanceScreen._SQL_FECHA`; la excepción
deliberada es `get_coverage()`, que mide cuándo se cargó movimiento real. Motivo completo y medición en
`20-Proyecto/spec-finanzas.md` § "Fase 1 — registro de lo hecho", paso 1.5.

**`booktrading.basico` — una venta cambia el costo medio, y hasta el 2026-10-10 lo copiaba.** La rama de
venta de `insert_booktrading` hacía `basico = costo_avg`, el promedio **previo** a la venta, mientras el
costo de los lotes consumidos (`importe`, de `maximiza_ganancias_corto_plazo`) solo alimentaba
`gprealizadas`. El error es acumulativo: la compra siguiente arranca de `basico * stock`. Detalle y medición en
`10-Memoria/ref-booktrading-dos-caminos.md`.

**Rectificado el 2026-10-29 — el divisor del broker se revirtió, y sí afectaba a Stock.** El arreglo del 10-10
dejó `(position * costo_avg - importe) / resto` y se documentó acá que el divisor era la posición del broker a
propósito y que no afectaba a Stock. Las dos cosas quedaron mal: `position * costo_avg` es literalmente
`costobase * factor_cambio`, el total de IB, mientras `importe` lo calcula el libro consumiendo **sus lotes más
baratos**, así que el resto no cerraba contra la suma de los lotes abiertos. Medido en FIRY (Stock): el `basico`
corría **37,57 USD por debajo** de sus propios 23 lotes y una venta de 45 unidades lo subió a 18,7038, por
encima del lote vivo más caro. Hoy es `(nw_producto - importe) / resto` con `resto = ustock + cantidad` — el
libro descuenta del libro. Lo que **sí** se conserva del 10-10 es descontar `importe` en vez de copiar el
promedio previo. El bloque `select_inversion` del método se eliminó: sin esa fórmula no tenía consumidor.

**La deduplicación de `insert_booktrading` pasó a `idtrans`** en el mismo trabajo. El hash no frena los
duplicados reales: FIRY entró dos veces con el execID `00010193.680a8fca.01.01` (97 contra 96 del broker) y las
dos filas traen el **mismo `hash_id`** `91ca7cc397feb1216ccf070a3028c8d4` — igual que ADAUSDT con el tradeId
`488521576` (ids 970 y 984). Con el hash repetido en BD, el camino que las insertó no lo validó o no pasó por
`insert_booktrading`; queda **sin determinar**. Y donde sí pasa, el hash es inestable: incluye `fechahora`, así
que el mismo trade reenviado con la hora corrida genera otro hash (174 de 188 trades de Binance el 10-10). El
guard se limita a `("Stock", "ETF", "Crypto")` y **va con `symbol`**: ARS y VES reúsan el número de 20 dígitos
del banco (15 y 1 grupos repetidos con fecha, cantidad y precio distintos) y Crypto trae `idtrans` correlativos
`1..21` de cargas manuales repetidos entre pares.

Dos tramos mas del mismo hecho, cerrados el 2026-10-10:

- **`recalculate_cost_chain` sella `otros_activos.avgcost`.** El panel de Crypto lee el costo base de ahi, asi
  que reescribir solo el libro deja la cadena corregida y la pantalla con el valor viejo. Sella la fecha de la
  **ultima fila de la cadena**, no la del recalculo — la posicion que ese costo describe. Por eso el
  `update_otros_activos` del final de `insert_booktrading` ya no se repite cuando el camino retroactivo sello:
  la retrocederia a la del movimiento insertado, que es justamente una vieja.
- **`sync_trades` valida la existencia por `idtrans`, no por hash.** `get_hash_booktrading` incluye `fechahora`,
  que sale de `datetime.fromtimestamp()` — hora local del equipo —, asi que una fila escrita bajo otro huso
  genera otro hash para el mismo trade y la deduplicacion no la reconoce nunca. Medido: un `desde=2026-01-01`
  reinserto los 188 trades de 2026 de los 12 pares con la fechahora corrida una hora exacta; de esos 188,
  **174 ya existian por (cuenta, simbolo, idtrans) y 14 eran reales**. `DashMain.py:801` (websocket) sigue
  validando por hash — mismo riesgo, no tocado porque es el camino en vivo.

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
| `Class_IA_modelos`, `scalar_features`, etiquetado IA | `20-Proyecto/ref-modelos-ia.md` |
| `ConvergIA/Scanner_Sentimiento`, `Interprete_Sentimiento`, `ThemeMapper` | `20-Proyecto/design-sentimiento.md` |
| Agentes nuevos / `AGENTES_SCHEDULE` | sección "Patrón para agregar un nuevo agente" en este archivo |
| `add_alert`, `insert_incidencia`, tab Alertas | sección "Columnas con semántica propia" en este archivo |
| `load_target_prices`, `api_vehiculo_iteractive`, columna Objetivo | sección "Precio objetivo — fuente única" en este archivo |
| `sync_objetivo_cartera`, `Agente_ObjetivoCrypto`, `otros_activos.objetivo` | sección "Precio objetivo — fuente única" § Crypto, en este archivo |
| `FinanceScreen`, `Class_Finance`, tablas `fin_*` | `20-Proyecto/spec-finanzas.md` (§0: objetivos, etapas, regla de KPIs, mapa de categorías) |
| Cualquier hallazgo de la revisión Opus (H1–H10) | `30-Gestion/resultado-revision-opus-preservation-gainscapture.md` + `30-Gestion/BACKLOG.md` |

Los docs viven en `AppOO/Doc/` (= `20-Proyecto/` del vault vía junction) y se comitean en el
repo del vault, aparte del commit de código. Que sean dos repos no los hace dos tareas.
