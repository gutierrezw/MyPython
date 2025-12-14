# Plan de Refactorización: select_sesion()

## 📋 Problemas Actuales

### 1. SQL Injection Vulnerabilities
```python
# ❌ ACTUAL (vulnerable):
cursor.execute(sql % vehiculo)
cursor.execute(upd % (fesesion, orden, vehiculo))

# ✅ DEBE SER:
cursor.execute(sql, (vehiculo,))
cursor.execute(upd, (fesesion, orden, vehiculo))
```

### 2. Mezcla de Responsabilidades
La función hace 4 cosas diferentes según `accion`:
- `accion="select"`: Solo leer sesión
- `accion="update"`: Actualizar fesesion + orcartera
- `accion="updateFun"`: Actualizar fechaFund
- `accion="updatexstrategy"`: Actualizar xstrategy

### 3. Parámetros Confusos
```python
def select_sesion(
    fecha,              # Usado solo en updates
    orden='...',        # Usado solo en update
    accion=False,       # Controla flujos diferentes
    invertir=0,         # Usado solo para setear en dict
    filtro=None,        # Usado solo en updatexstrategy
    vehiculo="Stock",   # Único parámetro realmente usado siempre
)
```

## 🎯 Estrategia de Refactorización

### Fase 1: Crear Funciones Nuevas (Sin Romper Nada)

**1.1. Función de lectura pura:**
```python
@staticmethod
def get_sesion_by_vehiculo(vehiculo: str) -> dict:
    """
    Obtiene sesión por vehículo.

    Returns:
        dict con todos los campos de la tabla sesion
    """
    sql = "SELECT * FROM sesion WHERE vehiculo = %s"
    conn = BDsystem.connect_dbase("select.sesion", False)

    try:
        cursor = conn.cursor(dictionary=True)  # Retorna dict automáticamente
        cursor.execute(sql, (vehiculo,))
        sesion = cursor.fetchone()

        if not sesion:
            raise ValueError(f"No existe sesión para vehículo: {vehiculo}")

        return sesion

    except Exception as error:
        print(f"[Mysql::get_sesion_by_vehiculo()]: {error}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
```

**1.2. Funciones de actualización separadas:**
```python
@staticmethod
def update_sesion_fecha_orden(vehiculo: str, fesesion: datetime, orcartera: str) -> bool:
    """Actualiza fesesion y orcartera de una sesión"""
    sql = "UPDATE sesion SET fesesion=%s, orcartera=%s WHERE vehiculo=%s"
    conn = BDsystem.connect_dbase("Sesion.Update", False)

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (fesesion, orcartera, vehiculo))
        conn.commit()
        return True
    except Exception as error:
        print(f"[Mysql::update_sesion_fecha_orden()]: {error}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@staticmethod
def update_sesion_fecha_fund(vehiculo: str, fecha_fund: date) -> bool:
    """Actualiza fechaFund de una sesión"""
    sql = "UPDATE sesion SET fefund=%s WHERE vehiculo=%s"
    conn = BDsystem.connect_dbase("Fe.fundamental.Update", False)

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (fecha_fund, vehiculo))
        conn.commit()
        return True
    except Exception as error:
        print(f"[Mysql::update_sesion_fecha_fund()]: {error}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@staticmethod
def update_sesion_strategy(vehiculo: str, xstrategy: str) -> bool:
    """Actualiza xstrategy de una sesión"""
    sql = "UPDATE sesion SET xstrategy=%s WHERE vehiculo=%s"
    conn = BDsystem.connect_dbase("Strategy.Update", False)

    try:
        cursor = conn.cursor()
        cursor.execute(sql, (xstrategy, vehiculo))
        conn.commit()
        return True
    except Exception as error:
        print(f"[Mysql::update_sesion_strategy()]: {error}")
        conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
```

### Fase 2: Mantener select_sesion() como Wrapper (Backward Compatible)

**2.1. Refactorizar select_sesion() usando las nuevas funciones:**
```python
@staticmethod
def select_sesion(
    fecha,
    orden='{"RetS": "ASC"}',
    accion=False,
    invertir=0,
    filtro=None,
    vehiculo="Stock",
) -> dict:
    """
    DEPRECATED: Usar get_sesion_by_vehiculo() y update_* en su lugar.

    Mantiene compatibilidad con código existente.
    """
    # Leer sesión base
    sesion = BDsystem.get_sesion_by_vehiculo(vehiculo)

    # Agregar campos adicionales que el código antiguo espera
    sesion["fectime"] = fecha

    # Ejecutar acción según parámetro
    if accion == "update":
        BDsystem.update_sesion_fecha_orden(vehiculo, fecha, orden)
        sesion["fesesion"] = fecha
        sesion["orcartera"] = orden
        sesion["Pinvertir"] = invertir

    elif accion == "select":
        # Ya tenemos todos los datos de get_sesion_by_vehiculo()
        pass

    elif accion == "updateFun":
        BDsystem.update_sesion_fecha_fund(vehiculo, fecha)
        sesion["fefund"] = fecha

    elif accion == "updatexstrategy":
        if filtro:
            BDsystem.update_sesion_strategy(vehiculo, filtro)
            sesion["xstrategy"] = filtro

    return sesion
```

### Fase 3: Migración Gradual

**3.1. Identificar usos:**
- 21 llamadas encontradas en el código
- Analizar cada una y clasificar por tipo de acción

**3.2. Migrar código nuevo:**
- En nuevos desarrollos, usar `get_sesion_by_vehiculo()` y `update_*`
- Marcar `select_sesion()` como `@deprecated` en docstring

**3.3. Migrar código existente (opcional):**
- Reemplazar gradualmente llamadas antiguas
- Ejemplo:
  ```python
  # ANTES:
  sesion = BDsystem.select_sesion("select", vehiculo="Stock")

  # DESPUÉS:
  sesion = BDsystem.get_sesion_by_vehiculo("Stock")
  ```

## 🔧 Beneficios de la Refactorización

1. ✅ **Seguridad**: Elimina SQL injection
2. ✅ **Claridad**: Funciones con un solo propósito
3. ✅ **Mantenibilidad**: Más fácil de entender y modificar
4. ✅ **Testing**: Funciones más pequeñas = más fáciles de testear
5. ✅ **Backward Compatible**: No rompe código existente
6. ✅ **Type hints**: Mejor autocompletado en IDE
7. ✅ **Error handling**: Manejo consistente de errores
8. ✅ **Resource cleanup**: `finally` asegura cierre de conexiones

## 📊 Análisis de Impacto

### Archivos que usan select_sesion():
1. API_vehiculos.py (3 usos)
2. Class_FondosInversion.py (2 usos)
3. Class_DashBot.py (2 usos)
4. Class_gestion.py (7 usos)
5. Class_customer.py (2 usos)
6. DashMainV9_ia.py (3 usos)

### Tipos de uso encontrados:
```python
# Tipo 1: Solo lectura (más común)
sesion = BDsystem.select_sesion("select", vehiculo="Stock")
sesion = BDsystem.select_sesion("select", vehiculo="Crypto")

# Tipo 2: Lectura con fecha (raro)
sesion = BDsystem.select_sesion(fecha, "select", vehiculo="Stock")

# Tipo 3: Update (muy raro)
sesion = BDsystem.select_sesion(fecha, orden, "update", vehiculo="Stock")
```

## 🚀 Plan de Implementación

### Paso 1: Crear nuevas funciones
- Agregar `get_sesion_by_vehiculo()`
- Agregar `update_sesion_fecha_orden()`
- Agregar `update_sesion_fecha_fund()`
- Agregar `update_sesion_strategy()`

### Paso 2: Refactorizar select_sesion()
- Usar nuevas funciones internamente
- Mantener firma y comportamiento

### Paso 3: Testing
- Probar DashMainV9_ia.py (uso principal)
- Probar Class_gestion.py (7 usos)
- Verificar no regresión

### Paso 4: Documentación
- Marcar select_sesion() como deprecated
- Documentar nuevas funciones
- Crear guía de migración

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Romper código existente | BAJA | Mantener select_sesion() como wrapper |
| Cambio de comportamiento | BAJA | Tests exhaustivos antes de deploy |
| Error en SQL parameterizado | BAJA | Validar con MySQL Workbench |
| Cursors no cerrados | MEDIA | Usar `finally` en todas las funciones |

## 📝 Notas Importantes

1. **cursor(dictionary=True)**: MySQL Connector/Python feature que retorna dict automáticamente
2. **fetchone() vs fetchall()**: select_sesion solo necesita un registro
3. **Commit/Rollback**: Agregar rollback en caso de error
4. **Connection pooling**: Considerar en el futuro para mejorar performance
