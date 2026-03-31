# AppOO — Convenciones específicas del proyecto

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

### Script de monitoreo
`SchemasSQL/mysql_index_analyzer.py` — analiza schema, índices sin uso, full scans y configuración InnoDB.

### Tarea recurrente
Cada lunes 8am → reporte HTML por Gmail (configurado en Claude Scheduled).

---

## Checklist antes de cerrar sesión

Antes de hacer commit, preguntar explícitamente:
1. ¿Quedó algún acuerdo de UI/columnas sin registrar?
2. ¿Hay ideas pendientes por guardar en memoria?
3. ¿Todos los cambios de código tienen su contraparte en datos (header + valor en mismo orden)?
4. ¿Se documentaron nuevos índices o cambios en la BD?
