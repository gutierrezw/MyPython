# BACKLOG — AppOO Trading Platform

Historial de versiones al final del archivo.

---

## Pendiente

| # | Módulo | Tarea | Prioridad |
|---|--------|-------|-----------|
| 1 | **Finanzas — PDF** | Parser BBVA tarjetas MC/Visa — `BbvaArTarjeta` en `load_statement.py` (base creada) | Alta |
| 2 | **Finanzas — PDF** | Parser BBVA cuenta corriente ARS — `BbvaArCuenta` | Alta |
| 3 | **Finanzas — PDF** | Parser Santander multi-sección (5 secciones en 1 PDF) — `SantanderAr` | Alta |
| 4 | **Finanzas — PDF** | Test end-to-end: cargar extracto real + verificar txns en BD | Alta |
| 5 | **Finanzas — FX** | Poblar `amount_usdt` al cargar txns — tasa desde `booktrading` por fecha y fiat | Alta |
| 6 | **Infraestructura** | Plan de respaldo: BD + código + base de conocimiento Claude | Alta |
| 7 | **Consenso/Telegram** | ¿Consenso reemplaza o complementa señal IA? Umbral mínimo de votos para habilitar/bloquear alerta | Alta |
| 8 | **Finanzas — FX** | `FinanceScreen.get_tasa(fiat, fecha)` — lookup tasa desde `booktrading` | Media |
| 9 | **Finanzas — Gmail** | Fase 0: OAuth setup + whitelist remitentes bancos | Media |
| 10 | **Finanzas — Gmail** | Fase 2: captura automática de extractos adjuntos | Media |
| 11 | **Finanzas — UI** | Dashboard Finance — gráfico evolución mensual ingresos/gastos | Media |
| 12 | **Stock/Cartera** | PHYS (ETF oro físico) — verificar categoriaActivo, decidir si participa en Consenso | Media |
| 13 | **Stock/Cartera** | ETFs `categoriaActivo='T'` descubiertos vía 13F — evaluar limpieza de market | Media |
| 14 | **Stock/Cartera** | Señal Net — validar distribución real p33/p67 | Media |
| 15 | **Integración** | Integrar Claude en ClassChatbot — consultar Claude desde chatbot interno | Media |
| 16 | **TradingView** | Toggle "Controlar TV web" en la app | Media |
| 17 | **TradingView** | BUY/SELL desde TV: botón → `POST /order` → broker API → confirmación en panel | Media |
| 18 | **Auto-Remediación** | BD: crear tablas `fallos`, `app_metrics`, `bd_metrics` | Media |
| 19 | **Auto-Remediación** | Agentes: `Agente_FallosLog` + `Agente_MetricasCodigo` + `Agente_MetricasBD` | Media |
| 20 | **Infraestructura** | MCP local: servidor de herramientas para acceso a shell/BD desde co-work | Media |
| 21 | **Mantenimiento** | Depuración imports — `Modulos_python.py` (vulture 63 hallazgos) | Baja |

---

## Historial

### v1.0 — 2026-04-05
**Cerrado:**
- ✅ TradingView integrado — servidor HTTP local puerto 5050, Violentmonkey, shapes nativos TV
- ✅ Módulo Finanzas Personales — diseño, 7 tablas MySQL, 9 cuentas, 48 categorías, 75 reglas
- ✅ `FinanceScreen` en `Modulos_Mysql.py` + `FinancePanel` tab Finance en la app
- ✅ Backfill VES 12 meses — 37 operaciones SELL en `booktrading` (`VES-0001`)
- ✅ `trade_USDT_diario()` — carga diaria ARS (BUY) + VES (SELL) desde la app
- ✅ `get_c2c_trade_history()` — acepta parámetro `fiat` para filtrar por moneda
