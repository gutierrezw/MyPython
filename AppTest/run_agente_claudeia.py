"""Fuerza una ejecución del Agente_ClaudeIA sin la app.
Lee posiciones desde BD, llama a Claude y guarda en ia_trace.
Ejecutar: python ../AppTest/run_agente_claudeia.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "AppOO"))

import Modulos_python  # noqa: F401
import requests
from Modulos_Mysql import BDsystem, IaTraceScreen, PlanInversion

with open(os.path.join(os.path.dirname(__file__), "..", "AppOO", "profiles", "main.json"), encoding="utf-8") as _f:
    BDsystem.configure(json.load(_f).get("db", {}))


def _load_params(vehiculo):
    ses = BDsystem.get_sesion_by_vehiculo(vehiculo)
    raw = ses.get("parameters")
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)


def _build_context(account, params):
    ia_config = params.get("agente_ia", {})
    gc_config = params.get("gains_capture", {})
    pinvertir = float(ia_config.get("monto_por_trade", 170))
    min_ganancia = float(gc_config.get("min_ganancia", 100.0))

    plan = PlanInversion()
    positions = plan.select_inversion(tipoin="Stock", ticket="all") or []

    portfolio = []
    for p in positions:
        if p.get("useraccount") != account:
            continue
        costo = float(p.get("costobase") or 0)
        mkt = float(p.get("mktvalue") or 0)
        gain_usd = round(mkt - costo, 2) if costo > 0 else 0
        roi_pct = round(gain_usd / costo * 100, 2) if costo > 0 else 0
        portfolio.append(
            {
                "symbol": p.get("ticket"),
                "roi_pct": roi_pct,
                "valor_mkt": round(mkt, 2),
                "gain_usd": gain_usd,
                "gains_candidate": gain_usd >= min_ganancia,
                "dividends": round(float(p.get("dividends") or 0), 2),
            }
        )

    ia_db = IaTraceScreen()
    candidatos = ia_db.select_candidatos_ia(account, consenso_min=ia_config.get("gate_consenso_min", 4))
    for c in candidatos:
        last = float(c.get("lastPrice") or 0)
        c["monto_sugerido"] = max(pinvertir, last) if last > 0 else pinvertir

    return {
        "portfolio": portfolio,
        "candidatos": candidatos,
        "pinvertir": pinvertir,
        "min_ganancia": min_ganancia,
    }


def _call_claude(ctx, params, api_key):
    ia_config = params.get("agente_ia", {})

    def _port_txt():
        if not ctx["portfolio"]:
            return "  (sin posiciones)"
        return "\n".join(
            f"  {p['symbol']}: ROI={p['roi_pct']:+.1f}% | mkt=${p['valor_mkt']:.0f} | "
            f"gain=${p['gain_usd']:.0f}" + (" [GAINS?]" if p.get("gains_candidate") else "")
            for p in ctx["portfolio"]
        )

    def _cand_txt():
        if not ctx["candidatos"]:
            return "  (sin candidatos)"
        return "\n".join(
            f"  {c['symbol']} ({(c.get('shortName') or '')[:20]}): "
            f"consenso_suma={c.get('consenso_suma')} inst_score={c.get('inst_score') or '-'} "
            f"yield={c.get('dividendYield') or '-'} monto_sugerido=${c.get('monto_sugerido', 0):.0f}"
            for c in ctx["candidatos"]
        )

    gains_syms = [p["symbol"] for p in ctx["portfolio"] if p.get("gains_candidate")]
    gains_txt = f"Posiciones con ganancia ≥${ctx['min_ganancia']:.0f}: " + (
        ", ".join(gains_syms) if gains_syms else "(ninguna)"
    )

    from datetime import datetime

    prompt = (
        "Sos el agente de inversión autónomo. Misión: acumular capital hacia 1.2M USD en 2030 "
        "generando ingresos pasivos ≥3%/año. Foco en dividendos, uso moderado de apalancamiento IB. "
        "En crisis → Hold o sumar posiciones, nunca vender por pánico.\n\n"
        f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Portfolio actual (Stock):\n{_port_txt()}\n\n"
        f"{gains_txt}\n\n"
        f"Candidatos de entrada (consenso ≥ {ia_config.get('gate_consenso_min', 4)}):\n{_cand_txt()}\n\n"
        f"Límites: monto_base=${ctx['pinvertir']:.0f} (ajusta al precio) | "
        f"leverage_max={ia_config.get('leverage_max', 1.8)}x | "
        f"inst_score_min={ia_config.get('gate_inst_score_min', 0.5)}\n\n"
        "Para BUY: usá el monto_sugerido del candidato elegido. "
        "Para [GAINS?]: evaluá si el contexto justifica captura parcial (SELL) u HOLD.\n\n"
        "Producí UNA decisión con formato JSON exacto:\n"
        '{"decision": "BUY|SELL|HOLD|ALERTA", "simbolo": "TICKER_O_VACIO", '
        '"monto": 0, "motivo": "max 150 chars"}'
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"].strip()
    usage = resp.json().get("usage", {})
    print(f"  Tokens: input={usage.get('input_tokens')} output={usage.get('output_tokens')}")
    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        result = json.loads(text[start:end])
        if "decision" in result:
            return result
    raise ValueError(f"Claude no retornó JSON válido: {text}")


def main():
    print("=== run_agente_claudeia.py ===")

    params = _load_params("Stock")
    ia_config = params.get("agente_ia", {})
    print(f"activo={ia_config.get('activo')} | monto_por_trade={ia_config.get('monto_por_trade')}")

    ses_stock = BDsystem.get_sesion_by_vehiculo("Stock")
    account = ses_stock["idcuenta"]
    print(f"account={account}")

    ses_claude = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
    api_key = ses_claude["userapi"].decode("utf-8") if ses_claude else ""
    if not api_key:
        print("ERROR: ClaudeAPIP sin API key")
        return

    print("\nConstruyendo contexto...")
    ctx = _build_context(account, params)
    print(f"  Portfolio: {len(ctx['portfolio'])} posiciones")
    print(f"  Candidatos: {len(ctx['candidatos'])} activos")
    gains = [p["symbol"] for p in ctx["portfolio"] if p.get("gains_candidate")]
    if gains:
        print(f"  Gains candidates: {gains}")

    print("\nLlamando a Claude...")
    decision = _call_claude(ctx, params, api_key)
    print(f"\n  Decisión: {json.dumps(decision, ensure_ascii=False, indent=2)}")

    ia_db = IaTraceScreen()
    trace_id = ia_db.insert_trace(
        vehiculo="Stock",
        simbolo=decision.get("simbolo", ""),
        decision=decision.get("decision", "HOLD"),
        monto=decision.get("monto", 0),
        motivo=decision.get("motivo", ""),
        gates_ok={"forzado": True, "origen": "run_agente_claudeia.py"},
    )
    print(f"\n  ✅ Guardado en ia_trace — id={trace_id}")

    # Actualiza last_run en agents_schedule.json para que el agente no corra de nuevo inmediatamente
    from Modulos_Utilitarios import read_json_tmp, write_json_tmp

    sched = read_json_tmp("agents_schedule.json")
    sched["Agente_ClaudeIA"] = time.time()
    write_json_tmp("agents_schedule.json", sched)
    print("  ✅ agents_schedule.json actualizado — próxima ejecución en 24h")


if __name__ == "__main__":
    main()
