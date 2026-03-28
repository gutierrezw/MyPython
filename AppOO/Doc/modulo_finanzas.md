# Módulo Finanzas Personales + Gmail Co-work

> **Proyecto de segundo plano.** Se trabaja en sesiones cortas sin presión.
> Una fase a la vez. No se integra a AppOO hasta que cada pieza esté probada sola.

## 1. Objetivo

Dos proyectos que comparten la misma integración Gmail y trabajan juntos:

**A) Finanzas personales:**
Capturar, clasificar y analizar gastos de forma automatizada. La fuente principal
son los extractos que los bancos mandan por mail — cero fricción para el usuario.
El sistema aprende de cada corrección.

**B) Organización Gmail (co-work):**
Limpiar la bandeja de entrada, eliminar spam recurrente, clasificar por remitente
y crear filtros automáticos. Es el paso previo que además habilita la captura
de extractos bancarios.

**Moneda de referencia:** USDT (dólar cripto) — unifica cuentas en VES, ARS y USD.
Los rates se obtienen de Binance (ya integrado en AppOO). No se usa tipo oficial
ni blue; solo el precio de mercado cripto.

------------------------------------------------------------------------

## 2. Arquitectura

### Submódulos

1. **Gmail integration** ← punto de entrada de todo
2. **Importación de extractos** (desde adjuntos de mail o carpeta vigilada)
3. Clasificación automática (reglas + IA)
4. Registro financiero (manual como complemento)
5. Análisis y métricas / hábitos de consumo
6. Planificación y objetivos
7. Motor de decisiones / alertas

### Cuentas en scope

| País      | Tipo                    | Moneda | Notas                               |
|-----------|-------------------------|--------|-------------------------------------|
| Venezuela | Cuenta corriente        | VES    | Alta volatilidad — rate diario      |
| Argentina | Cuentas de ahorro       | ARS    | Brecha cambiaria — usar rate cripto |
| Argentina | Tarjetas de crédito     | ARS    |                                     |
| EEUU      | Cuenta (tipo por definir)| USD   | Base natural en dólares             |
| Binance   | Spot / DeFi / Préstamos | USDT  | Ya integrado en AppOO               |

### Flujo principal

```
Extracto (CSV/PDF/Excel)
    └── Parser por banco (adapter)
            └── Normalizar → deduplicar
                    └── Clasificar (reglas → IA → manual)
                            └── transactions
                                    └── Convertir a USDT (via exchange_rates ← Binance)
                                            └── Métricas / Hábitos / Alertas
```

### Flujo cripto como puente de transferencia

```
ARS / VES
    └── Compra USDT en Binance
            └── Transfer a Venezuela o EEUU
                    └── Registrar como: expense(origen) + income(destino) + transfer en Binance
```
*(Las operaciones Binance ya están en AppOO — se linkearán en Fase 5)*

------------------------------------------------------------------------

## 3. Fuentes de datos y automatización

### Fuentes por prioridad

| Fuente | Mecanismo | Automatización | Cuándo usar |
|--------|-----------|---------------|-------------|
| **Gmail** | OAuth → leer adjuntos de mails bancarios | Total — agente periódico | Bancos que mandan extracto por mail |
| **Carpeta vigilada** | Drop en `data/extractos/` → app procesa sola | Alta — solo bajar del portal | Bancos sin adjunto en mail |
| **Manual** | Subir archivo directo en UI | Ninguna | Casos puntuales |

### Gmail — flujo de captura automática

```
Agente periódico (cada 24h)
    └── Gmail API (OAuth)
            └── Buscar mails de remitentes bancarios conocidos
                    └── Descargar adjunto (PDF o CSV)
                            └── Pipeline normal: parser → deduplicar → clasificar → transactions
```

Remitentes bancarios se configuran en `banks.gmail_sender` (ej: `noreply@bancolombia.com.co`).

### Gmail — organización (co-work)

```
Script de depuración (se corre una vez, luego mantenimiento liviano)
    ├── Listar remitentes con >N mails → proponer etiquetar o marcar spam
    ├── Detectar newsletters/publicidad → crear filtro "skip inbox + etiquetar"
    ├── Identificar mails bancarios → etiquetar "Bancos" + archivar tras procesar
    └── Resumen: X mails archivados, Y filtros creados, Z spam eliminado
```

------------------------------------------------------------------------

## 4. Seguridad

### Principios

- **Todo local**: MySQL en la misma máquina que AppOO. No hay sincronización cloud.
- **OAuth para Gmail**: Google maneja la autenticación. La app guarda un token
  (archivo `token_gmail.json`) — nunca la contraseña. El token se puede revocar
  desde la cuenta Google en cualquier momento.
- **Sin contraseñas en texto plano**: credenciales en variables de entorno o
  en la tabla `sesiones` ya usada por AppOO (encriptada).
- **Permisos mínimos Gmail**: solo los scopes necesarios.
  - Para leer mails y adjuntos: `gmail.readonly`
  - Para mover/etiquetar: `gmail.modify`
  - NO se pide `gmail.send` ni acceso a otros servicios Google.

### Scopes OAuth requeridos

| Scope | Para qué |
|-------|----------|
| `https://www.googleapis.com/auth/gmail.readonly` | Leer mails y descargar adjuntos |
| `https://www.googleapis.com/auth/gmail.modify` | Etiquetar, archivar, crear filtros |

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| `token_gmail.json` expuesto | Agregar a `.gitignore`, permisos de archivo restrictivos |
| Datos financieros en BD local | MySQL solo acepta conexiones localhost; sin puerto abierto |
| Extracto mal parseado genera datos erróneos | Campo `needs_review=True` + deduplicación por hash |
| Spam malicioso con adjunto falso | Solo procesar adjuntos de remitentes en whitelist (`banks.gmail_sender`) |

------------------------------------------------------------------------

## 5. Modelo de Datos

### 5.1 exchange_rates — tipos de cambio históricos a USDT

Se popula automáticamente desde Binance (precio spot del par correspondiente).
Se guarda un rate por moneda por día para poder convertir transacciones pasadas
con el rate correcto de la fecha, no el rate de hoy.

| Columna       | Tipo     | Descripción                                           |
|---------------|----------|-------------------------------------------------------|
| id            | INT PK   |                                                       |
| from_currency | CHAR(3)  | ARS, VES, USD, etc.                                   |
| to_currency   | CHAR(4)  | Siempre USDT (moneda base)                            |
| rate          | DECIMAL  | 1 unidad de from_currency = X USDT                   |
| date          | DATE     | Fecha del rate (un registro por moneda por día)       |
| source        | ENUM     | binance / manual                                      |
| pair          | VARCHAR  | Par Binance usado (ej: ARSUSDT, USDTARS invertido)    |

**Notas:**
- VES: Binance P2P es la referencia (no hay par spot directo) → carga manual o scraping
- ARS: par USDTARS en Binance P2P → invertir para obtener ARS/USDT
- USD: rate = 1.0 siempre (USD ≈ USDT para este propósito)
- Si no hay rate para una fecha, usar el rate más cercano disponible

---

### 5.2 banks — catálogo de bancos/tarjetas soportados

| Columna        | Tipo    | Descripción                                      |
|----------------|---------|--------------------------------------------------|
| id             | INT PK  |                                                  |
| name           | VARCHAR | Nombre del banco / tarjeta                       |
| country        | CHAR(2) | CO, US, etc.                                     |
| adapter_class  | VARCHAR | Nombre de la clase parser (ej: BancolombiaCsv)   |
| date_format    | VARCHAR | Formato de fecha en el extracto (ej: %d/%m/%Y)   |
| delimiter      | CHAR    | Separador CSV (, o ;)                            |
| encoding       | VARCHAR | utf-8, latin-1, etc.                             |
| currency       | CHAR(3) | Moneda por defecto (COP, USD, etc.)              |
| gmail_sender   | VARCHAR | Remitente autorizado (ej: noreply@banco.com) — whitelist de seguridad |
| notes          | TEXT    | Instrucciones de descarga / columnas esperadas   |
| is_active      | BOOL    |                                                  |

---

### 5.3 accounts — cuentas y tarjetas del usuario

| Columna             | Tipo    | Descripción                                 |
|---------------------|---------|---------------------------------------------|
| id                  | INT PK  |                                             |
| name                | VARCHAR | Alias (ej: "Visa Bancolombia")              |
| type                | ENUM    | checking / credit / savings / investment    |
| currency            | CHAR(3) |                                             |
| balance             | DECIMAL | Saldo actual                                |
| opening_balance     | DECIMAL | Saldo inicial al crear la cuenta            |
| credit_limit        | DECIMAL | Solo tarjetas de crédito                    |
| bank_id             | INT FK  | → banks                                     |
| account_number_last4| CHAR(4) | Últimos 4 dígitos (identificación rápida)   |
| institution         | VARCHAR | Nombre institución (puede diferir del banco)|
| is_active           | BOOL    |                                             |

---

### 5.4 statement_imports — registro de extractos importados

Controla qué archivos ya se procesaron para evitar doble importación.

| Columna          | Tipo     | Descripción                                      |
|------------------|----------|--------------------------------------------------|
| id               | INT PK   |                                                  |
| account_id       | INT FK   | → accounts                                       |
| bank_id          | INT FK   | → banks                                          |
| filename         | VARCHAR  | Nombre original del archivo                      |
| file_hash        | CHAR(64) | SHA-256 del archivo — deduplicación exacta       |
| period_from      | DATE     | Primera fecha del extracto                       |
| period_to        | DATE     | Última fecha del extracto                        |
| imported_at      | DATETIME | Cuándo se importó                                |
| row_count        | INT      | Total de filas en el archivo                     |
| processed_count  | INT      | Filas convertidas a transacciones                |
| skipped_count    | INT      | Filas ignoradas (duplicadas o sin monto)         |
| status           | ENUM     | pending / processed / error                      |
| error_log        | TEXT     | Detalle de errores de parseo                     |

---

### 5.5 categories — categorías de gasto/ingreso

| Columna   | Tipo    | Descripción                                          |
|-----------|---------|------------------------------------------------------|
| id        | INT PK  |                                                      |
| name      | VARCHAR | Ej: Alimentación, Transporte, Entretenimiento        |
| type      | ENUM    | income / expense / transfer                          |
| parent_id | INT FK  | → categories (subcategorías, ej: Restaurantes ⊂ Alimentación) |
| color     | CHAR(7) | Hex para UI (#FF5733)                               |
| icon      | VARCHAR | Nombre de ícono (ej: "fork", "car", "tv")           |
| is_active | BOOL    |                                                      |

Categorías base sugeridas (expense):
- Alimentación > Supermercado, Restaurantes, Delivery
- Transporte > Combustible, Taxi/Uber, Transporte público
- Hogar > Arriendo, Servicios, Mantenimiento
- Salud > Médico, Farmacia, Seguro
- Entretenimiento > Streaming, Eventos, Hobbies
- Educación
- Ropa y calzado
- Tecnología
- Viajes
- Finanzas > Cuotas crédito, Intereses, Comisiones
- Otros

Categorías base (income):
- Salario
- Freelance / Honorarios
- Inversiones / Dividendos
- Arriendos recibidos
- Otros ingresos

---

### 5.6 import_rules — motor de clasificación automática

Cada fila es una regla que mapea un patrón de descripción a una categoría.
El sistema las evalúa en orden de prioridad. Si ninguna aplica, consulta IA.

| Columna      | Tipo    | Descripción                                              |
|--------------|---------|----------------------------------------------------------|
| id           | INT PK  |                                                          |
| pattern      | VARCHAR | Texto a buscar en raw_description (ej: UBER, NETFLIX)    |
| match_type   | ENUM    | exact / contains / startswith / regex                    |
| category_id  | INT FK  | → categories                                             |
| priority     | INT     | Menor número = mayor prioridad. Reglas de usuario > IA   |
| is_active    | BOOL    |                                                          |
| created_by   | ENUM    | user / ai / system                                       |
| hit_count    | INT     | Veces que esta regla clasificó una transacción           |
| last_hit_at  | DATETIME|                                                          |
| created_at   | DATETIME|                                                          |

**Flujo de clasificación:**
1. Evaluar reglas `created_by='user'` por prioridad → si match, asignar categoría
2. Evaluar reglas `created_by='system'` (precargadas)
3. Si no hay match → enviar `raw_description` a IA → IA devuelve categoría sugerida
4. Guardar sugerencia como regla nueva `created_by='ai'` con `is_active=False`
5. Usuario confirma o corrige → la regla queda `is_active=True`

---

### 5.7 transactions — transacciones (fuente central)

| Columna                  | Tipo     | Descripción                                      |
|--------------------------|----------|--------------------------------------------------|
| id                       | INT PK   |                                                  |
| date                     | DATE     | Fecha de la transacción                          |
| type                     | ENUM     | income / expense / transfer                      |
| amount                   | DECIMAL  | Siempre positivo                                 |
| currency                 | CHAR(3)  |                                                  |
| amount_base              | DECIMAL  | Monto convertido a moneda base (para métricas)   |
| category_id              | INT FK   | → categories                                     |
| account_id               | INT FK   | → accounts                                       |
| description              | VARCHAR  | Descripción limpia (editada por usuario)         |
| raw_description          | VARCHAR  | Texto original del extracto — nunca editar       |
| import_id                | INT FK   | → statement_imports (NULL si es manual)          |
| classified_by            | ENUM     | rule / ai / manual                               |
| classification_confidence| FLOAT    | 0.0–1.0 (solo si classified_by='ai')            |
| is_recurring             | BOOL     | Detectado automáticamente o marcado por usuario  |
| recurring_group_id       | INT      | Agrupa pagos recurrentes del mismo origen        |
| tags                     | VARCHAR  | Etiquetas libres separadas por coma              |
| notes                    | TEXT     | Nota libre del usuario                           |
| needs_review             | BOOL     | True si clasificación pendiente de confirmar     |
| created_at               | DATETIME |                                                  |
| updated_at               | DATETIME |                                                  |

**Deduplicación de transacciones:**
Al importar, antes de insertar se verifica:
`(account_id, date, amount, raw_description)` → si ya existe, se marca como `skipped`.

---

### 5.8 budgets — presupuestos por categoría

| Columna         | Tipo    | Descripción                      |
|-----------------|---------|----------------------------------|
| id              | INT PK  |                                  |
| category_id     | INT FK  |                                  |
| monthly_limit   | DECIMAL |                                  |
| alert_threshold | FLOAT   | Ej: 0.80 → alerta al 80% del límite |
| currency        | CHAR(3) |                                  |
| is_active       | BOOL    |                                  |

---

### 5.9 goals — objetivos financieros

| Columna            | Tipo    | Descripción                                  |
|--------------------|---------|----------------------------------------------|
| id                 | INT PK  |                                              |
| name               | VARCHAR | Ej: "Viaje a Europa", "Fondo de emergencia"  |
| target_amount      | DECIMAL |                                              |
| current_amount     | DECIMAL |                                              |
| deadline           | DATE    |                                              |
| priority           | INT     |                                              |
| type               | ENUM    | savings / purchase / emergency / debt_payoff |
| status             | ENUM    | active / completed / paused / cancelled      |
| linked_account_id  | INT FK  | Cuenta donde se acumula el ahorro            |
| monthly_required   | DECIMAL | Calculado: (target - current) / meses_restantes |

---

### 5.10 savings_rules — reglas de ahorro automático

| Columna             | Tipo    | Descripción                                      |
|---------------------|---------|--------------------------------------------------|
| id                  | INT PK  |                                                  |
| rule_type           | ENUM    | percentage / fixed_amount / round_up             |
| value               | DECIMAL | % o monto fijo                                   |
| trigger             | ENUM    | on_income / monthly / on_transaction             |
| source_account_id   | INT FK  |                                                  |
| destination_account_id | INT FK |                                               |
| goal_id             | INT FK  | Objetivo al que aplica (NULL = ahorro general)   |
| is_active           | BOOL    |                                                  |
| frequency           | ENUM    | daily / weekly / monthly (si trigger=monthly)    |

---

### 5.11 daily_financial_state — snapshot diario (histórico)

Se popula automáticamente al final de cada día con un proceso batch.
Base para análisis histórico y predicciones.

| Columna                   | Tipo    | Descripción                         |
|---------------------------|---------|-------------------------------------|
| id                        | INT PK  |                                     |
| date                      | DATE    |                                     |
| account_id                | INT FK  |                                     |
| balance_eod               | DECIMAL | Saldo al cierre del día             |
| daily_income              | DECIMAL |                                     |
| daily_expense             | DECIMAL |                                     |
| cumulative_income_month   | DECIMAL | Acumulado desde inicio de mes       |
| cumulative_expense_month  | DECIMAL |                                     |
| savings_rate_month        | FLOAT   | % ahorro acumulado del mes          |
| top_category_id           | INT FK  | Categoría con más gasto del día     |

------------------------------------------------------------------------

## 4. Pipeline de importación (detalle técnico)

### Paso 1 — Parser por banco (adapter)

Cada banco tiene su clase adapter que hereda de `StatementParser`:

```
StatementParser (base)
    ├── BancolombiaCreditoCsv
    ├── DaviviendaCsv
    ├── NubankCsv
    └── ... (agregar según necesidad)
```

Responsabilidad del adapter:
- Leer el archivo (CSV/PDF/Excel)
- Devolver lista de dicts normalizados:
  `[{date, raw_description, amount, type, currency}, ...]`

### Paso 2 — Normalización

- Limpiar `raw_description`: strip, uppercase, remover caracteres especiales
- Detectar si es gasto o ingreso (por signo del monto o columna específica)
- Convertir fecha al formato estándar
- Calcular `amount_base` si la moneda difiere de la moneda base del usuario

### Paso 3 — Deduplicación

- Calcular SHA-256 del archivo → si `file_hash` ya existe en `statement_imports`, abortar
- Por transacción: verificar `(account_id, date, amount, raw_description)` en `transactions`

### Paso 4 — Clasificación

Ver flujo en sección 3.5 (import_rules)

### Paso 5 — Revisión pendiente

Todas las transacciones con `needs_review=True` aparecen en una cola de revisión
en la UI. El usuario las procesa una vez y el sistema aprende (regla nueva).

------------------------------------------------------------------------

## 5. Métricas y análisis de hábitos

*(Detalle en próxima iteración — primero consolidar captura de datos)*

Áreas previstas:
- Ratio de ahorro mensual
- Gasto por categoría (mes actual vs promedio histórico)
- Detección de gastos recurrentes
- Tendencias: categorías que suben/bajan
- Días/semanas de mayor gasto
- Fondo de emergencia: meses de runway
- Score financiero personal (ahorro 40 / control gasto 30 / estabilidad 20 / objetivos 10)

------------------------------------------------------------------------

## 6. Alertas

*(Detalle en próxima iteración)*

Canales: UI (notificación en app) + Telegram (bot existente en AppOO)

Tipos previstos:
- Presupuesto de categoría al 80% / 100%
- Mes con flujo negativo
- Gasto inusual (>2x promedio histórico en una categoría)
- Transacciones pendientes de clasificar > N
- Objetivo financiero en riesgo (ritmo actual no alcanza el deadline)

------------------------------------------------------------------------

## 7. Planificación de compras

```
ahorro_mensual_necesario = (precio - ahorro_actual) / meses_restantes
```

------------------------------------------------------------------------

## 8. Integración con AppOO (inversiones + Binance)

### Señales de control (Fase 4)
- Si `savings_rate < 10%` → señal en Screener: pausar nuevas posiciones
- Si `balance_total_usdt < fondo_emergencia_minimo` → bloquear compras automáticas BotCrypto
- Dividendos recibidos → registrar como `income` en `transactions` automáticamente

### Binance como fuente de tipos de cambio
- Agente en `Class_DashBot.py` con `@wait_rate(86400)` → descarga precio spot
  de los pares relevantes (ARSUSDT, VESUSDT vía P2P si disponible) y popula `exchange_rates`
- Para VES: P2P de Binance no tiene API pública → carga manual o scraping del portal

### Binance DeFi — integración futura (Fase 4)
- Operaciones Spot ya registradas en AppOO → mapear a `transactions` con
  `type='transfer'` cuando sean envíos VE/US
- Earn/DeFi: intereses recibidos → `type='income'`, `category='Inversiones/Dividendos'`
- Préstamos (loan): desembolso → `type='income'`; cuota/repago → `type='expense'`,
  `category='Finanzas/Cuotas crédito'`
- Las operaciones cripto que sean **puente de transferencia** (ARS→USDT→VES o ARS→USDT→USD)
  se registran como transfer entre cuentas, no como gasto

------------------------------------------------------------------------

## 9. Roadmap

> **Filosofía:** proyecto de segundo plano. Una fase a la vez, solo cuando haya
> tiempo disponible. Cada fase debe poder usarse sola sin depender de la siguiente.
> Preferir scripts independientes antes que integrar a AppOO — integrar solo cuando
> la funcionalidad ya esté probada y estable.

---

### Fase 0 — Gmail: organización + acceso *(punto de entrada)*

**Objetivo:** limpiar el mail y dejar la integración Gmail lista para todo lo demás.
Es el paso que habilita la captura automática de extractos.

Entregables:
1. Configurar proyecto en Google Cloud Console → obtener `credentials.json` (OAuth)
2. Script `gmail_setup.py` en `AppTest/`: autorizar app, guardar `token_gmail.json`
3. Script `gmail_cleanup.py`:
   - Listar top remitentes por volumen → proponer etiquetar o marcar spam
   - Detectar newsletters/publicidad → crear filtros "skip inbox + archivar"
   - Identificar mails de bancos conocidos → etiquetar "Bancos"
   - Resumen final: X mails procesados, Y filtros creados
4. Whitelist de remitentes bancarios: primer llenado manual de `banks.gmail_sender`

**Resultado esperado:** bandeja organizada + app con acceso Gmail funcionando.
No se toca la BD de finanzas todavía.

**Pendiente de confirmar:** ¿qué bancos mandan extracto/resumen por mail?
¿El adjunto viene en PDF, CSV o es solo texto en el cuerpo del mail?

---

### Fase 1 — Cimientos: tablas + primer extracto manual

**Objetivo:** poder cargar un extracto y ver los gastos clasificados en la BD.
Sin UI, sin automatización — solo que los datos entren correctos.

Entregables:
1. Crear las tablas en MySQL: `banks`, `accounts`, `exchange_rates`, `categories`,
   `import_rules`, `statement_imports`, `transactions`
2. Reglas base precargadas en `import_rules` (50–100 patrones comunes: UBER,
   NETFLIX, supermercados, etc.)
3. Adapter para el primer banco con extracto disponible (definir en esta fase)
4. Script `load_statement.py` en `AppTest/`: recibe archivo CSV/PDF,
   parsea, deduplica e inserta en `transactions`
5. Script de verificación: últimas N transacciones + cuántas quedaron `needs_review`

**Resultado esperado:** cargar un extracto real y ver los datos en la BD.

---

### Fase 2 — Gmail: captura automática de extractos

**Objetivo:** que los extractos se carguen solos cuando llega el mail del banco.

Entregables:
1. Script `gmail_fetch_statements.py`: busca mails de remitentes en whitelist,
   descarga adjuntos a `data/extractos/`, llama al pipeline de la Fase 1
2. Agente periódico (24h) en `Class_DashBot.py` que lo ejecuta
3. Log de lo procesado: qué mail, qué extracto, cuántas transacciones nuevas

**Resultado esperado:** no tener que hacer nada — los gastos aparecen solos.

---

### Fase 3 — Clasificación asistida

**Objetivo:** reducir a cero las transacciones `needs_review`, con mínimo esfuerzo.

Entregables:
1. Script `review_pending.py`: lista pendientes en consola, usuario escribe
   categoría → se guarda como regla nueva automáticamente
2. Clasificación por IA (Claude): para lo que no matchea reglas, sugiere
   categoría → usuario confirma con una tecla
3. Detección de recurrentes: mismo patrón + monto similar ~30 días → `is_recurring=True`

**Resultado esperado:** después de revisar una vez, los extractos futuros se
clasifican solos en >90%.

---

### Fase 4 — Métricas básicas (primer dashboard)

**Objetivo:** responder "¿en qué gasté este mes?" con una pantalla simple.

Entregables:
1. Tab nuevo en AppOO: "Finanzas" — gastos del mes agrupados por categoría
2. Comparación mes actual vs mes anterior
3. Total ingresos / gastos / % ahorro
4. Highlight: categorías con gasto >20% respecto al mes anterior

**Resultado esperado:** mirar el tab una vez por semana y entender el estado
financiero en 30 segundos.

---

### Fase 5 — Multi-país y tipos de cambio

**Objetivo:** unificar VES + ARS + USD + USDT en una sola vista.

Entregables:
1. Adapters para bancos venezolanos y argentinos
2. Agente que popula `exchange_rates` diariamente desde Binance
3. `amount_base` (USDT) calculado al importar
4. Dashboard muestra totales consolidados en USDT

---

### Fase 6 — Alertas e integración AppOO

**Objetivo:** que la app avise cuando algo está mal, sin tener que ir a buscar.

Entregables:
1. Alertas vía Telegram: flujo negativo, categoría sobre presupuesto
2. Señal a Screener/BotCrypto si `savings_rate` baja del umbral configurado
3. Linkear operaciones Binance existentes como transferencias entre cuentas

---

### Fase 6 — Planificación y objetivos *(long term)*

- Objetivos financieros con seguimiento (`goals`)
- Ahorro automático por reglas (`savings_rules`)
- Predicción de flujo futuro (`daily_financial_state`)
- Motor de decisiones completo
