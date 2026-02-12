# 📘 MÓDULO: Rotación Interna Automática

**Proyecto:** BotCrypto\
**Ámbito:** Binance SPOT\
**Universo:** Tabla `otros_activos`

------------------------------------------------------------------------

## 1️⃣ Objetivo

Permitir que el BOT:

-   Evalúe técnicamente los activos ya autorizados.
-   Priorice oportunidades dentro del universo curado.
-   Limite exposición simultánea.
-   Evite operar todos los activos al mismo tiempo.

⚠ Este módulo **no agrega ni elimina activos** del universo.\
Solo decide cuáles tienen prioridad operativa en cada ciclo.

------------------------------------------------------------------------

## 2️⃣ Principio Estratégico

Dentro del universo aprobado manualmente:

> No todos los activos deben operar simultáneamente.

El sistema debe:

-   Detectar cuáles presentan mejor estructura técnica.
-   Asignar prioridad dinámica.
-   Operar únicamente los mejores según capital y riesgo.

------------------------------------------------------------------------

## 3️⃣ Sistema de Scoring Interno

Cada activo recibe un **Score Técnico Dinámico**.

### 3.1 Fórmula General

    Score_Total = 
        Score_RSI +
        Score_MACD +
        Score_EMA +
        Score_Volatilidad

El score se recalcula en cada ciclo de evaluación.

------------------------------------------------------------------------

## 4️⃣ Componentes del Score

### 4.1 Score RSI

-   RSI \> 50 → +1\
-   RSI cruzando 30 (desde abajo) → +2\
-   RSI \> 70 → -1\
-   RSI \< 30 → 0

Objetivo: Detectar momentum temprano y evitar sobrecompra.

------------------------------------------------------------------------

### 4.2 Score MACD

-   MACD \> Signal → +1\
-   Cruce alcista reciente → +2\
-   Cruce bajista → -2

Objetivo: Confirmar impulso direccional.

------------------------------------------------------------------------

### 4.3 Score EMA (Tendencia)

-   Precio \> EMA200 → +2\
-   EMA50 \> EMA200 → +1\
-   Precio \< EMA200 → -2

Objetivo: Operar preferentemente en tendencia estructural favorable.

------------------------------------------------------------------------

### 4.4 Score Volatilidad (ATR)

Cálculo:

    Volatilidad = ATR / Precio

-   Volatilidad saludable → +1\
-   Volatilidad extrema → -1\
-   Volatilidad muy baja → 0

Objetivo: Evitar activos dormidos o excesivamente explosivos.

------------------------------------------------------------------------

## 5️⃣ Clasificación por Prioridad

    Score >= 5  → PRIORIDAD ALTA
    Score 3–4   → PRIORIDAD MEDIA
    Score 1–2   → OBSERVACIÓN
    Score <= 0  → BLOQUEADO

------------------------------------------------------------------------

## 6️⃣ Lógica de Rotación

### 6.1 Ordenamiento

1.  Ordenar activos por `Score_Total` descendente.
2.  Excluir activos en estado BLOQUEADO.

------------------------------------------------------------------------

### 6.2 Límite Operativo

Respetar:

-   `max_positions`
-   `capital_disponible`
-   `risk_per_trade`

Ejemplo:

    Universe = 10 activos
    max_positions = 4
    → Solo los 4 con mayor score pueden abrir nuevas posiciones.

------------------------------------------------------------------------

### 6.3 Reglas de Entrada

Un activo puede abrir posición si:

-   Está dentro del Top N.
-   Tiene señal técnica válida.
-   No supera exposición global.
-   No está en cooldown.

------------------------------------------------------------------------

### 6.4 Reglas de Rotación

Si un activo pierde score o sale del Top N:

-   No se cierran posiciones activas automáticamente.
-   Se bloquean nuevas entradas.
-   Se mantiene monitoreo hasta mejora estructural.

------------------------------------------------------------------------

## 7️⃣ Control de Exposición Global

    exposicion_actual + nueva_posicion <= max_exposure_global

------------------------------------------------------------------------

## 8️⃣ Frecuencia de Evaluación

-   Evaluación en cierre de vela principal (1H o 4H).
-   No recalcular en cada tick.

------------------------------------------------------------------------

## 9️⃣ Estructura de Salida

``` python
{
    "BTCUSDT": {
        "score": 6,
        "prioridad": "ALTA",
        "permitir_compra": True
    }
}
```

------------------------------------------------------------------------

## 🎯 Resultado Esperado

-   Concentrar capital en mejores estructuras técnicas.
-   Reducir dispersión innecesaria.
-   Mantener universo controlado.
-   Adaptarse dinámicamente sin perder disciplina.


## Estructura para loas activos de rotación:
Table: otros_activos
Columns:
    id int AI PK 
    symbol char(25) PK 
    cuenta char(10) 
    idcrypto bigint 
    descripcion char(50) 
    base_asset char(25) 
    quote_asset char(10) 
    avgcost float 
    objetivo float 
    indicadores blob 
    fecupdate datetime