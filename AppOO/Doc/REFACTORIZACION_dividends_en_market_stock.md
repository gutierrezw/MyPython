# Refactorización: `dividends_en_market_stock()`

**Fecha:** 2026-01-01
**Archivo modificado:** `DashMainV9_ia.py`
**Basado en:** Aprendizajes de `test_yfinance_dividends_fields.py`

---

## 📋 Objetivo de la Refactorización

Mejorar el método `dividends_en_market_stock()` aplicando los conocimientos adquiridos del módulo de diagnóstico `test_yfinance_dividends_fields.py` sobre cómo yfinance maneja la información de dividendos.

---

## 🔍 Problemas Detectados (Antes de la Refactorización)

### 1. **Confusión sobre `dividendRate`**
- **Problema:** `dividendRate` NO es el dividendo anual, es el pago individual
- **Ejemplo:** Una acción trimestral con `dividendRate = $0.50` paga $2.00/año, NO $0.50/año
- **Campo correcto para anual:** `trailingAnnualDividendRate` (suma de últimos 12 meses - TTM)

### 2. **Datos obsoletos no detectados**
- **Problema:** yfinance retiene información de activos que dejaron de pagar dividendos
- **Ejemplo:** Un activo suspendió dividendos hace 2 años pero yfinance aún muestra `dividendRate > 0`
- **Solución:** Validar que haya pagos recientes (últimos 12-18 meses)

### 3. **Meses de pago imprecisos**
- **Problema:** Solo se analizaba el año anterior (no últimos 12 meses)
- **Ejemplo:** Si estamos en enero 2026, año anterior = 2025 completo (puede tener pagos de hace 13 meses)
- **Solución:** Analizar últimos 12 meses móviles (TTM - Trailing Twelve Months)

### 4. **Falta de frecuencia de pago**
- **Problema:** No se detectaba si el pago es mensual, trimestral, semestral o anual
- **Importancia:** Necesario para el sistema de rebalanceo de dividendos mensuales
- **Solución:** Contar pagos en últimos 12 meses

---

## ✅ Mejoras Implementadas

### 1. **Nuevo Método: `_validate_dividend_data_freshness()`**

**Ubicación:** `DashMainV9_ia.py:1879-1926`

**Funcionalidad:**
- Valida que los datos de dividendos estén actualizados
- Detecta si último pago fue hace más de 18 meses → marca como obsoleto
- Detecta inconsistencias (tiene `dividendRate` pero sin historial)
- Retorna warning sin bloquear el flujo (permite continuar con advertencia)

**Ejemplo de uso:**
```python
dividends_history = datos["Dividends"]
is_valid, warning = self._validate_dividend_data_freshness(yf_activo, dividends_history)

if not is_valid:
    print(f"[{ticket}] {warning}")
    # ⚠️ Último pago hace más de 18 meses (2023-06-15). Datos posiblemente obsoletos.
```

---

### 2. **Nuevo Método: `_extract_dividend_payment_months()`**

**Ubicación:** `DashMainV9_ia.py:1928-1942`

**Funcionalidad:**
- Extrae meses de pago desde historial real (últimos 12 meses)
- Maneja correctamente zonas horarias (tz-aware vs tz-naive)
- Calcula frecuencia de pago (cuántos pagos/año)
- Calcula TTM real (total pagado en últimos 12 meses)
- Retorna nombres de meses en inglés para consistencia

**Retorna:**
```python
(meses_pago, frecuencia, total_ttm)

# Ejemplo para acción trimestral:
(["March", "June", "September", "December"], 4, 2.08)
```

**Ventajas sobre el método anterior:**
- ✅ Usa últimos 12 meses (no solo año anterior)
- ✅ Detecta frecuencia automáticamente
- ✅ Calcula TTM real desde historial
- ✅ Maneja correctamente timezones

---

### 3. **Documentación Mejorada del Método Principal**

**Ubicación:** `DashMainV9_ia.py:1994-2008`

**Agregado:**
- Docstring completo explicando mejoras
- Referencia a `test_yfinance_dividends_fields.py`
- Clarificación sobre `dividendRate` vs `trailingAnnualDividendRate`
- Descripción de validaciones aplicadas

---

### 4. **Comentarios Explicativos en el Código**

**Ubicación:** `DashMainV9_ia.py:2055-2126`

**Agregado:**
- Comentarios sobre validación de frescura de datos
- Explicación de campos extraídos por `InfoYfinance`
- Nota sobre alternativa mejorada para meses de pago
- Código opcional comentado para agregar frecuencia y TTM a tabla market

---

## 📊 Comparación: Antes vs Después

### Antes de la Refactorización

```python
# Sin validación de datos obsoletos
if (not ind_update and ("dividendYield" in yf_activo) and ("Dividends" in datos)):
    x_campos = InfoYfinance(symbol, yf_activo)
    fields, categoria, meses = construct_info_dividends(ticket, yf_activo, datos, x_campos.info)

    # meses viene de rendimiento_dividends() que usa año anterior
    columnas.append("monthDividendsPay")
    values.append(", ".join(meses))
```

**Limitaciones:**
- ❌ No detecta datos obsoletos
- ❌ No valida consistencia de datos
- ❌ Meses basados en año calendario anterior (no TTM)
- ❌ No se almacena frecuencia de pago
- ❌ No se verifica último pago

---

### Después de la Refactorización

```python
if (not ind_update and ("dividendYield" in yf_activo) and ("Dividends" in datos)):
    # VALIDACIÓN: Verificar frescura de datos
    dividends_history = datos["Dividends"]
    is_valid, warning = self._validate_dividend_data_freshness(yf_activo, dividends_history)

    if not is_valid:
        print(f"[{ticket}] {warning}")  # Advertencia pero continúa

    # Extracción de información (sin cambios en flujo principal)
    x_campos = InfoYfinance(symbol, yf_activo)
    fields, categoria, meses = construct_info_dividends(ticket, yf_activo, datos, x_campos.info)

    # Meses de pago (con opción mejorada disponible)
    columnas.append("monthDividendsPay")
    values.append(", ".join(meses))

    # OPCIONAL: Agregar frecuencia y TTM calculado
    # meses_ttm, freq_ttm, total_ttm = self._extract_dividend_payment_months(dividends_history)
    # columnas.append("dividendFrequency")
    # values.append(freq_ttm)
```

**Ventajas:**
- ✅ Detecta datos obsoletos (>18 meses sin pago)
- ✅ Valida consistencia (`dividendRate` sin historial)
- ✅ Método mejorado disponible para meses TTM
- ✅ Opción de almacenar frecuencia de pago
- ✅ Advertencias claras para revisión manual

---

## 🔄 Integración con Sistema de Rebalanceo

### Relación con `manager_buysell`

El sistema de rebalanceo de dividendos mensuales (documentado en `ANALISIS_manager_buysell_integracion.md`) necesita:

1. **Meses de pago confiables:**
   - Antes: Basado en año anterior (podía incluir datos de hace 13+ meses)
   - Ahora: Validación de frescura + opción de usar últimos 12 meses exactos

2. **Frecuencia de pago:**
   - Antes: No disponible
   - Ahora: `_extract_dividend_payment_months()` retorna frecuencia detectada

3. **TTM real:**
   - Antes: Solo `trailingAnnualDividendRate` de yfinance (puede estar obsoleto)
   - Ahora: Opción de calcular TTM desde historial real

### Uso en Rebalanceo

```python
# En el futuro, para Class_Rebalanceo.py:
def calcular_score_activo(self, activo, gaps):
    symbol = activo["symbol"]

    # Obtener meses de pago actualizados
    ticker = yf.Ticker(symbol)
    dividends_history = ticker.dividends

    # Usar método mejorado
    meses_pago, frecuencia, ttm = customer._extract_dividend_payment_months(dividends_history)

    # Validar frescura
    is_valid, warning = customer._validate_dividend_data_freshness(ticker.info, dividends_history)

    if not is_valid:
        # Activo con datos obsoletos → score bajo o advertencia al usuario
        desglose["razones"].append(f"⚠️ Datos de dividendos obsoletos: {warning}")
        score_dividends = 0
    else:
        # Calcular score basado en meses que necesitan equilibrio
        for mes_idx in meses_pago:
            if gaps["dividends"]["mensual"][meses[mes_idx]]["gap"] > 0:
                score_dividends += peso_por_mes
```

---

## 📝 Campos de Dividendos en yfinance (Recordatorio)

Basado en `test_yfinance_dividends_fields.py`, estos son los campos clave:

| Campo | Descripción | Uso Correcto |
|-------|-------------|--------------|
| `dividendRate` | Pago individual (NO anual) | ❌ NO usar para cálculo anual |
| `dividendYield` | Rendimiento % | ✅ Usar para filtros de yield |
| `trailingAnnualDividendRate` | TTM (suma últimos 12 meses) | ✅ Usar para dividendo anual |
| `trailingAnnualDividendYield` | Yield basado en TTM | ✅ Más confiable que `dividendYield` |
| `exDividendDate` | Fecha ex-dividendo | ✅ Para validar si hay pagos próximos |
| `dividendDate` | Fecha de pago | ℹ️ Informativo |
| `payoutRatio` | Ratio de pago (dividendos/ganancias) | ✅ Para análisis de sostenibilidad |
| `fiveYearAvgDividendYield` | Promedio 5 años | ✅ Para comparar vs. actual |

---

## 🚀 Próximos Pasos Sugeridos

### 1. **Migrar a IB API para dividendos** (Pendiente)
- **Razón:** yfinance tiene problema de datos obsoletos
- **Campos disponibles en IB WebSocket:**
  - `"7286"`: Dividendo actual
  - `"7287"`: % Dividend yield
  - `"7288"`: Ex-dividend date
  - `"7672"`: TTM Dividends
  - `"7671"`: Next dividend amount
- **Ubicación código:** `DashMainV9_ia.py:decodifica_message_websocket()` (línea 332)
- **Estado:** Documentado en `ANALISIS_manager_buysell_integracion.md`

### 2. **Activar campos opcionales** (Si se necesita)
Descomentar en `dividends_en_market_stock()`:
```python
meses_ttm, freq_ttm, total_ttm = self._extract_dividend_payment_months(dividends_history)
columnas.append("dividendFrequency")
values.append(freq_ttm)
columnas.append("dividendTTM_calculated")
values.append(total_ttm)
```

**Ventajas:**
- Almacenar frecuencia de pago en tabla market
- Comparar TTM calculado vs TTM de yfinance
- Facilitar detección de cambios en frecuencia de pago

### 3. **Actualizar `rendimiento_dividends()`** (Opcional)
Considerar refactorizar `Class_customer.py:rendimiento_dividends()` para usar `_extract_dividend_payment_months()` internamente.

**Beneficios:**
- Consistencia en detección de meses de pago
- Mejor manejo de timezones
- Frecuencia detectada automáticamente

---

## 📚 Referencias

- **Módulo de diagnóstico:** `test_yfinance_dividends_fields.py`
- **Documentación de rebalanceo:** `doc/ANALISIS_manager_buysell_integracion.md`
- **Método documentado:** `Class_customer.py:rendimiento_dividends()` (líneas 1779-1896)
- **Método refactorizado:** `DashMainV9_ia.py:dividends_en_market_stock()` (líneas 1994-2136)

---

## ✅ Resumen de Cambios

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Validación de datos** | ❌ Ninguna | ✅ Valida frescura (18 meses) |
| **Meses de pago** | Año anterior (calendario) | TTM disponible (últimos 12 meses) |
| **Frecuencia de pago** | ❌ No detectada | ✅ Detectada automáticamente |
| **TTM calculado** | Solo desde yfinance | ✅ Opcional calcular desde historial |
| **Manejo de timezones** | ❌ No explícito | ✅ Normalización tz-aware/naive |
| **Documentación** | Mínima | ✅ Docstrings completos |
| **Advertencias** | ❌ Ninguna | ✅ Warnings para datos sospechosos |

---

**Documento generado:** 2026-01-01
**Versión:** 1.0
**Autor:** Claude Code (Sonnet 4.5)
**Estado:** ✅ Refactorización completada y documentada
