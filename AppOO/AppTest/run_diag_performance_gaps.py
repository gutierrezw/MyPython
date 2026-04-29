import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"
VEHICULO = "Stock"
DESDE = "2025-12-01"

conn = BDsystem.connect_dbase("diag_gaps")
cursor = conn.cursor()

print("=" * 70)
print(f"DIAGNÓSTICO DE GAPS — diaria_performance desde {DESDE}")
print("=" * 70)

# 1. Cuántos símbolos distintos hay por fecha
cursor.execute(
    """
    SELECT Date, COUNT(DISTINCT symbol) as n_symbols, SUM(value) as total_value
    FROM diaria_performance
    WHERE account = %s AND Date >= %s
    GROUP BY Date
    ORDER BY Date
""",
    (ACCOUNT, DESDE),
)
rows = cursor.fetchall()

if not rows:
    print("  (sin datos desde esa fecha)")
else:
    counts = [r[1] for r in rows]
    max_syms = max(counts)
    avg_syms = sum(counts) / len(counts)
    print(f"\n  Fechas procesadas : {len(rows)}")
    print(f"  Max símbolos/día  : {max_syms}")
    print(f"  Avg símbolos/día  : {avg_syms:.1f}")
    print(f"\n  {'Fecha':<12} {'Símbolos':>9} {'TotalValue':>14}  {'Alerta'}")
    print(f"  {'-'*12} {'-'*9} {'-'*14}  {'-'*20}")
    for date, n, val in rows:
        alerta = ""
        if n < max_syms * 0.85:
            alerta = f"<< GAP ({max_syms - n} símbolos faltantes)"
        elif n < max_syms * 0.95:
            alerta = f"< menor ({max_syms - n} faltantes)"
        val_str = f"${val:>12,.0f}" if val else "     N/A"
        print(f"  {str(date):<12} {n:>9}  {val_str}  {alerta}")

# 2. Símbolos que tienen gaps (no están en TODAS las fechas)
print("\n" + "=" * 70)
print("SÍMBOLOS CON GAPS (faltan fechas respecto al máximo)")
print("=" * 70)

cursor.execute(
    """
    SELECT symbol, COUNT(DISTINCT Date) as n_dates, MIN(Date) as first, MAX(Date) as last
    FROM diaria_performance
    WHERE account = %s AND Date >= %s
    GROUP BY symbol
    ORDER BY n_dates ASC
""",
    (ACCOUNT, DESDE),
)
sym_rows = cursor.fetchall()

if sym_rows:
    total_dates = len(rows)
    print(f"\n  Total fechas esperadas: {total_dates}")
    print(f"\n  {'Symbol':<10} {'Fechas':>7} {'Faltantes':>10}  {'Desde':<12} {'Hasta'}")
    print(f"  {'-'*10} {'-'*7} {'-'*10}  {'-'*12} {'-'*12}")
    for sym, n_dates, first, last in sym_rows:
        faltantes = total_dates - n_dates
        if faltantes > 0:
            print(f"  {sym:<10} {n_dates:>7} {faltantes:>10}  {str(first):<12} {str(last)}")
    completos = sum(1 for _, n, _, _ in sym_rows if total_dates - n == 0)
    print(f"\n  Símbolos sin gaps    : {completos}/{len(sym_rows)}")
    print(f"  Símbolos con algún gap: {len(sym_rows) - completos}/{len(sym_rows)}")

# 3. Fechas con más gaps — top 10
print("\n" + "=" * 70)
print("TOP 10 FECHAS CON MÁS FALTANTES")
print("=" * 70)

if rows:
    sorted_gaps = sorted(rows, key=lambda r: r[1])
    print(f"\n  {'Fecha':<12} {'Símbolos':>9} {'Faltantes':>10}")
    print(f"  {'-'*12} {'-'*9} {'-'*10}")
    for date, n, _ in sorted_gaps[:10]:
        print(f"  {str(date):<12} {n:>9} {max_syms - n:>10}")

# 4. Patrón día de semana
print("\n" + "=" * 70)
print("PATRÓN POR DÍA DE SEMANA (0=Lun, 4=Vie)")
print("=" * 70)

cursor.execute(
    """
    SELECT WEEKDAY(Date) as dow, AVG(cnt) as avg_syms, COUNT(*) as n_dias
    FROM (
        SELECT Date, COUNT(DISTINCT symbol) as cnt
        FROM diaria_performance
        WHERE account = %s AND Date >= %s
        GROUP BY Date
    ) t
    GROUP BY dow
    ORDER BY dow
""",
    (ACCOUNT, DESDE),
)
dow_rows = cursor.fetchall()
dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
if dow_rows:
    print()
    for dow, avg, n in dow_rows:
        print(f"  {dias[dow]}  avg_símbolos={avg:.1f}  días={n}")

# 5. Performa_inversion — gaps en la curva
print("\n" + "=" * 70)
print(f"PERFORMA_INVERSION — gaps en curva {VEHICULO} desde {DESDE}")
print("=" * 70)

cursor.execute(
    """
    SELECT fechaclose,
           SUM(value) as total_value,
           SUM(nr_gyp) as total_nr_gyp,
           COUNT(*) as n_rows
    FROM performa_inversion
    WHERE idcuenta = %s AND vehiculo = %s AND fechaclose >= %s
    GROUP BY fechaclose
    ORDER BY fechaclose
""",
    (ACCOUNT, VEHICULO, DESDE),
)
perf_rows = cursor.fetchall()

if perf_rows:
    values = [r[1] for r in perf_rows if r[1]]
    avg_val = sum(values) / len(values) if values else 0
    print(f"\n  {'Fecha':<12} {'Value':>12} {'NR_GyP':>12} {'Rows':>6}  Alerta")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*6}  {'-'*20}")
    for fecha, val, nr_gyp, n_rows in perf_rows:
        alerta = ""
        if val and val < avg_val * 0.80:
            alerta = "<< CAÍDA"
        elif val and val < avg_val * 0.90:
            alerta = "< baja"
        print(f"  {str(fecha):<12} ${val:>11,.0f} ${nr_gyp:>11,.0f} {n_rows:>6}  {alerta}")
else:
    print("  (sin datos)")

cursor.close()
conn.close()
print("\nDone.")
