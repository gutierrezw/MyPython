# Consenso — Diseño de Expansión
**AppOO · 2026-05**

---

## Estado actual

El popup Consenso calcula **6 votos activos** más Mod (excluido de la suma):

| Clave | Fuente | Penaliza |
|---|---|---|
| Net | buy_ratio − sell_ratio vs percentiles cartera (13F) | Sí (+1/0/−1) |
| Opt | calls/(calls+puts) (13F) | Sí |
| Flujo | new_entrants − full_exits vs percentiles (13F) | Sí |
| Ana | analyst_rec Yahoo | Sí |
| Val | categoriaActivo (I/S/N) manual | Sí |
| Cob | fh_count ≥ 20/5 (13F) | Sí |
| Mod | CSV señal IA técnica | **Excluido** — solo informativo |

`senal_consenso()` → ★ UNÁNIME / ▲ CONSENSO / ↗ TENDENCIA / → NEUTRO / ↘ ALERTA / ▼ SALIDA

Código en `Class_Screener.py` (~línea 931), se computa al abrir el popup.

---

## Decisión de alcance — qué va a Consenso y qué va a los modelos IA

Los votos de Consenso deben ser señales **estructuralmente distintas** al análisis técnico:
flujos institucionales, recomendaciones de analistas, fundamentals.

| Señal | Destino | Razón |
|---|---|---|
| Rango 52 semanas | **Modelos IA (BUY/SELL)** | Indicador técnico de precio — el ML aprende el peso óptimo |
| Volumen relativo | **Modelos IA (BUY/SELL)** | Ídem — mejor como feature de entrenamiento que como regla fija |
| Tech Alignment | **Voto nuevo en Consenso** | Señal externa (noticias) que el modelo IA no ve |

Rango 52w y Volumen quedan **pendientes para la próxima revisión de features** de los modelos IA.
Ver `Doc/modelo_buyv01.md` y `Doc/modelo_sellv01.md` para el estado actual de features.

---

## Único voto nuevo para Consenso: Tech Alignment

### Qué mide

Si la empresa está alineada con una tendencia tecnológica emergente que aparece en noticias del día.
Es información que **ningún otro voto captura** y que el modelo IA no tiene como input.

### Cómo funciona

```
RSS feeds (TechCrunch, MIT Tech Review)
  → feedparser: extrae titulares
      → Claude Haiku: "¿qué categorías tech son prominentes hoy?"
          → retorna lista JSON: ["ai_semiconductors", "clean_energy", ...]
              → THEME_MAP: categoría → tickers en cartera
                  → voto_tech_alignment(symbol, temas_activos)
```

### Comportamiento del voto

| Caso | Voto |
|---|---|
| Símbolo en tema activo hoy | +1 |
| Sin alineación | 0 (abstención — no penaliza) |

No penaliza porque la mayoría de nuestras acciones son dividendo/utilities. Un banco no debería
bajar su consenso por no ser semiconductores.

### THEME_MAP propuesto

```python
THEME_MAP = {
    "ai_semiconductors": ["NVDA", "AMD", "INTC", "ASML", "QCOM", "MU"],
    "clean_energy":      ["VST", "PLUG", "NEE", "ENPH", "FSLR", "CEG"],
    "biotech":           ["PFE", "ABBV", "BMY", "AMGN", "GILD", "MRNA"],
    "blockchain":        ["CGPT", "MSTR", "COIN"],
    "cloud_saas":        ["MSFT", "AMZN", "GOOGL", "CRM", "NOW", "SNOW"],
    "robotics":          ["ISRG", "ABB", "ROK", "TER"],
}
```

### Infraestructura

| Qué | Detalle |
|---|---|
| Paquetes | `feedparser` + `anthropic` — ya instalados |
| API key | `ANTHROPIC_API_KEY` como env variable (igual que `APPOO_TMP`) |
| Módulo RSS + Claude | `ConvergIA/Scanner_Tecnologias.py` |
| Módulo THEME_MAP | `ConvergIA/ThemeMapper.py` |
| Agente | `Agente_TechAlignment` en `Class_DashBot.py` — 1 vez/día |
| Persistencia | `tmp/tech_temas.json` — el popup lo lee en tiempo real |
| Fallback | JSON vacío → voto 0 para todos → no rompe nada |

### Decisiones pendientes antes de codificar

1. **API key:** ¿env variable en `launch.json` o en tabla `sesion` bajo vehiculo `"CLAUDE"`?
2. **Scope del voto:** ¿solo en el popup Consenso o también en la columna del Screener?
3. **THEME_MAP:** ¿en código Python (archivo editable) o en JSON configurable desde la app?

---

## Idea futura — Scanner YouTube

### Origen de la idea

PLUG fue descubierto a través de un video de YouTube antes de que apareciera en ningún screener
institucional. Los canales de inversión de calidad a veces identifican activos antes que los datos
estructurados (13F, analistas). Eso es valor que hoy no capturamos.

### Cómo funcionaría

YouTube expone **RSS feeds por canal** sin necesidad de API key ni costo:
```
https://www.youtube.com/feeds/videos.xml?channel_id=XXXX
```
Devuelve títulos y descripciones de los últimos videos — exactamente el mismo formato que
TechCrunch. `feedparser` ya instalado lo lee sin cambios.

```
RSS feeds de canales de inversión seleccionados
  → feedparser: extrae títulos + descripciones
      → Claude Haiku: "¿qué tickers se mencionan como oportunidad?"
          → lista de símbolos candidatos
              → sync_market() los agrega con categoriaActivo='T' (descubierto externamente)
                  → entran al análisis normal de Consenso
```

### Por qué encaja bien

- Misma infraestructura que Tech Alignment (feedparser + Claude) — costo de implementación bajo
- Los tickers que salen se agregan a `market` con `categoriaActivo='T'`, que ya existe
- Desde ahí el sistema de Consenso los evalúa automáticamente como a cualquier otro activo

### Filtrado necesario (el problema central)

YouTube tiene demasiado volumen — la mayoría es ruido. Se necesitan 4 capas:

1. **Canales curados** — solo 5-10 canales ya validados por el usuario (no rastrear YouTube en general)
2. **Filtro de título** — descartar videos sin tickers o palabras clave de análisis (`buy`, `undervalued`, `dividend`). Bota el 80% sin costo.
3. **Claude como juez** — de los que pasan, evalúa si es análisis genuino o clickbait y si el tono es bullish
4. **Consenso como validación final** — el ticker descubierto entra a `market` con `categoriaActivo='T'` y pasa por los 6 votos existentes. YouTube solo detecta candidatos, no decide compras.

### Estado

**Idea documentada — no implementada.** Implementar después de validar Tech Alignment con RSS de noticias.

---

## Lo que NO vamos a hacer

- Sistema de consenso paralelo — el existente es la fuente de verdad
- Votos de indicadores técnicos en Consenso (van a los modelos IA)
- Alpha Vantage o Google Trends — otra dependencia inestable
- Tablas nuevas — si hace falta persistir algo, columna nueva en `market`
- Penalización negativa con Tech Alignment
