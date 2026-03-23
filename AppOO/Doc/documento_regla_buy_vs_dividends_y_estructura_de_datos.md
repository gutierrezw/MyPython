## Regla de Clasificación Buy / Dividends

La clasificación entre **buy** y **dividends** se define de forma determinística a partir de la existencia de dividendos en la posición.

**Regla de negocio:**
- Si el activo **no tiene dividendos** (`position["dividendo"] == 0`) ⇒ **buy**
- Si el activo **tiene dividendos** (`position["dividendo"] > 0`) ⇒ **dividends**

Esta regla es excluyente y obligatoria: un activo pertenece **solo a una** de las dos categorías.

---

## Variable de Control

La variable `BuyDividends` encapsula la decisión y es utilizada como clave dinámica dentro de la estructura de datos:

- `"buy"` cuando no hay dividendos
- `"dividends"` cuando existen dividendos

Esto garantiza consistencia en toda la arquitectura y evita estados ambiguos.

---

## Estructura de Datos Asociada a la Compra

La información generada para una operación de compra (ya sea **buy** o **dividends**) se almacena bajo la clave determinada por `BuyDividends`.

Cada bloque contiene los siguientes campos:

### Métricas de rendimiento
- **ganancia precio**: variación de precio estimada o realizada.
- **ganancia inversión**: ganancia total sobre el capital invertido.
- **retorno post**: retorno proyectado luego de la operación.

### Datos de posición
- **cantidad buy**: cantidad comprada en la operación.
- **cantidad post**: cantidad total luego de la compra.
- **last**: último precio de mercado.
- **avgcost**: costo promedio previo.
- **avgCost post**: nuevo costo promedio luego de la compra.

### Objetivo
- **objetivo**: objetivo estratégico asociado al activo.

### Dividendos
- **dividendYield**: tasa nominal de dividendos.
- **exDividendDate**: fecha ex-dividendo.
- **pre dividendos**: dividendos acumulados antes de la compra.
- **post dividendos**: dividendos proyectados luego de la compra.

### Costos
- **pre costobase**: base de costo previa.
- **post costobase**: base de costo posterior a la compra.

---

## Integración en `self.info[symbol]`

Dentro de `self.info[symbol]`, el bloque generado se integra de la siguiente forma:

- Activos sin dividendos incluyen la clave **buy**.
- Activos con dividendos incluyen la clave **dividends**.

Nunca se almacenan ambas claves simultáneamente para un mismo símbolo.

---

## Implicación para el Rebalanceo

- El rebalanceo **no evalúa dividendos directamente**.
- El rebalanceo consume la información ya clasificada bajo **buy** o **dividends**.
- La asignación de efectivo se realiza en una etapa posterior y separada.

Esta separación garantiza claridad, trazabilidad y escalabilidad del sistema.

---

## Campos Yahoo Finance — Dividendos

Referencia de campos yfinance para operaciones con dividendos. Errores comunes documentados.

| Campo | Descripción | Uso correcto |
|-------|-------------|--------------|
| `dividendRate` | Pago **individual** (NO anual) | ❌ NO usar para cálculo anual. Ej: trimestral $0.50 = $2.00/año |
| `trailingAnnualDividendRate` | TTM — suma últimos 12 meses | ✅ Usar para dividendo anual real |
| `dividendYield` | Rendimiento % | ✅ Para filtros de yield |
| `trailingAnnualDividendYield` | Yield basado en TTM | ✅ Más confiable que `dividendYield` |
| `exDividendDate` | Fecha ex-dividendo | ✅ Para validar pagos próximos |
| `dividendDate` | Fecha de pago | ℹ️ Informativo |
| `payoutRatio` | Ratio pago (dividendos/ganancias) | ✅ Para análisis de sostenibilidad |
| `fiveYearAvgDividendYield` | Promedio 5 años | ✅ Para comparar vs. actual |

### Validaciones implementadas en `dividends_en_market_stock()`

- **Frescura de datos**: si último pago fue hace más de 18 meses → advertencia (datos posiblemente obsoletos — yfinance puede retener históricos de activos que dejaron de pagar)
- **Meses de pago**: se usan últimos 12 meses móviles (TTM), no año calendario anterior
- **Frecuencia detectada**: mensual / trimestral / semestral / anual según conteo de pagos TTM

### Pendiente
Migrar a IB API para dividendos — campos disponibles vía WebSocket IB:
`"7286"` dividendo actual · `"7287"` yield% · `"7288"` ex-date · `"7672"` TTM · `"7671"` próximo pago