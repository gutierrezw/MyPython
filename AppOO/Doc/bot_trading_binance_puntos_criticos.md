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

### 4.4 Estrategia de Trading
Reglas claras y determinísticas.

Ejemplo conceptual:
- Compra:
  - RSI < 30
  - MACD cruza al alza
  - EMA rápida > EMA lenta
- Venta:
  - RSI > 70
  - MACD cruza a la baja

**Puntos críticos**:
- Señales contradictorias
- Ruido en temporalidades bajas
- Sobre-operar

---

### 4.5 Gestión de Riesgo
- Tamaño de posición
- Riesgo por trade (% capital)
- Take Profit parcial (25% / 33%)
- Stop Loss lógico (no emocional)

**Puntos críticos**:
- Sobreexposición
- No respetar capital disponible
- Slippage

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

### 4.7 Gestión de Estado
El bot debe conocer:
- Si hay posición abierta
- Precio de entrada
- Cantidad
- TP parciales ejecutados

**Puntos críticos**:
- Desincronización con Binance
- Reinicio del bot
- Estado inconsistente

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

## 6. Evolución Futura
- Backtesting con misma estrategia
- Score híbrido (técnico + IA)
- Multi-asset concurrente
- Optimización automática de parámetros

---

## 7. Regla de Oro
> Si el bot no entiende exactamente por qué entra o sale, **no debe operar**.

---

Documento vivo – pensado para iterar junto al código.

