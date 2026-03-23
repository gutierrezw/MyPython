# AppOO — Convenciones específicas del proyecto

## Screener — columnas scrollables (orden fijo)

El orden de `_COL_DEFS` en `Class_Screener.py` y los valores en `insert_treeview` deben estar **siempre sincronizados** (posición a posición).

Orden acordado (después de las 4 fijas: Symbol, Name, Status, Cart):

| # | Campo DB | Header |
|---|----------|--------|
| 1 | lastPrice | Last |
| 2 | rotacion | Rotación |
| 3 | inst_score | Inst Score |
| 4 | inst_funds | # Inst |
| 5 | inst_ownership_pct | Inst % |
| 6 | fh_count | **13F Inst** |
| 7 | fh_total_value | 13F Value |
| 8 | volume | Volume |
| 9 | averageVolume | Avg Vol |
| … | … country, sector, industry … | |
| … | grossMargins | Gross M |
| … | ebitdaMargins | EBITDA M |
| … | operatingMargins | **Op M** ← va después de EBITDA M |
| … | inst_top_holder | Top Holder |
| … | website | Website |

## Nomenclatura homologada (Screener ↔ Consenso)

- `fh_count` → siempre se muestra como **"13F Inst"** (no "# Inst 13F", no "# Inst")
- `inst_funds` → siempre **"# Inst"** (fuente Yahoo, worldwide)
- Ambas pantallas deben usar los mismos nombres de columna para los mismos conceptos

## Consenso popup — columnas fijas

`_FIXED_COLS = ("Symbol", "Div", "Nombre", "13F Inst", "Inst %")`

El `# Inst` del popup Consenso usa `fh_count` (pipeline EDGAR propio), **no** `inst_funds` de Yahoo.

## Autonomía del usuario

- **Nunca ejecutar scripts ni procesos largos en background sin que el usuario lo pida.**
- Siempre entregar el comando listo y dejar que el usuario decida cuándo correrlo.
- El usuario quiere mantener control y aprender del proceso.

## Checklist antes de cerrar sesión

Antes de hacer commit, preguntar explícitamente:
1. ¿Quedó algún acuerdo de UI/columnas sin registrar?
2. ¿Hay ideas pendientes por guardar en memoria?
3. ¿Todos los cambios de código tienen su contraparte en datos (header + valor en mismo orden)?
