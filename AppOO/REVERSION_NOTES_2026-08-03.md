# NOTAS DE REVERSIÓN — Sesión 2026-08-03

## Resumen de Cambios
Se corrigió uso inconsistente de parámetros `vehiculo` en llamadas a `get_yfinance()`.
**Cambios:** 4 archivos, 4 líneas modificadas.

---

## Cambios Realizados

### 1. **Class_customer.py:4821** (chart_setup)
**ANTES:**
```python
if self.vehiculo == "Stock":
    vehiculo = "hist"
elif self.vehiculo == "Crypto":
    vehiculo = "download"
```

**AHORA:**
```python
if self.vehiculo == "Stock":
    vehiculo = "Stock"
elif self.vehiculo == "Crypto":
    vehiculo = "Crypto"
```

**REVERTIR:** Cambiar línea 4821 de `"Stock"` → `"hist"` y línea 4824 de `"Crypto"` → `"download"`

---

### 2. **Class_customer.py:4754** (window_analisis)
**ANTES:**
```python
_veh_r = "hist" if self.vehiculo == "Stock" else ("download" if self.vehiculo == "Crypto" else self.vehiculo)
```

**AHORA:**
```python
_veh_r = "Stock" if self.vehiculo == "Stock" else ("Crypto" if self.vehiculo == "Crypto" else self.vehiculo)
```

**REVERTIR:** Cambiar línea 4754 de `"Stock"` → `"hist"` y `"Crypto"` → `"download"`

---

### 3. **dividends_rendimiento.py:30**
**ANTES:**
```python
x_none, pdatos = get_yfinance(ticket=symbol, vehiculo="hist")
```

**AHORA:**
```python
x_none, pdatos = get_yfinance(ticket=symbol, vehiculo="Stock")
```

**REVERTIR:** Cambiar `"Stock"` → `"hist"`

---

### 4. **Modulos_Comunes.py:573** (typo fix)
**ANTES:**
```python
activo, datos = get_yfinance(ticket=symbol, vehiculo="donwload", desde=desde, hasta=hoy)
```

**AHORA:**
```python
activo, datos = get_yfinance(ticket=symbol, vehiculo="download", desde=desde, hasta=hoy)
```

**REVERTIR:** Cambiar `"download"` → `"donwload"` (restaurar typo)

---

## Rationale
- `yf.Ticker().history()` **SÍ retorna Dividends y Stock Splits**
- `yf.download()` **NO retorna Dividends**
- Parámetros "hist" y "donwload" no son válidos, caen en el `else` de `get_yfinance()`
- Solución: usar parámetros válidos ("Stock", "Crypto", "download") consistentemente

## Result
✅ Todos los gráficos funcionan para Stock, Crypto y FCI
✅ Cache se limpió (sin duplicados)
✅ `get_yfinance()` sin cambios — estaba bien diseñado

## Para Revertir TODO
```bash
git checkout -- AppOO/Class_customer.py dividends_rendimiento.py Modulos_Comunes.py
```

---
**Sesión:** 2026-08-03  
**Responsable:** Claude Code (Haiku 4.5)  
**Status:** ✅ COMPLETADO Y VERIFICADO
