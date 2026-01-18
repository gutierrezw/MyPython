# =========================
# Standard library
# =========================
from Modulos_python import (
    math, Dict, 
Tuple, Optional, List,
)
from Modulos_Mysql import BDsystem, MarketScreen


# =========================
# Otros Metodos Engine
# =========================
class MetodoEngine:
    def _get_dividendos_mensuales(self) -> Dict[str, float]:
        """
        Obtiene distribución mensual de dividendos proyectados desde MARKET.
        Devuelve un dict {mes: ingreso_total}.

        Usa:
        - monthDividendsPay: meses de pago (ej: "Jan, Apr, Jul, Oct")
        - post dividendos: dividendos anuales proyectados del bloque dividends
        """
        ingresos_mensuales = {}
        market = MarketScreen()

        # Crear copia para evitar "dictionary changed size during iteration"
        info_snapshot = dict(self.info)

        for symbol, data in info_snapshot.items():
            if symbol == "TimeDataHub":
                continue

            # Filtrar solo activos del vehículo actual
            vehiculo_activo = data.get("vehiculo")
            if vehiculo_activo != self.vehiculo:
                continue

            # Solo procesar activos con bloque dividends
            div_block = data.get("dividends")
            if not div_block:
                continue

            # Obtener dividendos proyectados del bloque
            post_dividendos = div_block.get("post dividendos", 0)
            if not post_dividendos or post_dividendos <= 0:
                continue

            # Consultar meses de pago desde MARKET
            try:
                sql_result, columns = market.select(account="U4214563", symbol=symbol)
                if not sql_result:
                    continue

                # Obtener índice de monthDividendsPay
                month_pay_idx = columns.index("monthDividendsPay") if "monthDividendsPay" in columns else None
                if month_pay_idx is None:
                    continue

                month_pay_str = sql_result[0][month_pay_idx]
                if not month_pay_str:
                    continue

                # Parsear meses: "Jan, Apr, Jul, Oct" → ["Jan", "Apr", "Jul", "Oct"]
                meses = [m.strip() for m in month_pay_str.split(",") if m.strip()]
                if not meses:
                    continue

                # Distribuir dividendos entre los meses de pago
                dividendo_por_mes = post_dividendos / len(meses)
                for mes in meses:
                    ingresos_mensuales[mes] = ingresos_mensuales.get(mes, 0.0) + dividendo_por_mes

            except Exception as e:
                print(f"⚠️ Error obteniendo dividendos para {symbol}: {e}", flush=True)
                continue

        return ingresos_mensuales

    def _dividendos_necesitado(self, symbol: str) -> bool:
        """
        Devuelve True si el activo paga dividendos
        en meses que están por debajo del promedio.

        Consulta MARKET para obtener los meses de pago del activo.
        """
        if not symbol:
            return False

        data = self.info.get(symbol)
        if not data:
            return False

        div_block = data.get("dividends")
        if not div_block:
            return False

        # Verificar que tenga dividendos proyectados
        post_dividendos = div_block.get("post dividendos", 0)
        if not post_dividendos or post_dividendos <= 0:
            return False

        # Obtener ingresos mensuales del portfolio
        ingresos = self._get_dividendos_mensuales()
        if not ingresos:
            return False

        promedio = sum(ingresos.values()) / len(ingresos)

        # Consultar meses de pago desde MARKET
        try:
            market = MarketScreen()
            sql_result, columns = market.select(account="U4214563", symbol=symbol)
            if not sql_result:
                return False

            month_pay_idx = columns.index("monthDividendsPay") if "monthDividendsPay" in columns else None
            if month_pay_idx is None:
                return False

            month_pay_str = sql_result[0][month_pay_idx]
            if not month_pay_str:
                return False

            # Parsear meses: "Jan, Apr, Jul, Oct" → ["Jan", "Apr", "Jul", "Oct"]
            meses = [m.strip() for m in month_pay_str.split(",") if m.strip()]
            if not meses:
                return False

            # Verificar si alguno de los meses de pago está por debajo del promedio
            for mes in meses:
                if ingresos.get(mes, 0.0) < promedio:
                    return True

        except Exception as e:
            print(f"⚠️ Error en _dividendos_necesitado para {symbol}: {e}", flush=True)
            return False

        return False

    def _gap_valor_dividendos(self) -> float:
        """
        Devuelve el gap monetario de ingresos por dividendos.
        Representa el ingreso faltante para lograr uniformidad mensual.
        """
        ingresos = self._get_dividendos_mensuales()
        if not ingresos:
            return 0.0

        valores = list(ingresos.values())
        promedio = sum(valores) / len(valores)

        gap_valor = sum(max(promedio - v, 0.0) for v in valores)

        return gap_valor

    # =========================
    # sector
    # =========================
    def _get_pesos_por_sector(self) -> Dict[str, Dict]:
        """
        Devuelve pesos por sector junto con
        gap porcentual y gap monetario.
        """
        sector_data = self.datahub.manager_buysell.get("sector")
        if not sector_data:
            return {}

        # summary está directamente en sector_data, no en data
        summary = sector_data.get("summary", {})
        names = summary.get("Name", [])
        pesos = summary.get("Peso", [])

        total_valor = sector_data.get("total_valor_market", 0.0)
        if not names or not pesos or total_valor <= 0:
            return {}

        n = len(names)
        objetivo = 1 / n if n > 0 else 0.0

        resultado = {}

        for sector, peso in zip(names, pesos):
            gap_pct = objetivo - peso
            gap_valor = gap_pct * total_valor

            resultado[sector] = {
                "peso": peso,
                "objetivo": objetivo,
                "gap_pct": gap_pct,
                "gap_valor": gap_valor,
            }

        return resultado

    def _sector_necesitado(self, sector: str) -> bool:
        """
        Devuelve True si el sector está sub-ponderado
        y necesita más inversión para alcanzar equiponderación.

        Similar a _dividendos_necesitado pero para sectores:
        - Verifica que el sector exista en el portfolio
        - Verifica que esté por debajo del objetivo (gap_pct > 0)
        - Solo retorna True para sectores que necesitan balance
        """
        if not sector:
            return False

        pesos_sector = self._get_pesos_por_sector()
        if not pesos_sector:
            return False

        data = pesos_sector.get(sector)
        if not data:
            return False

        # gap_pct > 0 significa que el sector está por debajo del objetivo
        # (objetivo - peso_actual = gap_pct positivo)
        gap_pct = data.get("gap_pct", 0.0)

        # Solo necesitamos el sector si está sub-ponderado
        return gap_pct > 0

    def _gap_valor_sector(self, sector: str) -> float:
        data = self._get_pesos_por_sector().get(sector)
        if not data:
            return 0.0
        return max(data.get("gap_valor", 0.0), 0.0)

    # =========================
    # Activos
    # =========================
    def _get_pesos_por_tipo(self) -> Dict[str, Dict]:
        """
        Devuelve pesos por tipo de activo junto con
        gap porcentual y gap monetario.

        Calcula directamente desde DataHub.info filtrando por vehículo,
        replicando la lógica de grupo_activos() pero específica por vehículo.
        """
        # Calcular pesos desde DataHub.info filtrado por vehículo
        tipos_data = {}  # {asset_type: {"capital": X, "valor_market": Y}}
        total_valor_market = 0.0

        for symbol, data in self.info.items():
            if symbol == "TimeDataHub":
                continue

            if not isinstance(data, dict):
                continue

            # Filtrar solo activos del vehículo actual
            vehiculo_activo = data.get("vehiculo")
            if vehiculo_activo != self.vehiculo:
                continue

            # Obtener asset_type del activo
            asset_type = data.get("asset_type")
            if not asset_type:
                continue

            # Calcular valores
            costobase = data.get("costobase", 0) or 0
            unrealizedpnl = data.get("unrealizedpnl", 0) or 0
            valor_market = costobase + unrealizedpnl

            # Solo considerar activos con posición activa
            if costobase < self.min_costobase:
                continue

            # Acumular por tipo
            if asset_type not in tipos_data:
                tipos_data[asset_type] = {"capital": 0.0, "valor_market": 0.0}

            tipos_data[asset_type]["capital"] += costobase
            tipos_data[asset_type]["valor_market"] += valor_market
            total_valor_market += valor_market

        if not tipos_data or total_valor_market <= 0:
            return {}

        # Calcular pesos y gaps
        n = len(tipos_data)
        objetivo = 1 / n if n > 0 else 0.0

        resultado = {}
        for tipo, valores in tipos_data.items():
            peso = valores["capital"] / total_valor_market if total_valor_market > 0 else 0
            gap_pct = objetivo - peso
            gap_valor = gap_pct * total_valor_market

            resultado[tipo] = {
                "peso": peso,
                "objetivo": objetivo,
                "gap_pct": gap_pct,
                "gap_valor": gap_valor,
            }

        return resultado

    def _tipo_necesitado(self, asset_type: str) -> bool:
        """
        Devuelve True si el tipo de activo está sub-ponderado
        y necesita más inversión para alcanzar equiponderación.
        """
        if not asset_type:
            return False

        tipos = self._get_pesos_por_tipo()
        if not tipos:
            return False

        data = tipos.get(asset_type)
        if not data:
            return False

        # gap_pct > 0 significa que el tipo está por debajo del objetivo
        gap_pct = data.get("gap_pct", 0.0)
        return gap_pct > 0

    def _gap_valor_tipo(self, asset_type: str) -> float:
        data = self._get_pesos_por_tipo().get(asset_type)
        if not data:
            return 0.0
        return max(data.get("gap_valor", 0.0), 0.0)

    # =========================
    # region
    # =========================
    def _get_pesos_por_region(self) -> Dict[str, Dict]:
        """
        Devuelve pesos por región junto con
        gap porcentual y gap monetario.

        Calcula directamente desde DataHub.info filtrando por vehículo,
        replicando la lógica de grupo_region() pero específica por vehículo.
        """
        # Calcular pesos desde DataHub.info filtrado por vehículo
        regiones_data = {}  # {region: {"capital": X, "valor_market": Y}}
        total_valor_market = 0.0

        for symbol, data in self.info.items():
            if symbol == "TimeDataHub":
                continue

            if not isinstance(data, dict):
                continue

            # Filtrar solo activos del vehículo actual
            vehiculo_activo = data.get("vehiculo")
            if vehiculo_activo != self.vehiculo:
                continue

            # Obtener region del activo y normalizarla
            region = data.get("region")

            # Normalizar región (misma lógica que grupo_region)
            if not region or region in ("null", "None", ""):
                region = "NotCountry"
            elif region == "US":
                region = "United States"
            elif region == "Digital":
                region = "Crypto"

            # Para vehículo Crypto, forzar región="Crypto"
            if self.vehiculo == "Crypto":
                region = "Crypto"

            # Calcular valores
            costobase = data.get("costobase", 0) or 0
            unrealizedpnl = data.get("unrealizedpnl", 0) or 0
            valor_market = costobase + unrealizedpnl

            # Solo considerar activos con posición activa
            if costobase < self.min_costobase:
                continue

            # Acumular por región
            if region not in regiones_data:
                regiones_data[region] = {"capital": 0.0, "valor_market": 0.0}

            regiones_data[region]["capital"] += costobase
            regiones_data[region]["valor_market"] += valor_market
            total_valor_market += valor_market

        if not regiones_data or total_valor_market <= 0:
            return {}

        # Calcular pesos y gaps
        n = len(regiones_data)
        objetivo = 1 / n if n > 0 else 0.0

        resultado = {}
        for region, valores in regiones_data.items():
            peso = valores["capital"] / total_valor_market if total_valor_market > 0 else 0
            gap_pct = objetivo - peso
            gap_valor = gap_pct * total_valor_market

            resultado[region] = {
                "peso": peso,
                "objetivo": objetivo,
                "gap_pct": gap_pct,
                "gap_valor": gap_valor,
            }

        return resultado

    def _region_necesitada(self, region: str) -> bool:
        """
        Devuelve True si la región está sub-ponderada
        y necesita más inversión para alcanzar equiponderación.
        """
        if not region:
            return False

        pesos_region = self._get_pesos_por_region()
        if not pesos_region:
            return False

        data = pesos_region.get(region)
        if not data:
            return False

        # gap_pct > 0 significa que la región está por debajo del objetivo
        gap_pct = data.get("gap_pct", 0.0)
        return gap_pct > 0

    def _gap_valor_region(self, region: str) -> float:
        data = self._get_pesos_por_region().get(region)
        if not data:
            return 0.0
        return max(data.get("gap_valor", 0.0), 0.0)

    # =========================
    # comunes
    # =========================
    def _get_active_block(
        self, info_symbol: Dict
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Devuelve el modo activo y un bloque normalizado
        con los datos necesarios para operar.
        """
        if not isinstance(info_symbol, dict):
            return None, None

        # datos comunes (nivel raíz)
        websocket = info_symbol.get("websocket")
        lot_size = info_symbol.get("lotSize")
        vehiculo = info_symbol.get("vehiculo")  # vehiculo está en nivel raíz

        # determinar modo activo
        if "dividends" in info_symbol:
            modo = "dividends"
            block_data = info_symbol.get("dividends", {})
        else:
            modo = "buy"
            block_data = info_symbol.get("buy", {})

        # extraer valuation del bloque activo (si existe)
        valuation = block_data.get("valuation", {}) if isinstance(block_data, dict) else {}

        block = {
            "modo": modo,
            "vehiculo": vehiculo,
            "websocket": websocket,
            "lotSize": lot_size,
            "valuation": valuation,
        }

        return modo, block

    def monto_a_cantidad(
        self, symbol: str, monto: float, allow_fraction: bool = True
    ) -> float:
        """
        Convierte monto en cantidad usando el bloque activo
        (_get_active_block) como fuente única de verdad.
        """
        if monto <= 0:
            return 0.0

        info_symbol = self.info.get(symbol)
        if not info_symbol:
            return 0.0

        modo, block = self._get_active_block(info_symbol)
        if not isinstance(block, dict):
            return 0.0

        # ---- precio desde websocket ----
        websocket = block.get("websocket", {})
        try:
            precio = float(websocket.get("last"))
            if precio <= 0:
                return 0.0
        except (TypeError, ValueError):
            return 0.0

        cantidad_teorica = monto / precio

        vehiculo = block.get("vehiculo", "").lower()

        # ---- STOCK / ETF → enteros ----
        if vehiculo in ("stock", "etf"):
            return float(math.floor(cantidad_teorica))

        # ---- CRYPTO → fraccionable por stepSize ----
        if vehiculo == "crypto" and allow_fraction:
            lot = block.get("lotSize", {})
            try:
                step = float(lot.get("stepSize", 1))
                if step <= 0:
                    step = 1
            except (TypeError, ValueError):
                step = 1

            cantidad = math.floor(cantidad_teorica / step) * step
            return round(cantidad, 8)

        return 0.0


# =========================
# Rebalance Engine
# =========================
class RebalanceEngine(MetodoEngine):
    """
    Motor de rebalanceo determinístico.
    Lee el estado consolidado de la cartera y
    produce un ranking de activos prioritarios.
    """

    def __init__(self, DataHub: Dict, vehiculo: Optional[str] = None):
        self.info = DataHub.info
        self.datahub = DataHub

        self.gaps: Dict = {}
        self.normalized_gaps: Dict = {}
        self.dimension_priority: List[str] = []
        self.candidates: List[Dict] = []
        self.ranking: List[Dict] = []

        # Usar vehículo pasado como parámetro o detectarlo automáticamente
        self.vehiculo = vehiculo if vehiculo else self._detect_vehiculo()
        self.dimensiones_activas = self._get_dimensiones_por_vehiculo()

        # Obtener min_costobase desde sesion.gainInversion para el vehículo
        self.min_costobase = self._get_min_costobase()

        # Validar estructura de DataHub
        self._validate_datahub()

    def _detect_vehiculo(self) -> Optional[str]:
        """
        Detecta el vehículo actual desde los activos del portafolio.
        Asume que todos los activos pertenecen al mismo vehículo.
        """
        for symbol, data in self.info.items():
            if symbol == "TimeDataHub":
                continue

            if not isinstance(data, dict):
                continue

            # El vehiculo está directamente en el nivel raíz
            vehiculo = data.get("vehiculo")
            if vehiculo:
                return vehiculo

        return None

    def _get_min_costobase(self) -> float:
        """
        Obtiene el umbral mínimo de costobase desde sesion.gainInversion.
        Retorna 10.0 como valor por defecto si no se encuentra.
        """
        try:
            sesion = BDsystem.get_sesion_by_vehiculo(vehiculo=self.vehiculo)
            if sesion:
                return float(sesion.get("gainInversion", 10.0) or 10.0)
        except Exception:
            pass
        return 10.0

    def _get_dimensiones_por_vehiculo(self) -> Dict[str, bool]:
        """
        Devuelve las dimensiones aplicables según el vehículo.

        Reglas:
        - Crypto: dividendos, tipos, regiones (no sectores)
        - Stock/Otros: dividendos, sectores, tipos, regiones
        """
        dimensiones = {
            "dividendos": True,  # Aplica para todos
            "sectores": True,
            "tipos": True,
            "regiones": True,
        }

        if self.vehiculo == "Crypto":
            # Para crypto no aplican sectores industriales
            # pero sí tipos de activos y regiones
            dimensiones["sectores"] = False
            dimensiones["tipos"] = True
            dimensiones["regiones"] = True

        return dimensiones

    def _validate_datahub(self) -> bool:
        """
        Valida que DataHub tenga la estructura esperada.
        Retorna True si la estructura es válida, False en caso contrario.
        """
        if not hasattr(self.datahub, 'manager_buysell'):
            return False

        # Validación silenciosa - los errores se manejan en los métodos de gap
        return True

    # =========================
    # FASE 1 — GAPS
    # =========================
    def compute_gaps(self) -> Dict:
        """
        Calcula gaps solo para dimensiones activas según el vehículo.
        """
        self.gaps = {}

        if self.dimensiones_activas.get("dividendos", False):
            self.gaps["dividendos"] = self._gap_dividendos()

        if self.dimensiones_activas.get("sectores", False):
            self.gaps["sectores"] = self._gap_sectores()

        if self.dimensiones_activas.get("tipos", False):
            self.gaps["tipos"] = self._gap_tipos()

        if self.dimensiones_activas.get("regiones", False):
            self.gaps["regiones"] = self._gap_regiones()

        return self.gaps

    # =========================
    # FASE 2 — NORMALIZACIÓN
    # =========================
    def normalize_gaps(self) -> Dict:
        self.normalized_gaps = {
            dim: self._normalize_gap(value) for dim, value in self.gaps.items()
        }
        return self.normalized_gaps

    # =========================
    # FASE 3 — PRIORIDAD
    # =========================
    def prioritize_dimensions(self) -> List[str]:
        self.dimension_priority = sorted(
            self.normalized_gaps, key=lambda d: self.normalized_gaps[d], reverse=True
        )
        return self.dimension_priority

    # =========================
    # FASE 4 — CANDIDATOS
    # =========================
    def build_candidates(self) -> List[Dict]:
        """
        Construye lista de candidatos filtrando solo activos del vehículo actual.
        Esto asegura que solo se evalúen activos relevantes para el motor.
        """
        self.candidates = []

        for symbol, data in self.info.items():

            # ignorar metadata global
            if symbol == "TimeDataHub":
                continue

            tipo, block = self._get_active_block(data)
            if not block:
                continue

            # FILTRO CRÍTICO: solo incluir activos del vehículo actual
            vehiculo_activo = block.get("vehiculo")
            if vehiculo_activo != self.vehiculo:
                continue

            # FILTRO: solo activos con posición activa (costobase > min_costobase)
            costobase = data.get("costobase", 0) or 0
            if costobase < self.min_costobase:
                continue

            metadata = self._extract_metadata(data)
 
            self.candidates.append(
                {
                    "symbol": symbol,
                    "tipo": tipo,
                    "block": block,
                    "metadata": metadata,
                    "score": 0.0,
                    "impacto": {},
                }
            )

        return self.candidates

    # =========================
    # FASE 5 — SCORING
    # =========================
    def score_candidates(self) -> List[Dict]:
        # Para Crypto: usar heurística de equilibrio por costobase
        if self.vehiculo == "Crypto":
            self._score_candidates_crypto()
        else:
            for candidate in self.candidates:
                score, impacto = self._score_candidate(candidate)
                candidate["score"] = score
                candidate["impacto"] = impacto

        return self.candidates

    def _score_candidates_crypto(self):
        """
        Scoring específico para Crypto basado en equilibrio de costobase.
        Mayor score = menor costobase (necesita más inversión para equilibrar).
        """
        if not self.candidates:
            return

        # Obtener costobases de todos los candidatos
        costobases = []
        for candidate in self.candidates:
            symbol = candidate["symbol"]
            data = self.info.get(symbol, {})
            costobase = data.get("costobase", 0) or 0
            candidate["_costobase"] = costobase
            costobases.append(costobase)

        if not costobases:
            return

        # Calcular promedio y total
        promedio = sum(costobases) / len(costobases)
        total = sum(costobases)
        max_costobase = max(costobases) if costobases else 1

        # Asignar score: mayor score a menor costobase
        for candidate in self.candidates:
            costobase = candidate.get("_costobase", 0)

            # Gap: cuánto le falta para llegar al promedio
            gap_valor = max(promedio - costobase, 0)

            # Score normalizado (0-1): qué tan por debajo del promedio está
            if max_costobase > 0:
                # Invertir: menor costobase = mayor score
                score = (max_costobase - costobase) / max_costobase
            else:
                score = 0

            candidate["score"] = score
            candidate["impacto"] = {
                "costobase": costobase,
                "promedio": promedio,
                "gap_valor_total": gap_valor,
                "gap_valor_norm": score,
            }

            # Limpiar campo temporal
            del candidate["_costobase"]

    # =========================
    # FASE 6 — RANKING FINAL
    # =========================
    def rank(self) -> List[Dict]:
        self.compute_gaps()
        self.normalize_gaps()
        self.prioritize_dimensions()
        self.build_candidates()
        self.score_candidates()

        self.ranking = sorted(self.candidates, key=lambda c: c["score"], reverse=True)

        return self.ranking

    # =========================
    # Helpers
    # =========================
    def _extract_metadata(self, info_symbol: Dict) -> Dict:
        # Normalizar región para consistencia con grupo_region()
        region = info_symbol.get("region")

        # Para vehículo Crypto, forzar región="Crypto" para coincidir con gráficos
        if self.vehiculo == "Crypto":
            region = "Crypto"
        elif region == "US":
            region = "United States"
        elif region == "Digital":
            region = "Crypto"

        return {
            "sector": info_symbol.get("sector"),
            "region": region,
            "asset_type": info_symbol.get("asset_type"),
        }

    # ---- GAPS ----
    def _gap_dividendos(self):
        """
        Calcula el gap de dividendos como desbalance
        entre meses respecto al ingreso promedio.
        """
        # ejemplo: {"Jan": 120, "Feb": 80, ...}
        ingresos_mensuales = self._get_dividendos_mensuales()

        if not ingresos_mensuales:
            return 0.0

        valores = list(ingresos_mensuales.values())
        promedio = sum(valores) / len(valores)

        # desvío medio absoluto normalizado
        gap = sum(abs(v - promedio) for v in valores) / (promedio * len(valores))

        return gap

    def _gap_sectores(self):
        """
        Calcula el gap sectorial respecto
        a la equiponderación dinámica.
        """
        pesos = self._get_pesos_por_sector()
        if not pesos:
            return 0.0

        n = len(pesos)
        if n == 0:
            return 0.0

        gap = sum(abs(data["gap_pct"]) for data in pesos.values()) / n

        return gap

    def _gap_tipos(self):
        tipos = self._get_pesos_por_tipo()
        if not tipos:
            return 0.0

        n = len(tipos)
        if n == 0:
            return 0.0

        gap = sum(abs(data["gap_pct"]) for data in tipos.values()) / n
        return gap

    def _gap_regiones(self):
        regiones = self._get_pesos_por_region()
        if not regiones:
            return 0.0

        n = len(regiones)
        if n == 0:
            return 0.0

        gap = sum(abs(data["gap_pct"]) for data in regiones.values()) / n
        return gap

    # ---- Normalización ----
    def _normalize_gap(self, gap_value):
        """
        Normaliza un gap a rango 0–1 usando
        una función de saturación.

        gap_value: float >= 0
        """
        if gap_value is None:
            return 0.0

        try:
            gap = float(gap_value)
        except (TypeError, ValueError):
            return 0.0

        if gap <= 0:
            return 0.0

        # saturación suave
        return gap / (gap + 1)

    def _normalize_gap_valor(self, gap_valor: float) -> float:
        """
        Normaliza un gap monetario a rango 0–1.
        Usa saturación suave para evitar dominancia extrema.
        K es relativo al tamaño del portafolio (10%).
        """
        if gap_valor is None or gap_valor <= 0:
            return 0.0

        try:
            v = float(gap_valor)
        except (TypeError, ValueError):
            return 0.0

        # K relativo al tamaño del portafolio
        total_portafolio = 1.0
        try:
            sector_data = self.datahub.manager_buysell.get("sector", {})
            total_portafolio = sector_data.get("total_valor_market", 1.0)
            if total_portafolio <= 0:
                total_portafolio = 1.0
        except Exception:
            total_portafolio = 1.0

        K = total_portafolio * 0.1  # 10% del portafolio
        return v / (v + K)

    # ---- Scoring ----
    def _score_candidate(self, candidate: Dict):
        """
        Calcula el score de un activo en función de:
        - gaps normalizados (rebalanceo estructural)
        - metadata del activo (flexible con dimensiones incompletas)
        - ajuste opcional por valoración (no determinante)

        MEJORA: Maneja activos con metadata incompleta dando crédito proporcional
        por las dimensiones que SÍ mejoran, sin penalizar las que faltan.
        """
        score_estructural = 0.0
        impacto = {}

        meta = candidate.get("metadata", {})
        symbol = candidate["symbol"]

        # Rastrear dimensiones evaluables vs dimensiones aplicables
        dimensiones_evaluadas = 0
        dimensiones_aplicables = 0

        # =========================
        # Dividendos
        # =========================
        gap_div = self.normalized_gaps.get("dividendos", 0.0)
        tipo = candidate["tipo"]
        necesita_div = self._dividendos_necesitado(symbol)

        # Siempre es evaluable (todos los activos tienen tipo buy/dividends)
        dimensiones_evaluadas += 1

        if (
            gap_div > 0
            and tipo == "dividends"
            and necesita_div
        ):
            impacto["dividendos"] = gap_div
            score_estructural += gap_div
            dimensiones_aplicables += 1

            gap_valor_div = self._gap_valor_dividendos()
        else:
            impacto["dividendos"] = 0.0
            gap_valor_div = 0.0

        # =========================
        # Sectores
        # =========================
        gap_sec = self.normalized_gaps.get("sectores", 0.0)
        sector = meta.get("sector")

        # Solo evaluable si tiene metadata de sector
        if sector is not None:
            dimensiones_evaluadas += 1

            if gap_sec > 0 and self._sector_necesitado(sector):
                impacto["sectores"] = gap_sec
                score_estructural += gap_sec
                dimensiones_aplicables += 1
            else:
                impacto["sectores"] = 0.0
        else:
            impacto["sectores"] = 0.0

        # =========================
        # Tipos de activo
        # =========================
        gap_tipo = self.normalized_gaps.get("tipos", 0.0)
        asset_type = meta.get("asset_type")

        # Solo evaluable si tiene metadata de asset_type
        if asset_type is not None:
            dimensiones_evaluadas += 1

            if gap_tipo > 0 and self._tipo_necesitado(asset_type):
                impacto["tipos"] = gap_tipo
                score_estructural += gap_tipo
                dimensiones_aplicables += 1
            else:
                impacto["tipos"] = 0.0
        else:
            impacto["tipos"] = 0.0

        # =========================
        # Regiones
        # =========================
        gap_reg = self.normalized_gaps.get("regiones", 0.0)
        region = meta.get("region")

        # Solo evaluable si tiene metadata de region
        if region is not None:
            dimensiones_evaluadas += 1

            if gap_reg > 0 and self._region_necesitada(region):
                impacto["regiones"] = gap_reg
                score_estructural += gap_reg
                dimensiones_aplicables += 1
            else:
                impacto["regiones"] = 0.0
        else:
            impacto["regiones"] = 0.0

        # Guardar info de cobertura de dimensiones
        impacto["dimensiones_evaluadas"] = dimensiones_evaluadas
        impacto["dimensiones_aplicables"] = dimensiones_aplicables

        # =========================
        # Ajuste por valoración (opcional)
        # =========================
        valuation_factor = self._valuation_factor(candidate)

        # =========================
        # Impacto monetario
        # =========================
        impacto_valor_total = 0.0

        if impacto.get("sectores", 0) > 0:
            impacto_valor_total += self._gap_valor_sector(sector)

        if impacto.get("regiones", 0) > 0:
            impacto_valor_total += self._gap_valor_region(region)

        if impacto.get("tipos", 0) > 0:
            impacto_valor_total += self._gap_valor_tipo(asset_type)

        if impacto.get("dividendos", 0) > 0:
            impacto_valor_total += gap_valor_div

        impacto_valor_norm = self._normalize_gap_valor(impacto_valor_total)

        impacto["gap_valor_total"] = impacto_valor_total
        impacto["gap_valor_norm"] = impacto_valor_norm

        # =========================
        # Score final
        # =========================
        # DEBUG: Imprimir valores clave para diagnóstico
    
        # Si hay gaps estructurales, usar scoring completo
        if score_estructural > 0:
            # Scoring base por gaps estructurales
            score_final = score_estructural * (1 + impacto_valor_norm) * valuation_factor

            # MEJORA: Bonificación por cobertura de dimensiones
            # Si el activo tiene metadata incompleta pero mejora dimensiones evaluables,
            # bonificar proporcionalmente
            if dimensiones_evaluadas > 0:
                cobertura_ratio = dimensiones_aplicables / dimensiones_evaluadas
                # Bonificar hasta +20% si mejora todas las dimensiones evaluables
                cobertura_bonus = 1.0 + (0.2 * cobertura_ratio)
                score_final *= cobertura_bonus

            # print(f"✅ [DEBUG {symbol}] SCORE ESTRUCTURAL → score_final={score_final:.4f}", flush=True)

        else:
            # Sin gaps estructurales, scoring por oportunidad de valoración
            # Priorizar activos con mejor precio relativo
            if valuation_factor > 1.0:
                # Score base por valoración
                score_base = 0.05 * valuation_factor

                # Bonificación adicional si tiene metadata (ayuda a diversificar)
                metadata_count = sum([
                    1 for v in [meta.get("sector"), meta.get("region"), meta.get("asset_type")]
                    if v is not None
                ])
                # +10% por cada dimensión con metadata (max +30%)
                metadata_bonus = 1.0 + (0.1 * metadata_count)

                score_final = score_base * metadata_bonus
            else:
                score_final = 0.0

        return score_final, impacto

    def _valuation_factor(self, candidate: Dict) -> float:
        """
        Devuelve un factor multiplicativo según la valoración.
        Prioriza:
        1. Label de valuation (cheap/expensive/neutral)
        2. Precio actual vs precio promedio (gypPrecio)

        Retorna > 1.0 si es oportunidad, < 1.0 si está caro, 1.0 neutral
        """
        symbol = candidate.get("symbol", "???")
        block = candidate.get("block", {})
        valuation = block.get("valuation", {})

        # 1. Prioridad a label de valuation
        label = valuation.get("label", "neutral")

        if label == "cheap":
            # print(f"  💎 [{symbol}] valuation label='cheap' → factor=1.2", flush=True)
            return 1.2
        if label == "expensive":
            # print(f"  💸 [{symbol}] valuation label='expensive' → factor=0.8", flush=True)
            return 0.8

        # 2. Fallback: usar precio promedio (gypPrecio)
        # Si está por debajo del promedio (negativo), es oportunidad
        try:
            avgcost = block.get("avgcost", 0)
            last_price = block.get("mrkprice", 0)

            if avgcost > 0 and last_price > 0:
                gyp_precio = (last_price - avgcost) / avgcost

                # Si está más de 10% debajo del promedio -> oportunidad
                if gyp_precio < -0.10:
                    return 1.15
                # Si está más de 10% arriba del promedio → caro
                elif gyp_precio > 0.10:
                    return 0.85
                else:
                    pass
        except (TypeError, ValueError, ZeroDivisionError) as e:
            # print(f"  ⚠️  [{symbol}] Error calculando gypPrecio: {e}", flush=True)
            pass

        return 1.0

    def budget_allocator(self, min_ticket: float = 100.0) -> List[Dict]:
        """
        Asigna monto sugerido por activo usando
        el Pinvertir del vehículo asociado.
        """
        ranking = self.ranking or self.rank()

        if not ranking:
            return []

        asignaciones = []

        for candidate in ranking:
            symbol = candidate["symbol"]
            score = candidate.get("score", 0.0)

            if score <= 0:
                continue

            # obtener vehículo real
            vehiculo = BDsystem.get_vehiculo_by_ticket(symbol)
            if not vehiculo:
                continue

            pinvertir = vehiculo.get("Pinvertir", 0.0)
            if pinvertir < min_ticket:
                continue

            # gwi
            gap_valor = candidate.get("impacto", {}).get("gap_valor_total", 0.0)
            if gap_valor <= 0:
                continue

            # monto sugerido
            monto = min(pinvertir, gap_valor)

            if monto < min_ticket:
                continue

            monto = round(monto, 2)

            asignaciones.append(
                {
                    "symbol": symbol,
                    "monto_sugerido": monto,
                    "pinvertir": pinvertir,
                    "score": round(score, 4),
                    "impacto": candidate["impacto"],
                }
            )

        return asignaciones
