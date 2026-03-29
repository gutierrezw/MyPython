"""
run_check_holdings_stats.py
Valida load_fund_holdings_stats — tiempo de ejecución y métricas de flujo.
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_Mysql import MarketScreen

mkt = MarketScreen()
t = time.time()
stats = mkt.load_fund_holdings_stats()
elapsed = time.time() - t
print(f"Tiempo: {elapsed:.1f}s  Simbolos: {len(stats)}")
print()

print(f"{'Symbol':<8} {'fh_count':>8} {'buy_r':>7} {'sell_r':>7} {'CALL':>10} {'PUT':>10} {'new':>6} {'exits':>6} {'dCALL':>12} {'dPUT':>12}")
print("-" * 95)
for sym in ["CCI", "VALE", "CVS", "PFE", "SWK", "AMT", "HASI", "FMC"]:
    s = stats.get(sym, {})
    print(
        f"{sym:<8} {s.get('fh_count',0):>8} "
        f"{s.get('fh_buy_ratio',0):>7.1%} {s.get('fh_sell_ratio',0):>7.1%} "
        f"{s.get('fh_call_shares',0)/1e6:>9.1f}M {s.get('fh_put_shares',0)/1e6:>9.1f}M "
        f"{s.get('new_entrants',0):>6} {s.get('full_exits',0):>6} "
        f"{str(s.get('delta_call_shares')):>12} {str(s.get('delta_put_shares')):>12}"
    )
