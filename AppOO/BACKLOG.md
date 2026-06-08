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
| ~~14~~ | ~~**Stock/Cartera**~~ | ~~Señal Net — validar distribución real p33/p67~~ | ~~Media~~ |
| ~~47~~ | ~~**Pipeline/13F**~~ | ~~`sync_fund_filings` Opción B — corrió 2026-05-21 05:47, confirmado OK~~ | ~~Media~~ |
| ~~46~~ | ~~**Stock/Consenso**~~ | ~~CUSIP mismatch — BABA/BTG/VST: CUSIPs poblados manualmente (TradingView). PHYS: eliminado de market (quoteType='EQUITY' en Yahoo → no detectado como ETF). Fix: `_resolve_cusip_from_edgar` usa CIK lookup vía `company_tickers.json`; `audit_portfolio` agrega detección por nombre (`_ETF_NAME_KEYWORDS`) para trusts que Yahoo reporta como EQUITY~~ | ~~Baja~~ |
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
| ~~26~~ | ~~**Stock/IB**~~ | ~~Fallback yfinance cuando IB offline — precios + dGyP header no actualizaban~~ | ~~Media~~ |
| ~~27~~ | ~~**Stock/Gráficos**~~ | ~~`grupo_sector()` infla "Consumer Cyclical" — sector preservation en `update_inversion_stock()` + fallback `sectores()` → `""`~~ | ~~Media~~ |
| ~~37~~ | ~~**FCI/Selenium**~~ | ~~`download_cnv_selenium.py` — Safe Browsing Chrome bloquea descarga Excel de CNV → `.crdownload` huérfanos en `tmp/`; fix: `safebrowsing.enabled=False` + `--safebrowsing-disable-download-protection` + poll hasta `.xlsx` disponible (max 90s)~~ | ~~Media~~ |
| 28 | **Infraestructura** | Proceso de mantenimiento del sistema vía Claude scheduled: check NTP con `ntplib` (alerta si deriva >500ms), limpieza logs rotativos, verificación servicios críticos (IB, Binance, MySQL). Sin elevar la app a admin. | Media |
| ~~29~~ | ~~**TradingView**~~ | ~~Órdenes desde TV — handler `POST /order` en servidor TV conecta con broker: IB (`place_order` vía IBroks_Client) + Binance (`create_order` vía BinanceSpot); confirmación de ejecución devuelta al userscript TV~~ | ~~Alta~~ |
| ~~30~~ | ~~**Stock/Mantenimiento**~~ | ~~Correr `run_mark_delisted.py` (17 símbolos) + `run_rebuild_diaria_cartera.py`~~ | ~~Alta~~ |
| ~~31~~ | ~~**Stock/IB**~~ | ~~Reconexión IB sin reinicio — `_ib_on_reconnect` verifica si `run_websocket_stream(Stock)` está vivo; si arrancó offline (ws nunca iniciado) llama `stock_ts.run()` completo en vez de solo refresh. Probado: gateway offline al arrancar → login → ws aparece solo~~ | ~~Alta~~ |
| ~~🧪 32~~ | ~~**Stock/yfinance**~~ | ~~Verificar que rebuild genera precios ABX correctos (~$53 CAD vía ABX.TO) — `convierte_ticket_stock` mapea CAD→.TO en `Modulos_Utilitarios.py`~~ | ~~Media~~ |
| ~~33~~ | ~~**Stock/Mantenimiento**~~ | ~~`fecha_deliste` en booktrading: 1) ALTER TABLE, 2) `run_mark_delisted.py` (con fechas), 3) `run_balance_booktrading.py` (stock residual→0), 4) rebuild completo → cierra gap nr_gyp vs IB~~ | ~~Alta~~ |
| ~~34~~ | ~~**Stock/Mantenimiento**~~ | ~~Agente Splits: detectar splits vía `yf.splits`, ajustar `basico` y `stock` en booktrading — fuente principal del gap restante ~$2K vs IB~~ | ~~Media~~ |
| ~~35~~ | ~~**Stock/Mantenimiento**~~ | ~~Completar `fecha_deliste` para 12 símbolos con `None` (ETM, GHSI, GPS, NYMT, PBPB, PLM, SSUP, STON, ZY…) — buscar fechas exactas de fusión/privada~~ | ~~Baja~~ |
| ~~36~~ | ~~**Telegram/Órdenes**~~ | ~~Guard anti doble-tap en botón Aprobar — `handle_callback` + `put_order_aprovate_telegram`~~ | ~~Alta~~ |
| 38 | **Gmail/Productividad** | Depuración bandeja Gmail con Claude Desktop: clasificar, etiquetar y archivar correos masivos; definir reglas de limpieza recurrente; usar MCP Gmail tools de Claude Desktop | Media |
| 39 | **BotCrypto/Analytics** | `run_bot_analytics.py`: parsear JSON técnico en `booktrading` (RSI/MACD/ATR/Fibonacci × 3 timeframes diaria/semanal/mensual) de trades cerrados → tabla correlación condición→WR; identificar patrones de entrada ganadores/perdedores para mejorar reglas del scoring | Media |
| 40 | **BotCrypto/Analytics** | Panel Analytics en tab BotCrypto: WR por símbolo, WR por condición (RSI range, MACD estado, ATR%), filtro por período — alimentado por `booktrading` sin nueva infraestructura | Baja |
| ~~42~~ | ~~**Stock/Preservation**~~ | ~~Activar `Agente_ManagerPreservation` — actualmente comentado en `agentesIA()` (`Class_DashBot.py:1983`) con nota "No activar en prueba". Revisar `_preservation_run_vehiculo()`, validar con IB conectado, y habilitar para Stock + Crypto~~ | ~~Alta~~ |
| ~~43~~ | ~~**UI/BUY Dialog**~~ | ~~Modo "importe a invertir": en diálogo BUY agregar selector QTY ↔ USD (Listbox estilo LMT/MKT/STP); QTY se calcula automático — Stock: `floor(importe/precio)` entero; Crypto: respeta lotSize decimales. Sin perder modo cantidad actual~~ | ~~Media~~ |
| ~~44~~ | ~~**TradingView/BUY**~~ | ~~Integrar modo "importe a invertir" en órdenes desde TV panel — especificar monto $ en vez de cantidad; misma lógica conversión que ítem 43~~ | ~~Baja~~ |
| ~~41~~ | ~~**Distribución**~~ | ~~Ejecutable para hijo: PyInstaller → `.exe` standalone + config JSON que activa solo las pestañas deseadas (tabs son parámetro — mismo binario, distinta config); credenciales propias (Binance account); publicar en GitHub Releases~~ | ~~Media~~ |
| 45 | **Infraestructura/Releases** | Renombrar `DashMainV9_ia.py` → `DashMain.py` + crear `version.py` (APP_NAME, VERSION, RELEASE_DATE) + git tags semánticos por release + separar DEV/PROD en máquinas físicas distintas | Alta |

| 51 | **IA/Investigación** | Revisar agentes financieros que ofrece Claude (Managed Agents API) y evaluar integración al proyecto de inversiones — análisis de portafolio, señales, alertas u otros casos de uso relevantes | Media |

| 🧪 48 | **IA/Modelos** | Módulo Sentimiento general de noticias por símbolo (no orientado a temas tech). `Agente_Sentimiento` @8h (3×/día) + `Agente_InterpreteSentimiento` @24h — conectados en `Class_DashBot.py`. Lógica `inflexion` corregida: vota +1 solo si sentimiento≥0, abstiene si negativo. Depuración automática: retiene últimos 3 meses (`cleanup_sentiment(months=3)`). Voto `Sent` activo en Consenso. Key: `ClaudeAPIP`. **En prueba en producción** | Media |
| ~~49~~ | ~~**Infraestructura/Agentes**~~ | ~~Administrador de agentes — panel UI para activar/desactivar agentes en tiempo real sin reiniciar la app. Flag `active` en `AGENTES_SCHEDULE` + pestaña similar al panel Debugging (toggle por fila, doble-click activa/desactiva, persistido en `tmp/agents_config.json`). Permite controlar qué agentes corren sin modificar código~~ | ~~Media~~ |
| 🧪 50 | **IA/Modelos** | Integrar sentimiento como feature en modelos BUY/SELL — agregar `sentiment_score` (última lectura), `sentiment_3d_avg`, `sentiment_7d_avg`, `sentiment_patron` (encoded: acumulacion=1, neutro=0, distribucion=-1) en `aplanar_datos_tecnicos()` y `cargar_datos()`; reentrenar modelos. **Prerequisito:** ~1 mes de histórico en `market_sentiment` para que la señal sea estadísticamente válida | Media |
| ~~✅ 51~~ | ~~**IA/Descubrimiento**~~ | ~~Scanner YouTube RSS — `ConvergIA/Scanner_YouTube.py`: 6 canales hispanos de inversión, RSS feedparser, Claude Haiku extrae nombres de empresas → `yf.Search()` resuelve ticker. Tablas: `youtube_canales` + `youtube_candidatos`. `Agente_YouTubeScanner` @wait_rate(86400). Popup "Candidatos" en Screener con filtros País/Sector/Canal al estilo Screener.~~ | ~~Media~~ |
| 52 | **Infraestructura/Agentes** | Panel Agentes — niveles jerárquicos: N1 Datos (MarketScreener, EdgarFunds, FundFilings, 13FHoldings, Sentimiento, YouTubeScanner), N2 Señales (13FScores, InstitucionalScore, ConsensoCache, InterpreteSentimiento, ClasificadorETF, StockBeta), N3 Decisiones (ManagerPreservation, SyncOrders, LtvControl, OrderEodCleanup), N4 Soporte (PriceSync, PerformaValidator, SplitsControl, ExtractosWatcher, AuditPortfolio, ApiCostTracker). Agregar campo `nivel` en `AGENTES_SCHEDULE`, agrupar por nivel en treeview con separador visual, ajustar columnas del panel (ancho + orden). | Media |
| 53 | **Stock/GainsCapture** | `Agente_GainsCapture` — espíritu especulativo (distinto a Preservation que es defensivo). Opera sobre `categoriaActivo='N'` (volátiles): venta parcial por niveles de ROI (50%/100%/150%), validación Claude de técnicos (RSI_d/RSI_w/EMA) antes de cada nivel. Dos modos: `automatico` (LMT directo a IB + notif Telegram) y `autorizado` (propuesta Telegram /ok /no, timeout 30min → cancela sin ejecutar). Botón toggle en panel Agentes, persiste en `tmp/gains_capture_config.json`. Precio LMT = `last×0.995`. Estados: `normal` / `escalon_pendiente` / `esperando_reset` / `pendiente_autorizacion`. `json_detalle` en order_trader para aprendizaje futuro. Ver `Doc/gains_capture_design.md`. | Alta |
| 54 | **Stock/Preservation** | Bug escenario borde: si IB está offline cuando el agente corre, `preservation_get_price` retorna None → todos los símbolos se saltean → `preservation_state.json` no registra `order_id`. Al volver IB, el agente no encuentra `order_id_prev` y puede crear órdenes duplicadas sobre STOPs que ya existen en IB. Fix sugerido: antes de enviar nueva orden, consultar `select_pending_orders` en `order_trader` para verificar si ya existe una STP LMT activa para ese símbolo/account. | Media |

---

## Historial

### v3.4 — 2026-06-03
**Escalonamiento de salida — diseño completo:**
- 📋 ítem 53 anotado — escalonamiento activos volátiles (categoriaActivo='N')
- ✅ Fix `otros_activos.symbol` CHAR(25) → VARCHAR(100) + `descripcion` CHAR(80) → VARCHAR(120) — evita error 1406 en insert_otros_activos con nombres de fondos FCI
- ✅ `Doc/preservation_claude_dynamic_design.md` — Fase 2 diseñada: tipo orden LMT (last×0.995), validación Claude técnicos (RSI_d/RSI_w/EMA), modos automatico/autorizado, estados normal/escalon_pendiente/esperando_reset, botón toggle panel Agentes, timeout autorizado 30min → cancela sin ejecutar, json_detalle para aprendizaje futuro

### v3.3 — 2026-06-02
**Preservation activo + fixes Lista de Ordenes + alertas IB Gateway:**
- ✅ ítem 42 — `Agente_ManagerPreservation` activo y validado: 5 STOPs colocados en primera corrida
- ✅ Fix preservation first-run skip — `_preservation_get_config` ya no retorna `False` en primera llamada; evalúa inmediatamente
- ✅ Fix duplicate STOP orders — `preservation_last_run` ahora persiste como `_last_run_{vehiculo}` en `preservation_state.json`; sobrevive cierre/reapertura del Chatbot
- ✅ Fix ventana Diversificación — tamaño ampliado `847×780` + `resizable(True,True)`; botón Cancel ya no queda cortado
- ✅ Lista de Ordenes — columna `Stop` (auxPrice de IB) para órdenes STP LMT; columna `id_enviar` eliminada de la vista; `displaycolumns` para ocultar columnas internas sin líneas separadoras fantasma; sort automático por symbol dentro de cada grupo vehiculo
- ✅ Alerta IB Gateway caído → Telegram vía `DataHub.system_alerts` (class-level queue); `_flush_system_alerts()` async en loop agentesIA; alerta reconexión exitosa en `_ib_on_reconnect`
- ✅ Preservation dinámica con Claude Haiku — `_claude_preservation_eval` + `_build_preservation_context` (DataHub tiempo real) + `insert_preservation_order`; key `ClaudeAPIP` separada; `json_detalle` en `order_trader`; `select_preservation_context` (market + sentiment, sin oportunidades)
- ✅ Lista de Ordenes — columna `IA` (🤖) con doble-click abre popup análisis Claude: stop_final, urgencia, razón, consenso, inst_score, RSI, MACD
- ✅ `Class_SystemStatus.py` — fix canvas matplotlib `fill=tk.X` para que `self.connect` (panel API) sea visible debajo del área de recursos
- ✅ `AppTest/run_preservation_eval.py` — script standalone de validación preservation con Claude; validado contra TradingView (BP, CVS, CRNT, PLUG, UUUU, VALE)
- 📋 ítem 52 anotado — niveles jerárquicos en panel Agentes + ajuste columnas

### v3.2 — 2026-05-25
**YouTube Scanner + AgentManager + Cache tab:**
- ✅ `ConvergIA/Scanner_YouTube.py` — RSS 6 canales hispanos → Claude extrae nombres → `yf.Search()` ticker → `yf.fast_info` valida → `youtube_candidatos` BD
- ✅ Tablas `youtube_canales` (score, detecciones, validados, last_scan) + `youtube_candidatos` (apariciones, confidence, canales, status: pending/approved/rejected)
- ✅ `Agente_YouTubeScanner` @wait_rate(86400) registrado en `AgentManager.register_threads()`
- ✅ Popup "Candidatos" en Screener: tabla con En Market / En Cartera; colores verde=cartera / gris=market; Comprar → market(T) + status=approved; Rechazar → status=rejected
- ✅ Deduplicación `seen_ids` = solo IDs del RSS actual (máx ~90), no acumulado histórico
- ✅ Cleanup automático cada scan: rechaza candidatos expirados (apariciones=1 AND >15d ó <3 AND >30d)
- ✅ `ApiCostTracker` filtrado por `workspace_id` — muestra costos del workspace AppOO, no org total
- ✅ Cache tab rediseñado: árbol agrupado por vehiculo (Stock/Crypto/Referencia), collapsed por defecto, OHLCV últimas 15 filas, preserva selección en refresh
- ✅ `AgentManager` 4 domain loggers (Agente.Stock/Crypto/IA/Infra) + `YouTubeScanner` registrado en `Class_debugging.py`
- ✅ `version.py` → 10.3.0 / 2026-05-25
- ✅ ítem 51 — fixes producción: `date` → `datetime.now().date()`, rate-limit Yahoo (`time.sleep(0.3)` + eliminar `yf.fast_info`), `canal_origen` busca por nombre empresa en lugar de ticker, filtra símbolos >10 chars. Pendiente: `market_cap` (Yahoo Search no lo devuelve).

### v3.1 — 2026-05-23
**Panel Agentes + fixes:**
- ✅ ítem 49 — Panel "Agentes" en SystemStatus: treeview con Intervalo/Estado/Run/Próxima/Descripción; doble-click toggle activo/inactivo; clic derecho Activar/Desactivar; "Activar todos"; persistencia en `tmp/agents_config.json`; auto-refresh cada 10s (una sola lectura de `agents_schedule.json` por tick)
- ✅ Fix Run(0): `task_name = name` alineado con nombre de hilo — contadores ahora muestran iteraciones reales
- ✅ `Agente_ManagerPreservation`: SKIP por IB offline bajado de WARNING → DEBUG (estado normal, no error)
- ✅ Docs branch limpiada: eliminados 142 archivos `.py/.bat` — `docs` ahora solo contiene `.md` y `Doc/`; resuelve conflictos al cambiar de rama
- ✅ ítem 48 fixes: voto `Sent` como columna explícita en popup Consenso; weekend guard en `Agente_Sentimiento` e `Agente_InterpreteSentimiento` (sáb/dom = SKIP)
- 🧪 ítem 50 infra: `load_sentiment_features` en `MarketScreen` + `enriquecer_con_sentimiento` en modelos sell/buy — retrain pendiente ~1 mes de histórico

### v3.0 — 2026-05-22
**Módulo Sentimiento + Keys Claude por módulo:**
- ✅ ítem 48 — `ConvergIA/Scanner_Sentimiento.py`: fetch noticias por símbolo vía `yf.Ticker.news` + clasificación Claude Haiku en batches → {sym: +1/0/-1} → `market_sentiment` BD
- ✅ `ConvergIA/Interprete_Sentimiento.py`: análisis histórico 7 días por símbolo → patrón (acumulacion/distribucion/neutro/inflexion) + interpretación en español → `market_sentiment_analysis` BD
- ✅ `ConvergIA/ThemeMapper.py`: lee BD → `voto_tech_alignment(sym, sentiment, analysis)` → prioridad patrón histórico > sentimiento puntual
- ✅ 7 métodos nuevos en `MarketScreen`: `bulk_save_sentiment`, `load_latest_sentiment`, `load_sentiment_history`, `save_sentiment_analysis`, `load_sentiment_analysis`, `sentiment_already_run_today`, `cleanup_sentiment`
- ✅ `SchemasSQL/market_sentiment.sql` — DDL tablas `market_sentiment` + `market_sentiment_analysis` (creadas en BD)
- ✅ `Agente_Sentimiento` @wait_rate(3600) + `Agente_InterpreteSentimiento` @wait_rate(86400) registrados en loop agentes
- ✅ Voto `"Sent"` agregado al Consenso en `Class_Screener.py` (logger: `Sentimiento`)
- ✅ Keys Claude separadas por módulo en tabla `sesion`: `ClaudeAPIS` (Sentimiento), `ClaudeAPIE` (ETF), `ClaudeAPIC` (Chat) — permite monitorear consumo por módulo en console.anthropic.com
- ✅ `AppTest/run_claude_api_test.py` — valida las 3 keys en una sola corrida
- ✅ `AppTest/run_tech_alignment.py` — prueba end-to-end: Scanner + Intérprete + votos resultantes
- ✅ `AGENTES_SCHEDULE` — `Agente_Sentimiento` + `Agente_InterpreteSentimiento` agregados al dashboard
- ✅ `version.py` — `10.1.0` → `10.2.0`

### v2.9 — 2026-05-21
**Infraestructura + Pipeline 13F + Modelos IA:**
- ✅ ítem 47 — `sync_fund_filings` Opción B corrió 2026-05-21 05:47, OK
- ✅ `load_screener_health` — `pendientes` y `por_renovar` filtrados por account (antes contaban universo global 98K → ahora solo ~7.7K fondos relevantes); números correctos: 389 por_renovar / 4910 pendientes
- ✅ `profiles/main.json` — `tmp_path` absoluto `deploy\tmp` (relativo `"..\tmp"` daba `MyPython\tmp` desde VS Code → log en lugar equivocado)
- ✅ VS Code terminal — venv activo automáticamente + `APPOO_TMP` inyectado vía `terminal.integrated.env.windows`; log siempre en `deploy\logs\`
- ✅ `register_thread` — agrega thread a `DataHub.procesos` e incrementa `Run(N)` en cada iteración del wrapper; todos los agentes muestran contador real
- ✅ `sync_fund_filings` — parámetro `progress_cb` opcional; `Agente_FundFilings` pasa callback que actualiza `Run(i)` cada 100 fondos
- ✅ Modelos BUY/SELL — `rango_13w_pct`, `rango_26w_pct`, `rango_52w_pct` agregados como features en `aplanar_datos_tecnicos()` y `cargar_datos()`; reentrenamiento ejecutado sin novedad

### v2.8 — 2026-05-13
**TV Panel + Consenso + Infraestructura:**
- ✅ ítem 44 — TV panel v2: toggle QTY/USD con estado persistente entre redraws; equivalente siempre visible en ambas direcciones; Crypto usa `toFixed(4)` (no `Math.floor`); minimize no se pierde en el redraw 3s; Crypto incluido en chips cartera
- ✅ `stop_tv_server()` — `shutdown()` antes de `server_close()`: elimina `WinError 10038` al cerrar la app
- ✅ `refresh_consenso_tags` — incluye voto Mod (7 votos unificados con panel Consenso); `_load_csv_signals()` extraída como función de módulo
- ✅ Notificación Telegram: denominador corregido `/6` → `/7`
- ✅ `Panel Crypto mrg (FALLBACK equity)` — bajado de WARNING → DEBUG (no ensucia log mientras LtvControl no corrió)
- ✅ `profiles/main.json` + `profiles/hijo.json` — `tmp_path` corregido a `AppOO\tmp` (era `dist\AppOO\tmp`)
- ✅ `edgar_13f.py` — `_13F_SAVE_DIR` usa `APPOO_TMP` env var (fix path en build PyInstaller)
- ✅ `Class_debugging.py` — log path derivado de `APPOO_TMP` (unifica logs en `MyPython\logs\` siempre)
- ✅ `buildExe.bat` — `%~dp0` + backup/restore `tmp/` antes/después del build

### v2.7 — 2026-05-12
**Releases + UI + Infraestructura:**
- ✅ ítem 45 — `DashMainV9_ia.py` → `DashMain.py`; `version.py` con `APP_NAME="DashMain"`, `VERSION="10.0.0"`, `RELEASE_DATE`; splash y título de ventana leen de `version.py`; `DashMain_hijo.py` y `buildExe.bat` actualizados
- ✅ Splash screen: barra de progreso `ttk.Progressbar` 12 pasos — muestra avance módulo a módulo al iniciar
- ✅ Fix ventana vacía al arrancar: `self.root.withdraw()` en `__init__` justo después de `tk.Tk()`; `state("zoomed")` movido a después de `deiconify()` en `run()` — eliminado el flash de ventana en blanco
- ✅ Fix `Class_FondosInversion` — `self.path` usa `APPOO_TMP` env var con fallback `os.getcwd()/tmp` + `makedirs(exist_ok=True)` — resuelve `WinError 3` al correr desde VS Code
- ✅ Fix `tmp_old/` en git status — agregado a `.gitignore`
- ✅ BUY dialog — "Importe" renombrado a "USD"; `lbl_calc` reubicado en misma fila que entry (column=2) — recupera botón Cancel que quedaba desplazado
- ✅ ítem 43 — Modo "importe USD" implementado: `bt2` readonly Entry (QTY/USD), `lbm` Listbox, `lbl_calc` muestra qty calculado en tiempo real, `_get_qty_final()` calcula qty correcta al enviar; `_get_lot_exp()` nuevo método privado respeta decimales lotSize Crypto

### v2.6 — 2026-05-11
**FCI extractos — corrección NAV real + distribución hijo:**
- ✅ ítem 41 — Ejecutable hijo: `buildExe_hijo.bat` → `dist/AppOO_hijo.exe` onefile; `profiles/hijo.json` (Crypto, Ars, BotCrypto, Finance); tag `v9.1.0-hijo` publicado en GitHub Releases; `AppTest/export_hijo.bat` exporta schema + datos de referencia para setup BD hijo
- ✅ Fix tabs en blanco (`DashMainV9_ia.py`): eliminadas 10 llamadas `.pack()` en frames hijos del Notebook — conflicto con geometry manager de `ttk.Notebook` hacía desaparecer todas las tabs
- ✅ Splash screen minimalista al arranque: `_splash_open()` / `_splash_step()` — ventana borderless centrada, actualiza estado por módulo hasta `mainloop()`
- ✅ `tmp_path` absoluto en `profiles/main.json` — evita que el tmp se cree en `AppOO/` en vez de `dist/AppOO/tmp`
- ✅ `construir_extracto_fci` — parámetro `vehiculo` explícito; SANT0001 pasa `vehiculo="BBVA.ARS"` (único vehiculo en `performa_inversion` para ambas cuentas)
- ✅ `construir_extracto_fci` — `is_month_end` reemplazado por `groupby(to_period("M")).last()` — captura último día de mercado del mes aunque no sea fin de mes calendario; extracto siempre graba fecha fin de mes calendario
- ✅ UPDATE extractos BD — 25 registros: BBVA0001 (Nov-2024→Abr-2026) + SANT0001 (Oct-2025→Abr-2026) actualizados con `navcierre` y `costobase` reales desde `performa_inversion`

### v2.5 — 2026-05-06
**Defensa multicapa precios yfinance + Agente Splits:**
- ✅ ítem 34 — `Agente_SplitsControl` + `sync_splits()`: ya implementado y activo; fix bug timezone `datetime64[ns, America/New_York]` vs Timestamp naive en comparación de índice — `tz_localize` al timezone del índice antes de filtrar
- ✅ fix `auto_adjust=False` en `get_yfinance(vehiculo=Dividends)` — elimina corrupción de precios ADR (ABEV, BP) en raíz
- ✅ Cache quirúrgica: `DataFrameCache.add_bypass(symbol)` — invalida solo el símbolo corrupto, no todo el caché
- ✅ Cuarentena automática: 3+ purgas en 6h → `quarantine_symbols.json` → `detalle_book` saltea símbolo 24h (rompe loop infinito)
- ✅ `Agente_PerformaValidator`: log cache stats + `add_bypass` por anomalía + CRITICAL si cuarentena
- ✅ Guardian `close > basic*200` eliminado de `write_csv` — creaba gaps silenciosos incompatibles con validator
- ✅ `DataFrameCache.stats()`: size, maxsize, ttl, hits, misses, clears, bypass, symbols
- ✅ Decorator no cachea DataFrames vacíos (evita cachear errores transitorios de yfinance)
- ✅ fix `sync_splits` timezone: `pd.Timestamp(primera_compra).tz_localize(splits.index.tz)` cuando índice es tz-aware
- ✅ `AppTest/run_diag_abev_yfinance.py` — script diagnóstico reproducción exacta de detalle_book

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