# Rebalanceo de Cartera – Documento Unificado

## 1. Propósito del documento

Este documento **unifica y contrasta**:

- El **diseño conceptual original** de AppRebalanceo
- El **estado real de implementación** del motor de rebalanceo actual

El objetivo es dejar una **fuente única de verdad**, clara y auditable, que permita:

- Ver qué partes del diseño ya están implementadas
- Detectar diferencias o ajustes respecto a la idea original
- Servir como base para evolución futura (budget, simulación, IA explicativa)

---

## 2. Rol de AppRebalanceo (diseño original)

AppRebalanceo es un **motor determinístico de recomendación de compras** cuyo rol no es predecir mercados, sino **reducir riesgo estructural** mediante equiponderación dinámica.

Principios centrales:

- No timing
- No predicción
- No trading
- Sí disciplina estructural
- Sí explicabilidad

El motor trabaja **exclusivamente** sobre el estado consolidado del portafolio generado por `DataHub.manager_buysell`.

---

## 3. Estado actual del DataHub (implementado)

Hoy, `DataHub.manager_buysell` provee **cuatro dimensiones consolidadas**, todas con base monetaria explícita:

### Dimensiones disponibles

- `sector`
- `region`
- `activos` (tipos de activo)
- `dividends`

Cada dimensión contiene:

- `summary` con pesos relativos
- `media` (objetivo equiponderado dinámico)
- `total_valor_market`

Esto significa que el motor ya **no trabaja solo con porcentajes**, sino con impacto monetario real.

---

## 4. Motor de Rebalanceo – Arquitectura actual

El motor `RebalanceEngine` está dividido en **fases claras**:

1. Cálculo de gaps estructurales
2. Normalización de gaps
3. Priorización de dimensiones
4. Construcción de candidatos
5. Scoring
6. Ranking final

Todo el flujo es:

- Determinístico
- Reproducible
- Auditable

---

## 5. Dimensiones de rebalanceo – Diseño vs Implementación

### 5.1 Dividendos

**Diseño original**:
- Buscar equilibrio mensual de ingresos
- Penalizar concentración estacional

**Implementación actual**:
- `_get_dividendos_mensuales()` agrega dividendos por mes
- `_gap_dividendos()` calcula desvío medio respecto al promedio
- Los activos con bloque `dividends` participan del score

**Estado**: ✅ Implementado y funcional

---

### 5.2 Sectores

**Diseño original**:
- Equiponderación dinámica
- Sin pesos fijos

**Implementación actual**:
- `_get_pesos_por_sector()` devuelve peso, objetivo, gap_pct y gap_valor
- `_sector_necesitado()` evalúa subponderación **monetaria**

**Estado**: ✅ Implementado con impacto real

---

### 5.3 Tipos de activo

**Diseño original**:
- Balance estructural entre tipos
- Inspiración en cartera permanente

**Implementación actual**:
- `_get_pesos_por_tipo()` simétrico a regiones
- Gap porcentual + gap monetario
- `_tipo_necesitado()` basado en gap_valor > 0

**Estado**: ✅ Implementado

---

### 5.4 Regiones

**Diseño original**:
- Evitar concentración geográfica

**Implementación actual**:
- `_get_pesos_por_region()` devuelve estructura enriquecida
- `_region_necesitada()` evalúa déficit monetario

**Estado**: ✅ Implementado

---

## 6. Scoring – Punto clave de convergencia

### Diseño original

- Score basado en desbalances estructurales
- Explicable
- No predictivo

### Implementación actual

El score final es:

```
score_final = score_estructural
              × (1 + impacto_monetario_normalizado)
              × valuation_factor
```

Donde:

- `score_estructural`: suma de gaps normalizados por dimensión
- `impacto_monetario_normalizado`: función saturada del `gap_valor`
- `valuation_factor`: ajuste secundario (cheap / neutral / expensive)

Cada candidato conserva un bloque `impacto` con:

- impacto por dimensión
- gap_valor_total
- gap_valor_norm

**Estado**: ✅ Implementado y alineado al diseño

---

## 7. Qué ya está alineado con el diseño original

- Filosofía no predictiva
- Equiponderación dinámica
- Separación Buy / Dividends
- Uso exclusivo de estado consolidado
- Determinismo completo
- Explicabilidad por activo

---

## 8. Qué NO estaba explícito en el diseño original (y hoy existe)

- Uso explícito de `total_valor_market`
- Priorización por impacto monetario real
- Saturación del impacto para evitar dominancia

Estos puntos **no contradicen el diseño**, sino que lo **mejoran operativamente**.

---

## 9. Próximos pasos coherentes (no implementados aún)

Estos pasos **no rompen el diseño original** y son extensiones naturales:

1. `budget_allocator()` – asignar monto sugerido por activo
2. Simulación before / after
3. Persistencia histórica de decisiones
4. Capa IA explicativa (no decisoria)

---

## 10. Conclusión

El estado actual del motor:

- **Respeta completamente el diseño conceptual original**
- Ya opera con impacto económico real
- Está listo para pruebas offline y notebook
- Está preparado para evolucionar sin refactor estructural

En otras palabras:

> *El motor hoy no solo refleja la idea original: la ejecuta.*

