
# Institutional Accumulation Module
### Complemento para Screener de Dividendos

Autor: Wilmer Gutierrez  
Objetivo: Incorporar señales de acumulación institucional al sistema de análisis basado en empresas con dividendos.

---

# 1. Contexto del sistema actual

El sistema actual está centrado en la tabla Market, que representa el universo de empresas que se monitorean para inversión de largo plazo.

La tabla contiene principalmente:

- Empresas con dividendos
- Empresas que forman parte de la cartera
- Empresas bajo seguimiento
- Información fundamental descargada desde EDGAR
- Información de mercado desde Yahoo Finance

Por lo tanto Market representa el universo invertible del sistema.

---

# 2. Problema que se desea resolver

Las empresas con dividendos pueden tener:

- buenos fundamentales
- buen yield
- buen crecimiento

pero no necesariamente estar recibiendo flujo de capital institucional.

El objetivo del nuevo módulo es identificar:

Empresas de dividendos que están siendo acumuladas por grandes fondos.

Esto permite detectar:

- capital institucional entrando
- validación del mercado institucional
- potencial movimiento de precio a medio / largo plazo

---

# 3. Concepto de señal institucional

Los fondos institucionales manejan enormes cantidades de capital (AUM).

Ejemplos:

- Vanguard
- BlackRock
- State Street
- Fidelity
- Capital Group

Cuando estos fondos acumulan posiciones, suelen generar tendencias de largo plazo.

La señal institucional se puede medir utilizando:

- número de fondos que poseen la acción
- número de acciones en manos institucionales
- cambios en participaciones

Fuentes de datos:

- Yahoo Finance (institutional holders)
- Filings SEC (13F)

---

# 4. Objetivo del nuevo módulo

Crear un agente que:

1. consulte Yahoo Finance
2. obtenga los institutional holders
3. calcule un Institutional Score
4. actualice la tabla Market

Este score permitirá identificar acciones con dividendos que están siendo acumuladas por fondos.

---

# 5. Arquitectura del nuevo agente

Nuevo módulo:

Class_InstitucionalScore.py

Flujo de datos:

Market (lista de símbolos)
    |
    v
Yahoo Finance
    |
    v
Institutional Holders
    |
    v
Calculo Institutional Score
    |
    v
UPDATE Market

---

# 6. Campos nuevos en la tabla Market

inst_funds
inst_shares
inst_score


Descripción:

inst_funds
Número de fondos institucionales detectados.

inst_shares
Total de acciones en manos institucionales.

inst_score
Score calculado que mide acumulación institucional.

inst_update
Fecha de última actualización.

---

# 7. Cálculo del Institutional Score

Ejemplo simple:

score = log(funds) + log(shares)

Interpretación:

score alto → mayor acumulación institucional

---

# 8. Uso dentro del Screener

El score institucional no reemplaza la estrategia de dividendos.

Se utiliza como señal complementaria.

Flujo de análisis:

Dividend Screener
        +
Institutional Score

---

# 9. Ejemplo de ranking resultante

Symbol | DividendYield | InstScore
----------------------------------
AVGO | 2.2 | 18.4
MSFT | 0.8 | 18.1
O | 5.6 | 15.9
VZ | 7.1 | 12.0

Interpretación:

AVGO → dividend growth + acumulación institucional

---

# 10. Aplicación práctica

El ranking permite:

- priorizar investigación
- detectar empresas acumuladas por fondos
- validar decisiones de inversión
- detectar tendencias institucionales

---

# 11. Evolución futura del módulo

1) detectar cambios trimestrales en holdings
2) integrar filings 13F
3) calcular ranking de acumulación institucional
4) detectar acciones con mayor compra institucional

---

# 12. Resultado esperado

El sistema final combinará tres fuentes principales:

1) Fundamentales (EDGAR)
2) Dividendos
3) Flujo institucional

Esto permitirá construir un screener avanzado para inversión de largo plazo.
