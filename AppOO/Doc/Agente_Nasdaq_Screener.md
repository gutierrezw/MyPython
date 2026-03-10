# Especificación Técnica

## Agente de Actualización NASDAQ Screener

------------------------------------------------------------------------

# 1. Objetivo

Desarrollar un **agente automático** que consulte la API del NASDAQ
Screener y actualice la tabla **Market** en la base de datos del
sistema.

El agente debe:

-   Descargar información de acciones desde NASDAQ.
-   Filtrar únicamente **empresas que reportan dividendos**.
-   Insertar nuevas empresas en la tabla `Market`.
-   Actualizar empresas existentes.
-   No modificar registros bloqueados por el sistema.

Este agente alimenta el **módulo Screener del sistema de inversión**.

------------------------------------------------------------------------

# 2. Fuente de Datos

API utilizada:

https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=5000

Método HTTP:

GET

Headers requeridos:

User-Agent: Mozilla/5.0\
Accept: application/json

------------------------------------------------------------------------

# 3. Estructura de la Respuesta

La API devuelve un JSON con la siguiente estructura:

``` json
{
 "data": {
   "rows": [
      {...},
      {...}
   ]
 }
}
```

Cada elemento dentro de `rows` representa una empresa.

------------------------------------------------------------------------

# 4. Campos Disponibles en la API

  Campo API   Descripción
  ----------- ----------------------
  symbol      Ticker
  name        Nombre de la empresa
  lastsale    Último precio
  netchange   Cambio del precio
  pctchange   Cambio porcentual
  marketCap   Capitalización
  country     País
  ipoyear     Año IPO
  volume      Volumen
  sector      Sector
  industry    Industria
  url         URL de NASDAQ

------------------------------------------------------------------------

# 5. Filtro de Empresas con Dividendos

El agente debe almacenar **solo empresas que reporten dividendos**.

Condición principal:

dividendYield \> 0

Dado que la API no siempre incluye el campo `dividendYield`, se
utilizarán reglas adicionales.

Una empresa se considerará **empresa de dividendos** si cumple alguna de
las siguientes condiciones:

-   sector = Real Estate
-   industry contiene "REIT"
-   name contiene "Trust"

------------------------------------------------------------------------

# 6. Tabla de Destino

Tabla: `Market`

Clave primaria:

symbol

------------------------------------------------------------------------

# 7. Campos almacenados en la tabla Market

  Campo BD          Fuente
  ----------------- -------------
  symbol            symbol
  shortName         name
  lastPrice         lastsale
  marketCap         marketCap
  volume            volume
  country           country
  sector            sector
  industry          industry
  ipoYear           ipoyear
  pctChange         pctchange
  categoriaActivo   "Dividends"
  fecha_update      timestamp

------------------------------------------------------------------------

# 8. Normalización de Datos

La API devuelve valores con formato textual.

Ejemplos:

  Valor API   Conversión
  ----------- ------------
  \$183.22    183.22
  2.4B        2400000000
  3.5M        3500000

Antes de guardar en la base se deben **convertir a valores numéricos**.

------------------------------------------------------------------------

# 9. Lógica de Persistencia

Regla principal:

SI symbol NO existe en Market → INSERT\
SI symbol existe → UPDATE

La clave única es:

symbol

------------------------------------------------------------------------

# 10. Regla de Exclusión de Actualización

Si el registro existente tiene:

categoriaActivo IN ('I','S','X')

Entonces:

NO ACTUALIZAR

  Valor   Significado
  ------- -------------
  I       Inactivo
  S       Suspendido
  X       Excluido

------------------------------------------------------------------------

# 11. Lógica Completa del Proceso

Inicio\
↓\
Consultar API NASDAQ\
↓\
Recibir JSON\
↓\
Extraer registros\
↓\
Aplicar filtro de dividendos\
↓\
Normalizar datos\
↓\
Verificar existencia en tabla Market\
↓\
Si NO existe → INSERT\
↓\
Si existe → verificar categoriaActivo\
↓\
categoriaActivo IN ('I','S','X') → NO actualizar\
↓\
categoriaActivo diferente → UPDATE\
↓\
Guardar fecha_update\
↓\
Fin

------------------------------------------------------------------------

# 12. Frecuencia de Ejecución

Frecuencia recomendada:

1 vez por día

Hora sugerida:

08:00 AM

Antes de la apertura del mercado.

------------------------------------------------------------------------

# 13. Control de Ejecución

El agente debe registrar en log:

  Métrica                  Descripción
  ------------------------ --------------------------------
  registros_descargados    total API
  registros_filtrados      empresas dividendos
  registros_insertados     nuevas empresas
  registros_actualizados   registros modificados
  registros_omitidos       bloqueados por categoriaActivo

------------------------------------------------------------------------

# 14. Integración con el Sistema

El módulo:

Class_Screener.py

obtiene la información desde:

MarketScreen.select()

Arquitectura del sistema:

NASDAQ API\
↓\
Agente Screener\
↓\
MySQL (tabla Market)\
↓\
Class_Screener.py\
↓\
UI Screener

------------------------------------------------------------------------

# 15. Resultado Esperado

Número aproximado de empresas con dividendos:

  Mercado   Cantidad aproximada
  --------- ---------------------
  NASDAQ    \~600
  NYSE      \~900
  AMEX      \~100

Total esperado:

≈ 1500 empresas

------------------------------------------------------------------------

# 16. Posibles Mejoras Futuras

Integrar:

-   Yahoo Finance API (dividendos históricos)
-   Clasificación automática (High Yield / Dividend Growth)
-   Métricas avanzadas (Dividend CAGR, Payout Ratio)

------------------------------------------------------------------------

# 17. Versión del Documento

Agente NASDAQ Screener\
Version: 1.0\
Autor: Wilmer Gutierrez\
Sistema: Screener de Inversiones
