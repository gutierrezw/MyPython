# Refactorización: Clase DataHub - Variables de Entorno desde Base de Datos

**Fecha:** 2026-01-04
**Archivos modificados:**
- `Class_customer.py` (DataHub class)
- `DashMainV9_ia.py` (método run)
- `DashMainV9_ia.py` (open_envs_editor)

---

## 📋 Objetivo de la Refactorización

Centralizar la gestión de variables de entorno en la clase `DataHub`, cargándolas desde la base de datos (sesión "DataHub") en lugar de tener valores hardcodeados, mejorando la mantenibilidad y permitiendo configuración dinámica.

---

## 🎯 Cambios Principales

### 1. Reorganización de la Clase DataHub

**Archivo:** `Class_customer.py:141-410`

#### Antes:
```python
class DataHub:
    # configuracion de colores
    bgcolor = "DarkCyan"
    cgcolor = "black"
    cchart = { ... }

    # monitoreo de CPU y MEMORY
    display = None
    max_points = 40
    # ... variables dispersas sin organización clara
```

#### Después:
```python
class DataHub:
    """
    Clase global para variables de entorno y configuración del sistema.

    Las variables configurables se cargan desde la base de datos (sesión DataHub).
    Estructura organizada en 4 grupos:
    1. Colores (bgcolor, cgcolor, cchart)
    2. Monitor CPU/Memoria (display, max_points, interval, CpuLock)
    3. Parámetros de Trading (MinProfit, Toleranciasell, MaxRoi, InicioInversior, ib_gateway_host, ib_gateway_port)
    4. Estructuras runtime (no configurables - se inicializan en código)
    """

    # ========================================================================================================
    # GRUPO 1: CONFIGURACIÓN DE COLORES (Cargable desde DB)
    # ========================================================================================================
    bgcolor = "DarkCyan"
    cgcolor = "black"
    cchart = { ... }

    # ========================================================================================================
    # GRUPO 2: MONITOREO DE CPU Y MEMORIA (Cargable desde DB)
    # ========================================================================================================
    display = None
    max_points = 40
    interval = 1
    CpuLock = None

    # ========================================================================================================
    # GRUPO 3: PARÁMETROS DE TRADING (Cargable desde DB)
    # ========================================================================================================
    MinProfit = 80.0
    Toleranciasell = 0.10
    MaxRoi = 0.09
    InicioInversior = date(2020, 7, 31)
    ib_gateway_host = r"https://localhost"
    ib_gateway_port = r"5501"

    # ========================================================================================================
    # GRUPO 4: ESTRUCTURAS RUNTIME (NO configurables)
    # ========================================================================================================
    SessionYfinance = None
    QremoteOrder = { ... }
    manager_events = {}
    # ... etc
```

**Beneficios:**
- ✅ **Organización clara**: Variables agrupadas por función
- ✅ **Documentación explícita**: Docstring y comentarios de sección
- ✅ **Separación de responsabilidades**: Variables configurables vs runtime
- ✅ **Fácil mantenimiento**: Saber qué variables se pueden modificar vía UI

---

### 2. Nuevo Método: `load_from_database()`

**Ubicación:** `Class_customer.py:323-409`

```python
@staticmethod
def load_from_database():
    """
    Carga las variables de entorno desde la sesión DataHub en la base de datos.

    Grupos cargados:
    1. Colores (bgcolor, cgcolor, cchart)
    2. Monitor CPU/Memoria (display, max_points, interval, CpuLock)
    3. Parámetros de Trading (MinProfit, Toleranciasell, MaxRoi, InicioInversior, ib_gateway_host, ib_gateway_port)

    Returns:
        bool: True si cargó exitosamente, False si hubo error
    """
    try:
        from Modulos_Mysql import BDsystem
        import json

        # Obtener sesión DataHub
        datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")

        if not datahub_session or not datahub_session.get("userapi"):
            print("[DataHub.load_from_database] ADVERTENCIA: No se encontró configuración en DataHub")
            return False

        # Decodificar JSON desde BLOB
        envs_config = json.loads(datahub_session["userapi"].decode("utf-8"))

        # ====== GRUPO 1: COLORES ======
        if "bgcolor" in envs_config:
            DataHub.bgcolor = envs_config["bgcolor"]
            DataHub.colors["bgcolor"] = envs_config["bgcolor"]

        if "cgcolor" in envs_config:
            DataHub.cgcolor = envs_config["cgcolor"]
            DataHub.colors["cgcolor"] = envs_config["cgcolor"]

        if "cchart" in envs_config:
            DataHub.cchart.update(envs_config["cchart"])
            DataHub.cchart["fondo"] = DataHub.bgcolor
            DataHub.cchart["fondo_fig"] = DataHub.cgcolor
            DataHub.colors["cchart"] = DataHub.cchart

        # ====== GRUPO 2: MONITOR CPU/MEMORIA ======
        if "display" in envs_config:
            DataHub.display = envs_config["display"]

        if "max_points" in envs_config:
            DataHub.max_points = envs_config["max_points"]

        if "interval" in envs_config:
            DataHub.interval = envs_config["interval"]

        if "CpuLock" in envs_config:
            DataHub.CpuLock = envs_config["CpuLock"]

        # ====== GRUPO 3: PARÁMETROS DE TRADING ======
        if "MinProfit" in envs_config:
            DataHub.MinProfit = float(envs_config["MinProfit"])

        if "Toleranciasell" in envs_config:
            DataHub.Toleranciasell = float(envs_config["Toleranciasell"])

        if "MaxRoi" in envs_config:
            DataHub.MaxRoi = float(envs_config["MaxRoi"])

        if "InicioInversior" in envs_config:
            inicio_str = envs_config["InicioInversior"]
            if isinstance(inicio_str, str):
                from datetime import datetime
                DataHub.InicioInversior = datetime.strptime(inicio_str, "%Y-%m-%d").date()

        if "ib_gateway_host" in envs_config:
            DataHub.ib_gateway_host = envs_config["ib_gateway_host"]

        if "ib_gateway_port" in envs_config:
            DataHub.ib_gateway_port = envs_config["ib_gateway_port"]

        print("[DataHub.load_from_database] ✓ Variables de entorno cargadas desde base de datos")
        return True

    except Exception as e:
        print(f"[DataHub.load_from_database] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
```

**Características:**
- 🔄 **Carga dinámica**: Lee desde DB al inicio de la aplicación
- 🛡️ **Validación**: Verifica existencia de campos antes de asignar
- 🔀 **Conversión de tipos**: Maneja conversión de strings a tipos correctos (float, date)
- ⚠️ **Manejo de errores**: Advertencias claras si falla la carga
- 🔗 **Sincronización**: Actualiza tanto variables individuales como `colors` dict

---

### 3. Integración en Inicio de Aplicación

**Ubicación:** `DashMainV9_ia.py:5166-5168`

#### Antes:
```python
def run(self):

    # inicializa logging y excepciones globales
    debug = Debugging(DisplayConsole=False, GlobalHub=DataHub)
```

#### Después:
```python
def run(self):
    # Cargar variables de entorno desde base de datos (sesión DataHub)
    DataHub.load_from_database()

    # inicializa logging y excepciones globales
    debug = Debugging(DisplayConsole=False, GlobalHub=DataHub)
```

**Flujo de ejecución:**
1. ⚡ `DashMain.run()` se ejecuta
2. 📥 `DataHub.load_from_database()` carga variables desde DB
3. 🖥️ `Debugging` usa las variables ya actualizadas de `DataHub`
4. 🚀 Resto de la aplicación usa configuración desde DB

---

### 4. Eliminación de Hardcoded Defaults en `open_envs_editor()`

**Ubicación:** `DashMainV9_ia.py:4232-4255`

#### Antes:
```python
# Cargar configuración actual desde userapi
try:
    userapi_bytes = session_data.get("userapi")
    if userapi_bytes:
        envs_config = json.loads(userapi_bytes.decode("utf-8"))
    else:
        # Si no hay configuración, intentar cargar desde sesión DataHub
        try:
            datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")
            if datahub_session and datahub_session.get("userapi"):
                envs_config = json.loads(datahub_session["userapi"].decode("utf-8"))
            else:
                # ❌ VALORES HARDCODEADOS (75 líneas de defaults)
                envs_config = {
                    "bgcolor": "DarkCyan",
                    "cgcolor": "black",
                    "cchart": { ... 25 campos ... },
                    "display": None,
                    "max_points": 40,
                    # ... etc
                }
        except Exception as e2:
            # ❌ MÁS VALORES HARDCODEADOS (15 líneas de defaults finales)
            envs_config = { ... }
except Exception as e:
    ...
```

#### Después:
```python
# Cargar configuración desde userapi (de la sesión actual o DataHub)
try:
    userapi_bytes = session_data.get("userapi")
    if userapi_bytes:
        # La sesión actual tiene configuración
        envs_config = json.loads(userapi_bytes.decode("utf-8"))
    else:
        # Si no hay configuración, cargar desde sesión DataHub
        datahub_session = BDsystem.get_sesion_by_vehiculo(vehiculo="DataHub")
        if datahub_session and datahub_session.get("userapi"):
            envs_config = json.loads(datahub_session["userapi"].decode("utf-8"))
        else:
            # ✅ Error claro - no más fallbacks hardcodeados
            MyMessageBox(session_window).showerror(
                "Error de Configuración",
                "No se encontró configuración de variables de entorno.\n\n"
                "La sesión 'DataHub' debe existir en la base de datos\n"
                "con el campo 'userapi' correctamente configurado.",
            )
            return
except Exception as e:
    ...
```

**Ventajas:**
- ❌ **Eliminados ~90 líneas** de valores hardcodeados
- ✅ **Fuente única de verdad**: Solo la base de datos
- ⚠️ **Errores claros**: Si no hay configuración, se informa al usuario
- 🔧 **Mantenibilidad**: Cambios solo en DB, no en código

---

## 📊 Estructura de Datos en Base de Datos

### Tabla: `sesion`
### Campo: `userapi` (BLOB)

**Formato:** JSON

```json
{
  "bgcolor": "DarkCyan",
  "cgcolor": "black",
  "cchart": {
    "texto": "white",
    "titulo": "cyan",
    "fondo": "DarkCyan",
    "fondo_fig": "black",
    "asx": "black",
    "asy": "black",
    "axsy": "grey",
    "axsx": "grey",
    "2eje": "orange",
    "plot0": "white",
    "plot1": "green",
    "plot11": "GreenYellow",
    "plot2": "orange",
    "plot21": "DarkOrange",
    "plot3": "red",
    "plot31": "OrangeRed",
    "plot4": "yellow",
    "plot41": "Gold",
    "plot5": "DodgerBlue",
    "plot6": "skyblue",
    "plot7": "grey",
    "plot8": "black",
    "plot9": "blue"
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

## 🔄 Flujo de Configuración

### Carga al Inicio
```
1. Usuario inicia aplicación (DashMainV9_ia.py)
   ↓
2. DashMain.run() ejecuta DataHub.load_from_database()
   ↓
3. Se lee sesión "DataHub" de tabla `sesion`
   ↓
4. Se decodifica campo `userapi` (BLOB → JSON)
   ↓
5. Se actualizan variables de clase DataHub
   ↓
6. Debugging y resto de módulos usan configuración actualizada
```

### Edición vía UI
```
1. Usuario hace clic en botón "Envs" en ventana de sesiones
   ↓
2. on_envs_click() obtiene sesión DataHub de DB
   ↓
3. open_envs_editor() muestra formulario con valores actuales
   ↓
4. Usuario modifica valores y hace clic en "Guardar"
   ↓
5. save_envs() serializa a JSON y actualiza campo `userapi`
   ↓
6. BDsystem.update_sesion() guarda en base de datos
   ↓
7. (Requiere reinicio para aplicar cambios en DataHub)
```

---

## 🎨 Variables Configurables

### Grupo 1: Colores
| Variable | Tipo | Descripción | Ejemplo |
|----------|------|-------------|---------|
| `bgcolor` | str | Color de fondo principal | `"DarkCyan"` |
| `cgcolor` | str | Color de gráficos | `"black"` |
| `cchart` | dict | Paleta de colores para charts | `{ "texto": "white", ... }` |

### Grupo 2: Monitor CPU/Memoria
| Variable | Tipo | Descripción | Ejemplo |
|----------|------|-------------|---------|
| `display` | bool/None | Mostrar consola de debugging | `None` |
| `max_points` | int | Puntos máximos en gráfico de CPU | `40` |
| `interval` | int | Intervalo de muestreo (segundos) | `1` |
| `CpuLock` | bool/None | Lock para sincronización | `None` |

### Grupo 3: Parámetros de Trading
| Variable | Tipo | Descripción | Ejemplo |
|----------|------|-------------|---------|
| `MinProfit` | float | Beneficio mínimo para venta | `80.0` |
| `Toleranciasell` | float | Tolerancia de venta (%) | `0.10` (10%) |
| `MaxRoi` | float | ROI máximo permitido | `0.09` (9%) |
| `InicioInversior` | date | Fecha inicio del inversor | `2020-07-31` |
| `ib_gateway_host` | str | Host del IB Gateway | `"https://localhost"` |
| `ib_gateway_port` | str | Puerto del IB Gateway | `"5501"` |

---

## ⚠️ Consideraciones Importantes

### 1. Reinicio Requerido
- ⚡ Los cambios en variables de entorno **requieren reiniciar la aplicación**
- 📝 `DataHub.load_from_database()` solo se ejecuta al inicio en `run()`
- 🔄 Para aplicar cambios en tiempo real, sería necesario:
  - Agregar método `DataHub.reload_from_database()`
  - Llamarlo desde `save_envs()` después de guardar
  - Actualizar componentes que dependen de las variables

### 2. Validación de Datos
- ✅ El editor valida tipos básicos (numéricos, fechas, colores hexadecimales)
- ⚠️ No hay validación de rangos (ej: `max_points` > 0)
- 🔧 Futura mejora: Agregar validaciones de negocio

### 3. Sesión DataHub Obligatoria
- 🔴 **CRÍTICO**: Debe existir registro con `vehiculo='DataHub'` en tabla `sesion`
- 📝 Si no existe, la aplicación usa valores hardcodeados de `Class_customer.py`
- ✅ El editor muestra error claro si no encuentra configuración

### 4. Compatibilidad Hacia Atrás
- ✅ Si un campo no existe en JSON, se mantiene el valor por defecto de la clase
- ✅ Campos antiguos en DB no causan errores (se ignoran)
- ✅ Nuevos campos se pueden agregar sin romper configuraciones existentes

---

## 🚀 Próximos Pasos Sugeridos

### 1. Reload Dinámico (Opcional)
Agregar método para aplicar cambios sin reiniciar:

```python
@staticmethod
def reload_from_database():
    """Recarga configuración y notifica a componentes activos"""
    if DataHub.load_from_database():
        # Notificar cambios a componentes suscritos
        DataHub.manager_events.trigger("config_reloaded")
```

### 2. Validaciones Mejoradas
Agregar validación de rangos en `save_envs()`:

```python
# Validar rangos
if max_points_val < 10 or max_points_val > 200:
    errors.append("max_points debe estar entre 10 y 200")

if tolerancia_val < 0 or tolerancia_val > 1:
    errors.append("Toleranciasell debe estar entre 0 y 1")
```

### 3. Versionado de Configuración
Agregar campo `config_version` para migraciones:

```json
{
  "_version": "1.0",
  "bgcolor": "DarkCyan",
  ...
}
```

### 4. Exportar/Importar Configuración
Agregar botones en UI para:
- 💾 Exportar configuración a archivo JSON
- 📥 Importar configuración desde archivo JSON
- 🔄 Restaurar valores por defecto

---

## 📚 Archivos Relacionados

- **`Class_customer.py`**: Clase DataHub con variables de entorno
- **`DashMainV9_ia.py`**: Aplicación principal (método `run()` y editor de variables)
- **`Modulos_Mysql.py`**: Acceso a base de datos (`BDsystem.get_sesion_by_vehiculo()`)
- **`Class_debugging.py`**: Módulo de debugging que usa variables de DataHub

---

## ✅ Resumen de Beneficios

| Aspecto | Antes | Después |
|---------|-------|---------|
| **Organización** | Variables dispersas sin estructura | 4 grupos claramente definidos |
| **Fuente de datos** | Hardcoded + DB (duplicado) | Solo DB (única fuente de verdad) |
| **Mantenibilidad** | Cambios en múltiples lugares | Cambios solo en DB |
| **Documentación** | Comentarios mínimos | Docstrings completos + secciones |
| **Edición** | Solo por código | UI + DB |
| **Defaults** | ~90 líneas hardcoded | Error claro si falta config |
| **Escalabilidad** | Difícil agregar nuevas variables | Fácil agregar a JSON |

---

**Documento generado:** 2026-01-04
**Versión:** 1.0
**Autor:** Claude Code (Sonnet 4.5)
**Estado:** ✅ Refactorización completada y documentada
