# ConvergIA — Módulo de Consenso Multi-Fuente
**AppOO · Versión 2026-W21**
**Autor:** Wilmer Gutierrez

---

## 1. Propósito

ConvergIA es un módulo de **scan masivo y consenso multi-fuente** diseñado para identificar
oportunidades de inversión en acciones (NYSE/NASDAQ) y tokens crypto (Binance/CoinGecko),
cruzando señales técnicas, fundamentales, de sentimiento y de nuevas tecnologías.

Su objetivo no es reemplazar el análisis individual, sino actuar como **filtro inteligente**
que reduce el universo de miles de activos a una shortlist rankeada por score de consenso,
lista para ser analizada en profundidad por AppOO.

> *"No decide qué activo comprar. Decide cuáles merecen atención."*

### Filosofía
- No predice precios
- No ejecuta órdenes
- No reemplaza el criterio del inversor
- Sí genera señales de alerta temprana
- Sí prioriza por convergencia de múltiples fuentes
- Sí identifica activos alineados con tendencias tecnológicas emergentes

---

## 2. Integración en AppOO

ConvergIA se integra como un módulo independiente dentro de la arquitectura existente:

```
AppOO (DashMainV9_ia.py)
  └── ConvergIA
        ├── Scanner_Stocks          ← Yahoo Finance REST / Alpha Vantage
        ├── Scanner_Crypto          ← CoinGecko API / Binance REST
        ├── Scanner_Tecnologias     ← RSS feeds / web scraping / LLM
        ├── Motor_Consenso          ← Score multi-fuente
        ├── Agente_ConvergIA        ← Scheduler periódico (Class_DashBot.py)
        └── UI_ConvergIA            ← Tab nuevo en DashMainV9
```

### Relación con módulos existentes

| Módulo AppOO | Relación con ConvergIA |
|---|---|
| `CacheHut` | ConvergIA usa el mismo cache TTL para no duplicar descargas |
| `DataHub` | ConvergIA puede leer precios en tiempo real de `DataHub.info` |
| `Class_IA_modelos` | ConvergIA alimenta candidatos que luego pasan por `modelo_buyv01` |
| `Screener_Consenso` (existente) | ConvergIA es la extensión hacia crypto y tendencias tech |
| `BotCrypto` | ConvergIA puede sugerir activos para agregar al universo `otros_activos` |
| `Telegram` | Notificaciones cuando un activo cruza umbral de consenso |

---

## 3. Fuentes de Datos

### 3.1 Stocks (NYSE / NASDAQ)

| Fuente | Datos | Método | Frecuencia |
|---|---|---|---|
| Yahoo Finance REST | Precio, volumen, market cap, beta, P/E, 52w range | Batch 250 símbolos | Diaria |
| Yahoo Finance `yf.Ticker.info` | Fundamentals, dividend, analyst_rec | Por símbolo filtrado | Diaria |
| Alpha Vantage API | RSI, MACD, EMA, volumen relativo | Por símbolo filtrado | Diaria |
| EDGAR / SEC | Earnings recientes, insider trading | Agente existente | Semanal |

### 3.2 Crypto (Binance / CoinGecko)

| Fuente | Datos | Método | Frecuencia |
|---|---|---|---|
| CoinGecko API (free) | Precio, market cap, volumen 24h, % cambio | Batch paginado | 6h |
| Binance REST | Klines (OHLCV), RSI, MACD, EMA | Por par filtrado | 6h |
| CoinGecko Trending | Top 7 trending coins | Endpoint `/trending` | 6h |
| CoinMarketCap (opcional) | Fear & Greed Index, categorías | REST | Diaria |

### 3.3 Tendencias Tecnológicas (nuevo)

| Fuente | Datos | Método |
|---|---|---|
| RSS feeds (TechCrunch, MIT Tech Review, Wired) | Noticias tech emergentes | Parser RSS |
| Google Trends API (pytrends) | Tendencias de búsqueda por tecnología | REST |
| ArXiv API | Papers de IA/blockchain recientes | REST |
| Anthropic API (Claude) | Clasificación de noticias + mapeo a activos | LLM |

**Flujo de tendencias tech:**
```
RSS feed / Google Trends
    └── Filtrar por keywords (IA, blockchain, energía, biotech, etc.)
            └── Claude API: "¿Qué empresas o tokens se benefician de esta noticia?"
                    └── Mapear a tickers en universo ConvergIA
                            └── Bonus score por alineación tecnológica
```

---

## 4. Universo de Activos

### 4.1 Stocks
- Base inicial: tabla `Market` existente (AppOO) + NASDAQ screener (dividends)
- Expansión: S&P 500 completo + NASDAQ 100 + lista tech propia
- Filtros de entrada:
  - `marketCap >= 500M` (elimina micro-caps)
  - `averageVolume >= 500K` (liquidez mínima)
  - `price >= 1.0` (elimina peniques)

### 4.2 Crypto
- Base inicial: tabla `otros_activos` (BotCrypto) + CoinGecko top 500 por market cap
- Filtros de entrada:
  - `market_cap >= 10M USD`
  - `volume_24h >= 1M USD`
  - Excluir stablecoins (USDT, USDC, DAI, BUSD)

---

## 5. Señales del Motor de Consenso

Cada activo recibe votos de múltiples dimensiones. Cada señal emite:
`+1` favorable | `0` neutral | `-1` desfavorable | `None` abstiene

### 5.1 Señales Técnicas (aplica stocks y crypto)

| Señal | Cálculo | Voto |
|---|---|---|
| **RSI** | RSI < 35 → +1 / RSI 35–65 → 0 / RSI > 65 → -1 | +1/0/-1 |
| **MACD** | Cruce alcista reciente → +1 / bajista → -1 / plano → 0 | +1/0/-1 |
| **EMA Trend** | Precio > EMA50 > EMA200 → +1 / inverso → -1 | +1/0/-1 |
| **Volumen** | Vol actual > 1.5x promedio 20d → +1 / < 0.7x → -1 | +1/0/-1 |
| **52w Range** | Precio < 30% del rango (cerca mínimos) → +1 / > 80% → -1 | +1/0/-1 |

### 5.2 Señales Fundamentales (solo stocks)

| Señal | Cálculo | Voto |
|---|---|---|
| **Analistas** | buy/strong_buy → +1 / hold → 0 / sell → -1 | +1/0/-1 |
| **Earnings Trend** | Beat últimos 2 trimestres → +1 / miss → -1 | +1/0/-1 |
| **Dividend Yield** | Yield > 3% → +1 / 1-3% → 0 / sin dividendo → None | +1/0/None |
| **Valuación** | P/E < sector median → +1 / > 2x sector → -1 | +1/0/-1 |
| **Insider Buy** | Compras insider recientes → +1 / ventas → -1 | +1/0/-1 |
| **Institucional** | `inst_score` del módulo existente (Screener Consenso) | +1/0/-1 |

### 5.3 Señales Crypto Específicas

| Señal | Cálculo | Voto |
|---|---|---|
| **Market Cap Trend** | Subió >10% en 30d → +1 / bajó > -20% → -1 | +1/0/-1 |
| **Dominancia BTC** | BTC.dominance < 45% (altseason) → +1 para altcoins | +1/0/-1 |
| **Trending** | En CoinGecko trending top7 → +1 | +1/0/None |
| **Fear & Greed** | < 25 (Fear extremo) → +1 / > 80 (Greed) → -1 | +1/0/-1 |
| **On-Chain** | (futuro) Whale accumulation, exchange outflows | +1/0/-1 |

### 5.4 Señal Tecnológica (nueva — aplica ambos)

| Señal | Cálculo | Voto |
|---|---|---|
| **Tech Alignment** | LLM detecta alineación con tendencia emergente → +1 | +1/0/None |
| **Google Trends** | Búsquedas en alza >50% en 30d para categoría del activo → +1 | +1/0/None |
| **Sector Momentum** | Sector del activo está en tendencia según noticias → +1/0/-1 | +1/0/-1 |

---

## 6. Score de Consenso Final

```
                suma_votos_activos
consenso_pct = ─────────────────────    (abstenciones no cuentan)
                n_votos_activos

score_final = consenso_pct
            × (1 + tech_alignment_bonus)   ← 0.0 a 0.3
            × momentum_factor              ← 0.7 a 1.3 según volumen
```

### Clasificación

| Nivel | Condición | Acción sugerida |
|---|---|---|
| ★ UNÁNIME | todos los votos = +1 | Máxima convicción — analizar urgente |
| ▲ CONSENSO | pct ≥ 0.60 | Candidato fuerte — revisar en AppOO |
| ↗ TENDENCIA | pct ≥ 0.20 | Observar — puede mejorar |
| → NEUTRO | pct > -0.20 | Sin señal clara |
| ↘ ALERTA | pct > -0.60 | Evitar / reducir exposición |
| ▼ SALIDA | pct ≤ -0.60 | No entrar / considerar salida |

---

## 7. Arquitectura de Clases

```
AppOO/
  ConvergIA/
    ├── Class_ConvergIA.py          ← Motor principal + coordinación
    ├── Scanner_Stocks.py           ← Descarga y señales stocks
    ├── Scanner_Crypto.py           ← Descarga y señales crypto
    ├── Scanner_Tecnologias.py      ← RSS + Google Trends + LLM
    ├── Motor_Consenso.py           ← Score y ranking final
    ├── UI_ConvergIA.py             ← Tab en DashMainV9
    └── Doc/
          └── ConvergIA_especificacion.md   ← este archivo
```

### Class_ConvergIA (coordinador principal)

```python
class ConvergIA:
    """
    Coordinador del módulo de consenso multi-fuente.
    Se registra como agente en Class_DashBot.py.
    """

    def __init__(self, datahub, cache_hut, repositorio):
        self.datahub = datahub
        self.cache = cache_hut
        self.repositorio = repositorio
        self.resultados = {}        # symbol → ConsensoResult
        self.ultima_ejecucion = None

    def run_scan_completo(self):
        """Pipeline completo: scan → señales → consenso → notificar"""
        stocks = self.Scanner_Stocks.scan()
        crypto = self.Scanner_Crypto.scan()
        candidatos = stocks + crypto
        self.Motor_Consenso.calcular(candidatos)
        self._notificar_top()

    def get_shortlist(self, nivel_minimo="TENDENCIA") -> list:
        """Retorna activos que superan el umbral de consenso"""
        ...

    def get_tendencias_tech(self) -> list:
        """Retorna tendencias tech detectadas y activos mapeados"""
        ...
```

### ConsensoResult (estructura por activo)

```python
@dataclass
class ConsensoResult:
    symbol: str
    tipo: str                   # "Stock" | "Crypto"
    nombre: str
    precio: float
    consenso_pct: float
    nivel: str                  # ★ UNÁNIME / ▲ CONSENSO / etc.
    score_final: float
    votos: dict                 # {señal: voto} para explicabilidad
    votos_activos: int
    tech_alignment: bool
    tech_reason: str            # Texto del LLM explicando la alineación
    timestamp: datetime
```

---

## 8. Persistencia

### Tabla `convergia_resultados`

```sql
CREATE TABLE convergia_resultados (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL,
    tipo            ENUM('Stock', 'Crypto') NOT NULL,
    fecha           DATE NOT NULL,
    timestamp       DATETIME NOT NULL,
    consenso_pct    FLOAT,
    nivel           VARCHAR(20),
    score_final     FLOAT,
    votos_json      JSON,           -- detalle de cada señal
    tech_alignment  TINYINT(1),
    tech_reason     TEXT,
    notificado      TINYINT(1) DEFAULT 0,
    INDEX idx_symbol_fecha (symbol, fecha),
    INDEX idx_nivel (nivel)
);
```

### Tabla `convergia_tendencias`

```sql
CREATE TABLE convergia_tendencias (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    fecha       DATE NOT NULL,
    categoria   VARCHAR(50),        -- 'IA', 'blockchain', 'energia', 'biotech'
    titulo      TEXT,
    fuente      VARCHAR(100),
    url         TEXT,
    tickers     JSON,               -- ["NVDA", "MSFT", "CGPT"] mapeados por LLM
    relevancia  FLOAT               -- 0.0 a 1.0
);
```

---

## 9. Agente Scheduler

```python
# En Class_DashBot.py

@wait_rate(21600)   # cada 6 horas
def Agente_ConvergIA(self):
    """
    Agente periódico de scan masivo.
    - Stocks: scan diario (1 vez por día en horario de mercado)
    - Crypto: scan cada 6h (mercado 24/7)
    - Tendencias tech: scan diario
    """
    convergia = ConvergIA(DataHub, CacheHut, self.repositorio)
    convergia.run_scan_completo()
```

---

## 10. UI — Tab ConvergIA en DashMainV9

### Layout

```
+------------------------------------------------------------------+
|   ConvergIA — Consenso Multi-Fuente          [🔄 Scan Now]       |
|   Última actualización: 2026-05-17 14:30                         |
+------------------------------------------------------------------+
|  FILTROS: [Todos ▼] [★▲↗ ▼] [Stocks|Crypto|Ambos] [Tech Only □] |
+------------------------------------------------------------------+
|  Symbol | Tipo  | Precio | Nivel    | Score | RSI | MACD | Tech |
|---------|-------|--------|----------|-------|-----|------|------|
| NVDA    | Stock | 890.50 | ▲CONSENS | 0.82  |  38 |  ▲   |  ✓  |
| CGPT    | Crypto| 0.038  | ↗TENDENC | 0.61  |  42 |  ▲   |  ✓  |
| AMT     | Stock | 180.20 | ▲CONSENS | 0.79  |  31 |  ▲   |  ✗  |
+------------------------------------------------------------------+
|  Panel Tendencias Tech                                           |
|  🤖 IA: NVDA, MSFT, CGPT     🔋 Energía: VST, PLUG              |
|  🧬 Biotech: ---              ⛓ Blockchain: CGPT, ETH            |
+------------------------------------------------------------------+
|  [Agregar a Market] [Agregar a BotCrypto] [Ver Detalle]          |
+------------------------------------------------------------------+
```

### Acciones desde UI

| Acción | Función |
|---|---|
| **Agregar a Market** | Inserta el ticker en tabla `market` para análisis AppOO completo |
| **Agregar a BotCrypto** | Inserta en `otros_activos` con cuenta B0000002 |
| **Ver Detalle** | Popup con breakdown de todos los votos del consenso |
| **Scan Now** | Fuerza ejecución inmediata del `Agente_ConvergIA` |

---

## 11. Parámetros de Configuración

Almacenados en tabla `sesion` (campo `parameters`), vehículo `"ConvergIA"`:

```json
{
  "stocks": {
    "min_market_cap": 500000000,
    "min_avg_volume": 500000,
    "min_price": 1.0,
    "universo_extra": ["SKLZ", "PLUG", "FMC", "PSEC"]
  },
  "crypto": {
    "min_market_cap_usd": 10000000,
    "min_volume_24h": 1000000,
    "excluir_stables": true,
    "top_n_coingecko": 500
  },
  "consenso": {
    "nivel_notificacion": "TENDENCIA",
    "umbral_score_telegram": 0.65,
    "max_notificaciones_dia": 10
  },
  "tech": {
    "keywords": ["artificial intelligence", "blockchain", "clean energy",
                 "semiconductor", "biotech", "quantum computing"],
    "usar_llm": true,
    "llm_model": "claude-sonnet-4-20250514"
  },
  "scheduler": {
    "frecuencia_horas": 6,
    "horario_stocks": "09:30-16:00",
    "timezone": "America/New_York"
  }
}
```

---

## 12. Dependencias

```python
# Nuevas (agregar a requirements.txt)
pytrends          # Google Trends
feedparser        # RSS feeds
anthropic         # Claude API para clasificación LLM

# Existentes en AppOO (reutilizar)
requests          # Yahoo Finance REST / CoinGecko
pandas            # DataFrames
cachetools        # CacheHut
mysql-connector   # Persistencia
python-binance    # Klines crypto
```

---

## 13. Roadmap de Implementación

| Fase | Módulo | Estado | Prioridad |
|---|---|---|---|
| **1** | `Scanner_Stocks.py` — Yahoo Finance REST batch | ⬜ Pendiente | Alta |
| **1** | `Scanner_Crypto.py` — CoinGecko + Binance klines | ⬜ Pendiente | Alta |
| **1** | `Motor_Consenso.py` — señales técnicas básicas | ⬜ Pendiente | Alta |
| **2** | `Motor_Consenso.py` — señales fundamentales stocks | ⬜ Pendiente | Media |
| **2** | Persistencia BD (`convergia_resultados`) | ⬜ Pendiente | Media |
| **2** | Notificaciones Telegram | ⬜ Pendiente | Media |
| **3** | `Scanner_Tecnologias.py` — RSS + Google Trends | ⬜ Pendiente | Media |
| **3** | Integración Claude API para mapeo tech→tickers | ⬜ Pendiente | Media |
| **4** | `UI_ConvergIA.py` — Tab en DashMainV9 | ⬜ Pendiente | Baja |
| **4** | `Agente_ConvergIA` — scheduler en Class_DashBot | ⬜ Pendiente | Baja |
| **5** | Señales on-chain crypto (whale tracker) | ⬜ Pendiente | Futura |
| **5** | Integración con `modelo_buyv01` (AppOO IA) | ⬜ Pendiente | Futura |

---

## 14. Convenciones (heredadas de AppOO)

- Type hints y docstrings en toda función nueva
- `logging` en producción, nunca `print()`
- SQL parametrizado — sin riesgo de inyección
- Usar `CacheHut` para no duplicar descargas de Yahoo Finance
- Archivos `.md` de especificación antes de implementar
- Claude Code (VS Code) lee este `.md` como contexto antes de generar código

---

## 15. Nota para Claude Code

Este documento es el punto de entrada para implementar ConvergIA.

**Orden sugerido de implementación:**
1. Leer `PROJECT_INSTRUCTIONS.md` para entender el contexto global de AppOO
2. Leer `YahooFinance_REST_Market_Loader.md` para el patrón de descarga batch
3. Leer `BotCrypto_especificacion_tecnica.md` para entender la lógica de señales
4. Leer `screener_consenso_modelo.md` para reutilizar la lógica de votos existente
5. Implementar en el orden del roadmap (Fase 1 primero)

**Principio clave:** ConvergIA es una extensión natural del Screener de Consenso existente,
aplicada a un universo más amplio (miles de activos) y enriquecida con señales crypto
y tendencias tecnológicas via LLM.
