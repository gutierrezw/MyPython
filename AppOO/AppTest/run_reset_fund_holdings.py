import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
conn = mkt._conectar(tabla="update.market")
c = conn.cursor()
c.execute("TRUNCATE TABLE fund_holdings")
c.execute("UPDATE fund_filings SET processed=0")
conn.commit()
c.execute("SELECT COUNT(*) FROM fund_filings WHERE processed=0")
total = c.fetchone()[0]
conn.close()
print(f"fund_holdings truncado")
print(f"fund_filings reseteados: {total:,}")
