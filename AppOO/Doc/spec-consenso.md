# CONSENSO SCORE — ARQUITECTURA, IMPLEMENTACIÓN Y EXPANSIÓN
**AppOO · Versión 2026-W25**

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
     │   (7 votos)           │
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
| `sync_13f_holdings` | **Diario** | Parsea XMLs (`processed=0`), mapea CUSIP→symbol, calcula NEW/BUY/SELL/HOLD, bulk upsert `fund_holdings` |
| `sync_13f_scores` | **Diario** | Recalcula `inst_score` v2 + guarda fh_buy/sell_ratio, CALL/PUT, ΔCall/ΔPut, +Nuevos, -Salidas |

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

## COLUMNAS INSTITUCIONALES — MAPA COMPLETO

### Visibles en Screener

| Header | Campo BD | Fuente | Descripción |
|--------|----------|--------|-------------|
| Last | `lastPrice` | Yahoo | Último precio |
| Rotación | calculado | market | floatShares / volume — proxy de liquidez institucional |
| Inst Score | `inst_score` | EDGAR calc | Score blendado (ver fórmula v2 abajo) |
| Inst % | `inst_ownership_pct` | EDGAR calc | fh_total_shares / floatShares |
| 13F Inst | `fh_count` | EDGAR | Fondos con posición STK activa (último filing) |
| 13F Buy% | `fh_buy_ratio` | EDGAR | NEW+BUY / total STK filings |
| 13F Sell% | `fh_sell_ratio` | EDGAR | SELL / total STK filings |
| CALL | `fh_call_shares` | EDGAR | Total acciones opciones CALL Q4 (en millones) |
| PUT | `fh_put_shares` | EDGAR | Total acciones opciones PUT Q4 (en millones) |
| ΔCall | `delta_call_shares` | EDGAR calc | CALL Q4 − CALL Q3 → acumulación/distribución silenciosa |
| ΔPut | `delta_put_shares` | EDGAR calc | PUT Q4 − PUT Q3 → cobertura bajista creciente/decreciente |
| +Nuevos | `new_entrants` | EDGAR | Fondos que abrieron posición por 1ra vez en Q4 (operation='NEW') |
| -Salidas | `full_exits` | EDGAR calc | Fondos en Q3 que no presentaron Q4 (salida silenciosa) |
| 13F Value | `fh_total_value` | EDGAR | Valor total posiciones STK (miles USD) |
| Top Holder | `inst_top_holder` | Yahoo | Nombre del mayor fondo institucional |

### Usadas "tras bambalinas" — scoring y votos, no visibles como columna

| Campo BD | Dónde se usa | Descripción |
|----------|-------------|-------------|
| `floatShares` | sync_13f_scores | Base para calcular fh_ownership_pct |
| `sharesOutstanding` | sync_13f_scores | Fallback si no hay floatShares |
| `fh_total_shares` | sync_13f_scores | SUM acciones STK ÷ float = fh_ownership_pct |
| `analyst_rec` | Voto #3 Consenso | buy/strong_buy/hold/sell |
| `analyst_mean` | Inst Señal | media recomendación numérica |
| `analyst_count` | Consenso display | número de analistas |
| `categoriaActivo` | Voto #5 Valuación | I/S/N/X/T |
| `encartera` | Filtro Screener + Consenso | Y = en cartera |
| `insider_ownership_pct` | pendiente | % insiders (Yahoo) |

---

## FÓRMULA inst_score v2 — IMPLEMENTADA

```
fund_holdings (13F) — STK positions
  ├── SUM(shares) / floatShares  ──────────────►  fh_ownership_pct  (lo más tangible)
  ├── COUNT(DISTINCT fund_id)    ──────────────►  fh_count
  ├── NEW+BUY / total            ──────────────►  fh_buy_ratio
  └── (new_entrants − full_exits) / fh_count  ►  flujo_neto  [-1, +1]
       │
       ├── new_entrants  = fondos con operation='NEW' en Q4
       └── full_exits    = fondos en Q3 que NO aparecen en Q4

  inst_score = fh_ownership_pct       × 0.40   ← más tangible: cuánto del float tienen
             + log(max(fh_count, 1))  × 0.20   ← cobertura institucional
             + fh_buy_ratio           × 0.20   ← dirección del flujo
             + flujo_neto             × 0.20   ← entradas netas Q3→Q4
                                               ──►  Inst Score  [0..∞]
```

> **Nota floatShares:** Yahoo `heldPercentInstitutions` puede superar 100% por short selling.
> Usamos `floatShares` propio desde Yahoo `keyStatistics` en tabla `market` para reproducibilidad.
> Cubre ~9K fondos EDGAR — conservador pero consistente entre activos.
> **Cobertura 2026-W17:** 1299/1349 símbolos con `inst_ownership_pct` (96%) — batch Yahoo v7/finance/quote (250 símbolos/request).

> **full_exits:** cuando un fondo vende completamente, no reporta el símbolo (no hay registro shares=0).
> La salida se detecta por ausencia en Q4. Ventanas calculadas dinámicamente en `load_fund_holdings_stats`
> según calendario 13F (Q_ant: Aug–Dec, Q_act: Jan+).

---

## SEÑAL INSTITUCIONAL COMPUESTA (columna "Inst Señal")

Resume en una palabra la postura de los fondos institucionales:

- **ACOMPAÑAR** — inst_score ≥ 0.40 AND buy_ratio ≥ 0.50 AND fh_count ≥ 20
- **MANTENER** — inst_score ≥ 0.25 OR fh_count ≥ 10
- **REVISAR** — resto

---

## MODELO DE CONSENSO — 7 VOTOS (ACTUAL)

Cada señal emite: `+1` favorable | `0` neutral | `-1` desfavorable | `None` abstiene

```
  # FUENTE           CÁLCULO                        VOTO
  ──────────────────────────────────────────────────────────────────
  1. NET (13F)       fh_buy_ratio − fh_sell_ratio   +1 / 0 / -1
                     ranking cartera                None si sin datos
                     top 33%  → +1
                     mid 33%  →  0
                     bot 33%  → -1

  2. OPTIONS (13F)   call_shares/(call+put shares)  +1 / 0 / -1
                     ≥ 0.60   → +1                  None si sin opciones
                     ≥ 0.40   →  0
                     < 0.40   → -1

  3. FLUJO (13F)     (new_entrants − full_exits) /  +1 / 0 / -1
                     fh_count ranking cartera       None si sin fh_count
                     flujo_neto clipeado [-1, +1]
                     top 33%  → +1
                     mid 33%  →  0
                     bot 33%  → -1

  4. ANALISTAS (YF)  recommendationKey              +1 / 0 / -1
                     buy/strong_buy  → +1           None si sin datos
                     hold            →  0
                     sell/strong_sell→ -1

  5. IA SIGNAL (Mod) CSV buy/sell (mercado abierto)  +1 / 0 / -1
                     buy   → +1
                     sell  → -1
                     none  →  0
                     ──────────────────────────────────────────
                     ⚠ SOLO DISPLAY — NO cuenta en
                        gate Telegram ni en consenso_tag.
                        Aparece para referencia visual.

  6. VALUACIÓN       categoriaActivo                +1 / 0 / -1
                     I → +1 / N → 0 / S → -1        None si X/T
                     X / T → abstiene

  7. COBERTURA       fh_count                       +1 / 0 / -1
                     ≥ 20 → +1 / ≥ 5 → 0 / < 5 → -1
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

  Columna Consenso:  ↗ TENDENCIA  +4/7
                     (suma=+4 sobre 7 señales activas, 0 abstenciones)
```

---

## POPUP INSTITUCIONAL — ALIGNMENT CHECK

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

## GATE CONSENSO → TELEGRAM (implementado 2026-W17)

El Consenso actúa como **capa de permiso** sobre la señal técnica IA antes de enviar
alertas a Telegram. Evita que el modelo IA se confirme a sí mismo.

### Cómo funciona

```
  Señal IA (técnica)          Consenso (6 votos sin Mod)      Acción Telegram
  ─────────────────────────────────────────────────────────────────────────────
  BUY  (score ≥ umbral)  +  UNANIME / CONSENSO / TENDENCIA  →  ✅ Enviar alerta
  BUY                    +  NEUTRO / ALERTA / SALIDA         →  🔇 Silenciar
  SELL (score ≥ umbral)  +  ALERTA / SALIDA                  →  ✅ Enviar alerta
  SELL                   +  NEUTRO / TENDENCIA / CONSENSO    →  🔇 Silenciar
```

### Voto Mod excluido del gate

El voto `Mod` (señal IA técnica, voto #5) **NO cuenta** en el cálculo del gate.
Si se incluyera, la señal se confirmaría a sí misma: un BUY +1 ya empuja
el Consenso hacia TENDENCIA con solo 1 voto más de apoyo → umbral demasiado fácil.

El gate usa los **6 votos fundamentales/institucionales** (Net, Opt, Flujo, Ana, Val, Cob)
para verificar si los fundamentos apoyan de forma **independiente** la señal técnica.

### Implementación

| Componente | Archivo | Detalle |
|---|---|---|
| `refresh_consenso_tags(account)` | `Class_Screener.py` | Calcula 6 votos sin Mod, escribe `consenso_tag` + `consenso_suma` en market |
| `Agente_ConsensoCache` | `Class_DashBot.py` | `@wait_rate(300)` — refresca tags cada 5 min |
| Gate BUY | `Agente_message_Manager_Buy` | Bloquea si tag ∉ {UNANIME, CONSENSO, TENDENCIA} |
| Gate SELL | `Agente_message_Manager_sell` | Bloquea si tag ∉ {ALERTA, SALIDA} |

### Columnas BD

| Columna | Tipo | Descripción |
|---|---|---|
| `market.consenso_tag` | VARCHAR(15) | Tag limpio: UNANIME/CONSENSO/TENDENCIA/NEUTRO/ALERTA/SALIDA |
| `market.consenso_suma` | TINYINT | Suma de los 6 votos sin Mod (-6 a +6) |

> `tag=None` → gate abierto (símbolo sin tag calculado aún — no bloquea)

---

## HEALTH BAR (barra de estado — esquina inferior derecha)

Monitorea la integridad del pipeline en tiempo real:

| Indicador | Descripción | Verde | Naranja | Rojo |
|-----------|-------------|-------|---------|------|
| 📋 pendientes | Filings descargados no procesados (`processed=0`) | 0 | bajo | alto |
| 🔄 por renovar | Filings con `filing_date ≥ 80 días` | 0 | < 50 | ≥ 50 |
| ⚠ inconsistencias | `fund_holdings` sin symbol en market + market sin CUSIP | 0 | bajo | alto |

---

## EXPANSIÓN — DECISIONES DE ALCANCE

Los votos de Consenso deben ser señales **estructuralmente distintas** al análisis técnico:
flujos institucionales, recomendaciones de analistas, fundamentals.

| Señal | Destino | Razón |
|---|---|---|
| Rango 52 semanas | **Modelos IA (BUY/SELL)** | Indicador técnico de precio — el ML aprende el peso óptimo |
| Volumen relativo | **Modelos IA (BUY/SELL)** | Ídem — mejor como feature de entrenamiento que como regla fija |
| Tech Alignment | **Voto nuevo en Consenso** | Señal externa (noticias) que el modelo IA no ve |

Rango 52w y Volumen quedan **pendientes para la próxima revisión de features** de los modelos IA.
Ver `Doc/modelo_buyv01.md` y `Doc/modelo_sellv01.md` para el estado actual de features.

---

## VOTO FUTURO: TECH ALIGNMENT (Pendiente)

### Qué mide

Si la empresa está alineada con una tendencia tecnológica emergente que aparece en noticias del día.
Es información que **ningún otro voto captura** y que el modelo IA no tiene como input.

### Cómo funcionaría

```
RSS feeds (TechCrunch, MIT Tech Review)
  → feedparser: extrae titulares
      → Claude Haiku: "¿qué categorías tech son prominentes hoy?"
          → retorna lista JSON: ["ai_semiconductors", "clean_energy", ...]
              → THEME_MAP: categoría → tickers en cartera
                  → voto_tech_alignment(symbol, temas_activos)
```

### Comportamiento del voto

| Caso | Voto |
|---|---|
| Símbolo en tema activo hoy | +1 |
| Sin alineación | 0 (abstención — no penaliza) |

No penaliza porque la mayoría de nuestras acciones son dividendo/utilities. Un banco no debería
bajar su consenso por no ser semiconductores.

### THEME_MAP propuesto

```python
THEME_MAP = {
    "ai_semiconductors": ["NVDA", "AMD", "INTC", "ASML", "QCOM", "MU"],
    "clean_energy":      ["VST", "PLUG", "NEE", "ENPH", "FSLR", "CEG"],
    "biotech":           ["PFE", "ABBV", "BMY", "AMGN", "GILD", "MRNA"],
    "blockchain":        ["CGPT", "MSTR", "COIN"],
    "cloud_saas":        ["MSFT", "AMZN", "GOOGL", "CRM", "NOW", "SNOW"],
    "robotics":          ["ISRG", "ABB", "ROK", "TER"],
}
```

### Infraestructura necesaria

| Qué | Detalle |
|---|---|
| Paquetes | `feedparser` + `anthropic` — ya instalados |
| API key | `ANTHROPIC_API_KEY` como env variable (igual que `APPOO_TMP`) |
| Módulo RSS + Claude | `ConvergIA/Scanner_Tecnologias.py` |
| Módulo THEME_MAP | `ConvergIA/ThemeMapper.py` |
| Agente | `Agente_TechAlignment` en `Class_DashBot.py` — 1 vez/día |
| Persistencia | `tmp/tech_temas.json` — el popup lo lee en tiempo real |
| Fallback | JSON vacío → voto 0 para todos → no rompe nada |

### Decisiones pendientes antes de codificar

1. **API key:** ¿env variable en `launch.json` o en tabla `sesion` bajo vehiculo `"CLAUDE"`?
2. **Scope del voto:** ¿solo en el popup Consenso o también en la columna del Screener?
3. **THEME_MAP:** ¿en código Python (archivo editable) o en JSON configurable desde la app?

---

## IDEA FUTURA: SCANNER YOUTUBE (No implementada)

### Origen de la idea

PLUG fue descubierto a través de un video de YouTube antes de que apareciera en ningún screener
institucional. Los canales de inversión de calidad a veces identifican activos antes que los datos
estructurados (13F, analistas). Eso es valor que hoy no capturamos.

### Cómo funcionaría

YouTube expone **RSS feeds por canal** sin necesidad de API key ni costo:
```
https://www.youtube.com/feeds/videos.xml?channel_id=XXXX
```
Devuelve títulos y descripciones de los últimos videos — exactamente el mismo formato que
TechCrunch. `feedparser` ya instalado lo lee sin cambios.

```
RSS feeds de canales de inversión seleccionados
  → feedparser: extrae títulos + descripciones
      → Claude Haiku: "¿qué tickers se mencionan como oportunidad?"
          → lista de símbolos candidatos
              → sync_market() los agrega con categoriaActivo='T' (descubierto externamente)
                  → entran al análisis normal de Consenso
```

### Por qué encaja bien

- Misma infraestructura que Tech Alignment (feedparser + Claude) — costo de implementación bajo
- Los tickers que salen se agregan a `market` con `categoriaActivo='T'`, que ya existe
- Desde ahí el sistema de Consenso los evalúa automáticamente como a cualquier otro activo

### Filtrado necesario (el problema central)

YouTube tiene demasiado volumen — la mayoría es ruido. Se necesitan 4 capas:

1. **Canales curados** — solo 5-10 canales ya validados por el usuario (no rastrear YouTube en general)
2. **Filtro de título** — descartar videos sin tickers o palabras clave de análisis (`buy`, `undervalued`, `dividend`). Bota el 80% sin costo.
3. **Claude como juez** — de los que pasan, evalúa si es análisis genuino o clickbait y si el tono es bullish
4. **Consenso como validación final** — el ticker descubierto entra a `market` con `categoriaActivo='T'` y pasa por los 6 votos existentes. YouTube solo detecta candidatos, no decide compras.

### Estado

**Idea documentada — no implementada.** Implementar después de validar Tech Alignment con RSS de noticias.

---

## LO QUE NO VAMOS A HACER

- Sistema de consenso paralelo — el existente es la fuente de verdad
- Votos de indicadores técnicos en Consenso (van a los modelos IA)
- Alpha Vantage o Google Trends — otra dependencia inestable
- Tablas nuevas — si hace falta persistir algo, columna nueva en `market`
- Penalización negativa con Tech Alignment
