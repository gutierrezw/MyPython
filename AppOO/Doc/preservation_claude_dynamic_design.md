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

### Motivación
Stocks como SKLZ, PLUG, CRNT, CHPT pueden hacer movimientos de +50% a +150% en semanas.
Un trailing stop solo no es suficiente — hay que vender parcialmente en el camino para
asegurar ganancias antes de una corrección. SKLZ llegó a $20 (+79% ROI) y volvió a $9.

### Distinción por `categoriaActivo`
| Valor | Tipo | Estrategia preservation |
|---|---|---|
| `I` | Dividendo (CVS, BTI, AMT) | Trailing stop puro |
| `N` | Crecimiento/volátil (SKLZ, PLUG, CRNT) | Trailing stop + escalonamiento |
| `X`, `T` | ETF / 13F | Sin preservation |

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
Si `escalonamiento` no está en el config → comportamiento actual (trailing stop puro).

### Ejemplo SKLZ (avg cost $11.18, 136 acc)
| Precio | ROI | Acción |
|---|---|---|
| $12.30 | +10% | Trailing STOP activo |
| $16.77 | +50% | Vender 34 acc (25%) → recupera parte del costo |
| $22.36 | +100% | Vender 68 acc (50%) → recupera todo el costo |
| $27.95 | +150% | Vender 34 acc (25%) — stop muy ajustado sobre el resto |

Con SKLZ en $20: hubiera vendido 25% a $16.77 (nivel 50%) y 50% a $22.36 (nivel 100%).
Ganancia asegurada en vez de ver la caída completa.

### Lógica de implementación
```python
escalonamiento = pconfig.get("escalonamiento", [])
niveles_ejecutados = state.get("niveles_ejecutados", [])  # persistido en preservation_state

for nivel in sorted(escalonamiento, key=lambda x: x["roi"]):
    if roi >= nivel["roi"] and nivel["roi"] not in niveles_ejecutados:
        qty_vender = int(position_qty * nivel["vender_pct"])
        if qty_vender > 0:
            # Colocar orden SELL a precio de mercado (MKT) o LMT con pequeño descuento
            trama_sell = DataHub.preservation_build_trama_sell(vehiculo, account, symbol, conid, last, qty_vender)
            DataHub.preservation_send_order(vehiculo, trama_sell)
            niveles_ejecutados.append(nivel["roi"])
            # Actualizar preservation_state con niveles_ejecutados
```

### Persistencia
`preservation_state.json` agrega campo `niveles_ejecutados` por símbolo:
```json
{
  "SKLZ": {
    "max_price": 20.00,
    "stop_actual": 18.40,
    "niveles_ejecutados": [0.50],
    "last_check": "2025-11-15T10:30:00",
    "order_id": "IB-12345"
  }
}
```

---

## Plan de implementación

### Paso 1 — BD
```sql
ALTER TABLE order_trader ADD COLUMN json_detalle TEXT NULL AFTER hash_id_oportunidad;
```

### Paso 2 — `Modulos_Mysql.py`
- Agregar `insert_preservation_order(account, vehiculo, symbol, conid, order_id, stop_price, qty, json_detalle)` en `RepositorioOportunidadesBuySell`
- Agregar `update_preservation_order_status(order_id, status)` para el sync

### Paso 3 — `Class_DashBot.py`
- Agregar `_build_preservation_context(symbol, ...)` → dict con todos los campos
- Agregar `_claude_preservation_eval(context)` → dict con activar/stop/razon/urgencia
- Modificar `_preservation_run_vehiculo()`:
  - Ampliar umbral a 7% con Claude
  - Llamar Claude, con fallback a reglas
  - Insertar en order_trader con json_detalle al colocar STOP

### Paso 4 — `Agente_SyncOrders`
- Ya sincroniza IB → order_trader para Stock
- Verificar que actualiza status de órdenes tipo `intent='preservation'`

### Paso 5 — AppTest
- `AppTest/run_preservation_eval.py` — simula evaluación de posiciones sin colocar órdenes reales

---

## Pendientes / preguntas abiertas

- [ ] ¿Nueva key `ClaudeAPIP` en tabla sesion o reusar `ClaudeAPIC`?
- [ ] ¿Cómo obtener rsi_d/macd desde booktrading.indicadores en tiempo real? (el campo se graba al momento de la transacción, puede estar desactualizado)
- [ ] ¿El `Agente_SyncOrders` ya maneja órdenes STOP de preservation o solo BUY/SELL?
- [ ] Definir qué hacer cuando Claude dice "no activar" pero ROI supera 10% → ¿reglas fijas igual?
