# ESPECIFICACIÓN TÉCNICA

## Agente de Preservación de Ganancias

**Proyecto:** Rebalanceo de Cartera\
**Autor:** Wilmer\
**Fecha:** 2026-02-18

------------------------------------------------------------------------

# 1. Objetivo

Diseñar e implementar un **Agente de Preservación de Ganancias**
independiente del motor ofensivo (IA), cuya función sea proteger
ganancias ante correcciones estructurales del mercado.

Este agente:

-   No optimiza ventas.
-   No predice mercado.
-   No utiliza señales IA.
-   No compite con el Agente_ManagerSell.
-   Solo protege ganancias acumuladas mediante órdenes STOP dinámicas.

------------------------------------------------------------------------

# 2. Definición de Corrección Grande

Una corrección grande se define como:

    caída ≥ max(correccion_pct, atr_mult × ATR)

Donde:

-   `correccion_pct` → porcentaje fijo por vehículo
-   `ATR` → Average True Range actual
-   `atr_mult` → multiplicador configurado por vehículo

Precio Stop calculado:

    stop_price = max_price - max(
        correccion_pct × max_price,
        atr_mult × ATR
    )

------------------------------------------------------------------------

# 3. Parámetros por Vehículo

Los parámetros se almacenan en la tabla `sesion`, campo `parameters`
(JSON), dentro del bloque:

``` json
{
  "preservation": {
    "roi_minimo": 0.10,
    "proteccion_base": 0.50,
    "correccion_pct": 0.08,
    "atr_mult": 2.0,
    "revisiones_dia": 2
  }
}
```

Ejemplo Crypto:

``` json
{
  "preservation": {
    "roi_minimo": 0.18,
    "proteccion_base": 0.40,
    "correccion_pct": 0.12,
    "atr_mult": 2.5,
    "revisiones_dia": 2
  }
}
```

------------------------------------------------------------------------

# 4. Flujo Operativo del Agente

## 4.1 Activación

El agente solo actúa si:

    ROI >= roi_minimo

------------------------------------------------------------------------

## 4.2 Actualización de Máximo

    max_price = max(max_price_guardado, last)

------------------------------------------------------------------------

## 4.3 Cálculo del Stop

    stop_distance = max(
        correccion_pct × max_price,
        atr_mult × ATR
    )

    stop_calculado = max_price - stop_distance

------------------------------------------------------------------------

## 4.4 Regla de Oro (No Degradación)

Nunca bajar el stop:

    stop_final = max(stop_anterior, stop_calculado)

------------------------------------------------------------------------

## 4.5 Cantidad Protegida

    qty = round(position × proteccion_base)

Las órdenes se envían como STOP remotas en IB.

IB, por configuración fiscal, venderá automáticamente los lotes con
mayor ganancia.

------------------------------------------------------------------------

# 5. Integración con el Orquestador

El agente se integra dentro del loop principal:

``` python
self.exec_modulo_async(self.Agente_ManagerPreservation())
```

Debe autolimitar su ejecución para respetar:

    revisiones_dia = 2

Se recomienda validar ejecución por timestamp guardado por símbolo.

------------------------------------------------------------------------

# 6. Identificación de Órdenes

Las órdenes STOP deben incluir un identificador específico:

    order_tag = "PRESERVATION_STOP"

Esto permite:

-   Diferenciarlas del agente ofensivo.
-   Evitar duplicación.
-   Mantener idempotencia.
-   Modificar únicamente órdenes defensivas.

------------------------------------------------------------------------

# 7. Reglas Institucionales

1.  Nunca bajar un stop ya colocado.
2.  No activar si ROI es insignificante.
3.  No mezclar lógica ofensiva y defensiva.
4.  No ejecutar cada 15 segundos.
5.  El agente es estructural, no táctico.

------------------------------------------------------------------------

# 8. Estado Necesario por Símbolo

Debe persistirse:

-   max_price
-   stop_actual
-   last_preservation_check

------------------------------------------------------------------------

# 9. Separación Arquitectónica

  Agente                           Rol
  -------------------------------- -----------------------
  Agente_ManagerSell               Ofensivo
  Agente_ManagerBuy                Ofensivo
  Agente_ManagerTop10              Ranking
  Agente_downloads_filings_EDGAR   Data
  Agente_ManagerPreservation       Defensivo estructural

------------------------------------------------------------------------

# 10. Filosofía del Sistema

Este agente existe para:

> Nunca permitir que una ganancia significativa se transforme en una
> ganancia irrelevante.

Es un sistema mecánico de protección de capital. No toma decisiones
emocionales. No optimiza máximos. Solo protege.

------------------------------------------------------------------------

**Fin de Especificación**
