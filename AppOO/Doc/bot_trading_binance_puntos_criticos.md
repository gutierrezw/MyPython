# Bot de Trading Spot en Binance – Documento de Puntos Críticos

## 1. Objetivo del Bot
Diseñar un bot de trading **Spot** para Binance que evalúe activos individuales y tome decisiones de **compra y venta automática** basadas en indicadores técnicos clásicos (RSI, MACD, EMA), con reglas claras, parametrizables y auditables.

El bot **no predice precios**, sino que identifica **oportunidades razonables** de entrada y salida.

---

## 2. Alcance Funcional
- Mercado: **Binance Spot**
- Activos: Pares crypto (ej: BTCUSDT, ETHUSDT)
- Temporalidad: Configurable (1m, 5m, 15m, 1h, etc.)
- Operativa: Market / Limit
- Estrategia base: RSI + MACD + EMA

---

## 3. Principios de Diseño
- Separación de responsabilidades
- Estrategia desacoplada de la ejecución
- Parametrización total
- Persistencia histórica (operaciones, señales, resultados)
- Tolerancia a fallos (API, red, datos)

---

## 4. Componentes Críticos del Sistema

### 4.1 Cliente Binance (Spot)
Responsable de:
- Autenticación
- Consulta de mercado (klines, precios)
- Envío de órdenes
- Cancelación y consulta de órdenes

**Riesgos**:
- Errores de firma
- Límite de rate
- Timeouts

---

### 4.2 Obtención de Datos de Mercado
- Uso de klines históricos
- Validación de datos incompletos
- Sincronización de timestamps

**Puntos críticos**:
- Velas abiertas vs cerradas
- Datos faltantes
- Desfase horario

---

### 4.3 Cálculo de Indicadores Técnicos
Indicadores base:
- RSI
- EMA rápida / lenta
- MACD + Signal

**Puntos críticos**:
- Ventanas insuficientes
- NaN iniciales
- Recalcular solo nuevas velas

---

### 4.4 Estrategia de Trading (Refinada)

La estrategia es **determinística, explicable y auditable**. No busca anticipar el mercado, sino reaccionar ante condiciones técnicas claras.

#### 4.4.1 Principios de la Estrategia
- Operar **solo a cierre de vela** (evitar ruido intrabar)
- Confirmación mínima con **2 indicadores alineados**
- Evitar operar en rangos laterales sin tendencia
- Priorizar señales de **continuidad**, no de reversión agresiva

---

#### 4.4.2 Condiciones de Compra (Entrada LONG)
La compra se habilita únicamente si **todas** las siguientes condiciones se cumplen en la vela cerrada:

1. **RSI**
   - RSI < 35
   - RSI en pendiente positiva (RSI actual > RSI previo)

2. **MACD**
   - MACD cruza por encima de la Signal
   - Histograma MACD > 0 o creciendo

3. **EMA (Tendencia)**
   - EMA rápida > EMA lenta
   - Distancia entre EMAs creciente (confirmación de momentum)

4. **Filtro adicional (opcional)**
   - Volumen de la vela >= promedio de volumen (evitar falsas rupturas)

Resultado: **Señal de Compra Válida**

---

#### 4.4.3 Condiciones de Venta (Salida)
La salida puede darse por **toma de ganancia** o por **invalidez de la señal**.

##### A. Venta por invalidación técnica
Se ejecuta salida total o parcial si ocurre cualquiera:

- RSI > 65 y comienza a girar a la baja
- MACD cruza por debajo de Signal
- EMA rápida cruza por debajo de EMA lenta

##### B. Venta por toma de ganancia
- TP1: +X% → vender 25% o 33%
- TP2: +Y% → vender otro 25% o 33%
- Resto: dejar correr tendencia

---

#### 4.4.4 Condiciones en las que NO se opera
- RSI entre 45 y 55 (zona neutra)
- MACD plano sin divergencia
- EMAs entrelazadas (mercado lateral)
- Velas con volumen anormal extremo (eventos)

---

#### 4.4.5 Anti-Sobreoperación
- Máximo 1 trade activo por símbolo
- Cooldown tras salida (N velas)
- No reentrar en la misma vela

---

#### 4.4.6 Resultado de la Estrategia
Cada evaluación debe producir uno de estos estados:
- BUY
- SELL (TOTAL o PARCIAL)
- HOLD

La estrategia **nunca ejecuta órdenes**, solo emite decisiones.

---



### 4.5 Gestión de Riesgo (Refinada)

La gestión de riesgo es el **núcleo del sistema**. La estrategia puede fallar; el riesgo **no puede fallar**.

El objetivo no es maximizar ganancias, sino **evitar pérdidas irreversibles** y permitir la supervivencia del bot en el tiempo.

---

#### 4.5.1 Riesgo por Operación
- Riesgo máximo por trade: **1% – 2% del capital asignado al bot**
- El riesgo se calcula **antes** de enviar cualquier orden
- El capital del bot es independiente del capital total de la cuenta

Ejemplo:
- Capital bot: 1.000 USDT
- Riesgo 2% → pérdida máxima aceptable: 20 USDT

---

#### 4.5.2 Tamaño de Posición
El tamaño de la posición se calcula en función del riesgo y el precio de entrada.

Variables:
- Capital disponible
- % riesgo
- Precio de entrada

Reglas:
- Respetar minQty y stepSize del símbolo
- Nunca usar el 100% del capital
- Redondear siempre hacia abajo

---

#### 4.5.3 Stop Loss Técnico
El Stop Loss **no es fijo**, es técnico.

Opciones válidas:
- Último mínimo relevante
- EMA lenta
- % fijo de emergencia (hard stop)

Reglas:
- El SL se define **antes de entrar**
- Si el SL queda demasiado cerca → no operar
- El SL puede ajustarse solo a favor (trailing)

---

#### 4.5.4 Take Profit Parcial (Clave del Sistema)
La salida se realiza en **tramos**, no de forma binaria.

Estructura recomendada:

- **TP1**
  - +X% desde entrada
  - Vender **25% o 33%**
  - Objetivo: reducir riesgo

- **TP2**
  - +Y% desde entrada
  - Vender otro **25% o 33%**
  - Objetivo: asegurar ganancia

- **Resto de la posición**
  - Se deja correr la tendencia
  - Protegido con trailing stop

---

#### 4.5.5 Trailing Stop
Una vez ejecutado TP1:
- El Stop Loss se mueve a:
  - Precio de entrada (break-even)
  - O EMA lenta

Después de TP2:
- SL dinámico siguiendo:
  - EMA lenta
  - O % fijo de retroceso

---

#### 4.5.6 Escenarios de Salida Forzada
Se cierra la posición completa si:
- Se pierde conexión prolongada
- Error crítico de sincronización
- Cambio brusco de volatilidad
- Señal técnica contraria fuerte

---

#### 4.5.7 Reglas de Supervivencia
- Máximo X trades negativos consecutivos
- Stop diario de pérdidas
- Pausa automática tras drawdown

---

#### 4.5.8 Regla de Oro del Riesgo
> "El bot puede equivocarse en la entrada; nunca debe equivocarse en cuánto puede perder".

---



### 4.6 Ejecución de Órdenes
- MARKET vs LIMIT
- Control de cantidad mínima y stepSize
- Confirmación de ejecución

**Puntos críticos**:
- Órdenes parciales
- Rechazos por filtros de Binance
- Doble ejecución

---

### 4.7 Gestión de Estado (Refinada)

La gestión de estado garantiza que el bot **sepa exactamente dónde está parado** en todo momento, incluso ante reinicios, errores o desconexiones.

Sin un estado consistente, cualquier estrategia es inválida.

---

#### 4.7.1 Concepto de Estado
El estado representa la **fotografía operativa actual** del bot para un símbolo determinado.

El bot **no asume**, siempre **verifica**.

---

#### 4.7.2 Variables Críticas de Estado
Para cada símbolo, el bot debe persistir al menos:

- `symbol`
- `position_status` → NONE | LONG
- `entry_price`
- `position_qty`
- `remaining_qty`
- `tp1_executed` (bool)
- `tp2_executed` (bool)
- `stop_loss_price`
- `last_decision` → BUY | SELL | HOLD
- `last_update_timestamp`

---

#### 4.7.3 Estado Persistente
El estado **no vive solo en memoria**.

Debe persistirse en:
- Base de datos (MySQL)
- O almacenamiento durable equivalente

Motivos:
- Reinicio del bot
- Crash del proceso
- Actualización de código

---

#### 4.7.4 Sincronización con Binance
Al iniciar o reiniciar el bot:

1. Consultar posiciones reales en Binance Spot
2. Consultar órdenes abiertas
3. Reconstruir el estado local
4. Validar cantidades y precios

Si hay inconsistencias:
- Priorizar el estado real de Binance
- Ajustar estado interno

---

#### 4.7.5 Máquina de Estados (State Machine)
Estados posibles:

- FLAT (sin posición)
- ENTERING (orden enviada, no confirmada)
- IN_POSITION (posición activa)
- PARTIAL_EXIT (TP parcial ejecutado)
- EXITING (cerrando posición)
- ERROR (estado inválido)

Transiciones **permitidas** y **controladas**.

---

#### 4.7.6 Reglas de Integridad
- Nunca abrir una posición si `position_status != NONE`
- Nunca vender más de `remaining_qty`
- Nunca ejecutar TP dos veces
- Nunca modificar SL en contra de la posición

---

#### 4.7.7 Manejo de Reinicios
En cada arranque:
- Cargar estado persistido
- Validar contra Binance
- Resolver diferencias
- Registrar evento de recuperación

Si no se puede resolver:
- Pasar a estado ERROR
- No operar

---

#### 4.7.8 Manejo de Errores de Estado
Errores típicos:
- Órdenes parcialmente ejecutadas
- Órdenes canceladas externamente
- Cambios manuales en la cuenta

Acción:
- Log estructurado
- Reconstrucción de estado
- Cierre defensivo si es necesario

---

#### 4.7.9 Regla de Oro del Estado
> "Si el estado no es confiable, el bot debe dejar de operar inmediatamente".

---



### 4.8 Persistencia y Auditoría
Guardar:
- Señales generadas
- Órdenes enviadas
- Órdenes ejecutadas
- PnL diario

**Puntos críticos**:
- Duplicados
- Escrituras fallidas
- Performance en MySQL

---

### 4.9 Manejo de Errores
- Errores de red
- Errores de API
- Errores lógicos

Estrategias:
- Reintentos
- Logs estructurados
- Fail-safe (no operar)

---

### 4.10 Control de Ejecución
- Scheduler (time-based)
- Websocket (event-based)
- Threads / async

**Puntos críticos**:
- Condiciones de carrera
- Doble evaluación
- Bloqueos

---

## 5. Seguridad
- API Keys sin permisos de retiro
- Variables de entorno / BD segura
- Logs sin datos sensibles

---

## 6. Arquitectura del Sistema

### 6.1 Diagrama de Arquitectura (Lógico)

```text
+---------------------------+
|      Binance Websocket    |
|   (klines / ticker)       |
+-------------+-------------+
              |
              v
+---------------------------+
|      Websocket Listener   |
|  (event dispatcher)      |
+-------------+-------------+
              |
              v
+---------------------------+
|        BotManager         |
|  - Control global         |
|  - Enrutamiento símbolos  |
+------+------+-------------+
       |      |
       |      |
       v      v
+-----------+  +-----------+
| Bot BTC   |  | Bot ETH   |   ... (N símbolos)
| Strategy  |  | Strategy  |
| Risk      |  | Risk      |
| State     |  | State     |
+-----+-----+  +-----+-----+
      |              |
      +------+-------+
             v
     +-------------------+
     |  Binance Spot API |
     | (órdenes, estado) |
     +-------------------+

             |
             v
     +-------------------+
     |   MySQL / Storage |
     | estado / trades   |
     +-------------------+
```

---

### 6.2 Principios de la Arquitectura
- Un bot lógico por símbolo
- Estrategia desacoplada de ejecución
- Estado persistente y verificable
- Websocket como fuente primaria de eventos
- API REST solo para confirmación y órdenes

---

## 7. Flujo de Websocket (Event-Driven)

### 7.1 Flujo General

```text
[Websocket Binance]
        |
        v
[Mensaje recibido]
        |
        v
[Parseo y validación]
        |
        v
[Identificar símbolo]
        |
        v
[BotManager.on_event()]
        |
        v
[BotSymbol.on_market_data()]
        |
        v
[Evaluación estrategia]
        |
        +--> HOLD (no acción)
        |
        +--> BUY / SELL (decisión)
                     |
                     v
              [Gestión de Riesgo]
                     |
                     v
              [Enviar orden Spot]
                     |
                     v
              [Actualizar estado]
                     |
                     v
              [Persistir en MySQL]
```

---

### 7.2 Reglas del Flujo Websocket
- Solo evaluar **velas cerradas**
- Nunca ejecutar órdenes dentro del callback puro
- Separar recepción de evento y decisión
- Evitar bloqueos dentro del listener

---

### 7.3 Manejo de Desconexiones
- Detectar desconexión
- Pausar evaluación
- Re-sincronizar estado al reconectar
- Validar órdenes abiertas

---

### 7.4 Regla de Oro del Flujo
> "El Websocket informa; el bot decide; el manager coordina".

---

## 8. Evolución Futura
- Backtesting con mismo flujo de eventos
- Event sourcing completo
- Escalado multi-proceso
- Integración scoring IA

---

Documento vivo – pensado para iterar junto al código.

