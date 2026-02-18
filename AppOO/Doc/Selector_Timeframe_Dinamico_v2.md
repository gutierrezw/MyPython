# Selector Dinámico de Temporalidad (Timeframe Switching)

## Objetivo

Determinar automáticamente si el bot debe operar en 1H o 30m según
condiciones objetivas del mercado:

-   Volatilidad relativa (ATR%)
-   Volumen relativo
-   Contexto superior (4H)

El objetivo es mejorar eficiencia operativa y reducir ruido.

------------------------------------------------------------------------

## Clasificación del Contexto 4H

Condiciones evaluadas:

-   EMA20 \> EMA50
-   Precio \> EMA20
-   MACD \> 0
-   RSI \> 50

Clasificación:

-   4/4 → Fuerte
-   3/4 → Moderado
-   2/4 → Débil
-   0-1 → Bajista

------------------------------------------------------------------------

## Métricas Técnicas

### 1) ATR%

ATR_percent = ATR(14) / Precio

-   2.5% → Alta expansión

-   1.5% -- 2.5% → Moderado

-   \< 1.5% → Compresión

### 2) Volumen Relativo

Vol_ratio = Volumen_actual / Promedio_volumen_20

-   1.5 → Fuerte actividad

-   1.2 -- 1.5 → Normal

-   \< 1.2 → Bajo interés

------------------------------------------------------------------------

## Lógica de Decisión

### Contexto Fuerte (4/4)

Si ATR% \> 2.5% Y Vol_ratio \> 1.3: → Operar en 30m Sino: → Operar en 1H

### Contexto Moderado (3/4)

→ Operar solo en 1H → Reducir riesgo 20--30%

### Contexto Débil (2/4)

→ Operar solo 1H si scoring alto o → No operar

### Contexto Bajista (0-1)

→ No operar

------------------------------------------------------------------------

## Reglas Operativas

-   El timeframe se decide antes de abrir operación.
-   No cambiar temporalidad con posición abierta.
-   Registrar decisión en logs.
-   El contexto actúa como filtro maestro.

------------------------------------------------------------------------

## Flujo Integrado

1.  Evaluar contexto 4H.
2.  Clasificar fase.
3.  Calcular ATR% y Vol_ratio.
4.  Seleccionar timeframe.
5.  Ejecutar scoring.
6.  Calcular tamaño de posición según riesgo.
7.  Ejecutar orden protegida (OCO o STOP).

------------------------------------------------------------------------

## Conclusión

La temporalidad deja de ser fija y pasa a ser una consecuencia del
estado real del mercado.

Esto mejora calidad de entradas y eficiencia del capital.
