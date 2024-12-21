import keyboard
import yfinance as yf
import globales
from bd_conect import select_booktrading, insert_booktrading, min_fec_booktrading, select_inversion
from main_crypto import performa_asset
from bd_conect import *
from api_binance import *

utrading = select_booktrading(accion='timestamp')
sfecha = utrading[0]['fechahora']
sfecha += timedelta(days=-2)
efecha = datetime.now()

stime = int(sfecha.timestamp() * 1000)
etime = int(efecha.timestamp() * 1000)
ticket = 'ADAUSDT'
w_trade = trade_history(ticket, stime, etime)
print(w_trade)

