import yfinance as yf
import pandas as pd

# Obtener los símbolos de las empresas del Dow Jones
dow_jones_symbols = [
    'AAPL', 'AMGN', 'AXP', 'BA', 'CAT', 'CRM', 'CSCO', 'CVX', 'DIS', 'DOW',
    'GS', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KO', 'MCD', 'MMM', 'MRK',
    'MSFT', 'NKE', 'PG', 'TRV', 'UNH', 'V', 'VZ', 'WBA', 'WMT'
]

# Descargar datos de las empresas del Dow Jones
data = yf.download(dow_jones_symbols, period="1y", actions=True)

# Calcular el rendimiento por dividendo para cada empresa
dividend_yields = {}
for symbol in dow_jones_symbols:
    stock = yf.Ticker(symbol)
    info = stock.info
    dividend_yield = info.get('dividendYield', 0)  # Obtener el rendimiento por dividendo
    if dividend_yield:
        dividend_yields[symbol] = dividend_yield

# Crear un DataFrame con los resultados
dividend_yields_df = pd.DataFrame(list(dividend_yields.items()), columns=['Symbol', 'Dividend Yield'])
dividend_yields_df['Dividend Yield'] = dividend_yields_df['Dividend Yield'] * 100  # Convertir a porcentaje

print(dividend_yields_df)

# Calcular el rendimiento por dividendo promedio del Dow Jones
average_dividend_yield = dividend_yields_df['Dividend Yield'].mean()
print(f"El rendimiento por dividendo promedio del Dow Jones es: {average_dividend_yield:.2f}%")
