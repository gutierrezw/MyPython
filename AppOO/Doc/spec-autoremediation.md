# Módulo Auto-Remediación — AppOO

## Objetivo

Sistema de monitoreo continuo que detecta fallos, mide calidad y desempeño de la app,
los registra en BD con trazabilidad histórica y los expone en la UI (tab System).
Sienta las bases para remediación automática asistida por IA en fases posteriores.

---

## Dimensiones de monitoreo

### 1. Calidad de código — cada 15 días
**Fuente:** `CodeAnalysis/weekly_report.py` + vulture

Métricas a registrar:
- Archivos, líneas, clases, métodos (con delta vs período anterior)
- Hallazgos vulture: imports muertos, variables muertas, métodos sin uso, código inalcanzable
- Actividad git: commits del período, resumen de cambios

**Acción futura:** feed al LLM (Claude API) para sugerir/aplicar limpieza de imports y dead code.

---

### 2. Fallos del log — diarios
**Fuente:** log rotativo `../logs/dashmain_log_*`

Clasificación de fallos (todos se llaman "fallos"):
| Nivel | Tipo | Ejemplo actual |
|-------|------|----------------|
| ERROR | Bug de atributo | `'BotManager' has no attribute '_check_market_regime'` |
| ERROR | Red/conexión | IBroks puerto 5501, Binance WS perdido |
| ERROR | Orden rechazada | Binance 400 STOP_LOSS_LIMIT precio invertido |
| CRITICAL | Thread/socket | TVServer WinError 10038 |
| CRITICAL | Agente caído | `ClassChatbot run_agentesIA(all)` |

El agente lee el log del día, agrupa fallos por módulo+mensaje, descarta los esperados
(IBroks sin gateway = ruido conocido) y registra los nuevos/recurrentes en BD.

---

### 3. Desempeño BD — mensual
**Fuente:** `SchemasSQL/mysql_index_analyzer.py` (ya implementado, ya tiene scheduled lunes 8am)

Métricas a registrar:
- Queries lentas (slow_query_log)
- Índices sin uso / full scans detectados
- Configuración InnoDB vs baseline óptimo
- Tamaño de tablas críticas (fund_holdings, market, booktrading, etc.)

**Acción futura:** sugerir nuevos índices o ANALYZE TABLE según hallazgos.

---

### 4. UI — Tab System (nueva sección)
Panel "Fallos & Métricas" dentro del tab System existente:

| Sección | Contenido |
|---------|-----------|
| Fallos recientes | Treeview: fecha / módulo / tipo / mensaje / ocurrencias |
| Calidad código | Última snapshot: líneas, métodos, hallazgos vulture (con delta) |
| Desempeño BD | Último reporte: queries lentas, índices, tamaño tablas |
| Tendencia | Mini-gráfico o tabla histórica de métricas clave |

---

## Diseño de BD

### Tabla `fallos`
```sql
CREATE TABLE fallos (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    fecha         DATE NOT NULL,
    modulo        VARCHAR(60) NOT NULL,
    nivel         ENUM('WARNING','ERROR','CRITICAL') NOT NULL,
    tipo          VARCHAR(80),          -- 'bug_atributo', 'red', 'orden', 'socket', 'agente'
    mensaje       TEXT,
    ocurrencias   INT DEFAULT 1,
    primera_vez   DATETIME,
    ultima_vez    DATETIME,
    resuelto      TINYINT(1) DEFAULT 0,
    INDEX idx_fecha (fecha),
    INDEX idx_modulo (modulo)
);
```

### Tabla `app_metrics`
```sql
CREATE TABLE app_metrics (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    semana        VARCHAR(10) NOT NULL,  -- '2026-W14'
    fecha         DATETIME NOT NULL,
    archivos      INT,
    lineas        INT,
    clases        INT,
    metodos       INT,
    vulture_total INT,
    dead_imports  INT,
    dead_vars     INT,
    dead_methods  INT,
    commits       INT,
    report_json   LONGTEXT,             -- JSON completo del weekly_report
    UNIQUE KEY uk_semana (semana)
);
```

### Tabla `bd_metrics`
```sql
CREATE TABLE bd_metrics (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    fecha           DATE NOT NULL,
    slow_queries    INT,
    full_scans      INT,
    unused_indexes  INT,
    report_html     LONGTEXT,
    UNIQUE KEY uk_fecha (fecha)
);
```

---

## Agentes

| Agente | Frecuencia | Fuente | Destino |
|--------|-----------|--------|---------|
| `Agente_FallosLog` | Diario | log rotativo | tabla `fallos` |
| `Agente_MetricasCodigo` | Cada 15 días | weekly_report.py | tabla `app_metrics` |
| `Agente_MetricasBD` | Mensual | mysql_index_analyzer.py | tabla `bd_metrics` |

Todos viven en `Class_DashBot.py` como coordinadores puros.
La lógica de parseo/análisis va en clases dueñas del dominio (por definir).

---

## Roadmap

| Fase | Tarea | Prioridad |
|------|-------|-----------|
| **1** | Definir BD: tablas `fallos`, `app_metrics`, `bd_metrics` | Alta |
| **2** | Crear agentes: `Agente_FallosLog` + `Agente_MetricasCodigo` + `Agente_MetricasBD` | Alta |
| **3** | UI en tab System: panel "Fallos & Métricas" con Treeview + resumen | Media |
| **4** | Auto-remediación IA: feed vulture → Claude API → fix automático | Futura |

---

## Notas técnicas

- `weekly_report.py` requiere refactor mínimo: `generate()` debe retornar dict además de imprimir.
- `mysql_index_analyzer.py` ya genera reporte — solo agregar persistencia en `bd_metrics`.
- El parseo del log debe ser robusto: el formato es `timestamp - LEVEL - module - thread - message`.
- Fallos "esperados" (IBroks sin gateway) → configurar whitelist para no registrar como fallo real.
- Toda la lógica de parseo/BD en clases separadas — los agentes solo coordinan.
