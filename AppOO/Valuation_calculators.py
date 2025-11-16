# calculators.py
"""
Módulo de cálculos financieros para el Valuation Engine.

Funciones principales:
- calc_valuations(metrics, price, is_reit)
  Recibe un dict `metrics` (valores TTM y shares) y el precio de mercado,
  y devuelve un dict con múltiplos, valores intrínsecos y métricas clave.

Notas:
- `metrics` espera claves (pueden ser None):
    NetIncome, OperatingCashFlow, CapitalExpenditures,
    SharesOutstanding, FFO, AFFO, DividendsPaid, Revenues
- Todos los cálculos manejan None/0 de forma segura.
- Las fórmulas DDM y DCF son implementaciones simples (configurables).
"""

from typing import Dict, Any, Optional


def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """División segura: retorna None si no es posible."""
    try:
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator
    except Exception:
        return None


def _round_or_none(val: Optional[float], ndigits: int = 3) -> Optional[float]:
    if val is None:
        return None
    try:
        return round(val, ndigits)
    except Exception:
        return None


def calc_valuations(metrics: Dict[str, Any], price: Optional[float], is_reit: bool) -> Dict[str, Any]:
    """
    Calcula múltiplos y valores intrínsecos a partir de las métricas agregadas.

    Retorna un diccionario con:
     - múltiplos (P/E, P/S, P/FCF, P/FFO, P/AFFO)
     - métricas por acción (EPS, FCF, FFO_per_share, AFFO_per_share, dividend_per_share)
     - valores intrínsecos (DDM_value, DCF_value_per_share)
     - valores base (NetIncome, Revenues, OCF, CapEx, SharesOutstanding, DividendsPaid, FFO, AFFO)
    """

    out: Dict[str, Any] = {}

    # Extraer métricas (esperadas como absolutos TTM, o None)
    shares = metrics.get("SharesOutstanding")
    net_income = metrics.get("NetIncome")
    revenues = metrics.get("Revenues")
    ocf = metrics.get("OperatingCashFlow")
    capex = metrics.get("CapitalExpenditures")
    dividends_paid = metrics.get("DividendsPaid")
    ffo = metrics.get("FFO")
    affo = metrics.get("AFFO")

    # -----------------------
    # EPS
    # -----------------------
    eps = None
    if isinstance(net_income, (int, float)) and isinstance(shares, (int, float)) and shares != 0:
        eps = net_income / shares
    out["EPS"] = _round_or_none(eps, 6)

    # -----------------------
    # Free cash flow (FCF) = OCF - CapEx (TTM)
    # -----------------------
    fcf = None
    if isinstance(ocf, (int, float)) and isinstance(capex, (int, float)):
        fcf = ocf - capex
    out["FCF"] = _round_or_none(fcf, 2)

    # -----------------------
    # Múltiplos (usar precio / métrica_por_accion)
    # -----------------------
    # helper: precio por acción si shares está disponible
    price_per_share = price

    # P/E
    pe = None
    if price_per_share and eps and eps != 0:
        try:
            pe = price_per_share / eps
        except Exception:
            pe = None
    out["P/E"] = _round_or_none(pe, 3)

    # P/S
    ps = None
    if price_per_share and revenues and shares and shares != 0:
        rev_per_share = _safe_div(revenues, shares)
        if rev_per_share:
            ps = _safe_div(price_per_share, rev_per_share)
    out["P/S"] = _round_or_none(ps, 3)

    # P/FCF
    p_fcf = None
    if price_per_share and fcf and shares and shares != 0:
        fcf_per_share = _safe_div(fcf, shares)
        if fcf_per_share:
            p_fcf = _safe_div(price_per_share, fcf_per_share)
    out["P/FCF"] = _round_or_none(p_fcf, 3)

    # -----------------------
    # REIT metrics: FFO / AFFO per share and multiples
    # -----------------------
    ffo_per_share = None
    affo_per_share = None
    p_ffo = None
    p_affo = None

    if isinstance(ffo, (int, float)) and isinstance(shares, (int, float)) and shares != 0:
        ffo_per_share = ffo / shares

    if isinstance(affo, (int, float)) and isinstance(shares, (int, float)) and shares != 0:
        affo_per_share = affo / shares

    if price_per_share and ffo_per_share and ffo_per_share != 0:
        p_ffo = price_per_share / ffo_per_share

    if price_per_share and affo_per_share and affo_per_share != 0:
        p_affo = price_per_share / affo_per_share

    out["FFO_per_share"] = _round_or_none(ffo_per_share, 6)
    out["AFFO_per_share"] = _round_or_none(affo_per_share, 6)
    out["P/FFO"] = _round_or_none(p_ffo, 3)
    out["P/AFFO"] = _round_or_none(p_affo, 3)

    # -----------------------
    # Dividend per share (usar Abs(dividends_paid) porque en XBRL puede venir negativo)
    # -----------------------
    dividend_per_share = None
    if isinstance(dividends_paid, (int, float)) and isinstance(shares, (int, float)) and shares != 0:
        try:
            dividend_per_share = abs(dividends_paid) / shares
        except Exception:
            dividend_per_share = None
    out["Dividend_per_share"] = _round_or_none(dividend_per_share, 6)

    # -----------------------
    # DDM (Gordon Growth) simple
    # - sólo si dividend_per_share disponible y >0
    # - parámetros por defecto: g=0.03, r=0.09 (estos pueden parametrizarse más adelante)
    # -----------------------
    ddo = None
    if dividend_per_share and dividend_per_share > 0:
        g = 0.03
        r = 0.09
        if r > g:
            try:
                ddo = (dividend_per_share * (1 + g)) / (r - g)
            except Exception:
                ddo = None
    out["DDM_value"] = _round_or_none(ddo, 3)

    # -----------------------
    # DCF simple sobre FCF per share (proyección 5 años + terminal)
    # - parámetros por defecto: growth=0.03, discount=0.09, years=5
    # - requiere FCF (TTM) y shares
    # -----------------------
    dcf_value_per_share = None
    if fcf and isinstance(shares, (int, float)) and shares != 0:
        try:
            fcf_per_share = _safe_div(fcf, shares)
            if fcf_per_share:
                growth = 0.03
                discount = 0.09
                years = 5
                pv = 0.0
                for t in range(1, years + 1):
                    pv += (fcf_per_share * ((1 + growth) ** t)) / ((1 + discount) ** t)
                # terminal: perpetuity on last year's cash flow
                if discount > growth:
                    terminal = (fcf_per_share * ((1 + growth) ** years)) / (discount - growth)
                    pv += terminal / ((1 + discount) ** years)
                dcf_value_per_share = pv
        except Exception:
            dcf_value_per_share = None

    out["DCF_value_per_share"] = _round_or_none(dcf_value_per_share, 3)

    # -----------------------
    # Incluir los valores base sin formatear (para trazabilidad)
    # -----------------------
    out["SharesOutstanding"] = shares
    out["NetIncome"] = net_income
    out["Revenues"] = revenues
    out["OperatingCashFlow"] = ocf
    out["CapitalExpenditures"] = capex
    out["DividendsPaid"] = dividends_paid
    out["FFO"] = ffo
    out["AFFO"] = affo
    out["Price"] = price_per_share
    out["is_reit"] = bool(is_reit)

    return out
