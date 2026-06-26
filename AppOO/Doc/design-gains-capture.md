# Agente_GainsCapture — Diseño

**Estado:** Diseño completo — pendiente implementar  
**Fecha diseño:** 2026-06-03  
**Prioridad:** Alta (ítem 53 backlog)  
**Ver también:** `Doc/preservation_claude_dynamic_design.md` — agente complementario (defensivo)

---

## Motivación y espíritu

Stocks volátiles como SKLZ, PLUG, CRNT, CHPT pueden hacer movimientos de +50% a +150%
en semanas para luego corregir fuertemente. Un trailing stop solo no alcanza para capturar
esas ganancias — hay que vender parcialmente en el camino antes de la corrección.

**SKLZ:** llegó a $20 (+79% ROI) y volvió a $9. Con el agente: hubiera vendido 25% a $16.77
(nivel 50%) y 50% más a $22.36 (nivel 100%). Ganancia asegurada en vez de ver la caída completa.

**Espíritu especulativo** — a diferencia de `Agente_ManagerPreservation` (defensivo, stocks
estables de dividendo), este agente opera sobre activos de crecimiento/volátiles aprovechando
su movimiento, no protegiéndose de él.

---

## Distinción de responsabilidades

| | `Agente_ManagerPreservation` | `Agente_GainsCapture` |
|---|---|---|
| Espíritu | **Defensivo** — proteger lo ganado | **Especulativo** — capturar upside |
| Activos | `I` (dividendo, estables) | `N` (volátil, crecimiento) |
| Acción | Coloca STOP trailing | Vende parcialmente en niveles ROI |
| Trigger | ROI >= 10% | ROI >= 50% (primer nivel configurable) |
| Claude decide | Dónde poner el stop | Si hay más recorrido o vender ahora |
| Nivel jerárquico | N3 — Decisiones | N3 — Decisiones |

---

## Config en `sesion.parameters`

Sección propia `"gains_capture"`, independiente de `"preservation"`:

```json
{
  "gains_capture": {
    "niveles": [
      {"roi": 0.50, "vender_pct": 0.25},
      {"roi": 1.00, "vender_pct": 0.50},
      {"roi": 1.50, "vender_pct": 0.25}
    ],
    "revisiones_dia": 2
  }
}
```

`vender_pct` se aplica sobre la **posición corriente de IB** en el momento de ejecución.  
Si `gains_capture` no está en el config → agente deshabilitado sin error.

---

## Ejemplo SKLZ (avg cost $11.18, 136 acc)

| Precio | ROI | Acción |
|---|---|---|
| $16.77 | +50% | Claude valida técnicos → vender 34 acc (25% de 136) LMT $16.69 |
| $22.36 | +100% | Claude valida técnicos → vender ~51 acc (50% de las 102 restantes) LMT $22.25 |
| $27.95 | +150% | Claude valida técnicos → vender ~25 acc (25% de las 51 restantes) LMT $27.81 |

`Agente_ManagerPreservation` sigue corriendo en paralelo sobre SKLZ si tiene ganancia >= 10%,
pero como `categoriaActivo='N'`, su STOP es más amplio (ATR × 2.5). Los dos agentes conviven.

---

## Validación técnica por Claude antes de cada nivel

Antes de colocar la orden LMT, Claude evalúa si hay momentum restante o si el activo
está sobrecomprado. Puede **postergar** la ejecución al próximo ciclo si las condiciones
son favorables para continuar subiendo.

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

- `ejecutar: false` → nivel omitido en este ciclo, re-evalúa en el próximo
- Claude falla (timeout) → ejecuta igual usando solo la regla de nivel ROI (fallback a reglas)

---

## Tipo de orden — LIMIT fijo

`precio_lmt = last × 0.995` (0.5% bajo precio actual).  
Ejecuta rápido en mercado activo sin regalar precio. No se usan órdenes MKT.

---

## Modos de operación — botón en panel Agentes

El panel Agentes (`agentes_system()`) tiene un botón toggle junto a "Activar todos":

```
[ Activar todos ]   [ ⚡ GainsCapture: Automático ]   ← verde
[ Activar todos ]   [ 🔐 GainsCapture: Autorizado ]   ← naranja
```

**Implementación:**
- `DataHub.gains_capture_modo: str = "automatico"` (class var)
- Persiste en `tmp/gains_capture_config.json` via `write_json_tmp`
- En inicio de app lee el estado guardado via `read_json_tmp`

**Modo `automatico`** (sin presencia del usuario):
1. Claude valida técnicos → decide ejecutar
2. LMT enviada a IB directamente
3. Notificación Telegram posterior informando la acción tomada

**Modo `autorizado`** (quiero confirmar antes):
1. Claude valida técnicos → prepara la orden
2. Telegram envía propuesta:
   ```
   📈 GainsCapture — SKLZ
   Nivel ROI 50% alcanzado
   Vender 34 acc LMT $19.50
   RSI_d=78 sobrecomprado — urgencia: alta
   /ok_SKLZ  |  /no_SKLZ
   ```
3. `gains_capture_state` → `estado: "pendiente_autorizacion"`
4. `/ok_SKLZ` → coloca la orden → flujo normal de fill
5. `/no_SKLZ` → nivel marcado "omitido_manual", re-evalúa en 6h
6. **Sin respuesta en 30 minutos → propuesta cancelada** (conservador — no ejecuta sin confirmación)

---

## Flujo de estados por símbolo

```
[normal]
  ↓  ROI >= nivel.roi  AND  nivel no ejecutado  AND  Claude dice ejecutar
Colocar LMT SELL parcial  →  [escalon_pendiente]
  (guarda escalon_order_id en gains_capture_state)

Agente_SyncOrders detecta LMT filled
  → actualizar gains_capture_state: niveles_ejecutados + [nivel]
  → [esperando_reset]

Próximo ciclo Agente_GainsCapture
  → leer qty actual desde IB (posición ya reducida)
  → estado → [normal]
  → evalúa si hay próximo nivel alcanzado
```

| Estado | Qué hace el agente |
|---|---|
| `normal` | Chequea niveles ROI no ejecutados |
| `escalon_pendiente` | No toca nada — espera que SyncOrders detecte el fill |
| `esperando_reset` | Lee posición fresca de IB, vuelve a normal |
| `pendiente_autorizacion` | Espera /ok o /no por Telegram (timeout 30min → cancela) |

---

## Persistencia — `gains_capture_state.json`

Archivo propio, independiente de `preservation_state.json`:

```json
{
  "SKLZ": {
    "escalon_order_id": null,
    "estado": "normal",
    "niveles_ejecutados": [0.50],
    "pendiente_autorizacion": null,
    "last_check": "2026-06-03T10:30:00"
  }
}
```

---

## `json_detalle` en `order_trader` — para aprendizaje futuro

Cada orden guarda el contexto técnico + decisión Claude:

```json
{
  "tipo": "gains_capture",
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
- Cruzar contexto técnico vs. precio posterior a la venta → ¿fue oportuno vender?
- Detectar qué condiciones RSI/EMA predicen mejor el peak local
- Calibrar `vender_pct` por nivel según efectividad histórica
- Mejorar el prompt de Claude con casos reales de acierto/error

---

## Plan de implementación

### Paso 1 — BD
- `order_trader.json_detalle` ya existe (creado en Fase 1 de preservation)
- Sin cambios de schema adicionales

### Paso 2 — `Class_customer.py` — DataHub
- Agregar `DataHub.gains_capture_modo: str = "automatico"` (class var)
- Agregar `DataHub.gains_capture_build_trama_sell(vehiculo, account, symbol, conid, last, qty)` → trama LMT SELL
- En inicio leer `gains_capture_config.json` para restaurar el modo guardado

### Paso 3 — `Class_DashBot.py` — nuevo agente
- Agregar `_gains_capture_claude_eval(symbol, nivel_roi, ctx)` → `{"ejecutar": bool, "razon": str, "urgencia": str}`
  - Recibe RSI_d, RSI_w, EMA50/200 desde DataHub.info tiempo real
  - Claude decide si hay momentum restante o sobrecompra
- Agregar `Agente_GainsCapture(self)` con `@wait_rate(intervalo, persist=True)`:
  - Lee posiciones `categoriaActivo='N'` con ROI > primer nivel config
  - Por cada nivel no ejecutado con ROI alcanzado: llama `_gains_capture_claude_eval`
  - Si ejecutar + modo automático: coloca LMT, guarda escalon_order_id, estado → escalon_pendiente
  - Si ejecutar + modo autorizado: envía Telegram propuesta, estado → pendiente_autorizacion
  - Maneja estado `esperando_reset`: lee qty fresca de IB, vuelve a normal
- Registrar en `AgentManager.register_threads()`

### Paso 4 — `Agente_SyncOrders`
- Detectar fill de órdenes con `intent='gains_capture'`
- Al fill: actualizar `gains_capture_state` → `esperando_reset`

### Paso 5 — `Class_SystemStatus.py` — botón en panel Agentes
- En `btn_frame` de `agentes_system()`, agregar botón toggle
- Verde: `"⚡ GainsCapture: Auto"` | Naranja: `"🔐 GainsCapture: Autorizar"`
- Click → toggle `DataHub.gains_capture_modo` + `write_json_tmp("gains_capture_config.json", {"modo": ...})`

### Paso 6 — Telegram handler
- Comandos `/ok_<SYMBOL>` y `/no_<SYMBOL>` para modo autorizado
- `/ok_SKLZ` → coloca la orden pendiente → flujo normal de fill
- `/no_SKLZ` → nivel omitido 6h, re-evalúa en próximo ciclo
- Sin respuesta 30min → propuesta cancelada (no ejecuta)

### Paso 7 — `Class_debugging.py`
- Registrar logger `"GainsCapture"` con `setLevel(WARNING)`

---

## Pendientes / preguntas abiertas

- [ ] ¿`Agente_GainsCapture` corre en el mismo hilo que `Agente_ManagerPreservation` o en uno separado?
- [ ] Si ambos agentes operan sobre SKLZ simultáneamente (Preservation pone STOP, GainsCapture pone LMT SELL): ¿hay riesgo de conflicto en IB? Verificar que IB permita STOP + LMT abiertos al mismo tiempo sobre el mismo símbolo
- [ ] Definir intervalo del agente: `@wait_rate(43200)` (2 revisiones/día) o más frecuente para activos muy volátiles
