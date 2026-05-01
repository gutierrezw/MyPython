"""
run_compare_ib.py
==================
Compara Open Positions de IB (CSV mensual) contra diaria_performance.
Por defecto usa la última fecha disponible en DB; se puede pisar con argumento.

EJECUCIÓN
---------
    cd AppOO
    python AppTest/run_compare_ib.py            # usa MAX(Date) en diaria_performance
    python AppTest/run_compare_ib.py 2026-04-29 # fuerza fecha específica
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime

from Modulos_Mysql import BDsystem

ACCOUNT = "U4214563"

# ── Datos IB hardcodeados (Open Positions al 2026-04-30) ──────────────────────
# Fuente: U4214563_20260401_20260430.csv — sección Posiciones abiertas
# ABX en CAD convertido a USD al tipo 0.73626 (cierre abril)
IB_DATE = date(2026, 4, 30)
IB_POSITIONS = {
    "ABEV": {"qty": 260, "cost": 755.358799, "value": 759.20, "unr_pl": 3.841201},
    "ABX": {"qty": 5, "cost": 187.102876, "value": 196.470981, "unr_pl": 5.107693311},  # CAD→USD
    "AMT": {"qty": 4, "cost": 704.861314, "value": 730.84, "unr_pl": 25.978686},
    "BABA": {"qty": 6, "cost": 1117.85, "value": 791.28, "unr_pl": -326.57},
    "BBAI": {"qty": 255, "cost": 1393.646159, "value": 1014.90, "unr_pl": -378.746159},
    "BIL": {"qty": 6, "cost": 550.332771, "value": 549.84, "unr_pl": -0.492771},
    "BP": {"qty": 10, "cost": 392.498371, "value": 473.80, "unr_pl": 81.301629},
    "BTI": {"qty": 9, "cost": 524.477028, "value": 529.20, "unr_pl": 4.722972},
    "CCI": {"qty": 29, "cost": 2834.185604, "value": 2574.62, "unr_pl": -259.565604},
    "CFRXQ": {"qty": 340, "cost": 727.69891, "value": 0.00, "unr_pl": -727.69891},
    "CHPT": {"qty": 92, "cost": 2840.621939, "value": 589.72, "unr_pl": -2250.901939},
    "CIG": {"qty": 300, "cost": 608.890942, "value": 756.00, "unr_pl": 147.109058},
    "CRNT": {"qty": 597, "cost": 1683.097047, "value": 1498.47, "unr_pl": -184.627047},
    "CTRM": {"qty": 450, "cost": 1877.796703, "value": 927.00, "unr_pl": -950.796703},
    "CVS": {"qty": 19, "cost": 1384.555885, "value": 1582.51, "unr_pl": 197.954115},
    "FMC": {"qty": 75, "cost": 3140.001221, "value": 1153.50, "unr_pl": -1986.501221},
    "HASI": {"qty": 3, "cost": 108.794101, "value": 125.85, "unr_pl": 17.055899},
    "KHC": {"qty": 90, "cost": 2407.560456, "value": 2039.40, "unr_pl": -368.160456},
    "MPT": {"qty": 325, "cost": 1893.032512, "value": 1605.50, "unr_pl": -287.532512},
    "NNDM": {"qty": 1020, "cost": 2269.872061, "value": 1764.60, "unr_pl": -505.272061},
    "NOMD": {"qty": 90, "cost": 1034.407613, "value": 874.80, "unr_pl": -159.607613},
    "PFE": {"qty": 61, "cost": 1675.549654, "value": 1628.70, "unr_pl": -46.849654},
    "PFLT": {"qty": 35, "cost": 398.615106, "value": 313.95, "unr_pl": -84.665106},
    "PHYS": {"qty": 14, "cost": 481.812071, "value": 490.28, "unr_pl": 8.467929},
    "PLUG": {"qty": 213, "cost": 457.006028, "value": 666.69, "unr_pl": 209.683972},
    "PSEC": {"qty": 650, "cost": 2464.368911, "value": 1761.50, "unr_pl": -702.868911},
    "RELX": {"qty": 24, "cost": 761.281285, "value": 878.16, "unr_pl": 116.878715},
    "SKLZ": {"qty": 110, "cost": 1294.229634, "value": 886.60, "unr_pl": -407.629634},
    "SNDL": {"qty": 410, "cost": 1139.706197, "value": 557.60, "unr_pl": -582.106197},
    "SWK": {"qty": 32, "cost": 2667.004361, "value": 2501.12, "unr_pl": -165.884361},
    "TLRY": {"qty": 120, "cost": 2273.688126, "value": 748.80, "unr_pl": -1524.888126},
    "TLT": {"qty": 94, "cost": 8330.666856, "value": 8048.28, "unr_pl": -282.386856},
    "TU": {"qty": 113, "cost": 1587.464748, "value": 1415.89, "unr_pl": -171.574748},
    "UUUU": {"qty": 25, "cost": 424.040505, "value": 541.00, "unr_pl": 116.959495},
    "VALE": {"qty": 87, "cost": 1322.9241, "value": 1423.32, "unr_pl": 100.3959},
    "VGSH": {"qty": 14, "cost": 825.883279, "value": 818.58, "unr_pl": -7.303279},
    "VST": {"qty": 3, "cost": 455.091514, "value": 473.52, "unr_pl": 18.428486},
    "WKHS": {"qty": 20, "cost": 2120.239497, "value": 58.00, "unr_pl": -2062.239497},
    "XIFR": {"qty": 110, "cost": 1891.185876, "value": 1138.50, "unr_pl": -752.685876},
}
IB_TOTAL_UNR = -14123.669490689
# ──────────────────────────────────────────────────────────────────────────────


def main():
    conn = BDsystem.connect_dbase("compare_ib")
    cursor = conn.cursor()

    if len(sys.argv) > 1:
        db_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        cursor.execute(
            "SELECT MAX(Date) FROM diaria_performance WHERE account = %s",
            (ACCOUNT,),
        )
        db_date = cursor.fetchone()[0]
    if db_date is None:
        print("No hay datos en diaria_performance para esta cuenta.")
        cursor.close()
        conn.close()
        return

    cursor.execute(
        """
        SELECT symbol, value, costo_base, nr_gyp, cantidad
        FROM diaria_performance
        WHERE account = %s AND Date = %s
        ORDER BY symbol
        """,
        (ACCOUNT, db_date),
    )
    db_rows = {
        r[0]: {"value": float(r[1] or 0), "cost": float(r[2] or 0), "nr_gyp": float(r[3] or 0), "qty": float(r[4] or 0)}
        for r in cursor.fetchall()
    }
    cursor.close()
    conn.close()

    all_symbols = sorted(set(list(IB_POSITIONS.keys()) + list(db_rows.keys())))

    print("=" * 100)
    print(f"  COMPARACIÓN IB ({IB_DATE}) vs SISTEMA ({db_date})")
    print("=" * 100)
    print(
        f"  {'Symbol':<8} {'IB_qty':>7} {'DB_qty':>7} {'IB_cost':>10} {'DB_cost':>10} "
        f"{'IB_unrPL':>10} {'DB_nr_gyp':>10} {'DELTA':>10}  Estado"
    )
    print(f"  {'-'*8} {'-'*7} {'-'*7} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}  {'-'*20}")

    total_ib = 0.0
    total_db = 0.0
    total_delta = 0.0

    for sym in all_symbols:
        ib = IB_POSITIONS.get(sym)
        db = db_rows.get(sym)

        ib_pl = ib["unr_pl"] if ib else 0.0
        ib_qty = ib["qty"] if ib else 0
        ib_cost = ib["cost"] if ib else 0.0

        db_pl = db["nr_gyp"] if db else 0.0
        db_qty = db["qty"] if db else 0
        db_cost = db["cost"] if db else 0.0

        delta = db_pl - ib_pl

        estados = []
        if ib and not db:
            estados.append("FALTA EN DB")
        if db and not ib:
            estados.append("EXTRA EN DB")
        if ib and db and abs(ib_qty - db_qty) > 0.5:
            estados.append(f"QTY {int(ib_qty)}→{int(db_qty)}")
        if abs(delta) > 50:
            estados.append(f"DELTA ${delta:+.0f}")

        total_ib += ib_pl
        total_db += db_pl
        total_delta += delta

        flag = "  ← " if abs(delta) > 100 or (ib and not db) or (db and not ib) else ""
        print(
            f"  {sym:<8} {ib_qty:>7.0f} {db_qty:>7.0f} ${ib_cost:>9,.2f} ${db_cost:>9,.2f} "
            f"${ib_pl:>9,.2f} ${db_pl:>9,.2f} ${delta:>9,.2f}  {flag}{','.join(estados)}"
        )

    print(
        f"\n  {'TOTAL':<8} {'':>7} {'':>7} {'':>10} {'':>10} "
        f"${total_ib:>9,.2f} ${total_db:>9,.2f} ${total_delta:>9,.2f}"
    )
    print(f"\n  IB total oficial   : ${IB_TOTAL_UNR:>10,.2f}")
    print(f"  Sistema total      : ${total_db:>10,.2f}")
    print(f"  Gap (sistema - IB) : ${total_db - IB_TOTAL_UNR:>10,.2f}")
    print()


if __name__ == "__main__":
    main()
