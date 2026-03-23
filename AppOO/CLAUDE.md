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

## Checklist antes de cerrar sesión

Antes de hacer commit, preguntar explícitamente:
1. ¿Quedó algún acuerdo de UI/columnas sin registrar?
2. ¿Hay ideas pendientes por guardar en memoria?
3. ¿Todos los cambios de código tienen su contraparte en datos (header + valor en mismo orden)?
