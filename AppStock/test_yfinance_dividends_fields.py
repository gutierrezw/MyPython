"""
Módulo de diagnóstico para visualizar TODOS los campos de dividendos disponibles en yfinance
Objetivo: Identificar qué información exacta proporciona yfinance sobre dividendos
"""

import yfinance as yf
import pandas as pd
from datetime import datetime


def get_all_dividend_fields(symbol):
    """
    Obtiene TODOS los campos relacionados con dividendos desde yfinance

    Args:
        symbol: Símbolo del activo (ej: "AAPL", "O", "PFE")

    Returns:
        dict con todos los campos de dividendos encontrados
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Obtener historial de dividendos
        dividends_history = ticker.dividends

        print(f"\n{'='*100}")
        print(f"CAMPOS DE DIVIDENDOS PARA: {symbol}")
        print(f"{'='*100}\n")

        # 1. Campos del diccionario info que contienen "dividend" o "yield" ------------------------------------------------------------
        print("📊 (1) CAMPOS EN ticker.info:")
        print("-" * 100)

        dividend_fields = {}
        for key, value in sorted(info.items()):
            if "dividend" in key.lower() or "yield" in key.lower():
                dividend_fields[key] = value

                # Formatear el valor para mejor visualización
                if isinstance(value, float):
                    if "yield" in key.lower():
                        print(f"  {key:40} = {value:>10.4f}%")
                    elif "rate" in key.lower() or "amount" in key.lower():
                        print(f"  {key:40} = ${value:>10.4f}")
                    else:
                        print(f"  {key:40} = {value:>10.4f}")
                elif isinstance(value, int):
                    # Podría ser una fecha en formato timestamp
                    if "date" in key.lower() and value > 1000000000:
                        try:
                            date_str = datetime.fromtimestamp(value).strftime(
                                "%Y-%m-%d"
                            )
                            print(f"  {key:40} = {date_str} (timestamp: {value})")
                        except:
                            print(f"  {key:40} = {value}")
                    else:
                        print(f"  {key:40} = {value}")
                else:
                    print(f"  {key:40} = {value}")

        if not dividend_fields:
            print("  ⚠️  No se encontraron campos de dividendos en ticker.info")

        # 2. Historial de dividendos --------------------------------------------------------------------------------------------------
        print(f"\n📈 (2) HISTORIAL DE DIVIDENDOS (ticker.dividends):")
        print("-" * 100)

        if len(dividends_history) > 0:
            print(f"  Total de pagos registrados: {len(dividends_history)}")
            print(
                f"  Primer pago: {dividends_history.index[0].strftime('%Y-%m-%d')} = ${dividends_history.iloc[0]:.4f}"
            )
            print(
                f"  Último pago: {dividends_history.index[-1].strftime('%Y-%m-%d')} = ${dividends_history.iloc[-1]:.4f}"
            )

            # Últimos 12 meses
            cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=12)
            cutoff_date = cutoff_date.tz_localize(None)

            dividends_index = dividends_history.index
            if dividends_index.tz is not None:
                dividends_index = dividends_index.tz_localize(None)

            recent_dividends = [
                (date, dividends_history.loc[dividends_history.index == date].iloc[0])
                for date in dividends_history.index
                if date.tz_localize(None) > cutoff_date
            ]

            print(f"\n  Últimos 12 meses ({len(recent_dividends)} pagos):")
            for date, amount in recent_dividends:
                month_name = date.strftime("%B %Y")
                print(f"    {month_name:20} = ${amount:.4f}")

            # Calcular frecuencia
            if len(recent_dividends) > 0:
                total_last_12m = sum(amount for _, amount in recent_dividends)
                print(f"\n  Total últimos 12 meses: ${total_last_12m:.4f}")
                print(f"  Frecuencia detectada: {len(recent_dividends)} pagos/año")

                # Detectar meses de pago
                months_paid = [date.month for date, _ in recent_dividends]
                unique_months = sorted(set(months_paid))
                month_names = [
                    datetime(2000, m, 1).strftime("%B") for m in unique_months
                ]
                print(f"  Meses de pago: {', '.join(month_names)}")
        else:
            print("  ⚠️  No hay historial de dividendos")

        # 3. Campos adicionales relevantes---------------------------------------------------------------------------------------------
        print(f"\n💼 (3) CAMPOS ADICIONALES RELEVANTES:")
        print("-" * 100)

        additional_fields = [
            "currentPrice",
            "previousClose",
            "payoutRatio",
            "exDividendDate",
            "dividendDate",
            "currency",
            "quoteType",
        ]

        for field in additional_fields:
            if field in info:
                value = info[field]

                if isinstance(value, float):
                    if "price" in field.lower():
                        print(f"  {field:40} = ${value:>10.4f}")
                    elif "ratio" in field.lower():
                        print(f"  {field:40} = {value:>10.2%}")
                    else:
                        print(f"  {field:40} = {value:>10.4f}")
                elif isinstance(value, int):
                    if "date" in field.lower() and value > 1000000000:
                        try:
                            date_str = datetime.fromtimestamp(value).strftime(
                                "%Y-%m-%d"
                            )
                            print(f"  {field:40} = {date_str}")
                        except:
                            print(f"  {field:40} = {value:,}")
                    else:
                        print(f"  {field:40} = {value:,}")
                else:
                    print(f"  {field:40} = {value}")

        # 4. Calcular métricas derivadas-----------------------------------------------------------------------------------------------
        print(f"\n🔢 (4) MÉTRICAS CALCULADAS:")
        print("-" * 100)

        current_price = info.get("currentPrice", 0)
        dividend_rate = info.get("dividendRate", 0)
        trailing_annual = info.get("trailingAnnualDividendRate", 0)
        dividend_yield = info.get("dividendYield", 0)

        if current_price > 0 and dividend_rate > 0:
            calculated_yield = dividend_rate / current_price * 100
            print(
                f"  Yield calculado (dividendRate/price):  {calculated_yield:>10.4f}%"
            )
            print(f"  Yield reportado (dividendYield):       {dividend_yield:>10.4f}%")
            if abs(calculated_yield - dividend_yield) > 0.0001:
                print(
                    f"  Diferencia:                            {(calculated_yield - dividend_yield):>+10.4f}%"
                )

        if len(dividends_history) > 0:
            recent_dividends_list = [
                dividends_history.loc[dividends_history.index == date].iloc[0]
                for date in dividends_history.index
                if date.tz_localize(None) > cutoff_date
            ]

            if recent_dividends_list and dividend_rate > 0:
                print(
                    f"\n  dividendRate reportado:                ${dividend_rate:>10.4f}"
                )
                print(
                    f"  Último pago real:                      ${recent_dividends_list[-1]:>10.4f}"
                )
                if abs(dividend_rate - recent_dividends_list[-1]) > 0.0001:
                    print(
                        f"  Diferencia:                            ${dividend_rate - recent_dividends_list[-1]:>+10.4f}"
                    )

            if recent_dividends_list and trailing_annual > 0:
                num_payments = len(recent_dividends_list)
                implied_annual = dividend_rate * num_payments
                print(
                    f"\n  Anual calculado (rate × pagos/año):    ${implied_annual:>10.4f}"
                )
                print(
                    f"  Trailing annual reportado:             ${trailing_annual:>10.4f}"
                )
                if abs(implied_annual - trailing_annual) > 0.01:
                    print(
                        f"  Diferencia:                            ${implied_annual - trailing_annual:>+10.4f}"
                    )

        print(f"\n{'='*100}\n")

        return {
            "symbol": symbol,
            "dividend_fields": dividend_fields,
            "dividends_history": dividends_history,
        }

    except Exception as e:
        print(f"\n❌ Error obteniendo datos para {symbol}: {e}")
        import traceback

        traceback.print_exc()
        return None


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    print("=" * 100)
    print("MÓDULO DE DIAGNÓSTICO: CAMPOS DE DIVIDENDOS EN YFINANCE")
    print("=" * 100)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    while True:
        symbol = (
            input("\nIngresa el símbolo del activo (o 'salir' para terminar): ")
            .strip()
            .upper()
        )

        if (
            symbol.lower() == "salir"
            or symbol.lower() == "exit"
            or symbol.lower() == "s"
        ):
            print("\n¡Hasta luego!\n")
            break

        if not symbol:
            print("❌ Símbolo vacío. Intenta nuevamente.")
            continue

        print(f"\nAnalizando {symbol}...\n")
        get_all_dividend_fields(symbol)

    print("\n" + "=" * 100)
    print("CONCLUSIONES")
    print("=" * 100)
    print(
        """
CAMPOS PRINCIPALES DISPONIBLES EN YFINANCE:

1. dividendRate
   - Dividendo por pago individual (NO anual)
   - Para trimestral: es el dividendo de 1 trimestre
   - Para mensual: es el dividendo de 1 mes

2. dividendYield
   - Porcentaje de rendimiento (yield)
   - Calculado como: dividendRate / currentPrice

3. trailingAnnualDividendRate
   - Total de dividendos pagados en los últimos 12 meses (TTM)
   - ESTE es el valor correcto para dividendos anuales

4. trailingAnnualDividendYield
   - Yield basado en TTM

5. exDividendDate
   - Fecha ex-dividendo (timestamp)

6. dividendDate
   - Fecha de pago del dividendo (timestamp)

7. fiveYearAvgDividendYield
   - Promedio de yield en 5 años

8. payoutRatio
   - Ratio de pago (dividendos / ganancias)

IMPORTANTE:
- Para calcular dividendo mensual: usar trailingAnnualDividendRate / 12
- NO usar dividendRate / meses (esto da valores incorrectos)
- El historial (ticker.dividends) es la fuente más confiable para pagos históricos
    """
    )
    print("=" * 100 + "\n")
