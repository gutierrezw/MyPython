# Filtro Estructural con EMA100 / EMA200

## 1. Problema Detectado

En temporalidad 30 minutos, el bot estaba ejecutando entradas LONG basadas en:

- RSI
- MACD
- EMA cortas (20 / 50)
- Volumen

Sin embargo, no estaba considerando el **régimen estructural del mercado** definido por las EMAs de mayor periodo (100 y 200).

Esto generó:

- Entradas en contra de la tendencia media
- Pullbacks débiles que no alcanzan TP
- Aumento de SL consecutivos
- Rachas perdedoras estructurales

---

## 2. Causa Raíz

El sistema evaluaba señales de momentum local sin validar el contexto estructural.

En múltiples casos:

- Precio < EMA100
- EMA100 ≈ EMA200 o EMA100 < EMA200

Esto implica presión bajista o lateralización.

El bot estaba intentando capturar rebotes dentro de un régimen desfavorable.

---

## 3. Solución: Filtro de Régimen Estructural

Antes de evaluar cualquier ENTRY, se debe validar el régimen del mercado.

### Regla para permitir LONG:

```
close > EMA100
AND
EMA100 > EMA200
```

Opcional (más estricto):

```
Slope(EMA100) > 0
```

---

### Casos donde NO se permite LONG:

```
close < EMA100
OR
EMA100 < EMA200
```

En esos casos el sistema debe:

- No generar señal de entrada
- Mantener estado WAIT

---

## 4. Clasificación de Regímenes (Versión Avanzada)

Se pueden definir tres estados estructurales:

### BULL
- close > EMA100
- EMA100 > EMA200

### RANGE
- EMA100 ≈ EMA200
- Precio oscilando alrededor de EMA100

### BEAR
- close < EMA100
- EMA100 < EMA200


El régimen puede utilizarse para:

- Ajustar tamaño de posición
- Modificar SL
- Modificar TP
- Desactivar completamente entradas

---

## 5. Impacto Esperado

Al incorporar este filtro:

- Disminuye frecuencia de operaciones
- Aumenta probabilidad por trade
- Reduce drawdown estructural
- Mejora consistencia del sistema

El objetivo no es operar más, sino operar solo cuando el contexto favorece el movimiento.

---

## 6. Integración en TradingBotSpot

Debe incorporarse una función de validación previa:

```python

def _check_market_regime(self, df):
    ema100 = df["ema100"].iloc[-1]
    ema200 = df["ema200"].iloc[-1]
    close  = df["close"].iloc[-1]

    if close > ema100 and ema100 > ema200:
        return "BULL"
    else:
        return "NO_LONG"
```

Y en el método de evaluación:

```python
regime = self._check_market_regime(df)

if regime != "BULL":
    return NO_SIGNAL
```

---

## 7. Conclusión

La racha perdedora no fue causada por mala estrategia de señales, sino por ausencia de filtro estructural.

El Filtro EMA100/EMA200 agrega una capa de contexto que protege al sistema de operar contra tendencia media.

Es una mejora estructural crítica para un bot orientado a supervivencia y consistencia.

