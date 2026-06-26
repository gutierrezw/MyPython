# Documentación: Class_IA_modelos.py

## Descripción General
Módulo que implementa modelos de Machine Learning (RandomForestClassifier) para identificar oportunidades de inversión. Contiene dos clases principales:
- `ModeloOportunidadesSell`: Detecta oportunidades de venta
- `ModeloOportunidadesBuy`: Detecta oportunidades de compra

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    Class_IA_modelos.py                          │
├─────────────────────────────────────────────────────────────────┤
│  DEFAULT_PARAMS_SELL          DEFAULT_PARAMS_BUY                │
│         │                            │                          │
│         ▼                            ▼                          │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │ModeloOportunida- │      │ModeloOportunida- │                │
│  │   desSell        │      │   desBuy         │                │
│  ├──────────────────┤      ├──────────────────┤                │
│  │ - modelo         │      │ - modelo         │                │
│  │ - metrics        │      │ - metrics        │                │
│  │ - params         │      │ - params         │                │
│  │ - ReOportunidades│      │ - ReOportunidades│                │
│  └──────────────────┘      └──────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parámetros por Defecto

### DEFAULT_PARAMS_SELL
```python
{
    "n_estimators": 100,        # Número de árboles en el bosque
    "max_depth": 10,            # Profundidad máxima de cada árbol
    "min_samples_split": 5,     # Mínimo de muestras para dividir nodo
    "random_state": 42,         # Semilla para reproducibilidad
    "n_folds": 5,               # Folds para validación cruzada
    "test_size": 0.3,           # Proporción de datos para test
    "umbral_sell": 0.65,        # Confianza mínima para recomendar venta
    "umbral_observacion": 0.35  # Por debajo se descarta
}
```

### DEFAULT_PARAMS_BUY
```python
{
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "random_state": 42,
    "n_folds": 5,
    "test_size": 0.3,
    "umbral_buy": 0.65,         # Confianza mínima para recomendar compra
    "umbral_observacion": 0.35
}
```

---

## Clase: ModeloOportunidadesSell

### Propósito
Identificar activos que deben venderse basándose en indicadores técnicos y métricas de rentabilidad.

### Atributos
| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `modelo` | RandomForestClassifier | Modelo entrenado |
| `metrics` | dict | Métricas de rendimiento |
| `modelo_name` | str | "modelo_sellv01" |
| `params` | dict | Parámetros de configuración |
| `ReOportunidades` | RepositorioOportunidadesBuySell | Acceso a BD |

### Métodos

#### `__init__(self)`
Inicializa el modelo, carga parámetros desde BD si existen.

#### `_cargar_params_bd(self)`
Carga parámetros personalizados desde tabla `modelos_ia`.

#### `convertir_dataset_entrenamiento(self, datos) -> pd.DataFrame`
Convierte datos de BD a DataFrame para entrenamiento.
- Extrae `indicadores`, `profit`, `roi` del campo `json_detalle`
- Elimina columnas innecesarias (id, tipo, timestamp, etc.)

#### `aplanar_datos_tecnicos(self, df) -> pd.DataFrame`
Extrae indicadores de la columna `datos_tecnicos` creando columnas individuales:
- Por timeframe: `_d` (diario), `_w` (semanal), `_m` (mensual)
- Indicadores: RSI, MACD, Close, EMAs, Fibonacci, Máximos/Mínimos

#### `cargar_datos(self, df, usar_timeframes=["d"], umbral_columnas=0.5) -> (X, y)`
Prepara features y etiquetas para entrenamiento.
- Filtra columnas con demasiados NaN
- Genera etiquetas: `sell` (1) o `hold` (-1)

#### `entrenar_modelo(self, df)`
Entrena usando validación cruzada estratificada (StratifiedKFold).
- Calcula métricas: accuracy, precision, recall, F1, ROC-AUC
- Usa `class_weight="balanced"` para clases desbalanceadas

#### `metricas_de_clases(self, X, y, y_test, X_test)`
Calcula métricas adicionales en conjunto de test.

#### `calcular_feature_importance(self)`
Extrae importancia de las top 10 features.

#### `predecir_modelo(self, df) -> pd.DataFrame`
Realiza predicciones y clasifica:
- `sell`: confianza >= umbral_sell
- `observacion`: confianza >= umbral_observacion
- `descartar`: confianza < umbral_observacion

#### `save_modelo(self, file="modelo_ia")`
Guarda modelo y métricas como `.pkl` usando `define_FileCache`.

#### `load_modelo(self, file="modelo_ia")`
Carga modelo y métricas desde archivos `.pkl`.

#### `run_entraminetoSell(self)`
Ejecuta pipeline completo de entrenamiento para Sell.

---

## Clase: ModeloOportunidadesBuy

### Propósito
Identificar activos con precio deprimido que representan oportunidades de compra.

### Atributos
| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `modelo` | RandomForestClassifier | Modelo entrenado |
| `metrics` | dict | Métricas de rendimiento |
| `modelo_name` | str | "modelo_buyv01" |
| `params` | dict | Parámetros de configuración |
| `ReOportunidades` | RepositorioOportunidadesBuySell | Acceso a BD |

### Métodos
Misma estructura que `ModeloOportunidadesSell` con diferencias en:

#### `convertir_dataset_entrenamiento(self, datos)`
Extrae campos específicos de Buy:
- `ganancia_precio`: % diferencia entre precio actual y objetivo
- `ganancia_inversion`: Ganancia potencial
- `dividend_yield`: Rendimiento por dividendo
- `score`: Score de rebalanceo

#### `cargar_datos(self, df, usar_timeframes=["d"], umbral_columnas=0.5)`
Features específicas para Buy:
```python
scalar_features = ["ganancia_precio", "ganancia_inversion", "dividend_yield", "score"]
```
Etiquetas: `buy` (1) o `wait` (-1)

#### `predecir_modelo(self, df)`
Clasifica usando umbrales:
- `buy`: confianza >= umbral_buy
- `observacion`: confianza >= umbral_observacion
- `descartar`: confianza < umbral_observacion

#### `run_entrenamientoBuy(self)`
Ejecuta pipeline completo de entrenamiento para Buy.

---

## Features Utilizadas

### Indicadores Técnicos (por timeframe)
| Feature | Descripción | Sufijos |
|---------|-------------|---------|
| `rsi` | Relative Strength Index (0-100) | `_d`, `_w`, `_m` |
| `macd` | Moving Average Convergence Divergence | `_d`, `_w`, `_m` |
| `Close` | Precio de cierre | `_d`, `_w`, `_m` |

### EMAs (Medias Móviles Exponenciales)
| EMAs Largos | EMAs Cortos |
|-------------|-------------|
| EMA020 | EMA009 |
| EMA050 | EMA021 |
| EMA100 | EMA055 |
| EMA200 | EMA144 |

### Otros Indicadores
| Feature | Descripción |
|---------|-------------|
| `fibo_longico` | Nivel de retroceso Fibonacci |
| `13_semanas_max/min` | Máx/Mín últimas 13 semanas (diario) |
| `26_semanas_max/min` | Máx/Mín últimas 26 semanas (semanal) |
| `52_semanas_max/min` | Máx/Mín últimas 52 semanas (mensual) |

### Features Escalares (Solo Buy)
| Feature | Descripción |
|---------|-------------|
| `ganancia_precio` | % diferencia precio actual vs objetivo |
| `ganancia_inversion` | Ganancia potencial de inversión |
| `dividend_yield` | Rendimiento por dividendo |
| `score` | Score de rebalanceo calculado |

### Features Escalares (Solo Sell)
| Feature | Descripción |
|---------|-------------|
| `roi` | Retorno sobre inversión (%) |
| `profit` | Ganancia/Pérdida actual |

---

## Métricas Almacenadas

```python
metrics = {
    # Validación Cruzada
    "precision": float,      # Media de precisión
    "precision_std": float,  # Desviación estándar
    "recall": float,
    "recall_std": float,
    "f1_score": float,
    "f1_std": float,
    "accuracy": float,
    "accuracy_std": float,
    "roc_auc": float,
    "roc_auc_std": float,

    # Información del Dataset
    "n_folds": int,
    "n_samples": int,
    "n_aprobadas": int,      # sell/buy
    "n_rechazadas": int,     # hold/wait
    "balance_ratio": float,

    # Parámetros Usados
    "params": dict,

    # Métricas de Test
    "test_precision": float,
    "test_recall": float,
    "test_f1": float,
    "test_accuracy": float,
    "f1_macro": float,
    "test_roc_auc": float,

    # Feature Importance
    "feature_importance": [
        {"feature": str, "importance": float},
        ...
    ]
}
```

---

## Ciclo de Entrenamiento

```
┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE ENTRENAMIENTO                       │
└─────────────────────────────────────────────────────────────────┘

    BD: tabla oportunidades (tipo='buy' o 'sell')
                          │
                          ▼
         RepositorioOportunidadesBuySell.obtener_por_tipo()
                          │
                          ▼
         convertir_dataset_entrenamiento()
                          │
                          ▼
         aplanar_datos_tecnicos()
                          │
                          ▼
         ┌─────────────────────────────────────────┐
         │           entrenar_modelo()             │
         ├─────────────────────────────────────────┤
         │  1. cargar_datos() → X, y               │
         │  2. StratifiedKFold (5 folds)           │
         │  3. cross_val_score (métricas)          │
         │  4. train_test_split (70/30)            │
         │  5. RandomForestClassifier.fit()        │
         │  6. metricas_de_clases()                │
         │  7. calcular_feature_importance()       │
         └─────────────────────────────────────────┘
                          │
                          ▼
         save_modelo() → modelo_*.pkl + metrics.pkl
```

---

## Ciclo de Predicción

```
    Nuevos datos (DataFrame)
              │
              ▼
    load_modelo() ← modelo_*.pkl
              │
              ▼
    predecir_modelo()
              │
              ├── predict() → etiqueta
              └── predict_proba() → confianza
              │
              ▼
    Clasificación por umbral:
    ┌─────────────────────────────────────┐
    │ confianza >= 0.65 → sell/buy        │
    │ confianza >= 0.35 → observacion     │
    │ confianza <  0.35 → descartar       │
    └─────────────────────────────────────┘
```

---

## Archivos Generados

| Archivo | Descripción |
|---------|-------------|
| `modelo_sellv01.pkl` | Modelo RandomForest para Sell |
| `modelo_sellv01_metrics.pkl` | Métricas del modelo Sell |
| `modelo_buyv01.pkl` | Modelo RandomForest para Buy |
| `modelo_buyv01_metrics.pkl` | Métricas del modelo Buy |

Ubicación: Directorio definido por `define_FileCache()`

---

## Dependencias

```python
import json
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    cross_val_score,
    StratifiedKFold,
    train_test_split,
)
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.metrics import (
    classification_report,
    f1_score,
    roc_auc_score,
)
from Modulos_Mysql import RepositorioOportunidadesBuySell, BDsystem
from Modulos_Utilitarios import define_FileCache
```

---

## Uso desde CLI

```python
if __name__ == "__main__":
    AiSell = ModeloOportunidadesSell()
    AiSell.run_entraminetoSell()
```

---

## Integración con Sistema

### Fuente de Datos
- Tabla BD: `bdinv.oportunidades`
- Campos: `tipo='buy'` o `tipo='sell'`
- Campo JSON: `json_detalle` contiene indicadores técnicos

### Monitor IA (Class_SystemStatus.py)
- Botón "Entrenar" ejecuta `run_entrenamientoBuy()` / `run_entraminetoSell()`
- Muestra métricas del modelo
- Permite ajustar umbrales

### Evaluación de Oportunidades
- `Class_DashBot.py`: `evaluar_oportunidades_*_con_IA()`
- Sin modelo: envía todas las oportunidades con `origen="system"`
- Con modelo: filtra por umbral y envía con `origen="ia"`

---

## Notas Técnicas

1. **Balance de Clases**: Usa `class_weight="balanced"` para manejar datasets desbalanceados
2. **Validación Cruzada**: StratifiedKFold mantiene proporción de clases en cada fold
3. **Umbrales Ajustables**: Pueden modificarse en BD tabla `modelos_ia`
4. **Timeframes**: Por defecto solo usa diario `["d"]` para reducir features
5. **NaN Handling**: Elimina columnas con más del 50% de NaN, rellena resto con 0
