# Integración de Contexto Superior como Penalización Estructural

## Proyecto: BotCrypto -- Sistema Multi-Timeframe

------------------------------------------------------------------------

## Objetivo

Integrar la validación de **Contexto Superior** dentro del sistema
actual como una penalización fuerte dentro del scoring, sin romper la
arquitectura existente ni generar confusión futura.

El contexto NO reemplaza el scoring. El contexto modifica el resultado
final del scoring.

------------------------------------------------------------------------

# 1️⃣ Cambio Conceptual en Arquitectura

Antes:

    score_total = score_indicadores_tf_base

Ahora:

    score_base        → señales del timeframe operativo
    score_contexto    → validación timeframe superior
    score_total       → score_base + score_contexto

------------------------------------------------------------------------

# 2️⃣ Estructura Recomendada

## 2.1 Método nuevo: evaluar_contexto_superior()

Debe recibir: - symbol - timeframe_superior

Debe devolver:

    {
        "context_ok": bool,
        "detalle": {
            "ema_alineada": bool,
            "precio_sobre_ema": bool,
            "macd_positivo": bool,
            "rsi_mayor_50": bool
        }
    }

------------------------------------------------------------------------

# 3️⃣ Reglas de Validación del Contexto

Condiciones mínimas recomendadas:

✔ EMA20 \> EMA50\
✔ Precio \> EMA20\
✔ MACD \> 0\
✔ RSI \> 50

Si al menos 3 de 4 se cumplen → contexto_ok = True\
Si no → contexto_ok = False

------------------------------------------------------------------------

# 4️⃣ Penalización Estructural

Definir constante global:

    CONTEXTO_PENALIZACION = -5

Implementación sugerida:

    score_base = calcular_score_tf_base()
    contexto = evaluar_contexto_superior()

    if contexto["context_ok"]:
        score_contexto = 0
    else:
        score_contexto = CONTEXTO_PENALIZACION

    score_total = score_base + score_contexto

------------------------------------------------------------------------

# 5️⃣ Protección Anti-Confusión

Regla recomendada adicional:

    if not contexto["context_ok"]:
        score_total = min(score_total, 0)

Esto garantiza que un activo fuera de contexto no pueda liderar el
ranking.

------------------------------------------------------------------------

# 6️⃣ Visualización en UI

Agregar columnas:

  Symbol   Score Base   Contexto   Score Total
  -------- ------------ ---------- -------------

Mostrar:

✔ si contexto_ok = True\
❌ si contexto_ok = False

Esto permite monitorear eficiencia estructural.

------------------------------------------------------------------------

# 7️⃣ Impacto Esperado

✔ Menos operaciones ✔ Mejor alineación estructural ✔ Menos rotación
innecesaria ✔ Mejora relación riesgo / beneficio ✔ Mejora eficiencia de
capital

------------------------------------------------------------------------

# 8️⃣ Recomendación Estratégica

Registrar en base de datos:

-   score_base
-   score_contexto
-   score_total
-   contexto_ok

Esto permitirá análisis posterior comparando:

Trades con contexto alineado vs no alineado.

------------------------------------------------------------------------

# 9️⃣ Resumen Final

El Contexto Superior:

No es una señal más. Es un modificador estructural de probabilidad.

Se integra como penalización fuerte dentro del scoring, pero separado
conceptualmente del score operativo.

------------------------------------------------------------------------

Documento técnico generado para integración limpia en sistema BotCrypto
multi-timeframe.
