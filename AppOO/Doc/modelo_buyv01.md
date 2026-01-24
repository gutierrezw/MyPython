# Modelo IA: Oportunidades de Compra (Buy)

## Identificación
- **Nombre**: modelo_buyv01
- **Tipo**: RandomForestClassifier
- **Versión**: 1.0

## Objetivo
Identificar oportunidades de compra de activos basándose en indicadores de depresión de precio, métricas de valor y rendimiento por dividendos. El modelo clasifica si un activo debe ser comprado o esperar.

## Etiquetas de Clasificación
| Etiqueta | Significado | Recomendado |
|----------|-------------|-------------|
| `buy` | Comprar el activo | 1 |
| `wait` | Esperar mejor momento | -1 |

## Clasificación por Umbrales
| Clasificación | Condición | Acción |
|---------------|-----------|--------|
| `buy` | confianza >= umbral_buy | Recomendar compra |
| `observacion` | confianza >= umbral_observacion | Monitorear |
| `descartar` | confianza < umbral_observacion | No mostrar |

## Features Utilizadas

### Features Escalares (Principales)
- `ganancia_precio`: Diferencia porcentual entre precio actual y precio objetivo
- `ganancia_inversion`: Ganancia potencial basada en inversión
- `dividend_yield`: Rendimiento por dividendo (%)
- `score`: Score de rebalanceo calculado

### Datos del Activo
- `Symbol`: Símbolo del activo
- `account`: Cuenta de inversión
- `vehiculo`: Tipo de vehículo (Stock, ETF, Crypto, etc.)
- `tipo`: Clasificación del activo

### Métricas de Posición
- `last`: Último precio
- `avgcost`: Costo promedio actual
- `cantidad_buy`: Cantidad sugerida a comprar
- `cantidad_post`: Cantidad después de compra
- `avgcost_post`: Costo promedio proyectado post-compra
- `retorno_post`: Retorno proyectado post-compra

### Métricas de Dividendos
- `ex_dividend_date`: Fecha ex-dividendo
- `pre_dividendos`: Dividendos antes de compra
- `post_dividendos`: Dividendos proyectados post-compra

### Métricas de Costo Base
- `pre_costobase`: Costo base antes de compra
- `post_costobase`: Costo base proyectado post-compra
- `objetivo`: Precio objetivo

### Datos Técnicos (JSON)
- `Datostecnicos`: Indicadores técnicos serializados

## Parámetros del Modelo

```json
{
  "n_estimators": 100,
  "max_depth": 10,
  "min_samples_split": 5,
  "random_state": 42,
  "n_folds": 5,
  "test_size": 0.3,
  "umbral_buy": 0.65,
  "umbral_observacion": 0.35
}
```

## Criterios de Compra
- Precio significativamente por debajo del objetivo (`ganancia_precio` alto)
- RSI bajo (< 40) indica sobreventa
- Dividend yield atractivo
- Score de rebalanceo positivo
- Proximidad a mínimos históricos

## Fuente de Datos
- CSV: `csv_datosIA_buy.csv`
- Tabla BD: `bdinv.oportunidades` (tipo='buy')

## Estructura del CSV de Entrenamiento
| Campo | Descripción |
|-------|-------------|
| Symbol | Símbolo del activo |
| account | Cuenta de inversión |
| vehiculo | Tipo de vehículo |
| tipo | Clasificación |
| score | Score calculado |
| monto_sugerido | Monto a invertir |
| ganancia_precio | % ganancia por precio |
| ganancia_inversion | Ganancia por inversión |
| cantidad_buy | Cantidad a comprar |
| last | Precio actual |
| avgcost | Costo promedio |
| cantidad_post | Cantidad post-compra |
| avgcost_post | Costo promedio post |
| retorno_post | Retorno proyectado |
| objetivo | Precio objetivo |
| dividend_yield | Rendimiento dividendo |
| ex_dividend_date | Fecha ex-dividendo |
| pre_dividendos | Dividendos actuales |
| post_dividendos | Dividendos proyectados |
| pre_costobase | Costo base actual |
| post_costobase | Costo base proyectado |
| Datostecnicos | JSON con técnicos |
| Fecha | Fecha del registro |
| Recomendado | Etiqueta (1=buy, -1=wait) |
| Comentarios | Notas adicionales |

## Notas de Uso
1. El modelo debe reentrenarse periódicamente con nuevos datos etiquetados
2. Los umbrales pueden ajustarse según tolerancia al riesgo
3. Priorizar activos con alto dividend_yield para estrategias de ingreso
4. Usar en conjunto con análisis fundamental para mejores resultados
5. Considerar el score de rebalanceo para mantener diversificación

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