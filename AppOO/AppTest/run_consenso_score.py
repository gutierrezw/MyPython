import sys
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Modulos_Mysql import MarketScreen
from Modulos_Utilitarios import define_FileCache

import pandas as pd

ACCOUNT = "U4214563"


def _read_csv_signals(filename):
    try:
        path = define_FileCache(name=f"{filename}.CSV")
        df = pd.read_csv(path, header=0, sep=",", encoding="utf-8", index_col=False)
        df.columns = df.columns.str.strip()
        return set(df["Symbol"].dropna().str.strip().tolist()) if "Symbol" in df.columns else set()
    except Exception:
        return set()


def _build_net_percentiles(stats_subset):
    nets = sorted([(v.get("fh_buy_ratio") or 0.0) - (v.get("fh_sell_ratio") or 0.0) for v in stats_subset.values()])
    if len(nets) < 3:
        return 0.2, 0.5
    n = len(nets)
    return nets[n // 3], nets[(2 * n) // 3]


def voto_net_relativo(buy_r, sell_r, p33, p67):
    net = (buy_r or 0.0) - (sell_r or 0.0)
    if net >= p67:
        return 1
    if net >= p33:
        return 0
    return -1


def voto_options(calls, puts):
    total = (calls or 0) + (puts or 0)
    if total == 0:
        return None  # abstiene
    ratio = (calls or 0) / total
    if ratio >= 0.6:
        return 1
    if ratio >= 0.4:
        return 0
    return -1


def voto_analistas(rec):
    r = (rec or "").lower().replace(" ", "_")
    if r in ("strong_buy", "buy"):
        return 1
    if r in ("sell", "strong_sell"):
        return -1
    if r == "hold":
        return 0
    return None  # abstiene


def voto_modelo(sym, syms_buy, syms_sell):
    if sym in syms_buy:
        return 1
    if sym in syms_sell:
        return -1
    return 0


def voto_valuacion(categ):
    if categ == "I":
        return 1
    if categ == "S":
        return -1
    if categ == "N":
        return 0
    return None  # X/T abstiene


def voto_cobertura(fh_count):
    c = fh_count or 0
    if c >= 20:
        return 1
    if c >= 5:
        return 0
    return -1


def senal_consenso(votos_activos, suma):
    n = len(votos_activos)
    if n == 0:
        return "— S/D"
    pct = suma / n
    if suma == n:
        return "★ UNÁNIME"
    if pct >= 0.6:
        return "▲ CONSENSO"
    if pct >= 0.2:
        return "↗ TENDENCIA"
    if pct > -0.2:
        return "→ NEUTRO"
    if pct > -0.6:
        return "↘ ALERTA"
    return "▼ SALIDA"


# ── carga datos ─────────────────────────────────────────────────────────────
market = MarketScreen()
cartera = market.load_cartera_inst(ACCOUNT)
fh_stats = market.load_fund_holdings_stats()
syms_buy = _read_csv_signals("csv_datosIA_buy")
syms_sell = _read_csv_signals("csv_datosIA_sell")

cartera_syms = {r["symbol"] for r in cartera}
fh_cartera = {s: v for s, v in fh_stats.items() if s in cartera_syms}
p33_net, p67_net = _build_net_percentiles(fh_cartera)

print(f"Net percentiles — p33={p33_net:+.3f}  p67={p67_net:+.3f}")
print("=" * 115)
print(
    f"{'Symbol':<8} {'Cat':>3} {'buy_r':>6} {'sel_r':>6} {'net':>6} {'Net':>4} {'Opt':>4} {'Ana':>4} {'Mod':>4} {'Val':>4} {'Cob':>4} "
    f"{'Suma':>5} {'N':>2} {'Pct':>6}  Señal"
)
print("=" * 115)

resultados = []
for row in cartera:
    sym = row["symbol"]
    categ = row.get("categoriaActivo") or ""
    stats = fh_stats.get(sym, {})

    buy_r = stats.get("fh_buy_ratio") or 0.0
    sell_r = stats.get("fh_sell_ratio") or 0.0

    v_net = voto_net_relativo(buy_r, sell_r, p33_net, p67_net)
    v_opt = voto_options(stats.get("fh_call_count"), stats.get("fh_put_count"))
    v_ana = voto_analistas(row.get("analyst_rec"))
    v_mod = voto_modelo(sym, syms_buy, syms_sell)
    v_val = voto_valuacion(categ)
    v_cob = voto_cobertura(stats.get("fh_count"))

    votos = {
        "Net": v_net,
        "Opt": v_opt,
        "Ana": v_ana,
        "Mod": v_mod,
        "Val": v_val,
        "Cob": v_cob,
    }
    activos = {k: v for k, v in votos.items() if v is not None}
    suma = sum(activos.values())
    n = len(activos)
    pct = suma / n if n else 0
    senal = senal_consenso(list(activos.values()), suma)

    def fmt(v):
        if v is None:
            return "  — "
        return f"{v:+d}  " if v != 0 else "  0 "

    net_r = buy_r - sell_r
    print(
        f"{sym:<8} {categ:>3} {buy_r:>6.2f} {sell_r:>6.2f} {net_r:>+6.2f} {fmt(v_net)} {fmt(v_opt)} {fmt(v_ana)} {fmt(v_mod)} "
        f"{fmt(v_val)} {fmt(v_cob)} {suma:>+5} {n:>2} {pct:>+.2f}   {senal}"
    )

    resultados.append({"symbol": sym, "suma": suma, "n": n, "pct": pct, "senal": senal})

print("=" * 100)

conteo = Counter(r["senal"] for r in resultados)
print("\nResumen:")
for k, v in sorted(conteo.items(), key=lambda x: -x[1]):
    print(f"  {k:<20} {v}")
