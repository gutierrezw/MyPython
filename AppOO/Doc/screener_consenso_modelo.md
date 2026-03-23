# SCREENER & MODELO DE CONSENSO — CARTERA DE DIVIDENDOS
**AppOO · Versión 2026-W12**

---

## PROPÓSITO

Cartera orientada a **ingresos pasivos (dividendos)**. Se analiza cada activo
cruzando 4 fuentes independientes: flujo institucional 13F, recomendaciones
de Wall Street, señal del modelo IA propio y clasificación fundamental.
El Consenso Score sintetiza estas fuentes en una sola señal por activo,
evitando depender de una sola fuente.

---

## DIAGRAMA GENERAL DEL PIPELINE

```
╔══════════════════════════════════════════════════════════════════════╗
║                        FUENTES DE DATOS                             ║
╠══════════════╦═══════════════════════╦═══════════════════════════════╣
║  NASDAQ API  ║    Yahoo Finance      ║        SEC / EDGAR            ║
║  (dividends) ║  (quotes + fundament) ║  (13F institucional)          ║
╚══════╤═══════╩══════════╤════════════╩═════════════╤═════════════════╝
       │                  │                          │
       ▼                  ▼                          ▼
┌──────────────┐  ┌────────────────┐    ┌────────────────────────────┐
│  Phase 1     │  │  Phase 2 & 3   │    │  Pipeline 13F (4 etapas)   │
│  Discovery   │  │  Enriquecimien.│    │                            │
│  NASDAQ      │  │  Yahoo Quote   │    │  1. sync_edgar_funds       │
│  (paginado   │  │  batch=250     │    │     (~9K fondos, mensual)  │
│   offset)    │  │  + Fundamentals│    │                            │
└──────┬───────┘  └───────┬────────┘    │  2. sync_fund_filings      │
       │                  │             │     (XMLs 13F-HR, semanal  │
       └──────────┬────────┘            │      refresh ≥80 días)     │
                  │                     │                            │
                  ▼                     │  3. sync_13f_holdings      │
         ┌────────────────┐             │     (CUSIP→symbol,         │
         │  tabla market  │◄────────────│      fund_holdings)        │
         │                │             │                            │
         │ symbol         │             │  4. sync_13f_scores        │
         │ lastPrice      │             │     (inst_score blendado)  │
         │ floatShares    │             └────────────────────────────┘
         │ sharesOutstand │
         │ inst_score     │
         │ fh_count       │
         │ fh_ownership%  │
         │ analyst_rec    │
         │ categoriaActivo│
         └───────┬────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │   CONSENSO SCORE      │
     │   (6 votos)           │
     └───────────────────────┘
```

---

## CÓMO SE CONSTRUYE LA TABLA DE MERCADO

**Phase 1 — Descubrimiento NASDAQ**
API NASDAQ screener (dividends only) con paginación offset.
Solo ingresan símbolos con dividendo declarado.
Se filtran preferreds/warrants (símbolo con "-").

**Phase 2 — Enriquecimiento Yahoo Finance**
Batch de 250 símbolos. Actualiza precio, volume, marketCap,
sharesOutstanding, floatShares, beta, exDividendDate, dividendYield.
Retry x3 con backoff ante 429. Aborta si no hay crumb válido.

**Phase 3 — Fundamentals**
Detecta campos NULL y completa: country, sector, shortName,
analyst_rec, analyst_mean, analyst_count, PE, PB, márgenes,
deuda, floatShares, sharesOutstanding vía `yf.Ticker().info`.

**Limpieza (cleanup_market)**
Valida símbolos vs Yahoo. Elimina delistados.
Preserva siempre los que tienen `encartera='Y'`.

---

## CATEGORIZACIÓN DE ACTIVOS (categoriaActivo)

```
  categoriaActivo   Descripción              Voto Valuación
  ──────────────────────────────────────────────────────────
  I  Infravalorado  Atractivo para compra         +1
  S  Sobrevalorado  Evitar o reducir              -1
  N  Neutral        Sin dividendo, en análisis     0   (ej: PLUG, XIFR)
  X  Excluido       ETFs / fondos                None  (abstiene)
  T  Descubierto    Detectado vía 13F            None  (pendiente clasificar)
```

---

## PIPELINE 13F — DETALLE

| Etapa | Frecuencia | Descripción |
|-------|-----------|-------------|
| `sync_edgar_funds` | Mensual | Descarga company.idx EDGAR → ~9K fondos en tabla `funds` |
| `sync_fund_filings` | Semanal | Descarga XMLs 13F-HR. Refresh si filing ≥ 80 días y accession cambió. Metadata en `fund_filings` |
| `sync_13f_holdings` | Semanal | Parsea XMLs (`processed=0`), mapea CUSIP→symbol, calcula NEW/BUY/SELL/HOLD, bulk upsert `fund_holdings` |
| `sync_13f_scores` | Semanal | Recalcula `inst_score` = fh_ownership_pct×0.40 + log(fh_count)×0.40 + fh_buy_ratio×0.20 |

### Resolución CUSIP → symbol (sync_13f_holdings)

Los XMLs 13F usan CUSIP como identificador. La resolución a ticker se hace en dos pasos:

```
1. get_cusip_map(account)     ← tabla cusip_map en BD (cache — evita re-llamar API)
2. resolve_cusips_openfigi()  ← solo los CUSIPs nuevos no cacheados

   POST https://api.openfigi.com/v3/mapping
   [{"idType": "ID_CUSIP", "idValue": "037833100"}]  →  ticker: AAPL

   Free tier: batch de 10, 25 req/min → sleep 2.5s entre requests
   Implementado en: AppValuations/edgar_13f.py:resolve_cusips_openfigi()
```

### CIK EDGAR — fondos top conocidos

| Fondo | CIK SEC |
|-------|---------|
| Vanguard Group | 0000102909 |
| BlackRock | 0001364742 |
| State Street | 0000093751 |
| Fidelity (FMR) | pendiente resolver |
| Capital Group | pendiente resolver |

> Los ~9K fondos restantes se cargan automáticamente desde `company.idx` EDGAR en `sync_edgar_funds`.

---

## COLUMNAS INSTITUCIONALES — RELACIÓN ENTRE MÉTRICAS

```
fund_holdings (13F)
  └── STK positions
       ├── COUNT(DISTINCT fund_id)  ──────────────►  # Inst  (fh_count)
       │
       ├── SUM(shares) / floatShares ────────────►  Inst %  (fh_ownership_pct)
       │        │                                    ⚠ usamos floatShares propio
       │        │                                      (no heldPercentInstitutions
       │        │                                       de Yahoo — puede > 100%)
       │
       └── NEW+BUY / total ──────────────────────►  fh_buy_ratio

  inst_score = fh_ownership_pct × 0.40
             + log(max(fh_count, 1)) × 0.40
             + fh_buy_ratio          × 0.20
                                             ──►  Inst Score  [0..∞]

  Inst Score  →  SEÑAL:
    ≥ 0.40 AND buy_ratio ≥ 0.50 AND fh_count ≥ 20  →  ACOMPAÑAR
    ≥ 0.25 OR  fh_count ≥ 10                        →  MANTENER
    resto                                            →  REVISAR
```

| Columna | Campo BD | Fuente | Descripción |
|---------|----------|--------|-------------|
| `# Inst` | `fh_count` | fund_holdings (EDGAR) | Fondos con posición STK activa (último filing) |
| `Inst %` | `fh_ownership_pct` | Calculado (EDGAR) | fh_total_shares / floatShares — trazable, sin Yahoo |
| `Inst Score` | `inst_score` | Calculado (EDGAR) | Score blendado combinando ownership, cobertura y flujo |
| `CALL` | `fh_call_shares` | fund_holdings (EDGAR) | Acciones totales en opciones CALL (en millones) |
| `PUT` | `fh_put_shares` | fund_holdings (EDGAR) | Acciones totales en opciones PUT (en millones) |
| `Top Holder` | `inst_top_holder` | Yahoo quoteSummary | Nombre del mayor fondo institucional |

> **inst_top_holder** se obtiene vía Yahoo Finance (no EDGAR): `quoteSummary/{symbol}?modules=institutionOwnership,majorHoldersBreakdown` → `ownershipList[0].organization`. Usa `_yahoo_session()` compartida con el resto del pipeline. Campo complementario — no afecta el `inst_score`.

> **Nota floatShares:** Yahoo `heldPercentInstitutions` puede superar 100% por short selling
> y diferencias de timing. Usamos `floatShares` propio desde Yahoo `keyStatistics` almacenado
> en tabla `market` para calcular `fh_ownership_pct` de forma reproducible.
> Limitación: cubre ~9K fondos EDGAR — el número puede ser conservador pero es consistente entre activos.

---

## SEÑAL INSTITUCIONAL COMPUESTA (columna "Inst Señal")

Resume en una palabra la postura de los fondos institucionales:

- **ACOMPAÑAR** — inst_score ≥ 0.40 AND buy_ratio ≥ 0.50 AND fh_count ≥ 20
- **MANTENER** — inst_score ≥ 0.25 OR fh_count ≥ 10
- **REVISAR** — resto

---

## MODELO DE CONSENSO — 6 VOTOS

Cada señal emite: `+1` favorable | `0` neutral | `-1` desfavorable | `None` abstiene

```
  FUENTE              CÁLCULO                        VOTO
  ──────────────────────────────────────────────────────────────────
  1. NET (13F)        fh_buy_ratio − fh_sell_ratio   ranking cartera
                      top 33%  → +1                  +1 / 0 / -1
                      mid 33%  →  0                  None si sin datos
                      bot 33%  → -1

  2. OPTIONS (13F)    call_shares/(call+put shares)
                      ≥ 0.60   → +1                  +1 / 0 / -1
                      ≥ 0.40   →  0                  None si sin opciones
                      < 0.40   → -1
                      Usa acciones totales (millones), no cantidad de fondos.

  3. ANALISTAS (YF)   recommendationKey
                      buy/strong_buy  → +1            +1 / 0 / -1
                      hold            →  0            None si sin datos
                      sell/strong_sell→ -1

  4. IA SIGNAL        CSV buy/sell (activa en mercado abierto)
                      buy   → +1                      +1 / 0 / -1
                      sell  → -1
                      none  →  0

  5. VALUACIÓN        categoriaActivo
                      I → +1 / N → 0 / S → -1         +1 / 0 / -1
                      X / T → abstiene                 None

  6. COBERTURA        fh_count
                      ≥ 20 → +1 / ≥ 5 → 0 / < 5 → -1  +1 / 0 / -1
  ──────────────────────────────────────────────────────────────────

         suma_votos_activos
  pct =  ──────────────────    (abstenciones no cuentan)
         n_votos_activos

  ┌─────────────┬─────────────┬───────────────────────────────────┐
  │  NIVEL      │  CONDICIÓN  │  INTERPRETACIÓN                   │
  ├─────────────┼─────────────┼───────────────────────────────────┤
  │ ★ UNÁNIME   │ todos = +1  │ Máxima convicción — acumular      │
  │ ▲ CONSENSO  │ pct ≥  0.60 │ Comprar / aumentar posición       │
  │ ↗ TENDENCIA │ pct ≥  0.20 │ Mantener / pequeños aumentos      │
  │ → NEUTRO    │ pct > -0.20 │ Observar, sin movimiento          │
  │ ↘ ALERTA    │ pct > -0.60 │ Reducir / revisar tesis           │
  │ ▼ SALIDA    │ pct ≤ -0.60 │ Salir o no entrar                 │
  └─────────────┴─────────────┴───────────────────────────────────┘

  Columna Consenso:  ↗ TENDENCIA  +3/5
                     (suma=+3 sobre 5 señales activas, 1 abstención)
```

---

## POPUP INST. OUT

Muestra alineación para activos en cartera cruzando tres fuentes:
**Inst Señal** (ACOMPAÑAR/MANTENER/REVISAR) · **Analistas** (Wall Street) · **IA Signal** (modelo propio)

| Color | Significado |
|-------|-------------|
| Verde `#00FF88` | Triple coincidencia positiva |
| Cyan | 2 fuentes alineadas |
| Naranja | Señal mixta / alerta |
| Rojo | Divergencia |

---

## FILTROS DEL SCREENER

- **En Cartera** → muestra solo activos con `encartera='Y'`
- **Consenso** → columna ordenable; filtrar ★/▲ para oportunidades
- **Inst Señal** → filtrar ACOMPAÑAR para máxima convicción institucional
- **categoría** → I=compra, N=seguimiento, X=referencia, T=nuevo

---

## HEALTH BAR (barra de estado — esquina inferior derecha)

Monitorea la integridad del pipeline en tiempo real:

| Indicador | Descripción | Verde | Naranja | Rojo |
|-----------|-------------|-------|---------|------|
| 📋 pendientes | Filings descargados no procesados (`processed=0`) | 0 | bajo | alto |
| 🔄 por renovar | Filings con `filing_date ≥ 80 días` | 0 | < 50 | ≥ 50 |
| ⚠ inconsistencias | `fund_holdings` sin symbol en market + market sin CUSIP | 0 | bajo | alto |
