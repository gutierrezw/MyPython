"""
Class_AsesorIA.py - Asesor de consulta de la cartera (icono IA del Asistente de Inversion).

Opus responde preguntas sobre la cartera con una foto congelada (posiciones, deuda, mercado) en el system
y cuatro herramientas de solo lectura para el detalle: lotes y ordenes, votos del Consenso, traza de los
agentes y oportunidades vigentes. No ejecuta ordenes. Manda montos de la cartera a Anthropic: lo aprobo
el usuario para este chat.
"""

from Modulos_python import anthropic, datetime, json, math, timedelta
from Modulos_Mysql import BDsystem, IaTraceScreen, MarketScreen, RepositorioOportunidadesBuySell
from Modulos_Utilitarios import read_json_tmp, track_claude_usage
from Class_customer import DataHub
from Class_BrowserBridge import set_claude_contexto
from Class_Screener import contexto_consenso, senal_votos, votos_consenso


MODELO = "claude-opus-5-5"
MAX_TOKENS = 16000
MAX_VUELTAS = 8
FOTO_TTL = timedelta(minutes=30)
POLVO_USD = 1.0
TECHO_MARGEN_IB = 7000.0
MAX_LOTES = 40
MAX_FILAS_CSV = 25

VEHICULOS = {
    "Stock": "STOCK (Interactive Brokers)",
    "Crypto": "CRYPTO (Binance)",
    "BBVA.ARS": "FCI (BBVA y Santander, cuotapartes en ARS valuadas en USD)",
}

COLUMNAS_SELL = (
    "Symbol", "vehiculo", "Opcion", "CantidadSell", "Disponible", "PriceMarket", "Profit", "%Roi", "NroLotes",
    "PosAvgCost", "Objetivo", "Recomendado", "Comentarios", "Fecha",
)
COLUMNAS_BUY = (
    "Symbol", "vehiculo", "tipo", "score", "monto_sugerido", "cantidad_buy", "last", "avgcost", "avgcost_post",
    "retorno_post", "objetivo", "dividend_yield", "Recomendado", "Comentarios", "Fecha",
)
CAMPOS_POSICION = (
    "position", "mrkprice", "costobase", "mktvalue", "unrealizedpnl", "retorno", "objetivo", "dividendYield", "dgyp",
    "estrategia", "divisa",
)
CAMPOS_ORDEN = ("stampPlace", "side", "orderType", "intent", "quantity", "price", "status")
CAMPOS_INST = (
    "shortName", "lastPrice", "categoriaActivo", "inst_score", "inst_ownership_pct", "fh_count", "fh_buy_ratio",
    "fh_sell_ratio", "fh_call_shares", "fh_put_shares", "new_entrants", "full_exits", "analyst_rec",
    "analyst_mean", "analyst_count", "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "marketCap",
)

INSTRUCCIONES = """Sos el asesor de consulta de la cartera del usuario, integrado en su app de trading. Respondés \
en español con voseo, corto y con la conclusión primero.

Qué sos y qué no:
- Asesor de consulta: no ejecutás órdenes ni tenés cómo. El usuario decide y opera.
- La app ya genera sugerencias automáticas (oportunidades de compra y venta, GainsCapture, Preservation). Tu \
valor es cruzarlas con la cartera, el Consenso y la traza de los agentes, y decir si coincidís, con qué matiz \
o por qué no.

Cómo responder:
- Concreto: símbolo, cantidad, precio, monto en USD y qué invalidaría la sugerencia.
- No inventes cifras. Lo que no esté en la foto de abajo, buscalo con las herramientas; si un dato falta, decilo.
- Antes de sugerir comprar, vender o promediar un símbolo, mirá sus lotes con posicion_detalle y lo que \
sugirió la app con oportunidades_vigentes y traza_decisiones.
- Hablar de un vehículo (Stock, Crypto, FCI) es hablar solo de ese vehículo. Mezclalos solo si la pregunta es \
de la cartera entera.
- Texto plano, sin markdown: nada de asteriscos, numerales ni tablas con barras. Para listas usá guiones.

Reglas del usuario:
- Margen de IB: solo con tendencia alcista y por montos chicos, con un techo autoimpuesto de 7.000 USD de \
deuda de margen. No sugieras nada que lo supere.
- El préstamo de Binance va aparte: lo controla un agente por LTV (objetivo cerca de 28%).

Leyenda del Consenso (Stock):
- Votos: Net (compras contra ventas de fondos 13F, relativo al resto de la cartera), Opt (calls contra puts de \
los fondos), Flujo (fondos que entran contra los que salen), Ana (recomendación de analistas), Val \
(categoría de valuación: I infravalorado +1, N neutral 0, S sobrevalorado -1; ETF y descubiertos se \
abstienen), Cob (cobertura: 20 o más fondos +1, de 5 a 19 0, de 1 a 4 -1), Sent (alineación técnica). Mod \
(el modelo de oportunidades) se muestra pero no vota; un voto vacío se abstiene.
- Tags, de mejor a peor: ★ UNÁNIME, ▲ CONSENSO, ↗ TENDENCIA, → NEUTRO, ↘ ALERTA, ▼ SALIDA; — S/D es sin \
datos.
- Cripto solo usa TENDENCIA, NEUTRO y ALERTA: mide la divergencia entre el ratio long/short de los top \
traders y el de las cuentas en Binance, en desvíos contra la historia del propio par.

La foto de abajo se toma al empezar y vale 30 minutos. Los precios en vivo y el detalle por lote los traen \
las herramientas."""

TOOLS = [
    {
        "name": "posicion_detalle",
        "description": (
            "Detalle de una posición en cartera: lotes abiertos (fecha, cantidad, precio, costo, GyP y ROI de "
            "cada uno, valuados al precio en vivo), las 10 últimas órdenes y la fila de la foto. Los FCI no "
            "tienen lotes en USD: para ellos devuelve solo la fila."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Símbolo tal como figura en la foto"}},
            "required": ["symbol"],
        },
        "eager_input_streaming": True,
    },
    {
        "name": "consenso_simbolo",
        "description": (
            "Votos del Consenso de un símbolo. En Stock en cartera: cada voto, el tag y la suma, con los datos "
            "13F y de analistas que los explican. En cripto o fuera de cartera: el tag guardado y el contexto "
            "de mercado."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Símbolo, ej. DLR o ADAUSDT"}},
            "required": ["symbol"],
        },
        "eager_input_streaming": True,
    },
    {
        "name": "traza_decisiones",
        "description": (
            "Lo que dijeron los agentes automáticos: eventos de GainsCapture y Preservation (veces > 1 es la "
            "misma recomendación repetida desde primera_vez) y la traza de decisiones IA (decisión, monto, "
            "motivo, estado, gates). Sin symbol devuelve lo más reciente de toda la cartera."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string", "description": "Símbolo; omitir para toda la cartera"}},
            "required": [],
        },
        "eager_input_streaming": True,
    },
    {
        "name": "oportunidades_vigentes",
        "description": (
            "Las sugerencias automáticas de compra y venta vigentes, ya filtradas por los pisos de ganancia: "
            "hasta 25 de cada lado, con cantidad, precio, ROI y el comentario del modelo."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "eager_input_streaming": True,
    },
]


class AsesorCartera:
    def __init__(self, account, account_crypto, logger, leer_sell, leer_buy):
        self.account = account
        self.account_crypto = account_crypto
        self.logger = logger
        self.leer_sell = leer_sell
        self.leer_buy = leer_buy
        self.Repo = RepositorioOportunidadesBuySell()
        self.Market = MarketScreen()
        self.IaTrace = IaTraceScreen()
        self._foto_texto = ""
        self._foto_ts = datetime.min
        self._posiciones = {}
        self._inst = {}
        self._ctx_consenso = None

    def consultar(self, messages: list) -> str:
        """Responde la ultima pregunta de messages (historial de texto, roles user/assistant alternados)."""
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages[-20:]]
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        system = [
            {"type": "text", "text": f"{INSTRUCCIONES}\n\n{self._foto()}", "cache_control": {"type": "ephemeral"}}
        ]
        api_key = BDsystem.get_sesion_by_vehiculo("ClaudeAPIC")["userapi"].decode("utf-8")
        client = anthropic.Anthropic(api_key=api_key)
        tokens_in, tokens_out = 0, 0
        try:
            for _ in range(MAX_VUELTAS):
                resp = self._llamar(client, system, msgs)
                uso = resp.usage
                tokens_in += (
                    (uso.input_tokens or 0)
                    + (getattr(uso, "cache_read_input_tokens", 0) or 0)
                    + (getattr(uso, "cache_creation_input_tokens", 0) or 0)
                )
                tokens_out += uso.output_tokens or 0
                texto = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                if resp.stop_reason == "refusal":
                    return texto or "Claude no respondió esta consulta."
                if resp.stop_reason == "max_tokens":
                    # un tool_use cortado no se ejecuta: su input puede estar truncado
                    return f"{texto}\n\n(respuesta cortada por largo)".strip()
                if resp.stop_reason == "pause_turn":
                    msgs.append({"role": "assistant", "content": resp.content})
                    continue
                if resp.stop_reason != "tool_use":
                    return texto
                msgs.append({"role": "assistant", "content": resp.content})
                resultados = [self._ejecutar(b) for b in resp.content if b.type == "tool_use"]
                msgs.append({"role": "user", "content": resultados})
            return f"No llegué a una respuesta en {MAX_VUELTAS} consultas a los datos; probá algo más acotado."
        finally:
            track_claude_usage("ClaudeAPIC", tokens_in, tokens_out)

    def _llamar(self, client, system, msgs):
        for intento in range(2):
            try:
                with client.messages.stream(
                    model=MODELO,
                    max_tokens=MAX_TOKENS,
                    system=system,
                    tools=TOOLS,
                    messages=msgs,
                    output_config={"effort": "medium"},
                    cache_control={"type": "ephemeral"},
                ) as stream:
                    return stream.get_final_message()
            except ValueError as e:
                # el parser tolerante del stream no pudo armar el input de una herramienta: se repite el pedido
                if intento:
                    raise
                self.logger.warning(f"AsesorCartera._llamar(): input de herramienta ilegible, reintento — {e}")

    def _ejecutar(self, bloque) -> dict:
        herramientas = {
            "posicion_detalle": self._posicion_detalle,
            "consenso_simbolo": self._consenso_simbolo,
            "traza_decisiones": self._traza_decisiones,
            "oportunidades_vigentes": self._oportunidades_vigentes,
        }
        try:
            entrada = bloque.input if isinstance(bloque.input, dict) else {}
            symbol = entrada.get("symbol")
            if bloque.name not in herramientas:
                raise ValueError(f"herramienta desconocida: {bloque.name}")
            if symbol is not None and not (isinstance(symbol, str) and 0 < len(symbol.strip()) <= 40):
                raise ValueError(f"symbol inválido: {symbol!r}")
            if bloque.name in ("posicion_detalle", "consenso_simbolo") and not symbol:
                raise ValueError("falta symbol")
            args = {} if bloque.name == "oportunidades_vigentes" else {"symbol": self._simbolo(symbol)}
            resultado = herramientas[bloque.name](**args)
            contenido = json.dumps(self._redondear(resultado), ensure_ascii=False, default=self._json_default)
            return {"type": "tool_result", "tool_use_id": bloque.id, "content": contenido}
        except Exception as e:
            self.logger.error(f"AsesorCartera._ejecutar({bloque.name}): {e}")
            return {"type": "tool_result", "tool_use_id": bloque.id, "content": f"Error: {e}", "is_error": True}

    def _foto(self) -> str:
        """Foto de la cartera para el system. Se congela FOTO_TTL: un system estable es lo que reusa la cache."""
        if self._foto_texto and datetime.now() - self._foto_ts < FOTO_TTL:
            return self._foto_texto
        filas = [
            f for f in self.Repo.select_inversion(tipoin="activo") or [] if float(f.get("mktvalue") or 0) >= POLVO_USD
        ]
        self._inst = {r["symbol"]: r for r in self.Market.load_cartera_inst([self.account, self.account_crypto])}
        self._ctx_consenso = None
        self._posiciones = {}
        for f in filas:
            self._posiciones.setdefault(f["ticket"], []).append(f)

        snap = read_json_tmp("kpi_snapshot") or {}
        deuda = DataHub.deuda_real()
        lineas = [
            f"FOTO DE LA CARTERA — {datetime.now():%d/%m/%Y %H:%M} (montos en USD)",
            "",
            f"Mercado: Fear & Greed de CNN {float(snap.get('fear') or 0):.0f}/100 "
            f"(lectura {snap.get('fear_ts', 's/d')}) "
            f"· su componente de volatilidad {float(snap.get('vix') or 0):.0f}/100 (no es el VIX)",
            f"Deuda: margen IB {deuda['Stock']:,.2f} de un techo de {TECHO_MARGEN_IB:,.0f} "
            f"({deuda['Stock'] / TECHO_MARGEN_IB:.1%}) · préstamo Binance {deuda['Crypto']:,.2f}",
        ]
        presentes = {f["tipoinv"] for f in filas}
        for tipoinv in [t for t in VEHICULOS if t in presentes] + sorted(presentes - set(VEHICULOS)):
            lineas += [""] + self._foto_vehiculo(tipoinv, [f for f in filas if f["tipoinv"] == tipoinv])

        top = sorted(filas, key=lambda f: float(f.get("mktvalue") or 0), reverse=True)[:20]
        set_claude_contexto(
            {
                "posiciones": [
                    {
                        "symbol": f["ticket"],
                        "nombre": self._inst.get(f["ticket"], {}).get("shortName") or f["ticket"],
                        "precio": float(f.get("mrkprice") or 0),
                    }
                    for f in top
                ]
            }
        )
        self._foto_texto = "\n".join(lineas)
        self._foto_ts = datetime.now()
        return self._foto_texto

    def _foto_vehiculo(self, tipoinv, filas) -> list:
        valor = sum(float(f.get("mktvalue") or 0) for f in filas)
        costo = sum(float(f.get("costobase") or 0) for f in filas)
        dgyp = sum(float(f.get("dgyp") or 0) for f in filas)
        gyp = valor - costo
        cuentas = ", ".join(sorted({f["useraccount"] for f in filas}))
        por_tipo = {}
        for f in filas:
            tipo = f.get("tipoActivo") or "s/d"
            por_tipo[tipo] = por_tipo.get(tipo, 0.0) + float(f.get("mktvalue") or 0)
        lineas = [
            f"{VEHICULOS.get(tipoinv, tipoinv)} — cuenta {cuentas}",
            f"Valor {valor:,.2f} · costo {costo:,.2f} · GyP no realizada {gyp:+,.2f} "
            f"({gyp / costo if costo else 0:+.1%}) · dGyP hoy {dgyp:+,.2f} · {len(filas)} posiciones",
            "Por tipo de activo: "
            + " · ".join(
                f"{t} {v:,.2f} ({v / valor if valor else 0:.1%})"
                for t, v in sorted(por_tipo.items(), key=lambda x: -x[1])
            ),
            "símbolo | sector | cantidad @ precio | costo | valor (peso) | GyP (retorno) | objetivo | div% | consenso",
        ]
        for f in sorted(filas, key=lambda x: float(x.get("mktvalue") or 0), reverse=True):
            mv = float(f.get("mktvalue") or 0)
            inst = self._inst.get(f["ticket"], {})
            tag, suma = inst.get("consenso_tag"), inst.get("consenso_suma")
            consenso = f"{tag} {suma}" if tag and suma is not None else (tag or "—")
            lineas.append(
                f"- {f['ticket']} | {f.get('sector') or 's/d'} | {float(f.get('position') or 0):.6g} @ "
                f"{float(f.get('mrkprice') or 0):.6g} | {float(f.get('costobase') or 0):,.2f} | {mv:,.2f} "
                f"({mv / valor if valor else 0:.1%}) | {float(f.get('unrealizedpnl') or 0):+,.2f} "
                f"({float(f.get('retorno') or 0):+.1%}) | {float(f.get('objetivo') or 0):.6g} | "
                f"{float(f.get('dividendYield') or 0):.2f} | {consenso}"
            )
        return lineas

    def _posicion_detalle(self, symbol) -> dict:
        filas = self._posiciones.get(symbol)
        if not filas:
            return {"error": f"{symbol} no está en la cartera (o es polvo de menos de {POLVO_USD} USD)"}
        detalle = []
        info = DataHub.info.get(symbol)
        info = info if isinstance(info, dict) else {}
        ws = info.get("websocket")
        vivo = ws.get("last") if isinstance(ws, dict) else None
        for f in filas:
            last = float(vivo or info.get("mrkprice") or f.get("mrkprice") or 0)
            item = {
                "cuenta": f["useraccount"],
                "vehiculo": f["tipoinv"],
                "precio_vivo": last,
                "posicion": {k: f.get(k) for k in CAMPOS_POSICION},
            }
            if f["tipoinv"] in ("Stock", "Crypto"):
                item.update(self._lotes_y_ordenes(symbol, f, last))
            else:
                item["lotes"] = "no aplica: las cuotapartes del FCI se registran en ARS"
            detalle.append(item)
        return {"symbol": symbol, "detalle": detalle}

    def _lotes_y_ordenes(self, symbol, fila, last) -> dict:
        resumen, a_gain, a_lost = DataHub.get_lotesGainLost(
            opcion="ambos", account=fila["useraccount"], symbol=symbol, divisa=fila.get("divisa") or "USD", last=last
        ) or ({}, [], [])
        lotes = sorted(a_gain + a_lost, key=lambda l: str(l.get("fecha")))
        filas_ord, ix = self.Repo.select_order_trader(
            account=fila["useraccount"], vehiculo=fila["tipoinv"], symbol=symbol
        ) or ([], [])
        ordenes = sorted((dict(zip(ix, r)) for r in filas_ord), key=lambda o: str(o.get("stampPlace")), reverse=True)
        return {
            "lotes_abiertos": len(lotes),
            "lotes_en_ganancia": len(a_gain),
            "gyp_lotes_en_ganancia": sum(l["gyp"] for l in a_gain),
            "gyp_lotes_en_perdida": sum(l["gyp"] for l in a_lost),
            "lotes": [
                {
                    "fecha": l.get("fecha"),
                    "cantidad": l.get("cantidad"),
                    "precio": l.get("precio"),
                    "costo": l.get("costo"),
                    "gyp": l.get("gyp"),
                    "roi_pct": (l.get("roi") or 0) * 100,
                }
                for l in lotes[-MAX_LOTES:]
            ],
            "lotes_omitidos_mas_viejos": max(0, len(lotes) - MAX_LOTES),
            "ultimas_ordenes": [{k: o.get(k) for k in CAMPOS_ORDEN} for o in ordenes[:10]],
        }

    def _consenso_simbolo(self, symbol) -> dict:
        self._foto()
        row = self._inst.get(symbol)
        if row and row.get("categoriaActivo") != "C":
            if self._ctx_consenso is None:
                cartera = [r for r in self._inst.values() if r.get("categoriaActivo") != "C"]
                self._ctx_consenso = contexto_consenso(self.account, cartera)
            votos = votos_consenso(row, self._ctx_consenso)
            tag, suma, n = senal_votos(votos)
            return {
                "symbol": symbol,
                "tag": tag,
                "suma": suma,
                "votos_emitidos": n,
                "votos": votos,
                "datos": {k: row.get(k) for k in CAMPOS_INST},
            }
        es_cripto = (row or {}).get("categoriaActivo") == "C" or symbol.endswith(("USDT", "USDC"))
        ctx = self.Market.select_feed_context(symbol, self.account_crypto if es_cripto else self.account)
        if not ctx:
            return {"symbol": symbol, "error": "sin datos en market para este símbolo"}
        ctx["nota"] = (
            "señal cripto: divergencia long/short top traders contra cuentas en Binance"
            if es_cripto
            else "fuera de cartera: el tag guardado puede estar viejo, el Consenso solo se recalcula en cartera"
        )
        return {"symbol": symbol, **ctx}

    def _traza_decisiones(self, symbol=None) -> dict:
        eventos = self.Repo.select_symbol_decision_history(symbol, limit=15)
        traza = self.IaTrace.select_trace(limit=15, simbolo=symbol)
        for e in eventos:
            e["mensaje"] = str(e.get("mensaje") or "")[:400]
        for t in traza:
            t["motivo"] = str(t.get("motivo") or "")[:400]
        return {"symbol": symbol or "toda la cartera", "eventos_agentes": eventos, "traza_ia": traza}

    def _oportunidades_vigentes(self) -> dict:
        resultado = {}
        for lado, leer, archivo, columnas in (
            ("venta", self.leer_sell, "csv_datosIA_sell", COLUMNAS_SELL),
            ("compra", self.leer_buy, "csv_datosIA_buy", COLUMNAS_BUY),
        ):
            df = leer(file=archivo, filtrar=True)
            if df is None or df.empty:
                resultado[lado] = []
                continue
            cols = [c for c in columnas if c in df.columns]
            resultado[lado] = df[cols].head(MAX_FILAS_CSV).to_dict("records")
            resultado[f"{lado}_total"] = len(df)
        return resultado

    def _simbolo(self, symbol):
        """Simbolo canonico: el de la cartera si coincide sin distinguir mayusculas (los FCI tienen nombres), si no
        en mayusculas. posicion_detalle solo acepta los de la cartera, que es lo que llega al SQL sin parametros."""
        if symbol is None:
            return None
        limpio = symbol.strip()
        for ticket in self._posiciones:
            if ticket.casefold() == limpio.casefold():
                return ticket
        return limpio.upper()

    @staticmethod
    def _redondear(valor):
        if isinstance(valor, float):
            return None if math.isnan(valor) or math.isinf(valor) else float(f"{valor:.6g}")
        if isinstance(valor, dict):
            return {k: AsesorCartera._redondear(v) for k, v in valor.items()}
        if isinstance(valor, (list, tuple)):
            return [AsesorCartera._redondear(v) for v in valor]
        return valor

    @staticmethod
    def _json_default(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return str(valor)
