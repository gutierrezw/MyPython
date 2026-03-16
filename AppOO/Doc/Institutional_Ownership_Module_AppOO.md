# AppOO — Institutional Ownership & Fund Discovery Module
### Diseño Técnico Unificado

**Autor:** Wilmer Gutierrez
**Versión consolidada:** Marzo 2026
**Proyecto:** AppOO — Sistema de Inversión Personal

---

## 1. Objetivo Estratégico

Este módulo extiende AppOO con inteligencia de flujo institucional, cerrando el triángulo estratégico del sistema:

> **Dividendos + Fundamentales (EDGAR) + Flujo Institucional = Screener de largo plazo de alta convicción**

La hipótesis central es que las empresas de dividendos acumuladas sistemáticamente por los grandes fondos presentan una señal de calidad estructural que el análisis fundamental y técnico por sí solos no capturan. Identificar esa acumulación —y su evolución trimestral— permite filtrar el universo invertible con un criterio adicional de alta relevancia institucional.

---

## 2. Fuentes de Datos

| Fuente | Datos provistos | Prioridad |
|--------|----------------|-----------|
| Yahoo Finance (HTTP directo) | `institutionOwnership`, `majorHoldersBreakdown`: ownership pct, top holders, shares | Principal |
| SEC EDGAR (13F-HR) | Posiciones completas de cartera por fondo, evolución trimestral | Fase 3 |
| IB Client Portal API (REST/WS) | Datos de mercado, órdenes, posiciones | Mercado / Trading |

> **Decisión de diseño:** se descartó `yf.Ticker()` (librería yfinance) porque genera llamadas propias que interfieren con el sistema de caché de la App. En su lugar se usa `_yahoo_session()` de `Class_Screener.py` con requests HTTP directos al endpoint `quoteSummary`, idéntico al patrón de `_fetch_fundamentals` en `sync_market`.

---

## 3. Arquitectura del Flujo

### 3.1 Pipeline principal

```
Tabla market (todos los símbolos activos)
  └─► Yahoo quoteSummary (institutionOwnership + majorHoldersBreakdown)
        ├─► Ranking de fondos (frecuencia de aparición → tabla funds)
        └─► Institutional Score por empresa
              └─► UPDATE Market (inst_* fields)
                    └─► [Fase 3] SEC EDGAR 13F-HR
                              └─► fund_holdings (cusip, shares, operation)
```

### 3.2 Lógica de descubrimiento de fondos

En lugar de mantener una lista estática, los fondos se descubren automáticamente a partir del universo completo de símbolos activos en `market`.

1. Cargar todos los símbolos activos (`categoriaActivo NOT IN ('I','S','X')`).
2. Para cada símbolo consultar `institutionOwnership` vía `quoteSummary`.
3. Acumular la frecuencia de aparición de cada fondo en el universo.
4. Construir el ranking: los fondos con más apariciones son los más sistémicamente relevantes.
5. UPSERT en tabla `funds` con frecuencia actualizada.

> **Nota:** `discover_funds(top_n=200)` como método de clase mantiene la opción de limitar a Top 200 por MarketCap para uso ad-hoc. `sync_institutional` procesa el universo completo.

**Ejemplo de ranking esperado:**

| Fondo | Apariciones (universo completo) | CIK SEC |
|-------|---------------------------------|---------|
| Vanguard Group | ~190 | 0000102909 |
| BlackRock | ~188 | 0001364742 |
| State Street | ~170 | 0000093751 |
| Fidelity | ~145 | — |
| Capital Group | ~120 | — |

---

## 4. Módulo de Ownership — Yahoo quoteSummary

### 4.1 Endpoint y módulos

```
URL:     https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}
Módulos: institutionOwnership,majorHoldersBreakdown
Auth:    cookie + crumb via _yahoo_session() de Class_Screener.py
```

### 4.2 Mapeo de respuesta

```
majorHoldersBreakdown.institutionsPercentHeld.raw  → inst_ownership_pct
majorHoldersBreakdown.insidersPercentHeld.raw       → insider_ownership_pct
majorHoldersBreakdown.institutionsCount.raw         → inst_holders_count
institutionOwnership.ownershipList[0].organization  → inst_top_holder
institutionOwnership.ownershipList[0].position.raw  → inst_top_holder_shares
institutionOwnership.ownershipList[].organization   → fund_names (para fund discovery)
```

### 4.3 Campos extraídos

| Campo | Fuente Yahoo | Descripción |
|-------|-------------|-------------|
| `inst_ownership_pct` | `majorHoldersBreakdown.institutionsPercentHeld` | % del float en manos de instituciones |
| `insider_ownership_pct` | `majorHoldersBreakdown.insidersPercentHeld` | % en manos de insiders |
| `inst_top_holder` | `ownershipList[0].organization` | Nombre del mayor fondo institucional |
| `inst_top_holder_shares` | `ownershipList[0].position.raw` | Acciones en poder del top holder |
| `inst_holders_count` | `majorHoldersBreakdown.institutionsCount` | Total de fondos institucionales registrados |
| `inst_update` | generado en runtime | Timestamp de la última actualización |

---

## 5. Modelo de Datos

### 5.1 Extensión de la tabla Market

```sql
ALTER TABLE market ADD COLUMN inst_funds              INT;
ALTER TABLE market ADD COLUMN inst_shares             BIGINT;
ALTER TABLE market ADD COLUMN inst_score              FLOAT;
ALTER TABLE market ADD COLUMN inst_update             DATETIME;
ALTER TABLE market ADD COLUMN inst_ownership_pct      FLOAT;
ALTER TABLE market ADD COLUMN insider_ownership_pct   FLOAT;
ALTER TABLE market ADD COLUMN inst_top_holder         VARCHAR(120);
ALTER TABLE market ADD COLUMN inst_top_holder_shares  BIGINT;
ALTER TABLE market ADD COLUMN inst_holders_count      INT;
```

### 5.2 Tablas auxiliares

```sql
-- Fondos descubiertos automáticamente
CREATE TABLE funds (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    fund_name   VARCHAR(200) NOT NULL,
    cik         VARCHAR(20),
    frequency   INT DEFAULT 0,
    last_update DATETIME
);

-- Mapeo CUSIP → symbol (para resolución de 13F)
CREATE TABLE cusip_map (
    cusip       VARCHAR(12) PRIMARY KEY,
    symbol      VARCHAR(20),
    name        VARCHAR(200),
    last_update DATETIME
);

-- Posiciones por fondo con historial de operación (Fase 3)
CREATE TABLE fund_holdings (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    fund_id      INT,
    cusip        VARCHAR(12),
    symbol       VARCHAR(20),        -- resuelto desde cusip_map (nullable hasta resolver)
    shares       BIGINT,
    value        DECIMAL(20,2),      -- en miles USD (como viene del 13F)
    report_date  DATE,
    shares_prev  BIGINT,             -- shares del trimestre anterior
    shares_delta BIGINT,             -- shares - shares_prev
    pct_change   FLOAT,              -- % cambio vs trimestre anterior
    operation    VARCHAR(10),        -- NEW / BUY / SELL / HOLD / CLOSED
    UNIQUE KEY uq_holding (fund_id, cusip, report_date)
);
```

### 5.3 Lógica de actualización en market

La actualización respeta la regla de categorías del sistema (`categoriaActivo NOT IN ('I','S','X')`):

```sql
UPDATE market
SET
    inst_ownership_pct       = %s,
    insider_ownership_pct    = %s,
    inst_top_holder          = %s,
    inst_top_holder_shares   = %s,
    inst_holders_count       = %s,
    inst_score               = %s,
    inst_update              = NOW()
WHERE symbol = %s
  AND categoriaActivo NOT IN ('I', 'S', 'X');
```

### 5.4 Lógica de operation en fund_holdings

```
shares_prev = SELECT shares WHERE fund_id=X AND cusip=Y ORDER BY report_date DESC LIMIT 1

si shares_prev IS NULL  → operation = "NEW"     (primera aparición)
si shares > shares_prev → operation = "BUY"     (acumulando)
si shares < shares_prev → operation = "SELL"    (reduciendo)
si shares = shares_prev → operation = "HOLD"    (sin cambio)
si desaparece del filing → operation = "CLOSED" (salió completamente)
```

---

## 6. Fórmula Institutional Score

**Score por empresa** (combina peso relativo con amplitud de base de inversores):

```
score = inst_ownership_pct × 0.6  +  log(holders_count) × 0.4
```

**Score de ranking de fondos** (tabla `funds`):

```
fund_score = log(inst_funds) + log(inst_shares)
```

Donde `inst_funds` es el número de empresas en que aparece el fondo e `inst_shares` el total de acciones acumuladas. Permite distinguir fondos con alta diversificación vs. fondos con posiciones muy concentradas.

### 6.1 Volumen Relativo como señal complementaria

```
rel_volume = volume / averageVolume
```

`volume` y `averageVolume` ya están en `market` (populados por `sync_market` Phase 2 — Yahoo Quote). Es un campo **derivado**, calculado en runtime al mostrar el Screener o al generar features para el modelo. No requiere nueva descarga.

Señales combinadas:
- `inst_score` alto + `rel_volume` > 1.5 → fondos activamente comprando ahora
- `inst_score` cayendo + `rel_volume` > 2 → desinversión acelerada (input para `Agente_ManagerPreservation`)

---

## 7. Implementación — `Class_InstitucionalScore.py`

### 7.1 Estructura de la clase

```python
class InstitucionalScore:
    """
    Enriquece la tabla Market con señales de flujo institucional.
    Fuente: Yahoo Finance quoteSummary (institutionOwnership + majorHoldersBreakdown).
    Usa _yahoo_session() para compartir cookie/crumb con el resto de la App.
    """

    def __init__(self, session=None, crumb=""):
        self.market = MarketScreen()
        if session is None:
            session, crumb = _yahoo_session()
        self._session = session
        self._crumb = crumb

    def _fetch_ownership(self, symbol) -> dict:
        """Consulta quoteSummary. Retorna campos inst_* + fund_names para discovery."""
        ...

    def score_company(self, symbol) -> dict:
        """Retorna métricas institucionales + inst_score para un símbolo."""
        ...

    def discover_funds(self, account, top_n=200) -> dict:
        """Descubre fondos a partir del Top N por MarketCap. Retorna {fund_name: freq}."""
        ...

    def update_market(self, account, symbols) -> dict:
        """Actualiza tabla Market con inst_* fields. Respeta categoriaActivo."""
        ...
```

### 7.2 Función standalone

```python
def sync_institutional(account) -> dict:
    """
    Procesa TODOS los símbolos activos de market.
    Un único pass por símbolo: fund discovery + inst_* update.
    Sesión Yahoo creada una vez y compartida.
    """
    session, crumb = _yahoo_session()
    inst = InstitucionalScore(session, crumb)
    all_symbols = inst.market.load_symbols(account)
    symbols = [s for s, cat in all_symbols.items() if cat not in ("I", "S", "X")]
    ...
```

### 7.3 Agente en Class_DashBot.py

```python
@wait_rate(86400)
def Agente_InstitucionalScore(self):
    try:
        result = sync_institutional(account=self.account)
        self.logger.warning(
            f"InstitucionalScore: procesados={result['symbols_processed']} "
            f"actualizados={result['updated']} omitidos={result['skipped']} "
            f"fondos={result['funds_discovered']}"
        )
    except Exception as e:
        self.logger.error(f"Agente_InstitucionalScore(): {e}")
```

---

## 8. Fase 3 — SEC EDGAR 13F Parser (pendiente)

### 8.1 Infraestructura existente reutilizable

| Función en `valuation_edgar_downloader.py` | Uso para 13F |
|---|---|
| `get_filings_metadata(cik)` | Funciona igual — filtrar por form `13F-HR` |
| `download_filing_file(cik, accession, filename, save_dir)` | Descarga el XML sin cambios |
| `HEADERS` | Mismo User-Agent requerido por SEC |

### 8.2 Lo que falta para 13F

1. **Resolver CIK de fondos** — `get_cik_from_ticker()` busca empresas, no gestores. Para fondos usar búsqueda EDGAR:
   ```
   https://efts.sec.gov/LATEST/search-index?q="Vanguard+Group"&forms=13F-HR
   ```
   O poblar manualmente `funds.cik` para los top fondos conocidos.

2. **Filtrar filings por form `13F-HR`** dentro del resultado de `get_filings_metadata`.

3. **Parser XML del 13F** — estructura del archivo:
   ```xml
   <infoTable>
     <nameOfIssuer>APPLE INC</nameOfIssuer>
     <cusip>037833100</cusip>
     <value>47682</value>          <!-- en miles USD -->
     <shrsOrPrnAmt>
       <sshPrnamt>268898</sshPrnamt>
     </shrsOrPrnAmt>
   </infoTable>
   ```

4. **Resolución CUSIP → symbol** vía OpenFIGI API (gratuito, batch de 100):
   ```
   POST https://api.openfigi.com/v3/mapping
   [{"idType": "ID_CUSIP", "idValue": "037833100"}]
   → ticker: AAPL
   ```

5. **Lógica de operation** al insertar en `fund_holdings` (ver sección 5.4).

### 8.3 CIK conocidos para los principales fondos

| Fondo | CIK SEC |
|-------|---------|
| Vanguard Group | 0000102909 |
| BlackRock | 0001364742 |
| State Street | 0000093751 |
| Fidelity (FMR) | — por resolver |
| Capital Group | — por resolver |

---

## 9. Roadmap de Fases

| Fase | Alcance | Fuente | Estado |
|------|---------|--------|--------|
| Fase 1 | `inst_ownership_pct`, `insider_pct`, `holders_count`, `inst_score` | Yahoo quoteSummary | ✅ Implementado |
| Fase 2 | Detectar cambios trimestrales en ownership | Yahoo quoteSummary | ⬜ Pendiente |
| Fase 3 | Posiciones completas 13F + CUSIP → symbol + `operation` | SEC EDGAR | ⬜ Pendiente |
| Fase 4 | Señales de acumulación institucional acelerada (2+ trimestres) | 13F + Yahoo | ⬜ Pendiente |

---

## 10. Integración en AppOO

| Componente AppOO | Relación con Institutional Score |
|-----------------|----------------------------------|
| Tabla `market` | Destino de todos los campos `inst_*` |
| Tabla `funds` | Ranking de fondos descubiertos automáticamente |
| Tabla `fund_holdings` | Posiciones trimestrales con historial BUY/SELL (Fase 3) |
| Tabla `cusip_map` | Traducción CUSIP → symbol para datos del 13F |
| `Agente_InstitucionalScore` | `@wait_rate(86400)` — corre después de `Agente_MarketScreener` |
| `Agente_ManagerPreservation` | Señal de alerta: fondo top con `operation=SELL` en posición propia |
| `modelo_buyv01` | `inst_score` + `rel_volume` como features adicionales en RandomForest |
| `DashMainV9_ia.py` | Visualización de señal institucional en el Screener principal |
| `RebalanceEngine` | `inst_score` como 5.ª dimensión de rebalanceo |

> **Valor diferencial:** combinar Dividend Yield + Fundamental Strength (EDGAR) + Institutional Accumulation genera un screener de largo plazo de alta convicción, alineado con la estrategia personal del sistema AppOO.
