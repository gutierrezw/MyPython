# 📊 Módulo de Control de Apalancamiento (STOCK)

## 🧠 Objetivo

Construir un sistema que permita: - Evaluar el riesgo total de la
cartera - Determinar el apalancamiento máximo permitido - Controlar el
costo financiero (intereses) - Ajustar riesgo según volatilidad (Beta)

------------------------------------------------------------------------

## 🧱 Variables Base

### Inputs desde IB

-   NetLiquidation (capital total)
-   GrossPositionValue (exposición total)
-   Cash
-   InitialMargin
-   MaintenanceMargin

### Inputs de mercado

-   Price
-   Beta
-   Volatility (opcional)
-   Sector

### Inputs estratégicos

``` json
{
  "max_leverage": 1.8,
  "max_monthly_interest_pct": 0.02,
  "target_beta_portfolio": 1.2,
  "max_beta_portfolio": 1.5
}
```

------------------------------------------------------------------------

## ⚙️ Métricas Clave

### Apalancamiento

Leverage = GrossPositionValue / NetLiquidation

### Beta del portfolio

Beta_portfolio = Σ (peso_i \* beta_i)

### Riesgo real

Risk_real = Leverage \* Beta_portfolio

### Intereses

Interest = Deuda \* Tasa_IB / 12

Deuda = GrossPositionValue - NetLiquidation

### % costo

Interest_pct = Interest / NetLiquidation

------------------------------------------------------------------------

## 🚦 Reglas de Control

### 1. Límite de apalancamiento

``` python
if leverage > max_leverage:
    bloquear_compras()
```

### 2. Control de Beta

``` python
if beta_portfolio > max_beta_portfolio:
    reducir_activos_volatiles()
```

### 3. Riesgo combinado

``` python
if leverage * beta_portfolio > 2.0:
    activar_modo_defensivo()
```

### 4. Costo financiero

``` python
if interest_pct > max_monthly_interest_pct:
    reducir_apalancamiento()
```

------------------------------------------------------------------------

## 🧠 Interpretación

El control real no es el leverage, sino:

Risk_real = Leverage \* Beta

------------------------------------------------------------------------

## ⚙️ Función en Python

``` python
def evaluar_apalancamiento(portfolio, capital, tasa_ib):

    total_value = sum(p["value"] for p in portfolio)
    leverage = total_value / capital

    beta_port = sum(
        (p["value"] / total_value) * p["beta"]
        for p in portfolio
    )

    debt = max(0, total_value - capital)
    monthly_interest = debt * tasa_ib / 12
    interest_pct = monthly_interest / capital

    risk_real = leverage * beta_port

    return {
        "leverage": leverage,
        "beta_portfolio": beta_port,
        "risk_real": risk_real,
        "monthly_interest": monthly_interest,
        "interest_pct": interest_pct
    }
```

------------------------------------------------------------------------

## 🧩 Integración

Antes de operar:

``` python
if nuevo_leverage > limite:
    rechazar_trade()

if nuevo_risk_real > limite:
    reducir_size()
```

------------------------------------------------------------------------

## 🔥 Leverage dinámico

``` python
leverage_max = 2 / beta_portfolio
```

------------------------------------------------------------------------

## 🎯 Conclusión

El sistema debe enfocarse en controlar el riesgo total y no solo el
apalancamiento.
