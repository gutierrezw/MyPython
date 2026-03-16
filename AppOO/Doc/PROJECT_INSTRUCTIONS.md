# AppOO – Sistema de Inversión Personal (Project Instructions)
**Autor:** Wilmer Gutierrez  
**Stack:** Python 3.11 · MySQL (bdinv) · Dash · Windows 11  
**Repo:** https://github.com/gutierrezw/MyPython  
**App principal:** DashMainV9_ia.py

---

## Visión del Sistema

Plataforma de inversión personal estilo Bloomberg que combina:
1. **Fundamentales** — EDGAR (10-K, 10-Q, XBRL) + ValuationEngine.py
2. **Mercado** — Yahoo Finance REST + yfinance + Interactive Brokers API
3. **Flujo institucional** — Class_InstitucionalScore.py (en desarrollo)
4. **Crypto** — Binance SPOT (WebSocket + REST)

---

## Arquitectura Central

### Tabla `Market` (MySQL · bdinv)
Universo invertible: empresas con dividendos, cartera activa, seguimiento.  
Campos nuevos pendientes: `inst_funds`, `inst_shares`, `inst_score`, `inst_update`

### Módulos principales
| Módulo | Archivo | Estado |
|--------|---------|--------|
| Screener NASDAQ/NYSE | Agente_Screener | ✅ |
| Cache en memoria TTL | Class_DataFrame.py → CacheHut | ✅ |
| Rebalanceo 4 dimensiones | RebalanceEngine | ✅ |
| Modelos IA Buy/Sell | Class_IA_modelos.py | ✅ |
| Preservación ganancias | Agente_ManagerPreservation | ✅ |
| Bot Crypto Binance SPOT | Class_tradingBot.py | ✅ |
| UI BotCrypto | Class_BotCryptoUI.py | ✅ |
| Score institucional | Class_InstitucionalScore.py | 🔧 En diseño |
| Valoración EDGAR | ValuationEngine.py | 🔧 En progreso |

---

## Componentes Clave

### CacheHut
`DataFrameCache(maxsize=200, ttl=1800)` — cache global de DataFrames yfinance/Binance.  
Decorador `@use_dataframe_cache`. Parámetro `use_cache=False` para forzar refresh.

### RebalanceEngine — 4 dimensiones
1. **Dividendos** — equilibrio mensual de ingresos (TTM, no año calendario)
2. **Sectores** — equiponderación dinámica (100 / N sectores)
3. **Tipos de activo** — balance estructural, mínimo 80% generando ingresos
4. **Regiones** — diversificación geográfica equiponderada

Score final: `score_estructural × (1 + impacto_monetario_norm) × valuation_factor`

### Modelos IA
- **modelo_buyv01** — RandomForest, umbral_buy=0.65, features: ganancia_precio, dividend_yield, score, técnicos
- **modelo_sellv01** — RandomForest, umbral_sell=0.65, features: RSI/MACD/EMA multi-timeframe, ROI
- Ciclo: oportunidades → Telegram (etiquetado manual) → reentrenamiento

### BotCrypto Binance SPOT
- Cuenta: B0000002 | Universo: tabla `otros_activos`
- Estrategia: RSI + MACD + EMA con filtro estructural EMA100/EMA200
- Contexto superior multi-timeframe con penalización de score (-5 si contexto NO_BULL)
- Selector dinámico de timeframe (30m vs 1H según ATR% y volumen relativo)
- Estado persistente en MySQL + sincronización con Binance al reiniciar

### Sesiones (tabla `sesion`)
Refactorizado a funciones específicas:
- `get_sesion_by_vehiculo(vehiculo)` — reemplazó select_sesion()
- `update_sesion_fecha_orden()`, `update_sesion_fecha_fund()`, `update_sesion_strategy()`
- Vehículos: Stock · Crypto · BotCrypto · BBVA.ARS · SANT.ARS · Chatbot

### Regla Buy/Dividends
- `dividendo == 0` → clave `"buy"` en self.info[symbol]
- `dividendo > 0` → clave `"dividends"` en self.info[symbol]
- Nunca ambas simultáneamente

---

## Módulo en Diseño: Class_InstitucionalScore.py
**Objetivo:** Identificar empresas de dividendos acumuladas por fondos (Vanguard, BlackRock, etc.)  
**Flujo:** Market → yfinance institutional_holders → Institutional Score → UPDATE Market  
**Fórmula:** `score = log(inst_funds) + log(inst_shares)`  
**Futura evolución:** cambios trimestrales + filings 13F SEC

---

## Convenciones de Código

- Type hints y docstrings en toda función nueva
- `logging` en producción, nunca `print()`
- SQL parametrizado (refactorización select_sesion completada dic-2025)
- Datos faltantes de yfinance: registrar símbolo y continuar (no romper flujo)
- `dividendRate` ≠ dividendo anual → usar `trailingAnnualDividendRate`
- Validar frescura de dividendos: datos > 18 meses → warning

---

## Carpeta de Especificaciones
`C:\Users\InversionesWildaga\Documents\MyPython\AppOO\Doc\`  
Cada módulo tiene su propio `.md` con diseño detallado.  
Antes de implementar, consultar el `.md` correspondiente.

---

## Roadmap Personal
1. ✅ Motor de valoración (ValuationEngine.py)
2. ✅ Dashboard financiero histórico  
3. ⬜ Portfolio Optimizer (IO)
4. ⬜ Retirement Simulator (Monte Carlo)
5. 🔧 Sistema de alertas inteligentes
6. 🔧 Class_InstitucionalScore.py
