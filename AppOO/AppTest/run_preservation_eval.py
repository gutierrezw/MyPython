"""
run_preservation_eval.py
Simula evaluación Claude de preservation sin colocar órdenes reales.
Standalone: no importa Class_DashBot ni Class_customer.
NOTA: indicadores técnicos se toman de oportunidadesbuysell (aproximación).
En producción, _build_preservation_context usa DataHub.info[symbol]["datos_tecnicos"] (tiempo real).
"""

import json
import os
import sys
from decimal import Decimal


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_PROFILE = os.path.join(_BASE, "profiles", "main.json")
if os.path.exists(_PROFILE):
    with open(_PROFILE, encoding="utf-8") as _f:
        _cfg = json.load(_f)
    if _cfg.get("db"):
        from Modulos_Mysql import BDsystem

        BDsystem.configure(_cfg["db"])
    if _cfg.get("tmp_path"):
        os.environ["APPOO_TMP"] = _cfg["tmp_path"]

from Modulos_python import logging, yf, np, requests, json
from Modulos_Mysql import BDsystem, MarketScreen, RepositorioOportunidadesBuySell

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

ACCOUNT = "U4214563"
VEHICULO = "Stock"
HAIKU = "claude-haiku-4-5-20251001"


def _enrich_tecnicos(ctx: dict, symbol: str):
    """Agrega RSI/MACD/EMA200/rangos desde oportunidadesbuysell (aproximación standalone).
    En producción usa DataHub.info[symbol]['datos_tecnicos'] (tiempo real)."""
    try:
        conn = BDsystem.connect_dbase("select.oportunidadesbuysell")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT json_detalle FROM oportunidadesbuysell "
            "WHERE symbol = %s AND json_detalle IS NOT NULL AND vehiculo = 'Stock' "
            "ORDER BY timestamp DESC LIMIT 1",
            (symbol,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row or not row[0]:
            return
        det = json.loads(row[0])
        ind_raw = det.get("indicadores")
        ind = json.loads(ind_raw) if isinstance(ind_raw, str) else (ind_raw or {})
        d = ind.get("diaria", {})
        s = ind.get("semanal", {})
        precio = d.get("precio_calculo")
        if d.get("rsi") is not None:
            ctx["rsi_d"] = round(d["rsi"], 1)
        if s.get("rsi") is not None:
            ctx["rsi_w"] = round(s["rsi"], 1)
        macd_val = d.get("macd")
        if macd_val is not None:
            ctx["macd_estado"] = "alcista" if macd_val > 0 else ("bajista" if macd_val < 0 else "neutro")
        ema200 = (d.get("ema(20,50,100,200)") or {}).get("EMA200")
        if ema200 and precio:
            ctx["ema200_rel"] = "sobre" if precio > ema200 else "bajo"
        w13_min, w13_max = d.get("13_semanas_min"), d.get("13_semanas_max")
        if w13_min is not None and w13_max and w13_max > w13_min and precio:
            ctx["rango_13w_pct"] = round((precio - w13_min) / (w13_max - w13_min), 2)
        w26_min, w26_max = s.get("26_semanas_min"), s.get("26_semanas_max")
        if w26_min is not None and w26_max and w26_max > w26_min and s.get("precio_calculo"):
            ctx["rango_26w_pct"] = round((s["precio_calculo"] - w26_min) / (w26_max - w26_min), 2)
    except Exception as e:
        print(f"  _enrich_tecnicos({symbol}): {e}")


def _get_price_atr(symbol: str):
    """Precio actual y ATR(14) vía yfinance. Retorna (last, atr) o (None, None)."""
    try:
        df = yf.download(symbol, period="30d", interval="1d", auto_adjust=True, progress=False)
        if df is None or df.empty:
            return None, None
        close = df["Close"].dropna()
        high = df["High"].dropna()
        low = df["Low"].dropna()
        last = float(close.iloc[-1].item())
        tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
        atr = float(tr.rolling(14).mean().iloc[-1].item())
        return last, atr
    except Exception as e:
        print(f"  yfinance({symbol}): {e}")
        return None, None


def _claude_eval(ctx: dict, api_key: str) -> dict | None:
    """Llama Claude Haiku para afinar el stop. Retorna dict o None si falla."""

    def _v(key, fmt=None, default="N/D"):
        val = ctx.get(key)
        if val is None:
            return default
        try:
            return fmt.format(val) if fmt else str(val)
        except Exception:
            return str(val)

    prompt = (
        f"Eres un agente de preservación de ganancias para un portfolio de inversión.\n"
        f"Las reglas fijas ya activaron la protección de esta posición (ROI >= 10%).\n"
        f"Tu tarea es ajustar el nivel del STOP para maximizar la protección según el contexto.\n\n"
        f"Posición: {ctx['symbol']}\n"
        f"- ROI actual: {_v('roi', '{:.1%}')} | Precio: ${_v('last', '{:.2f}')} | Max histórico: ${_v('max_price', '{:.2f}')}\n"
        f"- Stop base (reglas): ${_v('stop_calculado', '{:.2f}')} | Stop anterior: ${_v('stop_anterior', '{:.2f}')}\n"
        f"- ATR(14): ${_v('atr', '{:.2f}')}\n\n"
        f"Contexto fundamental:\n"
        f"- Consenso: {_v('consenso_tag')} ({_v('consenso_suma')} votos)\n"
        f"- Inst Score: {_v('inst_score')} | 13F Buy ratio: {_v('fh_buy_ratio', '{:.1%}')}\n"
        f"- Analistas: {_v('analyst_rec')} (mean={_v('analyst_mean', '{:.1f}')})\n"
        f"- Sentimiento: {_v('patron')} (score={_v('sentiment_score')})\n\n"
        f"Técnico:\n"
        f"- RSI diario: {_v('rsi_d')} | RSI semanal: {_v('rsi_w')} | MACD: {_v('macd_estado')}\n"
        f"- EMA200: precio {_v('ema200_rel')}\n"
        f"- Rango 13 semanas: {_v('rango_13w_pct', '{:.0%}')} | Rango 26 semanas: {_v('rango_26w_pct', '{:.0%}')}\n\n"
        f"Podés subir el stop (más protección) o mantener el base.\n"
        f"NUNCA sugerir un stop inferior al base calculado por reglas (${ctx['stop_calculado']:.2f}).\n"
        f'Respondé SOLO con JSON válido: {{"stop_sugerido": float, "razon": "str max 120 chars", "urgencia": "alta"|"media"|"baja"}}'
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": HAIKU, "max_tokens": 256, "messages": [{"role": "user", "content": prompt}]},
            timeout=15,
        )
        if not resp.ok:
            print(f"  Claude HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        text = resp.json()["content"][0]["text"].strip()
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            if "stop_sugerido" in result:
                return result
        print(f"  Claude respuesta no parseable: {text}")
    except Exception as e:
        print(f"  Claude error: {e}")
    return None


def main():
    repo = RepositorioOportunidadesBuySell()
    market = MarketScreen()

    sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
    if not sesion:
        print("ERROR: ClaudeAPIP no configurada en tabla sesion")
        return
    api_key = sesion["userapi"].decode("utf-8")

    params_sesion = BDsystem.get_sesion_by_vehiculo(VEHICULO)
    if not params_sesion:
        print(f"ERROR: sesion {VEHICULO} no encontrada")
        return

    try:
        params_raw = params_sesion.get("parameters") or b"{}"
        pconfig = json.loads(params_raw.decode("utf-8") if isinstance(params_raw, bytes) else params_raw)
        preservation = pconfig.get("preservation", {})
    except Exception as e:
        print(f"ERROR parseando parameters: {e}")
        return

    roi_minimo = preservation.get("roi_minimo", 0.10)
    correccion_pct = preservation.get("correccion_pct", 0.08)
    atr_mult = preservation.get("atr_mult", 2.0)
    proteccion_base = preservation.get("proteccion_base", 0.50)

    print(f"\n{'='*60}")
    print(f"Preservation eval — {VEHICULO} | roi_min={roi_minimo:.0%} | account={ACCOUNT}")
    print(f"{'='*60}\n")

    positions = repo.select_inversion(tipoin=VEHICULO, ticket="all")
    candidatas = 0

    for pos in positions:
        symbol = pos.get("ticket")
        costobase = pos.get("costobase", 0)
        unrealizedpnl = pos.get("unrealizedpnl", 0)
        position_qty = pos.get("position", 0)

        if costobase <= 0 or position_qty <= 0:
            continue

        roi = unrealizedpnl / costobase
        if roi < roi_minimo:
            continue

        candidatas += 1
        print(f"[{symbol}] ROI={roi:.1%} | qty={position_qty} | pnl=${unrealizedpnl:.2f}")

        last, atr = _get_price_atr(symbol)
        if not last:
            print(f"  → sin precio yfinance, SKIP\n")
            continue
        if not atr:
            print(f"  → sin ATR yfinance, SKIP\n")
            continue

        max_price = last
        stop_calculado = max_price - max(correccion_pct * max_price, atr_mult * atr)
        stop_anterior = 0.0
        base_limit = unrealizedpnl * proteccion_base

        ctx = market.select_preservation_context(symbol, ACCOUNT)
        ctx.update(
            {
                "symbol": symbol,
                "roi": roi,
                "last": last,
                "max_price": max_price,
                "stop_calculado": stop_calculado,
                "stop_anterior": stop_anterior,
                "atr": atr,
                "base_limit": base_limit,
            }
        )
        _enrich_tecnicos(ctx, symbol)

        print(
            f"  consenso={ctx.get('consenso_tag')} | inst={ctx.get('inst_score')} | patron={ctx.get('patron')}\n"
            f"  RSI_d={ctx.get('rsi_d')} | RSI_w={ctx.get('rsi_w')} | MACD={ctx.get('macd_estado')} | "
            f"EMA200={ctx.get('ema200_rel')} | R13w={ctx.get('rango_13w_pct')} | R26w={ctx.get('rango_26w_pct')}"
        )
        print(f"  last={last:.2f} | ATR={atr:.2f} | stop_calculado={stop_calculado:.2f}")

        claude_result = _claude_eval(ctx, api_key)

        if claude_result:
            stop_sugerido = claude_result.get("stop_sugerido", stop_calculado)
            stop_final = max(stop_calculado, stop_sugerido)
            print(f"  CLAUDE → stop_sugerido={stop_sugerido:.2f} | urgencia={claude_result.get('urgencia')}")
            print(f"  razon: {claude_result.get('razon')}")
            print(f"  stop_final={stop_final:.2f}")
        else:
            stop_final = stop_calculado
            print(f"  CLAUDE → sin respuesta | stop_final={stop_final:.2f} (reglas)")

        det = {
            "tipo": "preservation_stop",
            "decision": {
                k: ctx.get(k) for k in ("consenso_tag", "inst_score", "fh_buy_ratio", "patron", "rsi_d", "macd_estado")
            },
            "claude": claude_result,
            "resultado": {"stop_final": round(stop_final, 4)},
        }
        print(f"  json_detalle: {json.dumps(det, ensure_ascii=False, cls=_Enc)}\n")

    if candidatas == 0:
        print(f"Sin posiciones con ROI >= {roi_minimo:.0%}")


if __name__ == "__main__":
    main()
