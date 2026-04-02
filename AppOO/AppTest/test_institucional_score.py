import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Class_InstitucionalScore import InstitucionalScore, sync_institutional

# Símbolos de prueba — dividendos conocidos con fuerte presencia institucional
TEST_SYMBOLS = ["AAPL", "JNJ", "KO", "PG", "MSFT", "O", "MAIN", "T"]

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("PRUEBA 1: _fetch_ownership — validar mapeo de campos Yahoo")
print("=" * 70)

inst = InstitucionalScore()

for symbol in TEST_SYMBOLS:
    raw = inst._fetch_ownership(symbol)
    print(f"\n  [{symbol}]")
    if not raw:
        print("    Sin datos")
        continue
    print(f"    inst_ownership_pct    : {raw.get('inst_ownership_pct')}")
    print(f"    insider_ownership_pct : {raw.get('insider_ownership_pct')}")
    print(f"    inst_holders_count    : {raw.get('inst_holders_count')}")
    print(f"    inst_top_holder       : {raw.get('inst_top_holder')}")
    print(f"    inst_top_holder_shares: {raw.get('inst_top_holder_shares')}")
    print(f"    fund_names (top 3)    : {raw.get('fund_names', [])[:3]}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PRUEBA 2: score_company — validar cálculo inst_score")
print("=" * 70)

for symbol in TEST_SYMBOLS[:4]:
    data = inst.score_company(symbol)
    print(f"\n  [{symbol}]")
    if not data:
        print("    Sin datos")
        continue
    print(f"    inst_score        : {data.get('inst_score')}")
    print(f"    inst_ownership_pct: {data.get('inst_ownership_pct')}")
    print(f"    inst_holders_count: {data.get('inst_holders_count')}")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PRUEBA 3: update_inst_fields — validar escritura en market (1 símbolo)")
print("=" * 70)

ACCOUNT = "B0000001"
symbol = "JNJ"
data = inst.score_company(symbol)

if data:
    ok = inst.market.update_inst_fields(symbol, ACCOUNT, data)
    print(
        f"\n  [{symbol}] update_inst_fields → {'OK actualizado' if ok else 'no afecto filas (simbolo no existe o I/S/X)'}"
    )
    print(f"    inst_score           : {data.get('inst_score')}")
    print(f"    inst_ownership_pct   : {data.get('inst_ownership_pct')}")
    print(f"    inst_top_holder      : {data.get('inst_top_holder')}")
else:
    print(f"  [{symbol}] Sin datos de ownership")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PRUEBA 4: upsert_fund — validar escritura en tabla funds")
print("=" * 70)

raw = inst._fetch_ownership("AAPL")
fund_names = raw.get("fund_names", [])[:5]
for name in fund_names:
    inst.market.upsert_fund(name, 1)
    print(f"  upsert_fund: '{name}' OK")

print("\nTests completados")
