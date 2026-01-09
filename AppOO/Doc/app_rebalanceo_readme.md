# AppRebalanceo

## Propósito del proyecto

**AppRebalanceo** es un módulo lógico integrado al sistema principal (`DashMain_v9_ia.py`) cuyo objetivo es **generar recomendaciones de compra para rebalancear una cartera de inversión**, bajo un enfoque **equiponderado, determinístico y orientado a control de riesgo**, no a predicción de mercado.

El proyecto nace como una formalización del motor `DataHub.manager_buysell`, llevándolo de un conjunto de cálculos dispersos a una **app conceptual con responsabilidades claras**, preparada para crecer en el tiempo.

---

## Filosofía central

> *“El riesgo debe estar distribuido en partes iguales.”*

AppRebalanceo no busca maximizar retornos ni anticipar precios. Su rol es:

- Reducir concentración de riesgo
- Suavizar el flujo de ingresos
- Mantener disciplina estructural
- Convertir el estado actual de la cartera en decisiones de compra coherentes

No hay trading, no hay timing, no hay señales predictivas.

---

## Enfoque general

El sistema trabaja exclusivamente sobre **datos ya consolidados del portafolio**, generados por el core existente.

A partir de ese estado, AppRebalanceo:

1. Calcula desbalances (gaps)
2. Define objetivos equiponderados dinámicos
3. Evalúa activos bajo múltiples dimensiones
4. Produce un ranking de compras sugeridas
5. Explica *por qué* cada activo es recomendado

Todo el proceso es **determinístico, reproducible y auditable**.

---

## Las 4 dimensiones de rebalanceo

El rebalanceo se realiza simultáneamente en **cuatro ejes independientes**, cada uno con su propio peso relativo.

### 1. Dividendos – Equilibrio mensual

Objetivo:
- Recibir ingresos de forma **uniforme a lo largo del año**

Principios:
- El objetivo anual se distribuye en 12 meses
- Se priorizan meses con déficit de ingresos
- Se penaliza la concentración estacional

Resultado buscado:
- Flujo de caja estable y predecible

---

### 2. Sectores – Equiponderación dinámica

Objetivo:
- Que cada sector tenga **el mismo peso porcentual** en la cartera

Principios:
- No existen pesos sectoriales fijos
- El peso objetivo se calcula como 100 / sectores presentes
- Los sectores subponderados se priorizan

Resultado buscado:
- Eliminación de apuestas sectoriales implícitas

---

### 3. Tipos de activos – Balance estructural

Objetivo:
- Distribuir la cartera de forma equilibrada entre tipos de activos

Principios:
- Inspirado en la idea de *cartera permanente*, pero adaptado
- El peso objetivo es dinámico según los tipos existentes
- Se aplica una **restricción estructural de ingresos**:
  - Al menos el 80% del valor del portafolio debe generar ingresos

Resultado buscado:
- Balance entre crecimiento, estabilidad e ingresos

---

### 4. Regiones / países – Diversificación geográfica

Objetivo:
- Evitar concentración geográfica excesiva

Principios:
- Todas las regiones presentes deben tender al mismo peso
- El peso objetivo se calcula dinámicamente

Resultado buscado:
- Reducción de riesgo país

---

## Estrategia de equiponderación

La equiponderación es **dinámica**, no estática:

- No se definen porcentajes fijos por categoría
- El sistema detecta cuántas categorías existen
- El objetivo se recalcula automáticamente

Ejemplo conceptual:
- Si hay 7 sectores → cada uno debería tender a ~14,3%
- Si hay 5 tipos de activos → cada uno a 20%

Esto permite que la cartera evolucione sin reconfiguración manual.

---

## Rol dentro del sistema general

AppRebalanceo **no es una aplicación independiente**.

Su rol es:
- Integrarse al ciclo de actualización de `DashMain_v9_ia.py`
- Consumir el estado ya calculado de `DataHub.manager_buysell`
- Devolver resultados estructurados para visualización

No interactúa directamente con:
- UI
- Callbacks de Dash
- Ejecución de órdenes

---

## Qué hace AppRebalanceo

- Analiza el estado actual de la cartera
- Detecta desbalances en múltiples dimensiones
- Calcula scores de prioridad por activo
- Genera recomendaciones de compra
- Explica cada recomendación con razones claras

---

## Qué NO hace AppRebalanceo

Explícitamente fuera de alcance:

- Predicción de precios
- Análisis técnico
- Valoración fundamental profunda
- Ejecución automática de operaciones
- Decisiones de venta como objetivo principal

Las ventas pueden existir en el futuro, pero no son el foco del sistema.

---

## Naturaleza del motor de decisión

El motor es:

- Determinístico
- Transparente
- Parametrizable
- Reproducible

Dado el mismo estado de la cartera y los mismos parámetros, **siempre produce el mismo resultado**.

Esto lo hace:
- Auditable
- Testeable
- Ideal para evolución futura con IA explicativa

---

## Evolución prevista

El diseño de AppRebalanceo permite crecer sin romper su filosofía:

- Simulación de impacto antes/después
- Visualización de progreso hacia el equilibrio
- Persistencia histórica de decisiones
- Incorporación de IA como capa explicativa (no predictiva)

---

## Idea clave para el futuro

AppRebalanceo no decide *qué activo es mejor*.

Decide:

> *qué activo ayuda más a que la cartera sea coherente con su propio diseño.*

Ese es el corazón del proyecto.

