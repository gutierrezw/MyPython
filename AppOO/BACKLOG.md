# BACKLOG — AppOO Trading Platform

Historial de versiones al final del archivo.

---

## Pendiente

| # | Módulo | Tarea | Prioridad |
|---|--------|-------|-----------|
| ~~1~~ | ~~**Finanzas — PDF**~~ | ~~Parser BBVA tarjetas MC/Visa — `BbvaArTarjeta`~~ | ~~Alta~~ |
| ~~2~~ | ~~**Finanzas — PDF**~~ | ~~Parser BBVA cuenta corriente ARS — `BbvaArCuenta`~~ | ~~Alta~~ |
| ~~3~~ | ~~**Finanzas — PDF**~~ | ~~Parser Santander multi-sección (5 secciones en 1 PDF) — `SantanderAr`~~ | ~~Alta~~ |
| ~~4~~ | ~~**Finanzas — PDF**~~ | ~~Test end-to-end: cargar extracto real + verificar txns en BD~~ | ~~Alta~~ |
| ~~8~~ | ~~**Finanzas — FX**~~ | ~~`FinanceScreen.get_tasa(fiat, fecha)` — lookup tasa desde `booktrading`~~ | ~~Media~~ |
| 6 | **Infraestructura** | Plan de respaldo: BD + código + base de conocimiento Claude | Alta |
| ~~7~~ | ~~**Consenso/Telegram**~~ | ~~Gate Consenso sobre señal IA — `Agente_ConsensoCache` + gate BUY/SELL~~ | ~~Alta~~ |
| ~~11~~ | ~~**Finanzas — UI**~~ | ~~Dashboard Finance — gráfico evolución mensual ingresos/gastos~~ | ~~Media~~ |
| ~~12~~ | ~~**Stock/Cartera**~~ | ~~PHYS (ETF oro físico) — verificar categoriaActivo, decidir si participa en Consenso~~ | ~~Media~~ |
| ~~13~~ | ~~**Stock/Cartera**~~ | ~~ETFs `categoriaActivo='T'` descubiertos vía 13F — evaluar limpieza de market~~ | ~~Media~~ |
| 14 | **Stock/Cartera** | Señal Net — validar distribución real p33/p67 | Media |
| ~~15~~ | ~~**Integración**~~ | ~~Integrar Claude en ClassChatbot — consultar Claude desde chatbot interno~~ | ~~Media~~ |
| 25 | **Integración** | claude.ai en browser vía Violentmonkey — endpoint `/contexto` en TV server + userscript inyecta cartera | Media |
| ~~16~~ | ~~**TradingView**~~ | ~~Toggle "Controlar TV web" en la app~~ | ~~Media~~ |
| ~~17~~ | ~~**TradingView**~~ | ~~BUY/SELL desde TV: botón → `POST /order` → broker API → confirmación en panel~~ | ~~Media~~ |
| 18 | **Auto-Remediación** | BD: crear tablas `fallos`, `app_metrics`, `bd_metrics` | Media |
| 19 | **Auto-Remediación** | Agentes: `Agente_FallosLog` + `Agente_MetricasCodigo` + `Agente_MetricasBD` | Media |
| 22 | **Auto-Remediación** | UI tab System: panel "Fallos & Métricas" — treeview fallos + resumen calidad + desempeño BD | Media |
| 20 | **Infraestructura** | MCP local: servidor de herramientas para acceso a shell/BD desde co-work | Media |
| ~~23~~ | ~~**IA/Datos**~~ | ~~LLM local (Ollama) — clasificar ETFs por tipo diversificación~~ | ~~Baja~~ |
| ~~24~~ | ~~**Finanzas — Gmail**~~ | ~~Gmail/Finanzas Personales Fase 0: setup OAuth + limpieza bandeja~~ | ~~Baja~~ |
| 21 | **Mantenimiento** | Depuración imports — `Modulos_python.py` (vulture 63 hallazgos) | Baja |
| ~~26~~ | ~~**Stock/IB**~~ | ~~Fallback yfinance cuando IB offline — precios + dGyP header no actualizaban~~ | ~~Media~~ |
| ~~27~~ | ~~**Stock/Gráficos**~~ | ~~`grupo_sector()` infla "Consumer Cyclical" — sector preservation en `update_inversion_stock()` + fallback `sectores()` → `""`~~ | ~~Media~~ |
| 28 | **Infraestructura** | Proceso de mantenimiento del sistema vía Claude scheduled: check NTP con `ntplib` (alerta si deriva >500ms), limpieza logs rotativos, verificación servicios críticos (IB, Binance, MySQL). Sin elevar la app a admin. | Media |
| 29 | **TradingView** | Órdenes desde TV — handler `POST /order` en servidor TV conecta con broker: IB (`place_order` vía IBroks_Client) + Binance (`create_order` vía BinanceSpot); confirmación de ejecución devuelta al userscript TV | Alta |

---

## Historial

### v1.8 — 2026-04-24
**Cerrado:**
- ✅ ítem 26 — IB offline: `ib_offline_sync()` calcula `dgyp` directo en positions; `header_total_positions()` rama `else` actualiza header desde positions cuando `summary=None`; `Sesion` preservado para no romper exclusión mutua en `resumen`; dividendos IB preservados (yfinance no provee pagos pendientes)
- ✅ ítem 26 — `prepost=True` en yf.download para capturar pre/post market
- ✅ ítem 26 — label "IB OFFLINE (yf)" en amarillo; fallback renombrado `ib_offline_sync()`
- ✅ ítem 27 — `sectores()` fallback cambiado `"Consumer Cyclical"` → `""` para evitar contaminación
- ✅ ítem 27 — `update_inversion_stock()`: sector yfinance vacío → preserva sector existente en BD desde `p_positions`
- ✅ Fix `get_yfinance(Dividends)`: guard `hasattr(index, "tz")` para tickers deslistados con RangeIndex
- ✅ Fix `set_header_panel()` simetría: siempre elimina una clave antes de agregar la otra (evitaba `list index out of range` en `header_panel()`)

### v1.7 — 2026-04-20
**Cerrado:**
- ✅ floatShares coverage: 1242/1317 símbolos actualizados → inst_ownership_pct 96% cobertura
- ✅ inst_score v2 recalculado: 1034 símbolos con componente ownership real
- ✅ `MarketScreen.select`: branch country+sector faltante + return `[],[]` en except (crash Screener)
- ✅ `ltv_check_and_adjust` movido de `BinanceSpot` → `ServiciosCrypto` (arquitectura)
- ✅ Gate Consenso Telegram: `refresh_consenso_tags()` + `Agente_ConsensoCache` @wait_rate(300) + gate BUY/SELL sin voto Mod (ítem 7)
- ✅ BD: columnas `consenso_tag VARCHAR(15)` + `consenso_suma TINYINT` en `market`
- ✅ Funciones de voto promovidas a módulo en `Class_Screener.py` (reutilizables fuera de la UI)

**Diseño gate Consenso:**
- BUY pasa si `consenso_tag` ∈ {UNANIME, CONSENSO, TENDENCIA} — fundamentos apoyan
- SELL pasa si `consenso_tag` ∈ {ALERTA, SALIDA} — fundamentos confirman salida
- Voto Mod (señal IA técnica) excluido del cálculo del gate para evitar auto-confirmación
- `tag=None` → gate abierto (símbolo nuevo sin tag calculado aún)

### v1.6 — 2026-04-15
**Cerrado:**
- ✅ Chatbot rediseñado — ventana nativa OS, redimensionable, colores estilo claude.ai (ítem 15)
- ✅ `_consultar_claude()` — integración Claude Haiku API (stateless); contexto de cartera inyectado por consulta
- ✅ `_enviar()` no bloqueante via `threading.Thread` — spinner "Analizando..." mientras espera API
- ✅ Fix: ventana chatbot se cerraba al escribir en input — cambiado `FocusOut` → `WM_DELETE_WINDOW`
- ✅ Fix: crash `_get_insert_fallidos()` con Binance 451 geo-restriction — try/except devuelve sin crash

### v1.5 — 2026-04-14
**Cerrado:**
- ✅ Race condition `subscribe_stocks(55→39)` — `x_activos` local + asignación atómica en `update_inversion_stock()` (ítem 24-bis)
- ✅ 3 bugs en `lotesGainLost()` — gyp incluye comisión, roi por lote individual, c_lost usa x_costo
- ✅ Watchdog en `websocket_stream(Stock)` — detecta freeze 5 min y reconecta
- ✅ PHYS verificado — estrategia P01=Oro ya asignada en `inversion`; sin cambios necesarios (ítem 12)
- ✅ `Agente_ClasificadorETF` — reemplaza Ollama por Claude Haiku API; clasifica ETFs en P01-P05 vía `EstrategiaInversion`; write-once; key en `sesion('ClaudeAPI')` (ítem 23)
- ✅ ETFs `categoriaActivo='T'` — decisión: ETFs fuera de market, manejados por Agente_ClasificadorETF (ítem 13)

### v1.4 — 2026-04-13
**Cerrado:**
- ✅ TradingView toggle "Controlar TV web" — activar/desactivar control desde la app (ítem 16)
- ✅ BUY/SELL desde TV: botón → `POST /order` → broker API → confirmación en panel (ítem 17)
- ✅ Gmail/Finanzas Personales Fase 0: setup OAuth + limpieza bandeja (ítem 24)

### v1.3 — 2026-04-13
**Cerrado:**
- ✅ `Class_ServiciosCrypto.py` — módulo Earn↔Spot (`earn_spot_balances`, `earn_subscribe`, `earn_redeem`, `ltv_check_and_adjust`)
- ✅ UI Gestión Earn↔Spot en AnalisisCrypto — treeview con scrollbar, columna USDT, botones Spot→Earn / Earn→Spot
- ✅ Fix %Mrg/Risk oscilación panel: `LtvControl` y `_seccion_deuda` ahora usan `earn_spot_balances` como base de `CapitalNeto`
- ✅ Fix `_seccion_deuda`: guard `if prestamos:` evita reset DataHub a 0 cuando API falla en auto-refresh
- ✅ Fix beta race condition en Analysis: `_refresh_mrg_display()` actualiza Beta/Mrg tras thread yfinance
- ✅ `MarketScreen.select_all(account)` — sin filtro tipo, para `Agente_StockBeta` (incluye todos los stocks)
- ✅ Gráfico LTV → stacked area (rojo=deuda, azul=colateral, línea blanca=LTV%)
- ✅ `margin_risk_status`: colores mejorados para fondo oscuro (`#f1c40f`, `#e67e22`, `#e74c3c`)
- ✅ `Class_Analisis.py`: 11 `print()` de errores → `_logger.error()` para trazabilidad en Debugging tab
- ✅ Panel Crypto: logging WARNING cuando usa fallback equity (`neto_api=0`)

### v1.2 — 2026-04-13
**Cerrado:**
- ✅ `get_tasa(fiat, fecha)` — lookup tasa FX desde `booktrading` (implementado)
- ✅ `BbvaArTarjeta` — parser extractos BBVA tarjetas MC/Visa (PDF)
- ✅ `BbvaArCuenta` — parser extractos BBVA cuenta corriente ARS (PDF)
- ✅ `SantanderAr` — parser extractos Santander multi-sección (5 secciones en 1 PDF)
- ✅ Test end-to-end extractos reales → `fin_transactions` en BD

### v1.1 — 2026-04-13
**Cerrado:**
- ✅ `BinancePay` — adaptador API remesas Pay → gastos USDT en `fin_transactions`
- ✅ `sync_binance_investment()` — registro sintético mensual Retención USDT
- ✅ KPIs Finance rediseñados — valor principal U$ (`amount_usdt`), sub-línea ARS; cuadran con categorías
- ✅ `get_kpis()` reescrita — `COALESCE(category_type,'expense')` como único criterio; 7 campos
- ✅ `get_monthly_evolution()` — últimos N meses para gráfico de tendencia anual
- ✅ `_EvolucionChart` — gráfico anual Ingresos/Gastos/Invertido integrado en panel izquierdo
- ✅ `save_rule()` fix — retroactivo sobre `classified_by=NULL|rule`; fix `Already closed`
- ✅ `fin_banks` — eliminadas 5 columnas sin uso (`adapter_class`, `date_format`, `delimiter`, `encoding`, `currency`)
- ✅ `fetch_pay_transactions()` — endpoint Binance Pay con paginación 90 días
- ✅ `Agente_ExtractosWatcher` — registrado en loop agentesIA (estaba definido pero nunca llamado)
- ✅ `scan_extractos()` — procesados 7 PDFs manualmente (3 BBVA + BDV + Santander)

### v1.0 — 2026-04-05
**Cerrado:**
- ✅ TradingView integrado — servidor HTTP local puerto 5050, Violentmonkey, shapes nativos TV
- ✅ Módulo Finanzas Personales — diseño, 7 tablas MySQL, 9 cuentas, 48 categorías, 75 reglas
- ✅ `FinanceScreen` en `Modulos_Mysql.py` + `FinancePanel` tab Finance en la app
- ✅ Backfill VES 12 meses — 37 operaciones SELL en `booktrading` (`VES-0001`)
- ✅ `trade_USDT_diario()` — carga diaria ARS (BUY) + VES (SELL) desde la app
- ✅ `get_c2c_trade_history()` — acepta parámetro `fiat` para filtrar por moneda

---

## Flujo de trabajo — rama docs

**`docs` es la fuente de verdad para todos los archivos `.md`.**

- Editar `.md` → pararse en `docs`, editar, commitear
- Llevar cambio a `Appoo` → `git checkout Appoo && git checkout docs -- <archivo>.md`
- Al cerrar sesión → actualizar `BACKLOG.md` en `docs` con lo completado
