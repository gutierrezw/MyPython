# Preservation Dinámico con Claude — Diseño

**Estado:** Diseño inicial — pendiente implementar  
**Fecha:** 2026-06-02  
**Prioridad:** Alta

---

## Problema actual

El agente `Agente_ManagerPreservation` usa reglas fijas:
- `roi_minimo = 10%` — umbral de activación
- `correccion_pct = 8%` — stop fijo bajo max_price
- `atr_mult = 2.0` — componente ATR

**Limitación:** No distingue contexto. CRNT con ROI 7%, señal VENDER y RSI bajando
es tratado igual que CRNT con ROI 7% en tendencia alcista → ambos son SKIP.
Un analista humano vería la primera combinación y activaría protección.

---

## Solución propuesta

Integrar Claude Haiku en `_preservation_run_vehiculo()` para razonar sobre cada
posición antes de decidir. Las reglas fijas siguen siendo el **piso y fallback**.

```
Reglas fijas (siempre corren)
  └── calculan stop_calculado base
Claude Haiku (corre sobre umbral ampliado 7%)
  └── decide activar/ajustar según contexto técnico/fundamental
  └── si falla → reglas fijas toman el control
```

---

## Datos a pasar a Claude por posición

### Del agente (ya disponibles)
| Campo | Fuente |
|---|---|
| symbol, qty, roi | `inversion` / IB |
| last, max_price, stop_actual | DataHub / preservation_state.json |
| atr | yfinance ATR(14) |
| base_limit | unrealizedpnl × proteccion_base |

### Desde `market` table (MarketScreen)
| Campo | Descripción |
|---|---|
| consenso_tag | UNANIME/CONSENSO/TENDENCIA/NEUTRO/ALERTA/SALIDA |
| consenso_suma | Suma de votos (+4 a -6) |
| inst_score | Score institucional v2 |
| inst_ownership_pct | % float en manos institucionales |
| fh_buy_ratio | % fondos 13F comprando |
| rotacion | Momentum institucional |
| analyst_rec | buy/hold/sell |
| analyst_mean | Score promedio analistas |

### Desde `market_sentiment` / `market_sentiment_analysis`
| Campo | Descripción |
|---|---|
| sentiment_score | +1/0/-1 puntual |
| patron | acumulacion/distribucion/neutro/inflexion |

### Desde `booktrading.indicadores` (ya grabado en cada transacción)
| Campo | Descripción |
|---|---|
| rsi_d | RSI diario |
| macd_d | MACD diario (estado) |
| EMA200 posición | sobre/bajo EMA200 |
| rango_52w_pct | posición dentro del rango anual |

---

## Rol de Claude — Opción B (acordada)

**Claude NO decide si activar** — eso lo hacen las reglas fijas (roi >= 10%, siempre).  
**Claude SOLO afina el stop** sobre posiciones que ya pasaron el umbral.

```
Reglas fijas (roi >= 10%)  →  activan preservation, calculan stop base
Claude Haiku               →  ajusta nivel del stop + agrega razon + urgencia
Si Claude falla (timeout)  →  stop base de reglas fijas se coloca igual
```

**Sin gray zone:** ninguna posición queda desprotegida por falla de Claude.

---

## Prompt a Claude (por posición)

```
Eres un agente de preservación de ganancias para un portfolio de inversión.
Las reglas fijas ya activaron la protección de esta posición (ROI >= 10%).
Tu tarea es ajustar el nivel del STOP para maximizar la protección según el contexto.

Posición: {symbol}
- ROI actual: {roi:.1%} | Precio: ${last:.2f} | Max histórico: ${max_price:.2f}
- Stop base (reglas): ${stop_calculado:.2f} | Stop anterior: ${stop_actual:.2f}
- ATR(14): ${atr:.2f}

Contexto fundamental:
- Consenso: {consenso_tag} ({consenso_suma:+d} votos)
- Inst Score: {inst_score} | 13F Buy ratio: {fh_buy_ratio:.1%}
- Analistas: {analyst_rec} (mean={analyst_mean:.1f})
- Sentimiento: {patron} (score={sentiment_score:+d})

Técnico diario:
- RSI: {rsi_d} | MACD: {macd_estado}
- EMA200: precio {ema200_rel}
- Rango 52W: {rango_52w_pct:.0%}

Podés subir el stop (más protección) o mantener el base.
NUNCA sugerir un stop inferior al base calculado por reglas.
Respondé SOLO con JSON válido:
{"stop_sugerido": float, "razon": "str max 120 chars", "urgencia": "alta"|"media"|"baja"}
```

---

## Lógica de activación — Opción B

```python
# Umbral único: reglas fijas siempre mandan
UMBRAL_REGLAS = 0.10   # 10% — sin cambio respecto al agente actual

if roi >= UMBRAL_REGLAS:
    # 1. Reglas fijas calculan el stop base (siempre)
    stop_calculado = max_price - max(correccion_pct * max_price, atr_mult * atr)
    
    # 2. Claude afina el nivel (opcional — si falla, stop base se usa igual)
    context = _build_preservation_context(symbol, ...)
    claude = _claude_preservation_eval(context)  # timeout 15s
    
    stop_claude = claude.get("stop_sugerido") if claude else None
    stop_final = max(stop_anterior, stop_calculado, stop_claude or 0)
    
    # 3. Colocar STOP siempre — Claude no puede bloquearlo
    # → colocar orden STOP con stop_final
```

**Invariante clave:** `stop_final >= stop_calculado` siempre.
Claude solo puede subir el stop, nunca bajarlo ni cancelarlo.

---

## Persistencia de decisiones — `order_trader`

### ALTER TABLE necesario
```sql
ALTER TABLE order_trader
ADD COLUMN json_detalle TEXT NULL AFTER hash_id_oportunidad;
```

### Formato estándar `json_detalle`
```json
{
  "tipo": "preservation_stop",
  "decision": {
    "roi": 0.07,
    "max_price": 3.01,
    "atr": 0.15,
    "stop_calculado_reglas": 2.73,
    "consenso_tag": "NEUTRO",
    "consenso_suma": 0,
    "inst_score": 45,
    "fh_buy_ratio": 0.32,
    "sentiment_patron": "distribucion",
    "rsi_d": 42,
    "macd_estado": "bajista",
    "ema200_rel": "bajo",
    "base_limit": 89.26
  },
  "claude": {
    "activar": true,
    "stop_sugerido": 2.78,
    "razon": "RSI bajando desde zona sobrecomprada, distribución institucional detectada",
    "urgencia": "media"
  },
  "resultado": {
    "stop_final": 2.78,
    "qty_protegida": 25,
    "ganancia_protegida_usd": 89.26
  }
}
```

### Ciclo de vida de la orden en `order_trader`

| Estado | Significado | Aprendizaje |
|---|---|---|
| NEW | STOP activo, posición protegida | — |
| FILLED | Stop tocado → ganancia limitada | Decisión correcta si alternativa era peor |
| CANCELLED (ajuste) | Precio subió → nueva orden con stop más alto | Stop conservador inicial |
| CANCELLED (cierre) | Posición cerrada por otra vía | Preservación exitosa o innecesaria |

### Valor futuro del dataset
- **Audit trail**: por qué se colocó cada stop
- **Training data**: cruzar decisión Claude + contexto vs outcome (FILLED/CANCELLED)
- **Análisis efectividad**: qué combinación roi+consenso+RSI tuvo mejor resultado
- **Calibración umbrales**: ajustar UMBRAL_CLAUDE según histórico de aciertos

---

## Configuración técnica

| Parámetro | Valor | Motivo |
|---|---|---|
| Modelo | `claude-haiku-4-5-20251001` | Costo mínimo ~$0.001/posición |
| Key BD | `ClaudeAPIP` (nueva) o `ClaudeAPIC` | Separar costos por módulo |
| Timeout | 15s | Si no responde → reglas fijas |
| Log | `preservation_diag.log` | Incluir razon Claude en cada línea |
| Frecuencia | Por posición, cada revisión (2x día) | Solo si roi >= UMBRAL_CLAUDE |

---

## Casos de uso identificados

| Caso real | Regla fija | Con Claude |
|---|---|---|
| CRNT ROI 7%, VENDER, RSI 42 bajando | SKIP | ✅ Activar stop ajustado |
| CVS ROI 22%, CONSENSO (+4) | ✅ Activa | Confirma, stop estándar |
| PLUG ROI 70%, NEUTRO | ✅ Activa | Mantiene o sube stop |
| Stock ROI 12%, distribución institucional | ✅ Activa stop std | Stop más ajustado, urgencia alta |
| Stock ROI 8%, acumulación, RSI subiendo | SKIP | ❌ No activar — tendencia alcista |

---

---

## Extensión — Escalonamiento de salida (activos volátiles)

**Estado:** Diseño completo — pendiente implementar  
**Fecha diseño:** 2026-06-03

### Motivación
Stocks como SKLZ, PLUG, CRNT, CHPT pueden hacer movimientos de +50% a +150% en semanas.
Un trailing stop solo no es suficiente — hay que vender parcialmente en el camino para
asegurar ganancias antes de una corrección. SKLZ llegó a $20 (+79% ROI) y volvió a $9.

### Distinción por `categoriaActivo`
| Valor | Tipo | Estrategia preservation |
|---|---|---|
| `I` | Dividendo (CVS, BTI, AMT) | Trailing stop puro — sin escalonamiento |
| `N` | Crecimiento/volátil (SKLZ, PLUG, CRNT) | Trailing stop + escalonamiento |
| `X`, `T` | ETF / 13F | Sin preservation |

---

### Config en `sesion.parameters`
```json
{
  "preservation": {
    "roi_minimo": 0.10,
    "proteccion_base": 0.40,
    "correccion_pct": 0.08,
    "atr_mult": 2.0,
    "revisiones_dia": 2,
    "escalonamiento": [
      {"roi": 0.50, "vender_pct": 0.25},
      {"roi": 1.00, "vender_pct": 0.50},
      {"roi": 1.50, "vender_pct": 0.25}
    ]
  }
}
```
Si `escalonamiento` no está en el config → trailing stop puro (comportamiento actual).  
`vender_pct` se aplica sobre la **posición corriente de IB** en el momento de ejecución, no sobre la qty original.

### Ejemplo SKLZ (avg cost $11.18, 136 acc)
| Precio | ROI | Acción |
|---|---|---|
| $12.30 | +10% | Trailing STOP activo |
| $16.77 | +50% | Claude valida técnicos → vender 34 acc (25%) LMT $16.69 |
| $22.36 | +100% | Claude valida técnicos → vender ~51 acc (50% de lo que queda) LMT $22.25 |
| $27.95 | +150% | Claude valida técnicos → vender ~25 acc (25% restante) LMT $27.81 |

---

### Validación técnica por Claude antes de cada nivel

Antes de colocar la orden LMT, Claude evalúa si hay momentum restante o si el activo
está sobrecomprado. Puede **postergar** la ejecución si las condiciones son favorables.

**Señales evaluadas (DataHub tiempo real):**

| Señal | "Esperar más" | "Ejecutar ahora" |
|---|---|---|
| RSI diario | < 65 (momentum intacto) | > 75 (sobrecomprado) |
| RSI semanal | < 65 | > 72 |
| Precio vs EMA50 diaria | Acelerando por encima | Tocando o debajo |
| Precio vs EMA200 diaria | Lejos por encima | Cerca o debajo |

**Respuesta Claude (JSON):**
```json
{"ejecutar": true, "razon": "RSI_d=78 sobrecomprado, señal de toma de ganancias", "urgencia": "alta"}
```
Si `ejecutar: false` → el nivel se omite en este ciclo y se re-evalúa en el próximo.  
Si Claude falla (timeout) → se ejecuta igual usando solo las reglas de nivel ROI.

---

### Tipo de orden — LIMIT fijo

`precio_lmt = last × 0.995` (0.5% bajo precio actual).  
Ejecuta rápido en mercado activo sin regalar precio. No se usan órdenes MKT.

---

### Flujo de estados por símbolo

```
[normal]
  ↓  ROI >= nivel.roi  AND  nivel no ejecutado  AND  Claude dice ejecutar
Colocar LMT SELL parcial  →  [escalon_pendiente]
  (guarda escalon_order_id en preservation_state)

Agente_SyncOrders detecta LMT filled
  → cancelar stop_order_id activo en IB
  → [esperando_reset]

Próximo ciclo preservation
  → leer qty actual desde IB (posición ya reducida)
  → recalcular stop desde cero con nueva qty
  → colocar nuevo STOP
  → [normal]
  (niveles_ejecutados se mantiene: no re-dispara el nivel ya ejecutado)
```

| Estado | Qué hace el agente |
|---|---|
| `normal` | Evalúa trailing stop + chequea niveles de escalonamiento |
| `escalon_pendiente` | No toca nada — espera que SyncOrders detecte el fill |
| `esperando_reset` | Lee posición fresca de IB, recalcula todo, coloca nuevo STOP |

---

### Modos de operación — botón en panel Agentes

El panel Agentes (`agentes_system()`) tiene un botón adicional junto a "Activar todos":

```
[ Activar todos ]   [ ⚡ Modo: Automático ]   ← verde
[ Activar todos ]   [ 🔐 Modo: Autorizado ]   ← naranja
```

**Implementación:**
- `DataHub.preservation_modo: str` = `"automatico"` | `"autorizado"` (class var)
- Persiste en `tmp/preservation_config.json` via `write_json_tmp`
- En inicio de app lee el estado guardado via `read_json_tmp`

**Modo `automatico`** (sin presencia del usuario):
1. Claude valida técnicos → decide ejecutar
2. LMT enviada a IB directamente
3. Notificación Telegram posterior informando la acción

**Modo `autorizado`** (quiero validar antes):
1. Claude valida técnicos → prepara la orden
2. Telegram envía propuesta:
   ```
   SKLZ: vender 25% (34 acc) LMT $19.50
   RSI_d=78 sobrecomprado — urgencia: alta
   /ok_SKLZ para confirmar | /no_SKLZ para cancelar
   ```
3. `preservation_state` → `estado: "pendiente_autorizacion"`
4. `/ok_SKLZ` → coloca la orden → flujo normal de fill
5. `/no_SKLZ` → nivel marcado como "omitido_manual", se re-evalúa en 6h
6. **Sin respuesta en 30 minutos → propuesta cancelada** (conservador — no ejecuta sin confirmación)

---

### Persistencia ampliada — `preservation_state.json`

```json
{
  "SKLZ": {
    "max_price": 20.00,
    "stop_order_id": "IB-12345",
    "escalon_order_id": null,
    "estado": "normal",
    "niveles_ejecutados": [0.50],
    "pendiente_autorizacion": null,
    "last_check": "2026-06-03T10:30:00"
  }
}
```

---

### `json_detalle` en `order_trader` — para aprendizaje futuro

Cada orden de escalonamiento guarda el contexto técnico + decisión Claude para análisis posterior:

```json
{
  "tipo": "escalonamiento",
  "nivel_roi": 0.50,
  "modo": "autorizado",
  "tecnico": {
    "rsi_d": 78.2,
    "rsi_w": 71.1,
    "ema200_rel": "sobre",
    "macd_estado": "alcista"
  },
  "claude": {
    "ejecutar": true,
    "razon": "RSI diario sobrecomprado, señal de toma de ganancias oportuna",
    "urgencia": "alta"
  },
  "orden": {
    "qty": 34,
    "lmt_price": 19.50
  }
}
```

**Valor futuro del dataset:**
- Cruzar `tecnico` + `claude.razon` vs. precio posterior a la venta → ¿fue oportuno?
- Detectar qué condiciones RSI/EMA predicen mejor el peak local
- Calibrar los niveles `vender_pct` según efectividad histórica
- Mejorar el prompt de Claude con casos reales de acierto/error

---

## Plan de implementación

### Fase 1 — Preservation Claude (trailing stop dinámico) — IMPLEMENTADO

#### Paso 1 — BD ✅
```sql
ALTER TABLE order_trader ADD COLUMN json_detalle TEXT NULL AFTER hash_id_oportunidad;
```

#### Paso 2 — `Modulos_Mysql.py` ✅
- `select_preservation_context(symbol, account)` — market + sentiment, sin oportunidadesbuysell

#### Paso 3 — `Class_DashBot.py` ✅
- `_build_preservation_context()` — indicadores técnicos desde DataHub tiempo real
- `_claude_preservation_eval()` — llama Haiku, retorna stop_sugerido/razon/urgencia
- `_preservation_run_vehiculo()` — integra Claude con fallback a reglas

#### Paso 4 — `DashMain.py` ✅
- Columna 🤖 en Lista de Ordenes + popup doble-click con análisis Claude

#### Paso 5 — AppTest ✅
- `AppTest/run_preservation_eval.py` — evaluación standalone con _enrich_tecnicos

---

### Fase 2 — Escalonamiento de salida (activos volátiles) — PENDIENTE

#### Paso 1 — BD
- Verificar que `order_trader.json_detalle` ya existe (lo tiene desde Fase 1)
- No requiere cambios de schema adicionales

#### Paso 2 — `Class_customer.py` — DataHub
- Agregar `DataHub.preservation_modo: str = "automatico"` (class var)
- Agregar `DataHub.preservation_build_trama_sell(vehiculo, account, symbol, conid, last, qty)` → trama LMT SELL
- En inicio leer `preservation_config.json` para restaurar el modo guardado

#### Paso 3 — `Class_DashBot.py`
- Agregar `_escalon_claude_eval(symbol, nivel_roi, ctx)` → `{"ejecutar": bool, "razon": str, "urgencia": str}`
  - Recibe RSI_d, RSI_w, EMA50/200 desde DataHub.info
  - Claude decide si hay momentum restante o sobrecompra
- Modificar `_preservation_run_vehiculo()`:
  - Si `categoriaActivo == 'N'` y config tiene `escalonamiento`:
    - Cargar `niveles_ejecutados` desde preservation_state
    - Por cada nivel no ejecutado con roi alcanzado: llamar `_escalon_claude_eval`
    - Si ejecutar: colocar LMT (`last × 0.995`), guardar escalon_order_id, estado → escalon_pendiente
    - Si modo autorizado: enviar Telegram propuesta, estado → pendiente_autorizacion; timeout 30min → cancelar
- Manejar estado `esperando_reset`: leer qty fresca de IB, recalcular stop, volver a normal

#### Paso 4 — `Agente_SyncOrders`
- Detectar fill de órdenes con `intent='escalon'`
- Al fill: cancelar stop_order_id activo, actualizar preservation_state → esperando_reset

#### Paso 5 — `Class_SystemStatus.py` — botón en panel Agentes
- En `btn_frame` de `agentes_system()`, agregar botón toggle junto a "Activar todos"
- Verde: `"⚡ Modo: Automático"` | Naranja: `"🔐 Modo: Autorizado"`
- Click → toggle `DataHub.preservation_modo` + `write_json_tmp("preservation_config.json", {"modo": ...})`

#### Paso 6 — Telegram handler
- Comandos `/ok_<SYMBOL>` y `/no_<SYMBOL>` para modo autorizado
- `/ok_SKLZ` → coloca la orden pendiente → flujo normal
- `/no_SKLZ` → cancela propuesta, nivel omitido 6h
- Sin respuesta 30min → propuesta cancelada (no ejecuta)

---

## Pendientes / preguntas abiertas

- [ ] ¿Nueva key `ClaudeAPIP` en tabla sesion o reusar `ClaudeAPIC`?
- [ ] ¿Cómo obtener rsi_d/macd desde booktrading.indicadores en tiempo real? (el campo se graba al momento de la transacción, puede estar desactualizado)
- [ ] ¿El `Agente_SyncOrders` ya maneja órdenes STOP de preservation o solo BUY/SELL?
- [ ] Definir qué hacer cuando Claude dice "no activar" pero ROI supera 10% → ¿reglas fijas igual?
