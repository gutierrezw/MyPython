from Modulos_python import (
    os,
    webbrowser,
    logging,
)

_logger = logging.getLogger("TradingView")

# Símbolo TradingView por vehículo: prefijo del exchange
_EXCHANGE_PREFIX = {
    "Crypto": "BINANCE:",
    "Stock": "",
    "FCI": "",
}


def _tv_symbol(symbol, vehiculo):
    """Convierte símbolo interno al formato TradingView según vehículo."""
    prefix = _EXCHANGE_PREFIX.get(vehiculo, "")
    return f"{prefix}{symbol}"


def _html_panel_lotes(lotes, posicion):
    """
    Genera el bloque HTML del panel de lotes.

    lotes: lista de dicts con keys: precio, cantidad, costo lote, gyp, roi, fechahora
    posicion: dict con keys: avgcost, costo_base, position, objetivo, last
    """
    avgcost = posicion.get("avgcost") or posicion.get("avgCost") or 0
    costo_base = posicion.get("costo_base") or posicion.get("costobase") or 0
    position = posicion.get("position") or 0
    last = posicion.get("last") or posicion.get("mrkprice") or 0

    filas_lotes = ""
    for i, lote in enumerate(lotes or [], start=1):
        precio = lote.get("precio") or lote.get("costo lote", 0)
        cantidad = lote.get("cantidad", 0)
        gyp = lote.get("gyp", 0)
        roi = lote.get("roi", 0)
        fecha = lote.get("fechahora", "")
        color = "#00FF88" if gyp >= 0 else "#FF6060"
        filas_lotes += f"""
        <tr>
          <td style="color:#aaa">{i}</td>
          <td>{fecha}</td>
          <td style="text-align:right">{precio:,.2f}</td>
          <td style="text-align:right">{cantidad:,.4f}</td>
          <td style="text-align:right; color:{color}">{gyp:+,.2f}</td>
          <td style="text-align:right; color:{color}">{roi:+.1%}</td>
        </tr>"""

    gyp_total = (last * position - costo_base) if last and position and costo_base else 0
    roi_total = (gyp_total / costo_base) if costo_base else 0
    color_total = "#00FF88" if gyp_total >= 0 else "#FF6060"

    return f"""
    <div class="section-title">POSICIÓN</div>
    <table class="data-table">
      <tr><td class="lbl">Precio medio</td><td class="val">{avgcost:,.2f}</td></tr>
      <tr><td class="lbl">Cantidad</td><td class="val">{position:,.4f}</td></tr>
      <tr><td class="lbl">Costo base</td><td class="val">{costo_base:,.2f}</td></tr>
      <tr><td class="lbl">Precio actual</td><td class="val">{last:,.2f}</td></tr>
      <tr><td class="lbl">G/P</td>
          <td class="val" style="color:{color_total}">{gyp_total:+,.2f} ({roi_total:+.1%})</td></tr>
    </table>

    <div class="section-title" style="margin-top:16px">LOTES</div>
    <table class="lotes-table">
      <thead>
        <tr>
          <th>#</th><th>Fecha</th><th>Precio</th><th>Cant.</th><th>G/P</th><th>ROI</th>
        </tr>
      </thead>
      <tbody>{filas_lotes}</tbody>
    </table>"""


def _html_panel_estrategia(posicion):
    """
    Genera el bloque HTML del panel de estrategia (objetivo, SL, R/R).

    posicion: dict con keys: last, objetivo, stop_loss (o sl), avgcost
    """
    last = posicion.get("last") or posicion.get("mrkprice") or 0
    objetivo = posicion.get("objetivo") or 0
    sl = posicion.get("stop_loss") or posicion.get("sl") or 0
    avgcost = posicion.get("avgcost") or posicion.get("avgCost") or 0

    obj_pct = ((objetivo - avgcost) / avgcost) if avgcost and objetivo else 0
    sl_pct = ((sl - avgcost) / avgcost) if avgcost and sl else 0
    rr = abs(obj_pct / sl_pct) if sl_pct else 0

    return f"""
    <div class="section-title" style="margin-top:16px">ESTRATEGIA</div>
    <table class="data-table">
      <tr><td class="lbl">Actual</td>
          <td class="val" style="color:cyan">{last:,.2f}</td></tr>
      <tr><td class="lbl">Objetivo</td>
          <td class="val" style="color:#00FF88">{objetivo:,.2f}
            <span style="font-size:10px;color:#00FF88"> ({obj_pct:+.1%})</span></td></tr>
      <tr><td class="lbl">Ref. SL</td>
          <td class="val" style="color:#FF6060">{sl:,.2f}
            <span style="font-size:10px;color:#FF6060"> ({sl_pct:+.1%})</span></td></tr>
      <tr><td class="lbl">R/R</td>
          <td class="val">1:{rr:.1f}</td></tr>
    </table>"""


def _html_full(symbol, vehiculo, posicion, lotes):
    """Genera el HTML completo: widget TV (izquierda) + panel datos (derecha)."""
    tv_symbol = _tv_symbol(symbol, vehiculo)
    panel_lotes = _html_panel_lotes(lotes, posicion)
    panel_estrategia = _html_panel_estrategia(posicion)

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{symbol} — TradingView</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #131722; color: #d1d4dc; font-family: Arial, sans-serif; font-size: 12px;
           display: flex; height: 100vh; overflow: hidden; }}
    #tv-container {{ flex: 1; min-width: 0; }}
    #panel {{ width: 280px; min-width: 280px; background: #1e2130; padding: 12px;
              overflow-y: auto; border-left: 1px solid #2a2e39; }}
    .section-title {{ color: #787b86; font-size: 10px; text-transform: uppercase;
                      letter-spacing: 1px; margin-bottom: 6px; border-bottom: 1px solid #2a2e39;
                      padding-bottom: 4px; }}
    .data-table {{ width: 100%; border-collapse: collapse; }}
    .data-table td {{ padding: 3px 0; }}
    .lbl {{ color: #787b86; width: 50%; }}
    .val {{ color: #d1d4dc; text-align: right; }}
    .lotes-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    .lotes-table th {{ color: #787b86; text-align: right; padding: 2px 2px;
                       border-bottom: 1px solid #2a2e39; }}
    .lotes-table th:first-child {{ text-align: left; }}
    .lotes-table td {{ padding: 2px 2px; border-bottom: 1px solid #1e2130; }}
    .lotes-table td:first-child {{ color: #787b86; }}
  </style>
</head>
<body>
  <div id="tv-container">
    <div class="tradingview-widget-container" style="height:100%; width:100%;">
      <div id="tradingview_chart" style="height:100%; width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1",
        "locale": "es",
        "toolbar_bg": "#131722",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "withdateranges": true,
        "save_image": true,
        "details": true,
        "load_chart_as_image": false,
        "load_last_chart": true,
        "container_id": "tradingview_chart"
      }});
      </script>
    </div>
  </div>
  <div id="panel">
    {panel_lotes}
    {panel_estrategia}
  </div>
</body>
</html>"""


def abrir_tradingview(symbol, vehiculo="Stock", posicion=None, lotes=None):
    """
    Genera el HTML con widget TradingView + panel de lotes/estrategia y lo abre en el browser.

    Args:
        symbol: símbolo del activo
        vehiculo: "Stock" | "Crypto" | "FCI"
        posicion: dict con avgcost, costo_base, position, last, objetivo, stop_loss
        lotes: lista de dicts de get_lotesGainLost
    """
    try:
        posicion = posicion or {}
        lotes = lotes or []
        html = _html_full(symbol, vehiculo, posicion, lotes)

        tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        html_path = os.path.join(tmp_dir, f"tv_{symbol}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        webbrowser.open(f"file:///{html_path.replace(os.sep, '/')}")
        _logger.warning(f"TradingView abierto: {symbol} ({vehiculo})")
    except Exception as e:
        _logger.error(f"abrir_tradingview({symbol}): {e}")
