# Modelo IA: Oportunidades de Venta (Sell)

## Identificación
- **Nombre**: modelo_sellv01
- **Tipo**: RandomForestClassifier
- **Versión**: 1.0

## Objetivo
Identificar oportunidades de venta de activos basándose en indicadores técnicos y métricas de rentabilidad. El modelo clasifica si un activo debe ser vendido o mantenido.

## Etiquetas de Clasificación
| Etiqueta | Significado | Recomendado |
|----------|-------------|-------------|
| `sell` | Vender el activo | 1 |
| `hold` | Mantener el activo | -1 |

## Clasificación por Umbrales
| Clasificación | Condición | Acción |
|---------------|-----------|--------|
| `sell` | confianza >= umbral_sell | Recomendar venta |
| `observacion` | confianza >= umbral_observacion | Monitorear |
| `descartar` | confianza < umbral_observacion | No mostrar |

## Features Utilizadas

### Indicadores Técnicos (por timeframe: _d, _w, _m)
- `rsi`: Relative Strength Index (0-100)
- `macd`: Moving Average Convergence Divergence
- `Close`: Precio de cierre

### EMAs Largos
- `EMA020`, `EMA050`, `EMA100`, `EMA200`

### EMAs Cortos
- `EMA009`, `EMA021`, `EMA055`, `EMA144`

### Fibonacci
- `fibo_longico`: Nivel de Fibonacci

### Máximos y Mínimos
- `13_semanas_max_d`, `13_semanas_min_d`
- `26_semanas_max_w`, `26_semanas_min_w`
- `52_semanas_max_m`, `52_semanas_min_m`

### Features Escalares
- `roi`: Retorno sobre inversión (%)

## Parámetros del Modelo

```json
{
  "n_estimators": 100,
  "max_depth": 10,
  "min_samples_split": 5,
  "random_state": 42,
  "n_folds": 5,
  "test_size": 0.3,
  "umbral_sell": 0.65,
  "umbral_observacion": 0.35
}
```

## Criterios de Venta
- RSI alto (> 70) indica sobrecompra
- Precio por encima de EMAs principales
- ROI positivo significativo
- Proximidad a máximos históricos

## Fuente de Datos
- CSV: `csv_datosIA_sell.csv`
- Tabla BD: `bdinv.oportunidades` (tipo='sell')

## Notas de Uso
1. El modelo debe reentrenarse periódicamente con nuevos datos etiquetados
2. Los umbrales pueden ajustarse según tolerancia al riesgo
3. Usar en conjunto con análisis fundamental para mejores resultados

┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE ENTRENAMIENTO                       │
└─────────────────────────────────────────────────────────────────┘

    CSV (csv_datosIA_buy.CSV / csv_datosIA_sell.CSV)
                          │
                          ▼
              readCSV_buy() / readCSV_sell()
                          │
                          ▼
         evaluar_oportunidades_*_con_IA()
                          │
                          ▼
                ┌─────────────────┐
                │  load_modelo()  │
                │                 │
                │ ¿modelo.pkl     │
                │   existe?       │
                └────────┬────────┘
                         │
           ┌─────────────┴─────────────┐
           │                           │
           ▼ NO                        ▼ SÍ
   ┌───────────────┐          ┌───────────────┐
   │ modelo = None │          │ modelo cargado│
   └───────┬───────┘          └───────┬───────┘
           │                          │
           ▼                          ▼
   Envía TODAS las            Predice confianza
   oportunidades              y filtra por umbral
   origen="system"            origen="ia"
           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
           oportunity_handler_*()
                      │
                      ▼
        ┌─────────────────────────┐
        │  • Inserta en BD        │
        │  • Envía a Telegram     │
        └─────────────────────────┘
                      │
                      ▼
        Usuario etiqueta en Telegram
        (1 = comprar/vender, -1 = esperar/hold)
                      │
                      ▼
        Datos etiquetados en tabla oportunidades
                      │
                      ▼
        Botón "Entrenar" en Monitor IA
                      │
                      ▼
        run_entrenamientoBuy() / run_entraminetoSell()
                      │
                      ▼
        Genera modelo_buyv01.pkl / modelo_sellv01.pkl
                      │
                      └──────► Próximo ciclo usa el modelo ◄──┘
Archivos Clave Modificados
Archivo	Cambio
Class_DashBot.py	readCSV_buy/sell(filtrar=False), envío sin modelo
Class_SystemStatus.py	Monitor muestra oportunidades sin modelo
Class_IA_modelos.py	ModeloOportunidadesBuy completo
Estado Actual
Sin modelo: Oportunidades van a BD y Telegram con origen="system"
Con modelo: Oportunidades filtradas por IA van con origen="ia"
Monitor: Muestra todas las oportunidades aunque no haya modelo (con "Sin IA")