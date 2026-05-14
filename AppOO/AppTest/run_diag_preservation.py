"""
Diagnóstico del pipeline de datos para Agente_ManagerPreservation (Stock).

Valida cada fuente de datos sin enviar ninguna orden al broker.
Ejecutar con IB conectado para validar precios live; sin IB muestra qué falla.

Uso: python AppTest/run_diag_preservation.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from Modulos_python import logging
from Modulos_Mysql import PlanInversion, BDsystem
from Modulos_Utilitarios import read_json_tmp

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("DiagPreservation")

ROI_MINIMO = 0.10
VEHICULO = "Stock"

VERDE = "\033[92m"
ROJO = "\033[91m"
AMARILLO = "\033[93m"
RESET = "\033[0m"


def ok(msg):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def warn(msg):
    print(f"  {AMARILLO}[WARN]{RESET} {msg}")


def fail(msg):
    print(f"  {ROJO}[FAIL]{RESET} {msg}")


# ─── 1. Sesión y configuración de BD ─────────────────────────────────────────
print("\n=== 1. Sesión y config preservation ===")
try:
    pi = PlanInversion()
    sesion = pi.get_sesion_by_vehiculo(VEHICULO)
    account = sesion["idcuenta"]
    ok(f"Sesión Stock: account={account}")

    import json

    params_raw = sesion.get("parameters")
    if not params_raw:
        fail("sesion.parameters vacío — preservation config no encontrada")
        sys.exit(1)
    params = json.loads(params_raw.decode("utf-8") if isinstance(params_raw, bytes) else params_raw)
    pconfig = params.get("preservation")
    if not pconfig:
        fail("Bloque 'preservation' no encontrado en parameters")
        sys.exit(1)
    ok(
        f"Config preservation: roi_min={pconfig.get('roi_minimo')} | prot={pconfig.get('proteccion_base')} | atr_mult={pconfig.get('atr_mult')}"
    )
except Exception as e:
    fail(f"Error cargando sesión: {e}")
    sys.exit(1)

# ─── 2. Posiciones desde BD ───────────────────────────────────────────────────
print("\n=== 2. Posiciones activas (inversion) ===")
try:
    positions = pi.select_inversion(tipoin=VEHICULO, ticket="all")
    ok(f"{len(positions)} posiciones cargadas")
    elegibles = []
    for p in positions:
        sym = p.get("ticket")
        costobase = p.get("costobase", 0)
        unrealizedpnl = p.get("unrealizedpnl", 0)
        position_qty = p.get("position", 0)
        conid = p.get("conid")
        mrkprice = p.get("mrkprice", 0)

        if costobase <= 0 or position_qty <= 0:
            continue
        roi = unrealizedpnl / costobase
        if roi < ROI_MINIMO:
            continue

        elegibles.append(p)
        conid_ok = "OK" if conid else "FALTA"
        print(
            f"    {sym}: ROI={roi:.1%} | costobase={costobase:.2f} | unrealizedpnl={unrealizedpnl:.2f} | conid={conid}[{conid_ok}] | mrkprice={mrkprice:.2f}"
        )

    if not elegibles:
        warn(f"Sin posiciones con ROI ≥ {ROI_MINIMO:.0%} — nada para preservar")
    else:
        ok(f"{len(elegibles)} posiciones elegibles para preservation")
except Exception as e:
    fail(f"Error cargando posiciones: {e}")

# ─── 3. Estado persistido (preservation_state.json) ──────────────────────────
print("\n=== 3. Estado persistido (preservation_state.json) ===")
try:
    state = read_json_tmp("preservation_state.json")
    if not state:
        warn("preservation_state.json vacío o inexistente — primer arranque")
    else:
        ok(f"{len(state)} símbolos con estado guardado:")
        for sym, s in state.items():
            print(
                f"    {sym}: stop_actual={s.get('stop_actual', 0):.2f} | max_price={s.get('max_price', 0):.2f} | last_check={s.get('last_check', '?')}"
            )
except Exception as e:
    fail(f"Error leyendo preservation_state.json: {e}")

# ─── 4. Precios live (DataHub.info — requiere IB conectado) ──────────────────
print("\n=== 4. Precios live (DataHub.info / websocket) ===")
try:
    from Class_customer import DataHub

    for p in elegibles:
        sym = p.get("ticket")
        mrkprice = p.get("mrkprice", 0)
        info_sym = DataHub.info.get(sym, {})
        ws = info_sym.get("websocket", {})
        last_ws = ws.get("last")
        if last_ws:
            ok(f"{sym}: last (websocket) = {last_ws:.2f}")
        elif mrkprice:
            warn(f"{sym}: websocket sin precio — usando mrkprice={mrkprice:.2f} (fallback BD)")
        else:
            fail(f"{sym}: sin precio disponible (IB offline + mrkprice=0)")
except Exception as e:
    fail(f"Error accediendo DataHub.info: {e}")

# ─── 5. ATR (CacheHut + yfinance fallback) ───────────────────────────────────
print("\n=== 5. ATR (CacheHut + yfinance fallback) ===")
try:
    for p in elegibles:
        sym = p.get("ticket")
        atr, atr_err = DataHub.preservation_get_atr(sym, VEHICULO)
        if atr is not None:
            ok(f"{sym}: ATR = {atr:.4f}")
        else:
            fail(f"{sym}: ATR no disponible — {atr_err}")
except Exception as e:
    fail(f"Error calculando ATR: {e}")

# ─── 6. IB live orders (requiere IB conectado) ───────────────────────────────
print("\n=== 6. Órdenes PRESERVATION abiertas en IB (get_preservation_stops) ===")
try:
    from Class_ApiIBrks import IB

    ib = IB()
    stp_orders = ib.get_preservation_stops()
    if stp_orders:
        ok(f"{len(stp_orders)} stops activos en IB:")
        for o in stp_orders:
            print(f"    {o['symbol']}: stop={o['stop_price']} | status={o['status']} | orderId={o['order_id']}")
    else:
        warn("Sin stops preservation en IB")
        stp_orders = []  # para el bloque siguiente
    if not stp_orders:
        warn("Sin órdenes STP SELL — ningún stop colocado en IB (esperado en dry-run)")
except Exception as e:
    warn(f"IB no accesible desde script standalone: {e}")

# ─── 7. Seguridad — verificar que live_enabled=False ────────────────────────
print("\n=== 7. Safety check ===")
try:
    from Class_customer import DataHub as DH

    if not DH.preservation_live_enabled:
        ok("DataHub.preservation_live_enabled = False — órdenes BLOQUEADAS (correcto para dry-run)")
    else:
        fail("DataHub.preservation_live_enabled = True — ¡ÓRDENES HABILITADAS! Verificar si es intencional")
except Exception as e:
    warn(f"No se pudo verificar preservation_live_enabled: {e}")

print("\n=== Diagnóstico completo ===\n")
