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
| ~~6~~ | ~~**Infraestructura**~~ | ~~Plan de respaldo: BD + código + base de conocimiento Claude~~ | ~~Alta~~ |
| ~~7~~ | ~~**Consenso/Telegram**~~ | ~~Gate Consenso sobre señal IA — `Agente_ConsensoCache` + gate BUY/SELL~~ | ~~Alta~~ |
| ~~11~~ | ~~**Finanzas — UI**~~ | ~~Dashboard Finance — gráfico evolución mensual ingresos/gastos~~ | ~~Media~~ |
| ~~12~~ | ~~**Stock/Cartera**~~ | ~~PHYS (ETF oro físico) — verificar categoriaActivo, decidir si participa en Consenso~~ | ~~Media~~ |
| ~~13~~ | ~~**Stock/Cartera**~~ | ~~ETFs `categoriaActivo='T'` descubiertos vía 13F — evaluar limpieza de market~~ | ~~Media~~ |
| 14 | **Stock/Cartera** | Señal Net — validar distribución real p33/p67 | Media |
| ~~15~~ | ~~**Integración**~~ | ~~Integrar Claude en ClassChatbot — consultar Claude desde chatbot interno~~ | ~~Media~~ |
| ~~25~~ | ~~**Integración**~~ | ~~claude.ai en browser vía Violentmonkey — endpoint `/contexto` en TV server + userscript inyecta cartera~~ | ~~Media~~ |
| ~~16~~ | ~~**TradingView**~~ | ~~Toggle "Controlar TV web" en la app~~ | ~~Media~~ |
| ~~17~~ | ~~**TradingView**~~ | ~~BUY/SELL desde TV: botón → `POST /order` → broker API → confirmación en panel~~ | ~~Media~~ |
| 18 | **Auto-Remediación** | BD: crear tablas `fallos`, `app_metrics`, `bd_metrics` | Media |
| 19 | **Auto-Remediación** | Agentes: `Agente_FallosLog` + `Agente_MetricasCodigo` + `Agente_MetricasBD` | Media |
| 22 | **Auto-Remediación** | UI tab System: panel "Fallos & Métricas" — treeview fallos + resumen calidad + desempeño BD | Media |
| 20 | **Infraestructura** | MCP local: servidor de herramientas para acceso a shell/BD desde co-work | Media |
| ~~23~~ | ~~**IA/Datos**~~ | ~~LLM local (Ollama) — clasificar ETFs por tipo diversificación~~ | ~~Baja~~ |
| ~~24~~ | ~~**Finanzas — Gmail**~~ | ~~Gmail/Finanzas Personales Fase 0: setup OAuth + limpieza bandeja~~ | ~~Baja~~ |
| 21 | **Mantenimiento** | Depuración imports — `Modulos_python.py` (vulture 63 hallazgos) | Baja |
| 39 | **Mantenimiento** | Unificar `insert_booktrading` + `insert_booktrading_bottrader` en `Modulos_Mysql.py` — misma lógica core duplicada, difieren en cálculo de `basico` y helpers; requiere testing antes de tocar | Baja |
| ~~26~~ | ~~**Stock/IB**~~ | ~~Fallback yfinance cuando IB offline — precios + dGyP header no actualizaban~~ | ~~Media~~ |
| ~~27~~ | ~~**Stock/Gráficos**~~ | ~~`grupo_sector()` infla "Consumer Cyclical" — sector preservation en `update_inversion_stock()` + fallback `sectores()` → `""`~~ | ~~Media~~ |
| 🧪 37 | **FCI/Selenium** | `download_cnv_selenium.py` — Safe Browsing Chrome bloquea descarga Excel de CNV → `.crdownload` huérfanos en `tmp/`; fix: `safebrowsing.enabled=False` + `--safebrowsing-disable-download-protection` + poll hasta `.xlsx` disponible (max 90s) | Media |
| 28 | **Infraestructura** | Proceso de mantenimiento del sistema vía Claude scheduled: check NTP con `ntplib` (alerta si deriva >500ms), limpieza logs rotativos, verificación servicios críticos (IB, Binance, MySQL). Sin elevar la app a admin. | Media |
| ~~29~~ | ~~**TradingView**~~ | ~~Órdenes desde TV — handler `POST /order` en servidor TV conecta con broker: IB (`place_order` vía IBroks_Client) + Binance (`create_order` vía BinanceSpot); confirmación de ejecución devuelta al userscript TV~~ | ~~Alta~~ |
| ~~30~~ | ~~**Stock/Mantenimiento**~~ | ~~Correr `run_mark_delisted.py` (17 símbolos) + `run_rebuild_diaria_cartera.py`~~ | ~~Alta~~ |
| 🧪 31 | **Stock/IB** | Verificar header tras reconexión IB: Mrg/Risk, Cash y label "IB OFFLINE" deben recuperarse con fix `self.summary = {}` en `schedule_ib_offline_sync` (DashMainV9_ia.py) | Media |
| 🧪 32 | **Stock/yfinance** | Verificar que rebuild genera precios ABX correctos (~$53 CAD vía ABX.TO) — `convierte_ticket_stock` mapea CAD→.TO en `Modulos_Utilitarios.py` | Media |
| ~~33~~ | ~~**Stock/Mantenimiento**~~ | ~~`fecha_deliste` en booktrading: 1) ALTER TABLE, 2) `run_mark_delisted.py` (con fechas), 3) `run_balance_booktrading.py` (stock residual→0), 4) rebuild completo → cierra gap nr_gyp vs IB~~ | ~~Alta~~ |
| 🧪 34 | **Stock/Mantenimiento** | Agente Splits: detectar splits vía `yf.splits`, ajustar `basico` y `stock` en booktrading — fuente principal del gap restante ~$2K vs IB | Media |
| 35 | **Stock/Mantenimiento** | Completar `fecha_deliste` para 12 símbolos con `None` (ETM, GHSI, GPS, NYMT, PBPB, PLM, SSUP, STON, ZY…) — buscar fechas exactas de fusión/privada | Baja |
| ~~36~~ | ~~**Telegram/Órdenes**~~ | ~~Guard anti doble-tap en botón Aprobar — `handle_callback` + `put_order_aprovate_telegram`~~ | ~~Alta~~ |
| 38 | **Gmail/Productividad** | Depuración bandeja Gmail con Claude Desktop: clasificar, etiquetar y archivar correos masivos; definir reglas de limpieza recurrente; usar MCP Gmail tools de Claude Desktop | Media |

---

## Historial

### v2.4 — 2026-05-05
**Booktrading monitor + corrección cantidades:**
- 🐛 Root cause identificado y corregido: `insert_booktrading` leía `ustock` antes del commit → segundo insert del mismo símbolo/fecha quedaba con stock incorrecto
- ✅ Fix `Modulos_Mysql.py` — `insert_booktrading` + `insert_booktrading_bottrader`: tras INSERT+commit, UPDATE recalcula `stock = SUM(cantidad)` desde BD usando `cursor.lastrowid` — elimina el desfase sin importar cuántas transacciones del mismo símbolo se inserten en la misma fecha
- ✅ `AppTest/run_monitor_booktrading.py` — compara `booktrading.stock` del último registro vs `inversion.position` (fuente de verdad IB); reporta desvíos; flag `--fix` genera SQLs correctivos
- ✅ 4 cantidades corregidas manualmente en booktrading + inversion: CRNT (+20 fantasma — fila duplicada 2026-03-23), SKLZ (+12 fantasma), BTI (+1 — doble entrada 2026-03-31), CVS (−2 — compras faltantes)
- ✅ KYN corregido — booktrading mostraba stock=150 pero inversion=0 (posición cerrada)
- ✅ Monitor post-corrección: 1 alerta activa restante — CFRXQ (340 en inversion, sin registros en booktrading)

**FCI extractos — fixes aplicados (sesión 2026-05-03/05):**
- ✅ `construir_extracto_fci` en `Class_gestion.py`: `navcierre` toma de `performa_inversion.value` (valor mercado fin de mes); `costobase` toma de `performa_inversion.costo_base`; eliminado cálculo derivado que igualaba navcierre a costobase cuando gyp=0
- ✅ `check_performance_vehiculo`: valida que performa llegue hasta el último día hábil del mes (`ultimo_dia_habil()`) antes de permitir el cierre
- ✅ `insert_extracto` en `Modulos_Mysql.py`: DELETE mes antes de INSERT → re-cierre no duplica registros
- ✅ `retiros`: fórmula corregida a `basico × cantidad / factor_cambio` (capital puro, sin ganancias)
- ✅ `AppTest/run_diag_extractos_fci.py` — script diagnóstico mes a mes: Nav_BD vs Nav_New, CB_BD vs CB_New
- ⚠️ `diaria_book_performance` Stock: proceso no corrió 2026-05-02 ni 2026-05-03 (solo 1 registro en diaria_performance esos días — solo AMT)

### v2.3 — 2026-05-02
**Cerrado:**
- ✅ ítem 6 — `backup_diario.bat` v2.2: dumps planos en Drive sin subcarpetas, retención 5 últimos `.sql` por conteo, log fijo `backup_diario.log` (sobreescribe cada corrida), dump local se elimina tras copia a Drive

### v2.2 — 2026-05-02
**Cerrado:**
- ✅ ítem 29 — Órdenes desde TV: `POST /order` en `Class_BrowserBridge.py` conecta con broker vía `_order_callback` → `put_order`; userscript muestra estado (Submitted/PreSubmitted/FILLED) y limpia qty; refresh automático del panel post-orden
- ✅ ítem 29 (extensión) — Selector de cartera en TV panel: botón ≡ en header abre lista de chips con todos los símbolos en posición; clic en chip hace `POST /current` → `_switch_callback` → `_abrir_tradingview(symbol)` → TV navega al símbolo; botón flotante 📊 siempre visible para reabrir el panel
- ✅ ítem 25 — claude.ai en browser vía Violentmonkey: endpoint `GET /contexto` en `Class_BrowserBridge.py` sirve contexto de cartera; `set_claude_contexto()` actualiza el payload; userscript inyecta datos en claude.ai
- ✅ ítem 33 — rebuild diaria_performance desde 2025-12-20: `run_balance_booktrading.py` sin residuos; `run_fix_hasi_stock.py` corrigió 19 registros HASI (5 acciones fantasma desde sec=25); rebuild completo ejecutado
- ✅ fix diaria fills múltiples — `diaria_app` usaba timestamp exacto → solo capturaba último fill parcial del día; fix: `DATE(fechahora)` trae todos los fills y `acumula_igual_date()` suma correctamente
- ✅ fix CNV Safe Browsing — Chrome bloqueaba descarga Excel CNV en headless → 321 `.crdownload` huérfanos; fix: `safebrowsing.enabled=False` + poll hasta `.xlsx` (ítem 37)

### v2.1 — 2026-05-01
**Cerrado:**
- ✅ ítem 36 — Guard anti doble-tap Telegram: `put_order_aprovate_telegram()` verifica `estado == "ejecutada"` antes de enviar al broker; `handle_callback()` llama `edit_message_reply_markup(reply_markup=None)` al primer tap para quitar los botones inmediatamente — dos capas de protección evitan ejecución duplicada de órdenes

**Diagnóstico gap IB vs sistema — en curso:**
- `AppTest/run_compare_ib.py` creado — compara IB Open Positions (hardcoded abril 2026) vs `diaria_performance`; auto-detecta MAX(Date) o acepta fecha por argumento
- Comparación IB 2026-04-30 vs DB 2026-04-29 identificó: CFRXQ by design (-$728), FMC/XIFR/MPT diferencia costo base, 4 símbolos con cantidades incorrectas en booktrading
- Correcciones booktrading pendientes: CRNT (+20 fantasma — borrar fila 2026-03-23 qty=20), SKLZ (+12 fantasma — agregar C -12), BTI (+1 — borrar O qty=1 del 2026-03-31), CVS (-2 — confirmar si hubo compra sin registrar)

### v2.0 — 2026-04-30
**Diagnóstico y corrección pipeline diaria_performance → performa_inversion:**
- 🐛 4 bugs identificados y corregidos en `Modulos_Comunes.py` + `Modulos_Mysql.py`:
  - `datos.empty` solo avanzaba 1 fila de ebook → dejaba intervalos sin procesar (fix: skip bloque completo del símbolo)
  - `accion="cartera"` filtraba `divisa='USD'` → excluía ABX (CAD) y otros no-USD (fix: sin filtro divisa)
  - Guardian lower bound `basic/20 ≤ close` rechazaba stocks con caída real >95% (fix: solo límite superior `close > basic*20`)
  - `pd.merge(on="Date")` KeyError — Date es índice no columna (fix: `left_index=True, right_index=True`)
- ✅ `detalle_book`: soporte `fecha_deliste` por símbolo — delisted con fecha procesa hasta esa fecha y registra `value=0`; sin fecha → skip completo (comportamiento anterior)
- ✅ `mark_booktrading_delisted(fecha_deliste=None)` — nuevo parámetro opcional en `Modulos_Mysql.py`
- ✅ `run_mark_delisted.py` refactorizado — dict con `fecha_deliste` por símbolo; 7 símbolos con fecha conocida (APHA, AUY, LLNW, STOR, ZVO, CFRXQ, GOEVQ)
- ✅ `AppTest/run_balance_booktrading.py` — nuevo: corrige `stock<0` y residuos `|stock|<0.01`
- ✅ `AppTest/run_diag_missing_symbols.py` — nuevo: compara booktrading activo vs diaria_performance por fecha
- ✅ `SchemasSQL/alter_booktrading_fecha_deliste.sql` — ALTER TABLE listo para ejecutar
- ✅ `AppTest/run_solo_performa.py` — reconstruye solo performa_inversion sin tocar diaria
- ✅ `AppTest/run_rebuild_diaria_cartera.py` — rebuild completo ejecutado: 39113 filas, 2020-07-09→2026-04-27
- 🔍 Gap nr_gyp vs IB: -$11.3K (app) vs -$14K (IB); CFRXQ (-$727) explica parte; splits (ítem 34) explican el resto

**Pendiente para cerrar este ítem:**
1. `ALTER TABLE booktrading ADD COLUMN fecha_deliste DATE NULL AFTER delisted`
2. `python AppTest/run_mark_delisted.py`
3. `python AppTest/run_balance_booktrading.py`
4. `python AppTest/run_rebuild_diaria_cartera.py` (rebuild completo con fecha_deliste activo)

### v1.9 — 2026-04-26
**Incidencia resuelta — Corrupción en performa_inversion por precios yfinance:**
- 🐛 Detectado: `nr_gyp` con valores absurdos en `performa_inversion` (ABEV +1.86M, PFE -1.63K)
- 🔍 Diagnóstico: booktrading correcto; yfinance devolvió precios corruptos (ABEV 2489x arriba, PFE 0.009x abajo) — causa probable: glitch de red/caché en el momento del `schedule_diario`
- ✅ Fix `write_csv()` en `Modulos_Comunes.py`: guardián `if basic > 0 and not (basic/20 <= close <= basic*20): return` — descarta precios yfinance que difieren >20x del costo promedio del activo
- ✅ `IPerformance.purgar_desde(account, vehiculo, desde)` en `Modulos_Mysql.py`: elimina `diaria_performance` + `performa_inversion` desde una fecha y resetea el schedule JSON — permite reconstrucción limpia
- ✅ `AppTest/run_purgar_performance_desde.py`: script interactivo de reparación con confirmación, estado antes/después y reset automático del schedule
- 🔧 Purga ejecutada manualmente: borrados registros desde 2026-04-15, reconstrucción delegada al próximo `schedule_diario`
- ✅ Pre-carga `DataHub.info` al arranque: `carga_inversion_en_positions()` lanza hilo `PrecargarInfo` solo si `IClient.authenticated=False`; se detiene si IB conecta durante el proceso
- ✅ `on_treeview_select()`: mensaje "aun no ha cargado self.info()" migrado de `print` → `logger.warning`

**Para reproducir / próxima vez:**
1. Correr `AppTest/run_purgar_performance_desde.py` ajustando `FECHA_PURGA`
2. El guardián en `write_csv()` previene reincidencia automáticamente
3. Si el guardián bloquea un precio legítimo (stock apreciado >20x desde compra), ajustar umbral en `Modulos_Comunes.py` línea del guardian

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
