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

# Minimo de votos activos para emitir senal. Con menos, el tag lo decidirian uno o dos votos
# sobre un denominador diminuto: se devuelve S/D en vez de un nivel que no representa nada.
MIN_VOTOS_SENAL = 3

# Umbral del unico eje medible hoy en cripto: |ls_top_pos - ls_cuentas| de los futuros perpetuos.
# No sale de un salto natural en los datos -- medido el 2026-11-09 sobre 540 observaciones (18 pares
# x 30 dias) la |divergencia| es continua: p10 0,135 / p25 0,313 / p50 0,702 / p75 1,294 / p90 1,993.
# Los cortes 0,40, 0,50 y 0,60 dan los mismos 12 votantes de 18, asi que 0,50 esta en el medio de una
# banda insensible: se elige el redondo y no un decimal con falsa precision.
UMBRAL_DIVERGENCIA_CRIPTO = 0.50


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


def voto_net_relativo(buy_r: float, sell_r: float, p33: float, p67: float, fh_count=None) -> int | None:
    """Voto Net: ranking relativo del flujo neto institucional 13F.
    Top 33% de cartera → +1 | Medio → 0 | Bottom 33% → -1.
    Abstiene (None) si no hay cobertura 13F: un 0 entraria al denominador del promedio
    como si fuera una lectura neutral medida, y hundiria el score del activo."""
    if not fh_count:
        return None
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


def voto_cobertura(fh_count: int) -> int | None:
    """Voto Cobertura: número de fondos institucionales con posición.
    ≥ 20 fondos → +1 | ≥ 5 → 0 | < 5 → -1 | sin dato → None (abstiene).
    El -1 se conserva con 1-4 fondos: ahi la poca cobertura es un hecho medido. Sin ningun
    fondo no hay medicion, y votar -1 penaliza al activo por una ausencia de datos."""
    c = fh_count or 0
    if not c:
        return None
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
    if n < MIN_VOTOS_SENAL:
        return "— S/D", 0, n
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


def senal_cripto(divergencia) -> tuple:
    """Senal de un par cripto. Mismo contrato que senal_consenso: (etiqueta, suma, n_activos).

    Es funcion aparte y no un voto mas de senal_consenso porque los 8 votos del Consenso se abstienen
    en un par: Net/Opt/Flujo/Cob necesitan los fh_* del 13F, Ana necesita analyst_rec, Val ve 'C' y se
    abstiene, Mod lee los CSV del modelo de Stock y Sent el sentimiento de Stock. Con MIN_VOTOS_SENAL
    el resultado seria siempre "— S/D".

    Tampoco reusa la tabla de niveles: con un solo voto pct = suma/1 da 1 y todo positivo saldria
    UNANIME. Las etiquetas si son las mismas cadenas formateadas que senal_consenso -- es lo que
    guarda market.consenso_tag y lo que leen los gates via _consenso_clave.

    Con un solo eje medido solo existen tres estados, asi que UNANIME, CONSENSO y SALIDA quedan sin
    emitir a proposito: llenarlos hoy inventaria precision que la medicion no tiene.

    `divergencia` None (par sin contrato de futuros, o sin serie persistida) devuelve S/D con n=0,
    que es lo que distingue "no medido" de "medido y neutral".
    """
    if divergencia is None:
        return "— S/D", 0, 0
    if divergencia >= UMBRAL_DIVERGENCIA_CRIPTO:
        return "\u2197 TENDENCIA", 1, 1
    if divergencia <= -UMBRAL_DIVERGENCIA_CRIPTO:
        return "\u2198 ALERTA", -1, 1
    return "\u2192 NEUTRO", 0, 1


def voto_flujo(new_entrants: int, full_exits: int, fh_count: int, p33: float, p67: float) -> int | None:
    """Voto Flujo: entrada/salida neta de fondos relativa a cartera.
    Top 33% → +1 | Medio → 0 | Bottom 33% → -1. Abstiene (None) si sin cobertura:
    mismo motivo que voto_net_relativo — un 0 pesa en el denominador como dato real."""
    if not fh_count:
        return None
    fn = max(-1.0, min(1.0, ((new_entrants or 0) - (full_exits or 0)) / fh_count))
    if fn >= p67:
        return 1
    if fn >= p33:
        return 0
    return -1


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
