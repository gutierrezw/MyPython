# Documentación: Estructura DataHub

## Descripción General
`DataHub` es una clase estática global que actúa como contenedor central de variables de entorno, configuración del sistema y datos en tiempo real de activos financieros. Funciona como un "hub" de datos compartidos entre todos los módulos de la aplicación.

**Ubicación**: `Class_customer.py`

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         DataHub                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   GRUPO 1        │  │   GRUPO 2        │  │   GRUPO 3    │  │
│  │   Colores        │  │   Monitor CPU    │  │   Trading    │  │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────┤  │
│  │ bgcolor          │  │ DCpu             │  │ MinProfit    │  │
│  │ cgcolor          │  │ DMem             │  │ Tolerancia   │  │
│  │ cchart           │  │ display          │  │ MaxRoi       │  │
│  │ colors           │  │ max_points       │  │ InicioInv    │  │
│  └──────────────────┘  │ interval         │  │ ib_gateway   │  │
│                        │ CpuLock          │  └──────────────┘  │
│                        └──────────────────┘                    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    GRUPO 4: Runtime                      │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  info{}  │  manager_buysell{}  │  rebalanceo{}          │   │
│  │  orders{}│  manager_events{}   │  procesos[]            │   │
│  │  logger{}│  manager_after{}    │  SupervisedThread[]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Grupos de Variables

### GRUPO 1: Configuración de Colores (Cargable desde BD)

```python
# Colores de interfaz
bgcolor = "#1e1e2e"      # Fondo principal
cgcolor = "#2d2d3d"      # Fondo secundario
cchart = {               # Colores para gráficos
    "fondo": bgcolor,
    "fondo_fig": cgcolor,
    "tab20": colormaps.get_cmap("tab20"),
    ...
}
colors = {
    "bgcolor": bgcolor,
    "cgcolor": cgcolor,
    "fgcolor": "white",
    "dw": 1290,          # Ancho por defecto ventana
    "dh": 700,           # Alto por defecto ventana
    "df": 1297,
    "max_dw": None,
    "max_dh": None,
    "cchart": cchart,
}
```

### GRUPO 2: Monitoreo de CPU y Memoria (Cargable desde BD)

| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `DCpu` | list | [] | Historial de uso de CPU |
| `DMem` | list | [] | Historial de uso de memoria |
| `display` | any | None | Configuración de display |
| `max_points` | int | 40 | Puntos máximos en gráfico |
| `interval` | int | 1 | Intervalo de muestreo (seg) |
| `CpuLock` | any | None | Lock para CPU |

### GRUPO 3: Parámetros de Trading (Cargable desde BD)

| Variable | Tipo | Default | Descripción |
|----------|------|---------|-------------|
| `MinProfit` | float | 50 | Profit mínimo para Sell ($) |
| `Toleranciasell` | float | 0.10 | Tolerancia para venta (10%) |
| `MaxRoi` | float | 0.09 | ROI máximo objetivo (9%) |
| `MinGananciaPrecio` | float | 0.05 | Ganancia mínima precio Buy (5%) |
| `MinScoreBuy` | float | 0.5 | Score mínimo para Buy |
| `InicioInversior` | date | - | Fecha inicio de inversión |
| `ib_gateway_host` | str | - | Host de Interactive Brokers |
| `ib_gateway_port` | int | - | Puerto de Interactive Brokers |

### GRUPO 4: Estructuras Runtime (NO configurables)

```python
# Sesiones y managers
SessionYfinance = None                    # Sesión yfinance
QremoteOrder = {                          # Colas de órdenes remotas
    "Stock": OrderManagerSync(),
    "Crypto": OrderManagerSync()
}
manager_events = {}                       # Eventos del sistema
manager_after = {}                        # Tareas programadas
manager_buysell = {}                      # Datos de compra/venta
rebalanceo = {}                           # Datos de rebalanceo
procesos = []                             # Lista de procesos activos
logger = {}                               # Loggers del sistema
orders = {}                               # Órdenes activas

# Diccionario principal de datos de activos
info = {
    "TimeDataHub": "2025-01-24 10:30:00",  # Timestamp de inicio
    # ... datos de cada símbolo
}
```

---

## Estructura de DataHub.info

### Descripción
`DataHub.info` es el diccionario central que almacena información en tiempo real de todos los activos monitoreados.

### Estructura General

```python
DataHub.info = {
    "TimeDataHub": "2025-01-24 10:30:00",  # Timestamp de creación

    "AAPL": {                               # Por cada símbolo
        "conid": 12345,                     # ID del contrato
        "account": "U1234567",              # Cuenta
        "vehiculo": "Stock",                # Tipo de vehículo
        "websocket": {...},                 # Datos de precio en tiempo real
        "sector": "Technology",             # Sector del activo
        "region": "United States",          # País/Región
        "country": "United States",         # País (para rebalanceo)
        "asset_type": "Acciones",           # Tipo de activo
        "costobase": 15000.00,              # Costo base total
        "update": True,                     # Flag de actualización
        "sell": {...},                      # Datos de oportunidad de venta
        "buy": {...},                       # Datos de oportunidad de compra
        "dividends": {...},                 # Datos de dividendos
    },

    "BTCUSDT": {
        "conid": 67890,
        "account": "binance_main",
        "vehiculo": "Crypto",
        "websocket": {...},
        ...
    }
}
```

### Estructura websocket (Precio en tiempo real)

```python
"websocket": {
    "last": 185.50,           # Último precio
    "open": 183.20,           # Precio de apertura
    "ask": 185.55,            # Precio de venta
    "bid": 185.45,            # Precio de compra
    "high": 186.00,           # Máximo del día
    "low": 182.80,            # Mínimo del día
    "timestamp": "2025-01-24 10:30:15",  # Hora de actualización
}
```

### Estructura sell (Oportunidad de venta)

```python
"sell": {
    "roi": 0.15,              # Retorno sobre inversión (15%)
    "profit": 2500.00,        # Ganancia en $
    "Nro_lotes": 3,           # Número de lotes a vender
    "cantidad_sell": 30,      # Cantidad a vender
    "price_market": 185.50,   # Precio de mercado
    "costo_acumulado": 15000, # Costo acumulado
    "costo_base": 14500,      # Costo base
    "position": 100,          # Posición total
    "Disponible": 70,         # Disponible después de venta
    "Pos_AvgCost": 145.00,    # Costo promedio
    "Pos_Position": 100,      # Posición actual
    "Pos_CostBase": 14500,    # Costo base posición
    "indicadores": {...},     # Indicadores técnicos
}
```

### Estructura buy (Oportunidad de compra)

```python
"buy": {
    "score": 0.85,            # Score de rebalanceo
    "monto_sugerido": 5000,   # Monto sugerido a invertir
    "ganancia_precio": 0.12,  # Ganancia potencial por precio (12%)
    "ganancia_inversion": 600,# Ganancia potencial en $
    "cantidad_buy": 27,       # Cantidad a comprar
    "last": 185.50,           # Último precio
    "avgcost": 145.00,        # Costo promedio actual
    "cantidad_post": 127,     # Cantidad después de compra
    "avgcost_post": 153.50,   # Costo promedio post-compra
    "retorno_post": 0.21,     # Retorno proyectado post-compra
    "objetivo": 210.00,       # Precio objetivo
    "dividend_yield": 0.025,  # Rendimiento por dividendo
    "ex_dividend_date": "2025-02-15",  # Fecha ex-dividendo
    "pre_dividendos": 250,    # Dividendos antes de compra
    "post_dividendos": 320,   # Dividendos proyectados
    "indicadores": {...},     # Indicadores técnicos
}
```

### Estructura dividends

```python
"dividends": {
    "ex_dividend_date": "2025-02-15",
    "dividend_yield": 0.025,
    "dividend_rate": 0.96,    # Dividendo por acción anual
    "payout_ratio": 0.25,     # Ratio de pago
    "last_dividend": 0.24,    # Último dividendo pagado
}
```

---

## Métodos Principales

### load_from_database()
```python
@staticmethod
def load_from_database() -> bool:
    """
    Carga las variables de entorno desde la sesión DataHub en la BD.

    Grupos cargados:
    1. Colores (bgcolor, cgcolor, cchart)
    2. Monitor CPU/Memoria (display, max_points, interval, CpuLock)
    3. Parámetros de Trading (MinProfit, Toleranciasell, MaxRoi, etc.)

    Returns:
        bool: True si cargó exitosamente, False si hubo error
    """
```

### update_self_procesos()
```python
def update_self_procesos(proces=None, tarea=None, itera=0):
    """
    Actualiza o consulta el contador de iteraciones de procesos.

    Args:
        proces: Nombre del proceso
        tarea: Nombre de la tarea
        itera: Número de iteración (0 = consultar, >0 = actualizar)

    Returns:
        int: Valor actual si itera=0, None si actualiza
    """
```

### csv_OptionSales_write()
```python
def csv_OptionSales_write() -> None:
    """
    Genera CSV con oportunidades de venta para modelo IA.
    Archivo: csv_datosIA_sell.csv
    """
```

### csv_OptionBuy_write()
```python
def csv_OptionBuy_write() -> None:
    """
    Genera CSV con oportunidades de compra para modelo IA.
    Archivo: csv_datosIA_buy.csv
    """
```

---

## Estructuras de CSV para IA

### ColumnCsvSell (Columnas para venta)
```python
ColumnCsvSell = [
    "Symbol", "account", "vehiculo", "Opcion", "Profit",
    "NroLotes", "CantidadSell", "PriceMarket", "Fecha",
    "CostoCum", "%Roi", "CostoBase", "Position", "Disponible",
    "PosAvgCost", "PosPosition", "PosCostobase", "Datostecnicos",
    "Recomendado", "Comentarios"
]
```

### ColumnCsvBuy (Columnas para compra)
```python
ColumnCsvBuy = [
    "Symbol", "account", "vehiculo", "tipo", "score",
    "monto_sugerido", "pinvertir", "ganancia_precio",
    "ganancia_inversion", "cantidad_buy", "last", "avgcost",
    "cantidad_post", "avgcost_post", "retorno_post", "objetivo",
    "dividend_yield", "ex_dividend_date", "pre_dividendos",
    "post_dividendos", "pre_costobase", "post_costobase",
    "Datostecnicos", "Fecha", "Recomendado", "Comentarios"
]
```

---

## Flujo de Actualización de DataHub.info

```
┌─────────────────────────────────────────────────────────────────┐
│                FLUJO DE ACTUALIZACIÓN DataHub.info              │
└─────────────────────────────────────────────────────────────────┘

    WebSocket Streams (Binance/IBKR)
              │
              ▼
    ┌───────────────────────┐
    │ on_message_binance_   │
    │ websocket()           │
    │ on_message_ibkr()     │
    └───────────┬───────────┘
                │
                ▼
    ┌───────────────────────┐
    │ with DataHub.lockInfo │  ← Thread-safe
    └───────────┬───────────┘
                │
     ┌──────────┴──────────┐
     │                     │
     ▼ Símbolo existe      ▼ Símbolo nuevo
┌─────────────────┐  ┌─────────────────┐
│ info[symbol]    │  │ info[symbol] =  │
│   .update({     │  │   {             │
│     websocket,  │  │     conid,      │
│     conid,      │  │     account,    │
│     account,    │  │     vehiculo,   │
│     vehiculo    │  │     websocket   │
│   })            │  │   }             │
└─────────────────┘  └─────────────────┘
         │                    │
         └────────┬───────────┘
                  │
                  ▼
    ┌───────────────────────┐
    │ Actualizar metadata:  │
    │ - sector              │
    │ - region/country      │
    │ - asset_type          │
    │ - costobase           │
    └───────────────────────┘
                  │
                  ▼
    ┌───────────────────────┐
    │ Actualizar signals:   │
    │ - sell (si aplica)    │
    │ - buy (si aplica)     │
    │ - dividends           │
    └───────────────────────┘
```

---

## Monitor DataHub (Class_SystemStatus.py)

### Pestaña DataHub en Monitor del Sistema

Visualiza el contenido de `DataHub.info` con:

| Panel | Contenido |
|-------|-----------|
| Lista (izquierda) | Símbolos organizados por timestamp |
| Detalle (derecha) | Información completa del símbolo seleccionado |

### Secciones en Detalle

| Sección | Icono | Descripción |
|---------|-------|-------------|
| websocket | 📂 | Precios en tiempo real |
| market | 📂 | Datos de mercado |
| position | 📂 | Posición actual |
| sell | 📂 | Oportunidad de venta |
| buy | 📂 | Oportunidad de compra |
| dividends | 📂 | Información de dividendos |

### Auto-refresh
- Actualiza cada 30 segundos
- Muestra timestamp de última actualización

---

## Sincronización y Locks

```python
# Lock para acceso thread-safe a info
lockInfo = threading.Lock()

# Lock para escritura de CSV
lockCsvAi = threading.Lock()

# Lista de threads supervisados
SupervisedThread = []
```

### Uso de lockInfo
```python
with DataHub.lockInfo:
    DataHub.info[symbol].update({
        "websocket": precio_data,
        "conid": conid,
    })
```

---

## Fechas y Procesos Batch

```python
# Fechas de referencia
now = datetime.now()
mrk_anterior = get_ultimo_dia_mercado(market="Stock")
dia_anterior = get_ultimo_dia_mercado(market="Crypto")
mrv_anterior = get_ultimo_dia_mercado(market="BBVA.ARS")
mrv_safeday = mrv_anterior - timedelta(days=1)

# Control de procesos
wait_3m = now + timedelta(minutes=3)
last_process = {
    "Stock": {
        "diaria_book_performance": mrk_anterior,
        "wait": wait_3m
    },
    "Crypto": {
        "diaria_book_performance": dia_anterior,
        "wait": wait_3m
    },
    "BBVA.ARS": {
        "diaria_book_performance": mrv_safeday,
        "wait": wait_3m
    },
    "graph_performace_portafolio": False,
    "dividends_en_market_stock": now,
}
```

---

## Parámetros de Mensajería

```python
max_mensajes = 5              # Máximo mensajes en cola
min_tiempo = 300              # Segundos entre mensajes Sell (5 min)
min_tiempo_buy = 300          # Segundos entre mensajes Buy (5 min)
```

---

## Acceso a BD

```python
# Repositorio de oportunidades
RepositorioOportunidades = RepositorioOportunidadesBuySell()
```

---

## Carga desde Base de Datos

### Fuente de Configuración
```python
session_data = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")
envs_config = json.loads(session_data["userapi"].decode("utf-8"))
```

### Estructura JSON en BD (userapi)
```json
{
    "bgcolor": "DarkCyan",
    "cgcolor": "black",
    "cchart": {
        "texto":    "white",
        "titulo":   "cyan",
        "fondo":    "DarkCyan",
        "fondo_fig":"black",
        "asx":      "black",
        "asy":      "black",
        "axsy":     "grey",
        "axsx":     "grey",
        "2eje":     "orange",
        "plot0":    "white",
        "plot1":    "green",
        "plot11":   "GreenYellow",
        "plot2":    "orange",
        "plot21":   "DarkOrange",
        "plot3":    "red",
        "plot31":   "OrangeRed",
        "plot4":    "yellow",
        "plot41":   "Gold",
        "plot5":    "DodgerBlue",
        "plot6":    "skyblue",
        "plot7":    "grey",
        "plot8":    "black",
        "plot9":    "blue"
    },
    "display": null,
    "max_points": 40,
    "interval": 1,
    "CpuLock": null,
    "MinProfit": 80.0,
    "Toleranciasell": 0.10,
    "MaxRoi": 0.09,
    "InicioInversior": "2020-07-31",
    "ib_gateway_host": "https://localhost",
    "ib_gateway_port": "5501"
}
```

---

## Métodos de Sesión BD (BDsystem)

Métodos en `Modulos_Mysql.py` usados para leer/escribir la configuración de DataHub y sesiones de vehículos.

### Lectura
```python
# Obtener sesión completa por vehículo
sesion = BDsystem.get_sesion_by_vehiculo("Stock")
sesion = BDsystem.get_sesion_by_vehiculo("Crypto")
sesion = BDsystem.get_sesion_by_vehiculo("DataHub")   # ← config de DataHub

# Campos retornados
sesion["idcuenta"]    # cuenta
sesion["userapi"]     # BLOB con JSON de config (para DataHub)
sesion["userpass"]    # credencial
sesion["environment"] # PROD / TESTNET
sesion["xstrategy"]   # estrategia activa
```

### Escritura
```python
# Actualizar fecha de sesión y orden de cartera
BDsystem.update_sesion_fecha_orden(vehiculo, fesesion, orcartera)

# Actualizar fecha fundamental
BDsystem.update_sesion_fecha_fund(vehiculo, fecha_fund)

# Actualizar estrategia de trading
BDsystem.update_sesion_strategy(vehiculo, xstrategy)
```

> Estos métodos reemplazaron a `select_sesion()` (eliminado dic-2025).
> Usan SQL parametrizado — sin riesgo de inyección.

---

## Integración con Otros Módulos

| Módulo | Uso de DataHub |
|--------|----------------|
| `DashMainV9_ia.py` | Actualiza `info` con precios y signals |
| `Class_SystemStatus.py` | Visualiza `info` en monitor |
| `Class_DataFrame.py` | Usa colores para gráficos |
| `Class_IA_modelos.py` | Lee datos para entrenamiento |
| `rebalance_engine.py` | Lee metadata de activos |

---

## Notas Técnicas

1. **Clase Estática**: DataHub es una clase sin instanciación, todas las variables son de clase
2. **Thread-Safe**: Usar `lockInfo` para modificar `DataHub.info`
3. **Persistencia**: Configuración se guarda en BD, datos runtime son volátiles
4. **Lazy Loading**: `info` se puebla dinámicamente al recibir datos
5. **Timestamp**: `TimeDataHub` marca el inicio de la sesión

---

## Troubleshooting

### Símbolo no aparece en info
```python
# Verificar si el símbolo existe
if symbol in DataHub.info:
    data = DataHub.info[symbol]
else:
    print(f"Símbolo {symbol} no encontrado en DataHub.info")
```

### Datos desactualizados
```python
# Verificar timestamp del websocket
if "websocket" in DataHub.info[symbol]:
    ts = DataHub.info[symbol]["websocket"]["timestamp"]
    print(f"Última actualización: {ts}")
```

### Error de concurrencia
```python
# Siempre usar lock para modificar
with DataHub.lockInfo:
    DataHub.info[symbol]["websocket"] = new_data
```
