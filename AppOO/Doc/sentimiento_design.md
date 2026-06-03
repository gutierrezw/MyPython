# Módulo Sentimiento — Diseño y estado
**AppOO · 2026-06**

---

## Qué es

Scanner de **sentimiento general de noticias** para todos los símbolos en cartera.
No está orientado a temas tecnológicos — cubre toda la cartera sin distinción de sector.

Alimenta el voto **`Sent`** en el popup Consenso.

---

## Flujo

```
yfinance.Ticker(sym).news  →  titulares del día por símbolo
  → Claude Haiku: clasifica sentimiento (+1 / 0 / −1)
      → BD: market_sentiment  (lectura puntual)

BD: market_sentiment (historial días anteriores)
  → Claude Haiku: detecta patrón de comportamiento
      → BD: market_sentiment_analysis  (patrón diario)
```

---

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `ConvergIA/Scanner_Sentimiento.py` | Descarga noticias + llama Haiku por símbolo |
| `ConvergIA/Interprete_Sentimiento.py` | Lee historial BD + llama Haiku → patrón |
| `ConvergIA/ThemeMapper.py` | `voto_sentimiento()` — combina sentimiento + patrón |

---

## Agentes

| Agente | Intervalo | Función |
|---|---|---|
| `Agente_Sentimiento` | 8 horas (3×/día) | Llama `scan_sentimiento()` |
| `Agente_InterpreteSentimiento` | 24 horas (1×/día) | Llama `interpretar_sentimiento()` |

API key: `sesion.vehiculo = 'ClaudeAPIP'`

---

## Lógica del voto `Sent`

| Patrón | Sentimiento | Voto |
|---|---|---|
| `acumulacion` | cualquiera | `+1` |
| `distribucion` | cualquiera | `−1` |
| `neutro` | cualquiera | `0` |
| `inflexion` | `>= 0` | `+1` |
| `inflexion` | `< 0` | `0` (abstención — no penaliza) |
| sin datos | — | `None` (excluido del denominador) |

**Criterio de inflexión:** un activo en transición con noticias negativas no se penaliza
porque puede estar en el inicio de una recuperación. Solo vota positivo si el sentimiento
acompaña el cambio de dirección.

---

## Cobertura esperada

- 36 símbolos en cartera
- ~30-34 con noticias disponibles en yfinance
- ~28-32 clasificados exitosamente por Haiku

---

## Estado

- Implementado y operativo
- Voto `Sent` activo en popup Consenso y en `refresh_consenso_tags()`
- Agentes en `AGENTES_SCHEDULE` con `active: True` — pendiente conectar en `Class_DashBot.py`
