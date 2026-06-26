# Documentación: Sistema de Cache (CacheHut)

## Descripción General
Sistema de caché en memoria para almacenar DataFrames y datos de mercado financiero. Utiliza `TTLCache` de la librería `cachetools` para gestionar automáticamente la expiración de datos.

**Ubicación**: `Class_DataFrame.py`

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                     Sistema de Cache                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐      ┌─────────────────────────────┐      │
│  │ DataFrameCache  │      │   @use_dataframe_cache      │      │
│  │    (Clase)      │◄─────│      (Decorador)            │      │
│  ├─────────────────┤      └─────────────────────────────┘      │
│  │ - cache         │                   │                       │
│  │ - GetCounter    │                   ▼                       │
│  │ - logger        │      ┌─────────────────────────────┐      │
│  └─────────────────┘      │     get_yfinance()          │      │
│          │                │     (Función decorada)      │      │
│          ▼                └─────────────────────────────┘      │
│  ┌─────────────────┐                                           │
│  │    CacheHut     │  ← Instancia global                       │
│  │ (maxsize=200)   │                                           │
│  │ (ttl=1800s)     │                                           │
│  └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Clase: DataFrameCache

### Constructor

```python
class DataFrameCache:
    def __init__(self, maxsize=200, ttl=3600):
        """
        maxsize: cantidad máxima de elementos en caché
        ttl: tiempo de vida (en segundos)
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.GetCounter = 0
        self.logger = logging.getLogger("DataFrameCache")
```

### Atributos

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `cache` | TTLCache | Diccionario con TTL automático |
| `GetCounter` | int | Contador de accesos (lecturas) |
| `logger` | Logger | Logger para mensajes de cache |

### Métodos

| Método | Parámetros | Retorno | Descripción |
|--------|------------|---------|-------------|
| `get(key)` | key: any | value \| None | Obtiene valor, incrementa contador |
| `set(key, value)` | key, value | None | Almacena valor en cache |
| `keys()` | - | list | Lista de claves actuales |
| `clear()` | - | None | Limpia todo el cache |
| `has(key)` | key: any | bool | Verifica si existe la clave |
| `remove(key)` | key: any | None | Elimina una clave específica |

---

## Instancia Global: CacheHut

```python
CacheHut = DataFrameCache(maxsize=200, ttl=1800)
```

### Configuración

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `maxsize` | 200 | Máximo 200 elementos en memoria |
| `ttl` | 1800 | 30 minutos de vida útil por elemento |

---

## Decorador: @use_dataframe_cache

### Propósito
Automatiza el cacheo de funciones que retornan DataFrames o datos de mercado.

### Funcionamiento

```python
@use_dataframe_cache(CacheHut)
def get_yfinance(ticket, vehiculo, period, interval, desde, hasta):
    ...
```

### Generación de Claves
La clave se genera automáticamente a partir de:
```python
key = (func.__name__, args, tuple(sorted(kwargs.items())))
```

**Ejemplo de clave:**
```python
('get_yfinance', ('AAPL', 'Stock', '5y', '1d', None, None), ())
```

### Parámetro especial: `use_cache`
```python
# Usar cache (por defecto)
get_yfinance("AAPL", vehiculo="Stock")

# Forzar descarga fresca (sin usar cache)
get_yfinance("AAPL", vehiculo="Stock", use_cache=False)
```

---

## Tipos de Datos Almacenados

### 1. Datos de Acciones (Stock)

```python
# Clave: ('get_yfinance', ('AAPL', 'Stock', '5y', '1d', None, None), ())
# Valor: (dict, pd.DataFrame)

activo = {
    "shortName": "Apple Inc.",
    "country": "United States",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "marketCap": 3000000000000,
    "dividendYield": 0.005,
    "fiftyTwoWeekLow": 150.0,
    "fiftyTwoWeekHigh": 200.0,
    ...
}

pdatos = pd.DataFrame({
    "Open": [...],
    "High": [...],
    "Low": [...],
    "Close": [...],
    "Volume": [...],
    "Dividends": [...],
    "Stock Splits": [...]
})
# Index: DatetimeIndex (fechas)
```

### 2. Datos de Criptomonedas (Crypto)

```python
# Clave: ('get_yfinance', ('BTCUSDT', 'Crypto', '5y', '1d', None, None), ())
# Valor: (dict, pd.DataFrame)

# activo: info desde yfinance (BTC-USD)
# pdatos: klines desde Binance API
pdatos = pd.DataFrame({
    "Open": [...],
    "High": [...],
    "Low": [...],
    "Close": [...],
    "Volume": [...]
})
```

### 3. Solo Info (info())

```python
# Clave: ('get_yfinance', ('AAPL', 'info()', ...), ())
# Valor: dict

activo = {
    "shortName": "Apple Inc.",
    "country": "United States",
    ...
}
```

### 4. Dividendos (Dividends)

```python
# Clave: ('get_yfinance', ('AAPL', 'Dividends', ...), ())
# Valor: (yf.Ticker, pd.DataFrame)

pdatos = pd.DataFrame({
    "Open": [...],
    "High": [...],
    "Low": [...],
    "Close": [...],
    "Volume": [...],
    "Dividends": [...]  # Columna adicional con dividendos
})
```

---

## Flujo de Cache

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO DE CACHE                               │
└─────────────────────────────────────────────────────────────────┘

    Llamada a get_yfinance("AAPL", vehiculo="Stock")
                          │
                          ▼
              ┌───────────────────────┐
              │ Genera clave única    │
              │ key = (func, args,    │
              │        kwargs)        │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ ¿use_cache == True?   │
              └───────────┬───────────┘
                          │
           ┌──────────────┴──────────────┐
           │ SÍ                          │ NO
           ▼                             ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ ¿Existe en      │          │ Ejecuta función │
    │ cache?          │          │ (descarga)      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
      ┌──────┴──────┐                     │
      │ SÍ          │ NO                  │
      ▼             ▼                     │
┌───────────┐ ┌───────────────┐           │
│ Retorna   │ │ Ejecuta       │           │
│ de cache  │ │ función       │           │
│ (HIT)     │ │ (MISS)        │           │
└───────────┘ └───────┬───────┘           │
                      │                   │
                      ▼                   │
              ┌───────────────┐           │
              │ Guarda en     │           │
              │ cache         │           │
              └───────┬───────┘           │
                      │                   │
                      └───────────────────┘
                              │
                              ▼
                      ┌───────────────┐
                      │ Retorna       │
                      │ resultado     │
                      └───────────────┘
```

---

## Comportamiento TTL

```
┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA TTL                            │
└─────────────────────────────────────────────────────────────────┘

    t=0min      t=15min     t=30min     t=31min
       │           │           │           │
       ▼           ▼           ▼           ▼
    ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
    │SET   │   │GET   │   │GET   │   │GET   │
    │AAPL  │   │AAPL  │   │AAPL  │   │AAPL  │
    └──────┘   └──────┘   └──────┘   └──────┘
       │           │           │           │
       ▼           ▼           ▼           ▼
    Creado     Cache HIT   Cache HIT   EXPIRADO
    en cache   (válido)    (límite)    → MISS
                                       → Nuevo SET
```

---

## Monitor de Cache (Class_SystemStatus.py)

### Pestaña Cache en Monitor del Sistema

Visualiza el contenido de `CacheHut.cache` con:

| Columna | Descripción |
|---------|-------------|
| Cache Keys | Nombre de la clave con icono según tipo |
| Tipo | DataFrame, dict, list, tuple, etc. |
| Tamaño | Tamaño aproximado en memoria |
| Contenido | Preview del contenido (símbolos, filas, etc.) |

### Iconos por Tipo
| Icono | Tipo |
|-------|------|
| 📊 | DataFrame |
| 📂 | dict / DotMap |
| 📋 | list / tuple |
| 📦 | Otros tipos |

### Funcionalidades
- **Refrescar**: Actualiza lista de cache
- **Eliminar**: Borra clave seleccionada
- **Auto-refresh**: Actualiza cada 30 segundos
- **Detalle**: Muestra información completa al seleccionar

---

## Uso en el Sistema

### Archivos que usan CacheHut

| Archivo | Uso |
|---------|-----|
| `Class_DataFrame.py` | Define CacheHut, decorador y get_yfinance() |
| `Class_customer.py` | Accede a datos cacheados vía lambda |
| `Class_SystemStatus.py` | Monitor y visualización del cache |
| `DashMainV9_ia.py` | Importa CacheHut para acceso global |

### Ejemplo de Acceso Indirecto

```python
# En Class_customer.py - Acceso diferido (lazy)
{
    "activos": activos,
    "datos": lambda: CacheHut.get(key_cache),  # Acceso lazy
    "lotSize": lotSize,
}
```

---

## Dependencias

```python
from cachetools import TTLCache
from functools import wraps
import logging
import pandas as pd
```

---

## Configuración Recomendada

### Para Desarrollo
```python
CacheHut = DataFrameCache(maxsize=50, ttl=600)  # 10 min, menos memoria
```

### Para Producción
```python
CacheHut = DataFrameCache(maxsize=200, ttl=1800)  # 30 min, más capacidad
```

### Para Alto Volumen
```python
CacheHut = DataFrameCache(maxsize=500, ttl=3600)  # 1 hora, máxima capacidad
```

---

## Notas Técnicas

1. **Thread Safety**: `TTLCache` NO es thread-safe por defecto. Si se usa en entornos multi-hilo, considerar `cachetools.cached` con lock.

2. **Memoria**: El tamaño reportado por `sys.getsizeof()` es aproximado para DataFrames (no incluye datos numpy subyacentes).

3. **Expiración**: Los elementos expiran por tiempo (TTL) o por capacidad máxima (LRU cuando se alcanza maxsize).

4. **Claves Inmutables**: Las claves deben ser hashables. Los args/kwargs se convierten a tuplas para esto.

5. **Logging**: El decorador registra cache misses con nivel WARNING para debugging.

---

## Métricas Disponibles

```python
# Contador de accesos
CacheHut.GetCounter  # int: número de llamadas a get()

# Elementos actuales
len(CacheHut.cache)  # int: cantidad de elementos

# Claves actuales
CacheHut.keys()  # list: todas las claves
```

---

## Troubleshooting

### Cache no funciona
```python
# Verificar que use_cache=True (default)
get_yfinance("AAPL", use_cache=True)

# Verificar que la clave existe
print(CacheHut.has(('get_yfinance', ('AAPL',), ())))
```

### Datos desactualizados
```python
# Forzar refresh
get_yfinance("AAPL", use_cache=False)

# O limpiar cache completo
CacheHut.clear()
```

### Memoria alta
```python
# Reducir maxsize
CacheHut.cache._maxsize = 100

# O limpiar cache
CacheHut.clear()
```
