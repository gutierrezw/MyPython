# Guía de Restauración — Contexto Claude + Entorno de Desarrollo
> Documento para migración de máquina o reinstalación desde cero.
> Última actualización: 2026-03-30

---

## 1. Instalar Claude Desktop

1. Descarga Claude Desktop desde https://claude.ai/download
2. Instala y abre sesión con la cuenta **gutierrez.madrid.wilmer@gmail.com**
3. En **Configuración → Perfil → Preferencias personalizadas**, pega exactamente esto:

```
Enfoque técnico ambiente Windows, Python y Java. Enfocado a las finanzas.

Estilo de trabajo:
- Nunca ejecutar scripts ni procesos largos en background sin que el usuario lo pida.
- Siempre entregar el comando listo y dejar que el usuario decida cuándo correrlo.
- El usuario quiere mantener control y aprender del proceso.
- Preferencia por Python con entorno virtual (.venv).
- Base de datos: MySQL 8.x, schema principal: bdinv.
- Proyecto principal en: C:\Users\InversionesWildaga\Documents\MyPython\AppOO
```

---

## 2. Conectar Gmail

En Claude Desktop → Conectores → Buscar "Gmail" → Conectar con la cuenta de Google.
Esto permite que las tareas recurrentes envíen reportes automáticos.

---

## 3. Restaurar el entorno Python

```powershell
# Crear entorno virtual
cd C:\Users\InversionesWildaga\Documents\MyPython
python -m venv .venv

# Activar
& .\.venv\Scripts\Activate.ps1

# Instalar dependencias del proyecto
pip install -r AppOO\requirements.txt

# Dependencias adicionales para scripts de Claude
pip install mysql-connector-python tabulate
```

---

## 4. Conectar carpeta del proyecto a Claude

En Claude Desktop (modo Cowork), cuando abras una sesión de trabajo:
- Conectar carpeta: `C:\Users\InversionesWildaga\Documents\MyPython\AppOO`
- Esto permite a Claude leer/escribir directamente en el proyecto y respaldar con Git.

---

## 5. Restaurar MySQL 8.x

### 5.1 Instalar MySQL 8.x
Descarga desde https://dev.mysql.com/downloads/mysql/

### 5.2 Aplicar configuración optimizada
Abre `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini` como Administrador
y agrega en la sección `[mysqld]` (asegúrate de no duplicar parámetros):

```ini
innodb_buffer_pool_size         = 2G
innodb_buffer_pool_instances    = 2
innodb_log_file_size            = 512M
innodb_flush_log_at_trx_commit  = 2
innodb_flush_method             = O_DIRECT
join_buffer_size                = 4M
sort_buffer_size                = 4M
tmp_table_size                  = 256M
max_heap_table_size             = 256M
max_connections                 = 200
slow_query_log                  = ON
long_query_time                 = 1
log_queries_not_using_indexes   = ON
```

Reinicia el servicio:
```
Win + R → services.msc → MySQL80 → Reiniciar
```

### 5.3 Verificar que el buffer pool se aplicó
```sql
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
-- Debe mostrar: 2147483648 (2GB)
```

### 5.4 Restaurar índices críticos en schema bdinv
Si restauras la BD desde backup, verifica y crea los índices que pueden no venir en el dump:

```sql
USE bdinv;

-- booktrading
ALTER TABLE booktrading ADD INDEX idx_hash_id (hash_id);

-- oportunidadesbuysell
ALTER TABLE oportunidadesbuysell ADD INDEX idx_hash_id (hash_id);

-- trazaplan
ALTER TABLE trazaplan ADD INDEX idx_idcuenta (idcuenta);

-- fund_holdings (tabla grande ~763K filas, tarda ~1 hora)
ALTER TABLE fund_holdings ADD INDEX idx_cusip (cusip);
ALTER TABLE fund_holdings ADD INDEX idx_fund_date (fund_id, report_date);
ALTER TABLE fund_holdings ADD INDEX idx_report_date (report_date);

-- market
ALTER TABLE market ADD INDEX idx_symbol (symbol);
ALTER TABLE market ADD INDEX idx_cusip (cusip);

-- funds
ALTER TABLE funds ADD INDEX idx_cik (cik);

-- diaria_cnv
ALTER TABLE diaria_cnv ADD INDEX idx_fecha_cod (fecha, codCAFCI);

-- performa_inversion
ALTER TABLE performa_inversion ADD INDEX idx_idcuenta_vehiculo (idcuenta, vehiculo);
ALTER TABLE performa_inversion ADD INDEX idx_fechaclose (fechaclose);

-- order_trader
ALTER TABLE order_trader ADD INDEX idx_account_symbol (account, symbol);
```

---

## 6. Restaurar herramientas de monitoreo

### 6.1 Script de análisis de schema
Ya está en el repo: `SchemasSQL/mysql_index_analyzer.py`

Edita las credenciales al inicio del script:
```python
CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "tu_usuario",
    "password": "tu_contraseña",
    "database": "bdinv",
}
```

Ejecución:
```powershell
python SchemasSQL\mysql_index_analyzer.py
```

### 6.2 Archivo de credenciales para tarea recurrente
Crea el archivo en:
`C:\Users\InversionesWildaga\Documents\Claude\outputs\mysql_config.json`

```json
{
    "host":     "localhost",
    "port":     3306,
    "user":     "tu_usuario",
    "password": "tu_contraseña",
    "database": "bdinv"
}
```

---

## 7. Restaurar tareas recurrentes de Claude

Las tareas programadas se guardan en:
`C:\Users\InversionesWildaga\Documents\Claude\Scheduled\`

Si migraste la carpeta `Scheduled\` completa, Claude las retomará automáticamente.

Si no, recrear la tarea semanal de MySQL desde Claude:
> "Crea una tarea recurrente que corra cada lunes a las 8am, conecte a MySQL bdinv,
> analice el schema e índices, y mande el reporte HTML a gutierrez.madrid.wilmer@gmail.com"

---

## 8. Verificación final

Después de restaurar todo, corre este checklist:

```powershell
# 1. Verificar Python y venv
python --version
pip list | findstr "mysql-connector"

# 2. Verificar conexión MySQL
python SchemasSQL\mysql_index_analyzer.py

# 3. Verificar buffer pool en Workbench
# SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
# Esperado: 2147483648
```

En Claude Desktop:
- [ ] Preferencias personalizadas cargadas
- [ ] Gmail conectado
- [ ] Carpeta AppOO conectada
- [ ] Tarea semanal MySQL visible en sidebar "Scheduled"

---

## Notas de arquitectura del proyecto

| Módulo | Descripción |
|--------|-------------|
| `Class_Screener.py` | Screener de activos con score institucional (13F EDGAR) |
| `Class_FondosInversion.py` | Análisis de fondos de inversión |
| `Class_IA_modelos.py` | Modelos de IA para señales de trading |
| `Class_ApiIBrks.py` / `Class_Ibrks.py` | Integración con Interactive Brokers |
| `Class_ApiBinnace.py` | Integración con Binance (crypto) |
| `Modulos_Mysql.py` | Capa de acceso a MySQL (usar siempre este módulo) |
| `Modulos_Comunes.py` | Utilidades compartidas entre módulos |
| `DashMainV9_ia.py` | Dashboard principal con IA integrada |
| `CLAUDE.md` | Convenciones del proyecto para Claude (este repo) |
| `SETUP_CLAUDE.md` | Este archivo — guía de restauración |
