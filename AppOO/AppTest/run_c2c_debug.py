"""
Debug: inspecciona respuesta raw de la API C2C para detectar operaciones VES.
Uso: C:\\...\\venv\\Scripts\\python.exe AppTest/run_c2c_debug.py
"""

import sys
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Class_ApiBinnace import BinanceClient

client = BinanceClient().spot

# Últimos 6 meses sin filtro de fiat — ver todo lo que devuelve
hoy = datetime.today()
inicio = hoy - relativedelta(months=6)

start_ms = int(inicio.timestamp() * 1000)
end_ms = int(hoy.timestamp() * 1000)

print("Consultando API C2C sin filtro fiat (últimos 6 meses)...")
response = client.get_c2c_trade_history(
    tradeType="BUY",
    startTimestamp=start_ms,
    endTimestamp=end_ms,
    rows=100,
)

if not response or "data" not in response:
    print("Sin respuesta o sin data:", response)
    sys.exit(1)

print(f"Total registros recibidos: {len(response['data'])}\n")

fiats_vistos = set()
for row in response["data"]:
    fiats_vistos.add(row.get("fiat", "?"))
    print(
        f"  {row.get('fiat','?'):4s} | {row.get('orderStatus','?'):12s} | "
        f"{row.get('tradeType','?'):4s} | "
        f"{datetime.fromtimestamp(row['createTime']/1000).strftime('%Y-%m-%d')} | "
        f"{row.get('takerAmount','?')} USDT @ {row.get('unitPrice','?')} | "
        f"advNo={row.get('advNo','?')}"
    )

print(f"\nFiats encontrados en respuesta: {fiats_vistos}")
