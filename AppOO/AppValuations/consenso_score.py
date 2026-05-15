"""
Módulo: consenso_score.py
Propósito: Definición canónica del modelo de Señales de Consenso para cartera de dividendos.

RESUMEN DEL MODELO
==================
El Consenso Score combina 6 señales independientes para sintetizar la alineación
institucional, de analistas, del modelo IA y de valuación de cada activo en cartera.
Cada señal emite un voto:  +1 (favorable) | 0 (neutral) | -1 (desfavorable) | None (abstiene)
El score final es  suma / n_activos → clasifica en 6 niveles de acción.

SEÑALES (6 votos)
=================
1. Net         — Flujo neto institucional 13F (buy_ratio - sell_ratio), ranking relativo
2. Options     — Ratio CALL/(CALL+PUT) en posiciones de opciones 13F
3. Analistas   — Recomendación de Wall Street (yfinance recommendationKey)
4. Modelo IA   — Señal del modelo propio (CSVs buy/sell generados por el IA)
5. Valuación   — Clasificación fundamental del activo (categoriaActivo)
6. Cobertura   — Número de fondos institucionales con posición en el activo

NIVELES DE CONSENSO
===================
★ UNÁNIME   — todos los votos activos coinciden positivamente   → máxima convicción
▲ CONSENSO  — pct ≥ 0.60                                       → comprar / acumular
↗ TENDENCIA — pct ≥ 0.20                                       → mantener / aumentar
→ NEUTRO    — pct > -0.20                                      → observar
↘ ALERTA    — pct > -0.60                                      → reducir / revisar
▼ SALIDA    — pct ≤ -0.60                                      → salir / no entrar

SEÑAL INSTITUCIONAL (Inst Señal — resumen 13F + yfinance)
==========================================================
ACOMPAÑAR   — inst_score ≥ 0.40 AND buy_ratio ≥ 0.50 AND fh_count ≥ 20
MANTENER    — inst_score ≥ 0.25 OR fh_count ≥ 10
REVISAR     — resto

inst_score = inst_ownership_pct * 0.40 + log(max(fh_count,1)) * 0.40 + fh_buy_ratio * 0.20
"""

# ---------------------------------------------------------------------------
# Umbrales del modelo (fuente única de verdad)
# ---------------------------------------------------------------------------

# Voto Net — ranking relativo sobre cartera (percentiles calculados en tiempo de ejecución)
# p33, p67 = _build_net_percentiles(fh_cartera)   top 33% → +1 | medio → 0 | bottom → -1

# Voto Options
CALL_RATIO_POSITIVO = 0.60  # calls/(calls+puts) ≥ 0.60 → +1
CALL_RATIO_NEUTRO = 0.40  # calls/(calls+puts) ≥ 0.40 → 0   (< 0.40 → -1)

# Voto Cobertura (fh_count = número de fondos con posición)
FH_COUNT_POSITIVO = 20  # ≥ 20 fondos → +1
FH_COUNT_NEUTRO = 5  # ≥  5 fondos → 0   (< 5 → -1)

# Señal Institucional compuesta
INST_SCORE_ACOMPANAR = 0.40
BUY_RATIO_ACOMPANAR = 0.50
FH_COUNT_ACOMPANAR = 20
INST_SCORE_MANTENER = 0.25
FH_COUNT_MANTENER = 10

# inst_score blending weights
INST_SCORE_W_YFINANCE = 0.40  # inst_ownership_pct
INST_SCORE_W_FH_COUNT = 0.40  # log(max(fh_count, 1))
INST_SCORE_W_BUY_RATIO = 0.20  # fh_buy_ratio

# Tabla de decisión (pct = suma / n_activos)
NIVEL_UNANIME = None  # suma == n (todos positivos)
NIVEL_CONSENSO = 0.60  # pct ≥ 0.60
NIVEL_TENDENCIA = 0.20  # pct ≥ 0.20
NIVEL_NEUTRO = -0.20  # pct > -0.20
NIVEL_ALERTA = -0.60  # pct > -0.60
# NIVEL_SALIDA si pct ≤ -0.60


# ---------------------------------------------------------------------------
# Funciones del modelo
# ---------------------------------------------------------------------------


def build_net_percentiles(fh_cartera: dict) -> tuple:
    """Calcula percentiles p33 y p67 del flujo neto (buy_ratio - sell_ratio)
    sobre los activos de cartera con datos 13F.
    Retorna (p33, p67) para clasificar cada activo relativamente al universo."""
    nets = sorted(
        (v.get("fh_buy_ratio") or 0.0) - (v.get("fh_sell_ratio") or 0.0)
        for v in fh_cartera.values()
        if v.get("fh_count")
    )
    if len(nets) < 3:
        return 0.2, 0.5
    n = len(nets)
    return nets[n // 3], nets[(2 * n) // 3]


def voto_net_relativo(buy_r: float, sell_r: float, p33: float, p67: float, fh_count=None) -> int:
    """Voto Net: ranking relativo del flujo neto institucional 13F.
    Top 33% de cartera → +1 | Medio → 0 | Bottom 33% → -1."""
    if not fh_count:
        return 0
    net = (buy_r or 0.0) - (sell_r or 0.0)
    if net >= p67:
        return 1
    if net >= p33:
        return 0
    return -1


def voto_options(calls: int, puts: int) -> int | None:
    """Voto Options: ratio CALL/(CALL+PUT) en posiciones de opciones 13F.
    Abstiene (None) si no hay opciones reportadas."""
    total = (calls or 0) + (puts or 0)
    if total == 0:
        return None
    ratio = (calls or 0) / total
    if ratio >= CALL_RATIO_POSITIVO:
        return 1
    if ratio >= CALL_RATIO_NEUTRO:
        return 0
    return -1


def voto_analistas(analyst_rec: str) -> int | None:
    """Voto Analistas: recomendación de Wall Street.
    strong_buy/buy → +1 | hold → 0 | sell/strong_sell → -1 | desconocido → None."""
    r = (analyst_rec or "").lower().replace(" ", "_")
    if r in ("strong_buy", "buy"):
        return 1
    if r in ("sell", "strong_sell"):
        return -1
    if r == "hold":
        return 0
    return None


def voto_valuacion(categoria_activo: str) -> int | None:
    """Voto Valuación: clasificación fundamental del activo.
    I=Infravalorado → +1 | N=Neutral → 0 | S=Sobrevalorado → -1
    X=Excluido (ETF/fondo) | T=Descubierto 13F → abstienen (None)."""
    if categoria_activo == "I":
        return 1
    if categoria_activo == "S":
        return -1
    if categoria_activo == "N":
        return 0
    return None  # X, T, o vacío: abstiene


def voto_cobertura(fh_count: int) -> int:
    """Voto Cobertura: número de fondos institucionales con posición.
    ≥ 20 fondos → +1 | ≥ 5 → 0 | < 5 → -1."""
    c = fh_count or 0
    if c >= FH_COUNT_POSITIVO:
        return 1
    if c >= FH_COUNT_NEUTRO:
        return 0
    return -1


def senal_consenso(votos_activos: list, suma: int) -> tuple:
    """Clasifica el Consenso Score final.
    Retorna (etiqueta, suma, n_activos).
    pct = suma / n_activos → tabla de niveles."""
    n = len(votos_activos)
    if n == 0:
        return "— S/D", 0, 0
    pct = suma / n
    if suma == n:
        etiqueta = "★ UNÁNIME"
    elif pct >= NIVEL_CONSENSO:
        etiqueta = "▲ CONSENSO"
    elif pct >= NIVEL_TENDENCIA:
        etiqueta = "↗ TENDENCIA"
    elif pct > NIVEL_NEUTRO:
        etiqueta = "→ NEUTRO"
    elif pct > NIVEL_ALERTA:
        etiqueta = "↘ ALERTA"
    else:
        etiqueta = "▼ SALIDA"
    return etiqueta, suma, n


def senal_institucional(inst_score: float, fh_buy_ratio: float, fh_count: int) -> str:
    """Señal institucional compuesta (Inst Señal en popup).
    Resume inst_score (blend yfinance+13F) + flujo neto + cobertura."""
    score = inst_score or 0.0
    buy_r = fh_buy_ratio or 0.0
    count = fh_count or 0
    if score >= INST_SCORE_ACOMPANAR and buy_r >= BUY_RATIO_ACOMPANAR and count >= FH_COUNT_ACOMPANAR:
        return "ACOMPAÑAR"
    if score >= INST_SCORE_MANTENER or count >= FH_COUNT_MANTENER:
        return "MANTENER"
    return "REVISAR"
