"""
Class_AgentManager.py - Administrador de agentes síncronos
Dominios: Stock | Crypto | IA | Infra
"""

from Modulos_python import logging, json, datetime, timedelta, yf, requests, textwrap, Path, ntplib
from Modulos_Utilitarios import wait_rate, read_json_tmp, write_json_tmp, track_claude_usage, load_vehiculo_params
from Modulos_Mysql import (
    RepositorioOportunidadesBuySell,
    BDsystem,
    PlanInversion,
    MarketScreen,
    EstrategiaInversion,
    IPerformance,
)
from Class_Finance import scan_extractos
from Class_IbFlex import Class_IbFlex
from Class_IbReconcile import Class_IbReconcile
from Class_Screener import sync_market, sync_prices, audit_portfolio, refresh_consenso_tags, sync_dividend_status_screener
from Class_InstitucionalScore import sync_institutional, sync_edgar_funds, sync_13f_scores
from edgar_13f import sync_fund_filings, sync_13f_holdings
from ConvergIA.Scanner_Sentimiento import scan_sentimiento
from ConvergIA.Scanner_YouTube import scan_youtube, backfill_youtube_candidatos
from ConvergIA.Interprete_Sentimiento import interpretar_sentimiento
from valuation_edgar_downloader import BASE_DIR, download_filing
from valuation_xbrl_api import get_zip_files
from Class_customer import DataHub
from Class_ServiciosCrypto import ServiciosCrypto
from Class_ApiCosts import ApiCostTracker
from Class_DataFrame import CacheHut


class AgentManager:
    """Coordinador de agentes síncronos. Cada dominio tiene su propio logger."""

    def __init__(self, account: str, vehiculo: str = "Stock"):
        self.account = account
        self.vehiculo = vehiculo
        self.positions = []
        self.NotFound = []
        self.PlanInversion = PlanInversion()
        self.RepositorioOportunidades = RepositorioOportunidadesBuySell()
        self.Performa = IPerformance()
        self._params_cache: dict = {}

        self._log_stock = logging.getLogger("Agente.Stock")
        self._log_crypto = logging.getLogger("Agente.Crypto")
        self._log_ia = logging.getLogger("Agente.IA")
        self._log_infra = logging.getLogger("Agente.Infra")
        self._log_performa = logging.getLogger("Agente.Performa")
        self._log_edgar = logging.getLogger("Agente.EDGAR")
        self._log_institucion = logging.getLogger("Agente.Institucion")
        self._preservation_logger = logging.getLogger("Agente.Preservation")

        # Preservation state management
        self.preservation_config = {}
        self.preservation_state = {}
        self.preservation_last_run = {}
        self._preservation_dry_run = False

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_params(self, vehiculo: str):
        return load_vehiculo_params(vehiculo, self._params_cache, self.PlanInversion)

    def _clasificar_etf_claude(self, yf_info: dict, opciones: list):
        sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIE")
        api_key = sesion["userapi"].decode("utf-8") if sesion else ""
        if not api_key:
            self._log_ia.error("_clasificar_etf_claude: userapi no configurada en sesion ClaudeAPIE")
            return None
        opciones_str = " | ".join(f"{o['descripcion']}({o['estrategia']})" for o in opciones)
        nombre = yf_info.get("longName") or yf_info.get("shortName", "")
        descripcion = (yf_info.get("longBusinessSummary") or "N/A")[:400]
        categoria = yf_info.get("category") or "N/A"
        prompt = (
            f"Clasificá este activo financiero en exactamente una de estas categorías:\n{opciones_str}\n\n"
            f"Nombre: {nombre}\nDescripción: {descripcion}\nCategoría Morningstar: {categoria}\n\n"
            f"Respondé solo el código de estrategia (ej: P01). Sin explicación."
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        resp.raise_for_status()
        usage = resp.json().get("usage", {})
        track_claude_usage("ClaudeAPIE", usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        codigo = resp.json()["content"][0]["text"].strip()
        return codigo if codigo in {o["estrategia"] for o in opciones} else None

    # ── Agente.Stock ──────────────────────────────────────────────────────────

    @wait_rate(3600)
    def Agente_downloads_filings_EDGAR(self):
        try:
            self.positions = self.PlanInversion.select_inversion(tipoin=self.vehiculo, ticket="all")
            counter = 1
            for pos in self.positions:
                ticker = pos.get("ticket")
                sectype = pos.get("sectype")
                if ticker in self.NotFound:
                    continue
                if sectype not in ("STK", "EQUITY"):
                    continue
                ticker_dir = Path(BASE_DIR) / f"{ticker}_EDGAR_Files"
                if get_zip_files(ticker_dir=ticker_dir):
                    continue
                counter += 1
                found = download_filing(ticker=ticker)
                if not found:
                    self.NotFound.append(ticker)
                    self._log_stock.warning(textwrap.dedent(f"""
                        ==============================================================================================
                        Agente_downloads_filings_EDGAR():
                        🚨 FILINGS DENEGADO. Posible deslistado del ticker: {ticker}
                        ==============================================================================================
                    """))
                elif found and counter > 2:
                    return None
        except Exception as e:
            self._log_stock.error(f"Agente_downloads_filings_EDGAR(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_MarketScreener(self):
        try:
            result = sync_market(account=self.account)
            self._log_stock.warning(
                f"MarketScreener: descargados={result['descargados']} insertados={result['insertados']} "
                f"omitidos={result['omitidos']} actualizados={result['actualizados']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_MarketScreener(): {e}")

    @wait_rate(43200, persist=True, initial_delay=120)
    def Agente_PriceSync(self):
        try:
            result = sync_prices(account=self.account)
            self._log_stock.warning(
                f"PriceSync: updated={result['updated']} market={result['market']} "
                f"candidatos={result['candidatos']} errors={result['errors']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_PriceSync(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_InstitucionalScore(self):
        try:
            result = sync_institutional(account=self.account)
            self._log_institucion.warning(
                f"InstitucionalScore: procesados={result['symbols_processed']} actualizados={result['updated']}"
            )
        except Exception as e:
            self._log_institucion.error(f"Agente_InstitucionalScore(): {e}")

    @wait_rate(300, persist=True)
    def Agente_ConsensoCache(self):
        try:
            result = refresh_consenso_tags(account=self.account)
            self._log_institucion.warning(f"ConsensoCache: actualizados={result['actualizados']}/{result['total']}")
        except Exception as e:
            self._log_institucion.error(f"Agente_ConsensoCache(): {e}")

    @wait_rate(2592000, persist=True)
    def Agente_EdgarFunds(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_EdgarFunds._overdue:
            return
        try:
            result = sync_edgar_funds()
            self._log_edgar.warning(f"EdgarFunds: total={result['total']} insertados={result['inserted']}")
        except Exception as e:
            self._log_edgar.error(f"Agente_EdgarFunds(): {e}")

    @wait_rate(604800, persist=True)
    def Agente_FundFilings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_FundFilings._overdue:
            return
        try:
            task_name = "Agente_FundFilings()"

            def _progress(i, total):
                DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=i)

            result = sync_fund_filings(account=self.account, progress_cb=_progress)
            self._log_edgar.warning(
                f"FundFilings: fondos={result['funds']} descargados={result['downloaded']} "
                f"skipped={result['skipped']} fallidos={result['failed']}"
            )
        except Exception as e:
            self._log_edgar.error(f"Agente_FundFilings(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_13FScores(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FScores._overdue:
            return
        try:
            result = sync_13f_scores(account=self.account)
            self._log_edgar.warning(
                f"13FScores: símbolos={result['symbols']} actualizados={result['updated']} skipped={result['skipped']}"
            )
        except Exception as e:
            self._log_edgar.error(f"Agente_13FScores(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_13FHoldings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FHoldings._overdue:
            return
        try:
            result = sync_13f_holdings(account=self.account)
            self._log_edgar.warning(
                f"13FHoldings: archivos={result['xml_files']} "
                f"holdings={result['inserted_holdings']} opciones={result['inserted_options']}"
            )
            deleted = MarketScreen().cleanup_fund_holdings_nulls()
            self._log_edgar.warning(f"13FHoldings cleanup: eliminadas={deleted} filas NULL")
        except Exception as e:
            self._log_edgar.error(f"Agente_13FHoldings(): {e}")

    @wait_rate(2592000, persist=True)
    def Agente_AuditPortfolio(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_AuditPortfolio._overdue:
            return
        try:
            result = audit_portfolio(account=self.account)
            self._log_institucion.warning(
                f"AuditPortfolio: total={result['total']} delistados={result['delistados']} "
                f"nombres_upd={result['nombres_upd']} cusips_upd={result['cusips_upd']} "
                f"etfs_upd={result['etfs_upd']} sin_precio={result['sin_precio']} errores={result['errores']}"
            )
        except Exception as e:
            self._log_institucion.error(f"Agente_AuditPortfolio(): {e}")

    @wait_rate(2592000, persist=True, desc="Actualiza categoriaActivo Screener ex-cartera (30d)", nivel=2)
    def Agente_DividendStatusScreener(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_DividendStatusScreener._overdue:
            return
        try:
            result = sync_dividend_status_screener(account=self.account)
            self._log_stock.warning(
                f"DividendStatusScreener: procesados={result['processed']} errores={result['errors']} total={result['total']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_DividendStatusScreener(): {e}")

    @wait_rate(3600, persist=True)
    def Agente_StockBeta(self):
        try:
            positions = [p for p in DataHub.manager_positions.get("Stock", []) if float(p.get("mktvalue", 0)) > 0]
            if not positions:
                return
            result = MarketScreen().select_all(account=self.account)
            if not result:
                return
            rows, ix = result
            if not rows or not ix:
                return
            beta_map = {dict(zip(ix, row))["symbol"]: dict(zip(ix, row)).get("beta") for row in rows}
            total_val = beta_sum = 0.0
            for p in positions:
                val = float(p.get("mktvalue", 0))
                try:
                    beta = float(beta_map.get(p.get("ticket", "")) or 1.0)
                except (TypeError, ValueError):
                    beta = 1.0
                beta_sum += val * beta
                total_val += val
            beta_port = round(max(beta_sum / total_val, 0.1), 3) if total_val > 0 else 1.0
            DataHub.manager_GyP["Stock"]["BetaPortfolio"] = beta_port
            self._log_institucion.warning(f"StockBeta: β={beta_port:.3f}  ({len(positions)} posiciones)")
        except Exception as e:
            self._log_institucion.error(f"Agente_StockBeta(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_SplitsControl(self):
        try:
            result = self.RepositorioOportunidades.sync_splits(account=self.account)
            self._log_stock.warning(
                f"SplitsControl: nuevos={result['nuevos']} aplicados={result['aplicados']} residuos={result['residuos']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_SplitsControl(): {e}")

    @wait_rate(3600, persist=True)
    def Agente_PerformaValidator(self):
        try:
            st = CacheHut.stats()
            self._log_performa.warning(
                f"PerformaValidator: cache size={st['size']}/{st['maxsize']} "
                f"hits={st['hits']} misses={st['misses']} bypass={st['bypass']}"
            )
            for veh in ["Stock", "Crypto"]:
                extreme_threshold = 100.0 if veh == "Crypto" else 2.0
                result = self.Performa.validate_performa(
                    account=self.account,
                    vehiculo=veh,
                    extreme_threshold=extreme_threshold
                )
                if result["purgados"]:
                    extremas = result.get("extremas", 0)
                    if extremas > 0:
                        self._log_performa.critical(
                            f"PerformaValidator {veh}: ⚠️ {extremas} ANOMALÍAS EXTREMAS (>100x) detectadas y purgadas"
                        )
                    for a in result["anomalias"]:
                        sym, fecha, ratio = a["symbol"], a["fecha"], a["ratio"]
                        if a.get("extrema", False):
                            self._log_performa.critical(
                                f"PerformaValidator {veh}: {sym} {fecha} EXTREMA ratio={ratio:.1f}x — purgado"
                            )
                        elif a.get("quarantined"):
                            self._log_performa.critical(
                                f"PerformaValidator {veh}: {sym} CUARENTENA — purgado 3+ veces en 6h, ratio={ratio:.2f}x"
                            )
                        else:
                            self._log_performa.warning(
                                f"PerformaValidator {veh}: {sym} {fecha} ratio={ratio:.2f}x purgado — bypass cache"
                            )
                            CacheHut.add_bypass(sym)
        except Exception as e:
            self._log_performa.error(f"Agente_PerformaValidator(): {e}")

    # ── Agente.Crypto ─────────────────────────────────────────────────────────

    @wait_rate(300, persist=True)
    def Agente_LtvControl(self):
        try:
            params = self._load_params("Crypto")
            lconfig = (params or {}).get("ltv", {})
            svc = ServiciosCrypto()
            analisis = svc.ltv_check_and_adjust(lconfig)
            if not analisis:
                self._log_crypto.warning("LtvControl: sin préstamos activos")
                return

            total_col = sum(i["collateral_usd"] for i in analisis)
            total_deuda = sum(i["loan_usd"] for i in analisis)
            try:
                earn_balances = svc.earn_spot_balances()
                earn_map = {b["asset"]: b.get("usdt_value", 0.0) for b in earn_balances}
                col_assets = {i["collateralCoin"] for i in analisis}
                capital_earn_col = sum(earn_map.get(a, 0.0) for a in col_assets)
            except Exception as e_earn:
                self._log_crypto.error(f"LtvControl earn_spot_balances: {e_earn}")
                capital_earn_col = 0.0

            capital_neto = (capital_earn_col if capital_earn_col > 0 else total_col) - total_deuda
            DataHub.manager_GyP["Crypto"]["Colateral"] = total_col
            DataHub.manager_GyP["Crypto"]["CapitalNeto"] = capital_neto
            DataHub.manager_GyP["Crypto"]["Debit"] = total_deuda
            DataHub.manager_GyP["Crypto"]["Leverage"] = total_col / max(capital_neto, 1.0)
            beta_actual = DataHub.manager_GyP["Crypto"].get("BetaPortfolio", 1.5)
            mrg_actual = total_deuda / max(capital_neto, 1.0) * beta_actual
            step = lconfig.get("rebalance_step", 0.25)
            self._log_crypto.warning(
                f"LtvControl DataHub: col={total_col:.2f} earn_col={capital_earn_col:.2f} "
                f"deuda={total_deuda:.2f} neto={capital_neto:.2f} beta={beta_actual:.3f} → mrg={mrg_actual:.2%} step={step}"
            )

            if not lconfig:
                return
            for item in analisis:
                gap = item["ltv_actual"] - lconfig.get("target", 0.50)
                gap_str = f"+{gap:.2%}" if gap >= 0 else f"{gap:.2%}"
                if item["ajuste_direction"] and item["ajuste_coin"] > 0:
                    resp = svc._spot.get_flexible_adjust_ltv(
                        loanCoin=item["loanCoin"],
                        collateralCoin=item["collateralCoin"],
                        adjustType=item["ajuste_direction"],
                        amount=item["ajuste_coin"],
                    )
                    ajuste_str = (
                        f"{item['ajuste_direction']} {item['ajuste_coin']:.4f} {item['collateralCoin']} → {resp}"
                    )
                else:
                    ajuste_str = "sin ajuste"
                self._log_crypto.warning(
                    f"LTV [{item['collateralCoin']}] {item['ltv_actual']:.2%} gap={gap_str} "
                    f"{item['estado']} | col={item['collateral_amount']:.4f} (~{item['collateral_usd']:.2f}) "
                    f"deuda={item['loan_usd']:.2f} | {ajuste_str}"
                )
        except Exception as e:
            self._log_crypto.error(f"Agente_LtvControl(): {e}")

    @wait_rate(21600)
    def Agente_CryptoBeta(self):
        try:
            positions = [p for p in DataHub.manager_positions.get("Crypto", []) if float(p.get("position", 0)) > 0]
            if not positions:
                return
            orig_names = [p["ticket"] for p in positions]
            yf_names = [s[:-4] + "-USD" if s.endswith("USDT") else s for s in orig_names]
            name_map = dict(zip(yf_names, orig_names))
            raw = yf.download(yf_names, period="6mo", auto_adjust=True, progress=False)
            if raw.empty:
                return
            close = (
                raw[["Close"]].rename(columns={"Close": orig_names[0]})
                if len(yf_names) == 1
                else raw["Close"].rename(columns=name_map)
            )
            returns = close.pct_change().dropna()
            if returns.empty or len(returns) < 10:
                return
            btc_col = next((c for c in returns.columns if "BTC" in c.upper()), None)
            market_ret = returns[btc_col] if btc_col else returns.mean(axis=1)
            market_var = market_ret.var()
            if market_var == 0:
                return
            beta_map = {col: returns[col].cov(market_ret) / market_var for col in returns.columns}
            total_val = sum(float(p.get("mktvalue", 0)) for p in positions)
            if total_val <= 0:
                return
            beta_port = sum(
                (float(p.get("mktvalue", 0)) / total_val) * beta_map.get(p["ticket"], 1.5) for p in positions
            )
            DataHub.manager_GyP["Crypto"]["BetaPortfolio"] = round(max(beta_port, 0.1), 3)
            self._log_crypto.warning(
                f"CryptoBeta: β={DataHub.manager_GyP['Crypto']['BetaPortfolio']:.3f}  ({len(positions)} posiciones)"
            )
        except Exception as e:
            self._log_crypto.error(f"Agente_CryptoBeta(): {e}")

    # ── Agente.IA ─────────────────────────────────────────────────────────────
    # Sentimiento e InterpreteSentimiento viven en Class_DashBot (incluyen cleanup_sentiment)

    def _run_clasificador(self, estrategia_svc, ivehiculo: str, pendientes: list, nombre: str):
        opciones = estrategia_svc.select(accion="vehiculo", ivehiculo=ivehiculo)
        clasificados = 0
        for item in pendientes:
            symbol = item["symbol"]
            yf_info = DataHub.info.get(symbol, {}).get("activos", {}) or {"shortName": item.get("shortName", symbol)}
            codigo = self._clasificar_etf_claude(yf_info, opciones)
            if codigo:
                estrategia_svc.update_estrategia_etf(symbol, self.account, codigo)
                clasificados += 1
        self._log_ia.warning(f"{nombre}: pendientes={len(pendientes)} clasificados={clasificados}")

    @wait_rate(604800, persist=True)
    def Agente_ClasificadorETF(self):
        try:
            svc = EstrategiaInversion()
            self._run_clasificador(svc, "Balance", svc.get_etfs_pendientes(self.account), "ClasificadorETF")
        except Exception as e:
            self._log_ia.error(f"Agente_ClasificadorETF(): {e}")

    @wait_rate(604800, persist=True, desc="Reclasifica crypto y Exchange legacy con estrategia incorrecta (semanal)", nivel=2)
    def Agente_ClasificadorCrypto(self):
        try:
            svc = EstrategiaInversion()
            pendientes = svc.get_crypto_pendientes(self.account) + svc.get_exchange_pendientes(self.account)
            self._run_clasificador(svc, "Crypto", pendientes, "ClasificadorCrypto")
        except Exception as e:
            self._log_ia.error(f"Agente_ClasificadorCrypto(): {e}")

    @wait_rate(3600, persist=True)
    def Agente_ApiCostTracker(self):
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIA")

            def _s(v):
                return v.decode("utf-8") if isinstance(v, bytes) else (v or "")

            api_key = _s(sesion.get("userapi")) if sesion else ""
            workspace_id = _s(sesion.get("environment")) if sesion else ""
            result = ApiCostTracker(api_key, workspace_id).get_monthly_summary()
            self._log_ia.warning(f"ApiCostTracker: cost=${result['total_cost']:.4f} hoy=${result['today_cost']:.4f}")
        except Exception as e:
            self._log_ia.error(f"Agente_ApiCostTracker(): {e}")

    @wait_rate(21600, persist=True)
    def Agente_YouTubeScanner(self):
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIS")
            _s = lambda v: v.decode("utf-8") if isinstance(v, bytes) else (v or "")
            api_key = _s(sesion.get("userapi")) if sesion else ""
            result = scan_youtube(self.account, api_key)
            self._log_ia.warning(
                f"YouTubeScanner: videos={result['videos']} financieros={result['filtered']} "
                f"detectados={result['detected']} nuevos={result['new_validated']}"
            )
        except Exception as e:
            self._log_ia.error(f"Agente_YouTubeScanner(): {e}")

    @wait_rate(900, persist=True)
    def Agente_YouTubeBackfill(self):
        try:
            completados = backfill_youtube_candidatos(limit=5)
            if completados:
                self._log_ia.warning(f"YouTubeBackfill: {completados} candidatos completados")
        except Exception as e:
            self._log_ia.error(f"Agente_YouTubeBackfill(): {e}")

    # ── Agente.Infra ──────────────────────────────────────────────────────────

    @wait_rate(3600, persist=True)
    def Agente_ExtractosWatcher(self):
        try:
            result = scan_extractos()
            self._log_infra.warning(f"ExtractosWatcher: {result}")
        except Exception as e:
            self._log_infra.error(f"Agente_ExtractosWatcher(): {e}")

    # ── registro ──────────────────────────────────────────────────────────────

    @wait_rate(86400, persist=True, desc="Detecta posiciones residuales/fantasma en booktrading (diario)", nivel=1)
    def Agente_MonitorBooktrading(self):
        try:
            alertas = self.PlanInversion.monitor_residual_positions()
            if not alertas:
                self._log_infra.warning("Agente_MonitorBooktrading: OK — sin posiciones residuales")
                return

            cerrados = []
            for a in alertas:
                if a["motivo"].startswith("residual_fci"):
                    ok = self.PlanInversion.close_residual_fci(account=a["account"], symbol=a["symbol"])
                    if ok:
                        cerrados.append(a["symbol"])
                        self._log_infra.warning(
                            f"Agente_MonitorBooktrading: FCI cerrado — {a['symbol']}({a['account']}) "
                            f"mktval=${a['mktvalue']:.2f} → activa=N stock=0 iactiva=N"
                        )

            pendientes = [a for a in alertas if a["motivo"] != "residual_fci" or a["symbol"] not in cerrados]
            if pendientes:
                resumen = "; ".join(
                    f"{a['symbol']}({a['account']}) stock={a['book_stock']:.4f} [{a['motivo']}]" for a in pendientes
                )
                self._log_infra.warning(f"Agente_MonitorBooktrading: {len(pendientes)} residuales manuales → {resumen}")
                DataHub.add_alert(
                    "⚠️ Monitor Booktrading: {} residuales\n{}".format(
                        len(pendientes),
                        "\n".join(
                            "  • {} [{}] stock={:.4f} mktval=${:.2f} — {}".format(
                                a["symbol"], a["account"], a["book_stock"], a["mktvalue"], a["motivo"]
                            )
                            for a in pendientes
                        ),
                    ),
                    telegram=True,
                )
        except Exception as e:
            self._log_infra.error(f"Agente_MonitorBooktrading(): {e}")

    def run_loop(self):
        """Agentes ejecutados en el loop principal cada 15s (throttleados por wait_rate)."""
        self.Agente_LtvControl()
        self.Agente_StockBeta()
        self.Agente_CryptoBeta()
        self.Agente_ExtractosWatcher()
        self.Agente_SplitsControl()
        self.Agente_PerformaValidator()
        self.Agente_downloads_filings_EDGAR()

    def _browser_fci_notify_blocked(self, data: dict):
        alerta = (
            f"[FCI_BLOCKED]⚠️ BrowserFCI BLOQUEADO\n"
            f"Razón: {data.get('reason', '?')}\n"
            f"Desde: {data.get('timestamp', '?')}\n"
            f"FCI desactualizado."
        )
        if not any(isinstance(a, dict) and a.get("msg") == alerta for a in DataHub.system_alerts):
            DataHub.add_alert(alerta, telegram=True)

    @wait_rate(3600, persist=True, desc="BrowserFCI descarga FCI BBVA+Santander (L-V 8:30)", nivel=2)
    def Agente_BrowserFCI(self, forced=False):
        from Class_BrowserFCI import BrowserFCI  # import diferido — evita ciclo

        # Siempre verificar bloqueo — notificar aunque sea fuera del horario
        blocked_data = read_json_tmp("browser_fci_blocked.json")
        if blocked_data.get("blocked"):
            self._log_infra.error(
                f"Agente_BrowserFCI: BLOQUEADO desde {blocked_data.get('timestamp')} — {blocked_data.get('reason')}"
            )
            self._browser_fci_notify_blocked(blocked_data)
            return

        now = datetime.now()
        if now.weekday() >= 5 and not forced:
            return
        if not (now.hour == 8 and now.minute >= 30) and not (now.hour == 9) and not forced:
            return
        try:
            from Class_FondosInversion import sync_fci_browser  # import diferido — evita ciclo

            result = sync_fci_browser()
            self._log_infra.warning(f"Agente_BrowserFCI: procesados={result}")
        except Exception as e:
            self._log_infra.error(f"Agente_BrowserFCI(): {e}")

    @wait_rate(300, persist=True, desc="Check deriva NTP — alerta si >500ms (5min)", nivel=1)
    def Agente_NtpCheck(self):
        try:
            result = self._check_ntp_drift()
            self._log_infra.warning(f"NtpCheck: offset={result['offset_ms']:.0f}ms server={result['server']}")
        except Exception as e:
            self._log_infra.error(f"Agente_NtpCheck(): {e}")

    @wait_rate(604800, persist=True, desc="IB Flex — descarga semanal + import a ib_flex_trades (7d)", nivel=1)
    def Agente_IbFlex(self):
        try:
            result = self._ib_flex_sync()
            self._log_infra.warning(f"IbFlex: {result}")
        except Exception as e:
            self._log_infra.error(f"Agente_IbFlex(): {e}")

    def _ib_flex_sync(self) -> str:
        sesion     = BDsystem.get_sesion_by_vehiculo("Stock")
        account_id = sesion.get("idcuentaIB") or sesion.get("idcuenta")
        bt_account = sesion.get("idcuenta")
        params_raw = sesion.get("parameters") or b"{}"
        if isinstance(params_raw, (bytes, bytearray)):
            params_raw = params_raw.decode("utf-8")
        params   = json.loads(params_raw) if params_raw.strip() else {}
        ib       = params.get("ib", {})
        token    = str(ib.get("token") or "").strip()
        query_id = str(ib.get("consulta_flex") or "").strip()
        if not token or not query_id:
            return "SKIP — token o consulta_flex no configurados en session.parameters['ib']"
        db    = RepositorioOportunidadesBuySell()
        flex  = Class_IbFlex(token=token, query_id=query_id)
        result = flex.import_to_db(db, account_id)
        stats  = db.count_ib_trades(account_id)
        msg = (f"inserted={result['inserted']} skipped={result['skipped']} "
               f"total_db={stats['total']} rango={stats['date_min']}→{stats['date_max']}")
        if result["inserted"] > 0:
            self._ib_reconcile_check(db, account_id, bt_account)
        return msg

    def _ib_reconcile_check(self, db, ib_account: str, bt_account: str):
        """Corre reconcile tras import y pushea diffs a DataHub.reconcile_pending para aprobación Telegram."""
        try:
            period_start = (datetime.now().replace(year=datetime.now().year - 1)).strftime("%Y-01-01")
            rec  = Class_IbReconcile(db)
            df   = rec.reconcile_from_db(bt_account, period_start)
            diffs = df[df["diff"].abs() > 0.001]
            if diffs.empty:
                return
            pending = []
            for _, row in diffs.iterrows():
                pending.append({
                    "symbol":     row["symbol"],
                    "bt_id":      int(row["bt_id"]) if row["bt_id"] and str(row["bt_id"]) != "nan" else None,
                    "bt_current": float(row["bt_current"]),
                    "expected":   float(row["expected"]),
                    "diff":       float(row["diff"]),
                })
            DataHub.reconcile_pending.extend(pending)
            self._log_infra.warning(f"IbReconcile: {len(pending)} diffs pendientes de aprobación Telegram")
        except Exception as e:
            self._log_infra.error(f"_ib_reconcile_check(): {e}")

    def _check_ntp_drift(self):
        client = ntplib.NTPClient()
        response = client.request("pool.ntp.org", version=3)
        offset_ms = abs(response.offset) * 1000
        if offset_ms > 500:
            import time as _time
            _now = _time.time()
            _last = getattr(self, "_ntp_last_alert_ts", 0)
            if _now - _last > 3600:
                DataHub.add_alert(
                    f"⏱ NTP: reloj deriva {offset_ms:.0f}ms — riesgo de rechazo de órdenes IB/Binance",
                    telegram=True,
                )
                self._ntp_last_alert_ts = _now
        return {"offset_ms": offset_ms, "server": "pool.ntp.org"}

    @wait_rate(86400, persist=True, desc="Reconcile lotes vs IB (24h)", nivel=2)
    def Agente_LotesReconcile(self):
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("Stock")
            ib_account = sesion.get("idcuentaIB") or sesion.get("idcuenta")
            deltas = self.PlanInversion.check_lotes_vs_position(account=self.account)
            if not deltas:
                self._log_infra.warning("Agente_LotesReconcile: OK — sin diferencias lotes vs IB")
                return
            date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            ib_net = {
                r["symbol"]: float(r["ib_net"])
                for r in self.RepositorioOportunidades.get_ib_trades_net(ib_account, date_from)
            }
            lineas = []
            for d in deltas:
                sym = d["simbolo"]
                flex_net = ib_net.get(sym)
                diag = f"Flex 90d={flex_net:+.2f}" if flex_net is not None else "sin datos Flex"
                self._log_infra.warning(
                    f"Agente_LotesReconcile: {sym} Δ={d['delta']:+.2f} "
                    f"book={d['lotes_book']:.2f} IB={d['ib_position']:.2f} [{diag}]"
                )
                lineas.append(f"{sym}: book={d['lotes_book']:.2f} IB={d['ib_position']:.2f} Δ={d['delta']:+.2f} [{diag}]")
            DataHub.add_alert(
                "⚠️ Reconcile Lotes: {} dif\n{}".format(
                    len(deltas),
                    "\n".join(f"  • {l}" for l in lineas),
                ),
                telegram=True,
            )
        except Exception as e:
            self._log_infra.error(f"Agente_LotesReconcile(): {e}")

    @wait_rate(86400, persist=True, desc="Limpia market sin enriquecimiento (24h)", nivel=1)
    def Agente_CleanupMarketNoScore(self):
        """Elimina símbolos sin datos enriquecidos: sin inst_score AND sin fh_count (13F).
        Mantiene símbolos con fh_count > 0 aunque falte inst_score (solo falta calcular score)."""
        try:
            market = MarketScreen()
            conn = BDsystem.connect_dbase("select.market")
            cursor = conn.cursor()

            # Diagnóstico
            cursor.execute("""
                SELECT
                    SUM(CASE WHEN inst_score IS NULL AND fh_count IS NULL THEN 1 ELSE 0 END),
                    SUM(CASE WHEN inst_score IS NULL AND fh_count > 0 THEN 1 ELSE 0 END)
                FROM market WHERE account=%s AND encartera != 'Y' AND tipo = 'Dividends'
            """, (self.account,))
            sin_datos, sin_score_13f = cursor.fetchone()

            if not sin_datos:
                self._log_stock.warning(
                    f"Agente_CleanupMarketNoScore: OK — sin_score_13f={sin_score_13f or 0} (mantienen), sin_datos=0"
                )
                cursor.close()
                conn.close()
                return

            # Obtener y eliminar símbolos sin datos (sin inst_score AND sin fh_count)
            cursor.execute("""
                SELECT symbol FROM market
                WHERE account=%s AND encartera != 'Y' AND tipo = 'Dividends'
                AND inst_score IS NULL AND fh_count IS NULL
            """, (self.account,))
            symbols = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            for sym in symbols:
                market.delete(symbol=sym, account=self.account)

            self._log_stock.warning(
                f"Agente_CleanupMarketNoScore: eliminados={len(symbols)} sin_datos, "
                f"mantenidos={sin_score_13f or 0} sin_score_pero_13f"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_CleanupMarketNoScore(): {e}")

    # ── Preservation: Protección de ganancias con STOP dinámicos ────────────────

    @wait_rate(43200, persist=True, desc="Preservación de ganancias (12h)", nivel=1)
    def Agente_ManagerPreservation(self):
        """
        Agente de Preservación de Ganancias (Stock + Crypto).
        Protege ganancias acumuladas mediante órdenes STOP dinámicas.
        No optimiza ventas, no predice mercado, solo protege.
        """
        for vehiculo in ("Stock", "Crypto"):
            try:
                if DataHub.manager_sesion.get(vehiculo):
                    self._preservation_run_vehiculo(vehiculo)
                else:
                    self._preservation_logger.debug(f"Agente_ManagerPreservation({vehiculo}): sesion no activa → SKIP")
            except Exception as e:
                self._preservation_logger.error(f"Agente_ManagerPreservation({vehiculo}): {e}")

    def _build_preservation_context(
        self, symbol, account, roi, last, sma_base, max_price, stop_calculado, stop_anterior, atr, base_limit
    ) -> dict:
        """Arma el dict de contexto completo para el prompt Claude de preservation."""
        ctx = MarketScreen().select_preservation_context(symbol, account)
        ctx.update(
            {
                "symbol": symbol,
                "roi": roi,
                "last": last,
                "sma_base": sma_base,
                "max_price": max_price,
                "stop_calculado": stop_calculado,
                "stop_anterior": stop_anterior,
                "atr": atr,
                "base_limit": base_limit,
            }
        )
        dt = DataHub.info.get(symbol, {}).get("datos_tecnicos", {})
        d = dt.get("diaria", {})
        s = dt.get("semanal", {})
        if d:
            ctx["rsi_d"] = round(d["rsi"], 1) if d.get("rsi") is not None else None
            macd_val = d.get("macd")
            if macd_val is not None:
                ctx["macd_estado"] = "alcista" if macd_val > 0 else ("bajista" if macd_val < 0 else "neutro")
            ema200 = (d.get("ema(20,50,100,200)") or {}).get("EMA200")
            precio = d.get("precio_calculo")
            if ema200 and precio:
                ctx["ema200_rel"] = "sobre" if precio > ema200 else "bajo"
            w13_min, w13_max = d.get("13_semanas_min"), d.get("13_semanas_max")
            if w13_min is not None and w13_max and w13_max > w13_min and precio:
                ctx["rango_13w_pct"] = round((precio - w13_min) / (w13_max - w13_min), 2)
        if s:
            ctx["rsi_w"] = round(s["rsi"], 1) if s.get("rsi") is not None else None
            precio_s = s.get("precio_calculo")
            w26_min, w26_max = s.get("26_semanas_min"), s.get("26_semanas_max")
            if w26_min is not None and w26_max and w26_max > w26_min and precio_s:
                ctx["rango_26w_pct"] = round((precio_s - w26_min) / (w26_max - w26_min), 2)
        return ctx

    def _claude_preservation_eval(self, ctx: dict, api_key: str) -> dict | None:
        """Llama a Claude Haiku para afinar el stop. Retorna dict o None si falla."""
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
            f"- ROI actual: {_v('roi', '{:.1%}')} | Precio: ${_v('last', '{:.2f}')} | SMA20: ${_v('sma_base', '{:.2f}')} | Max reciente: ${_v('max_price', '{:.2f}')}\n"
            f"- Stop base (SMA20): ${_v('stop_calculado', '{:.2f}')} | Stop anterior: ${_v('stop_anterior', '{:.2f}')}\n"
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
        from Class_ServiciosCrypto import _call_claude
        result = _call_claude(prompt, api_key, "ClaudeAPIP", max_tokens=256, timeout=15)
        return result if result and "stop_sugerido" in result else None

    def _preservation_get_config(self, vehiculo):
        """
        Carga config desde BD una sola vez por vehículo (cache en self.preservation_config).
        En cada ciclo solo verifica si pasó el intervalo — sin tocar BD.
        Retorna (pconfig, intervalo_min, ejecutar) donde ejecutar=True cuando toca revisión.
        """
        if vehiculo not in self.preservation_config:
            params = self._load_params(vehiculo)
            if not params:
                self._preservation_logger.warning(f"Preservation({vehiculo}): sin parameters en sesion → SKIP")
                self.preservation_config[vehiculo] = None
                return None, 0, False
            pconfig = params.get("preservation")
            if not pconfig:
                self._preservation_logger.warning(f"Preservation({vehiculo}): sin bloque 'preservation' en parameters → SKIP")
                self.preservation_config[vehiculo] = None
                return None, 0, False
            self.preservation_config[vehiculo] = pconfig
            roi_minimo = pconfig.get("roi_minimo", 0.10)
            proteccion_base = pconfig.get("proteccion_base", 0.50)
            self._log_stock.warning(
                f"Preservation({vehiculo}): config cargada | roi_min={roi_minimo} | prot={proteccion_base}"
            )

        pconfig = self.preservation_config.get(vehiculo)
        if not pconfig:
            return None, 0, False

        revisiones_dia = pconfig.get("revisiones_dia", 2)
        intervalo_min = 86400 / revisiones_dia

        _preservation_state_fresh = read_json_tmp("preservation_state.json")
        last_run_str = _preservation_state_fresh.get(f"_last_run_{vehiculo}")
        last_run = datetime.fromisoformat(last_run_str) if isinstance(last_run_str, str) else None
        if last_run is not None:
            elapsed = (datetime.now() - last_run).total_seconds()
            if elapsed < intervalo_min:
                return pconfig, intervalo_min, False

        now = datetime.now()
        self.preservation_last_run[vehiculo] = now
        _state_snap = read_json_tmp("preservation_state.json")
        _state_snap[f"_last_run_{vehiculo}"] = now.isoformat()
        write_json_tmp("preservation_state.json", _state_snap)
        roi_minimo = pconfig.get("roi_minimo", 0.10)
        proteccion_base = pconfig.get("proteccion_base", 0.50)
        elapsed_log = (now - last_run).total_seconds() if last_run else 0
        self._log_stock.warning(
            f"Preservation({vehiculo}): REVISIÓN | roi_min={roi_minimo} | prot={proteccion_base} | elapsed={elapsed_log:.0f}s"
        )
        return pconfig, intervalo_min, True

    def _preservation_run_vehiculo(self, vehiculo):
        """Orquesta la preservación para un vehículo. Lógica de vehículo en DataHub."""
        import time
        import json

        pconfig, intervalo_min, time_revision = self._preservation_get_config(vehiculo)
        if not time_revision:
            return

        try:
            sesion_data = BDsystem.get_sesion_by_vehiculo(vehiculo)
            gain_inv_usd = sesion_data.get("gainInversion", 100 if vehiculo == "Stock" else 20) if sesion_data else (100 if vehiculo == "Stock" else 20)
        except Exception as _e:
            self._preservation_logger.warning(f"Preservation({vehiculo}): no se pudo obtener gainInversion → usando default | {_e}")
            gain_inv_usd = 100 if vehiculo == "Stock" else 20

        roi_minimo = pconfig.get("roi_minimo", 0.10)
        proteccion_base = pconfig.get("proteccion_base", 0.50)
        correccion_pct = pconfig.get("correccion_pct", 0.08)
        atr_mult = pconfig.get("atr_mult", 2.0)
        proteccion_qty_pct = pconfig.get("proteccion_qty_pct", 0.33)

        _claude_key = None
        try:
            _ses = BDsystem.get_sesion_by_vehiculo("ClaudeAPIP")
            _claude_key = _ses["userapi"].decode("utf-8") if _ses else None
        except Exception as e:
            self._preservation_logger.error(f"Preservation({vehiculo}): ClaudeAPIP no disponible → {e}")

        positions = self.PlanInversion.select_inversion(tipoin=vehiculo, ticket="all")
        self._preservation_logger.warning(f"Preservation({vehiculo}): {len(positions)} posiciones cargadas")

        for positio in positions:
            symbol = positio.get("ticket")
            costobase = positio.get("costobase", 0)
            position_qty = positio.get("position", 0)
            conid = positio.get("conid")
            account = positio.get("useraccount")

            if costobase <= 0 or position_qty <= 0:
                continue

            mktvalue = positio.get("mktvalue") or 0
            unrealizedpnl = (mktvalue - costobase) if mktvalue else positio.get("unrealizedpnl", 0)

            roi = unrealizedpnl / costobase
            if roi < roi_minimo:
                _state_exit = self.preservation_state.get(symbol, {})
                _order_exit = _state_exit.get("order_id")
                if _order_exit:
                    try:
                        DataHub.preservation_cancel_order(vehiculo, account, _order_exit, symbol)
                        try:
                            self.RepositorioOportunidades.update_order_trader_by_client_id(
                                str(_order_exit), account, "CANCELED"
                            )
                        except Exception as _db_e:
                            self._log_stock.warning(f"[EXIT-DB] {symbol}: no se pudo actualizar status en BD → {_db_e}")
                        self.preservation_state.pop(symbol, None)
                        _snap_exit = {}
                        for _s, _sd in self.preservation_state.items():
                            _lc = _sd.get("last_check")
                            _snap_exit[_s] = {**_sd, "last_check": _lc.isoformat() if isinstance(_lc, datetime) else _lc}
                        for _veh, _lr in self.preservation_last_run.items():
                            _snap_exit[f"_last_run_{_veh}"] = _lr.isoformat() if isinstance(_lr, datetime) else str(_lr)
                        write_json_tmp("preservation_state.json", _snap_exit)
                        try:
                            self.RepositorioOportunidades.insert_symbol_decision_history(
                                symbol=symbol,
                                agente="Preservation",
                                tag="EXIT",
                                mensaje=f"ROI={roi:.1%} < {roi_minimo:.0%} → cancelada",
                                json_contexto={
                                    "roi": round(float(roi), 4),
                                    "roi_minimo": round(float(roi_minimo), 4),
                                    "order_id_cancelada": int(_order_exit) if _order_exit else None
                                },
                                order_trader_id=None
                            )
                        except Exception as _e2:
                            self._log_stock.debug(f"[SYMBOL_HISTORY] {symbol}: error registrando EXIT → {_e2}")
                    except Exception as _e:
                        if "doesn't exist" in str(_e):
                            self._preservation_logger.info(
                                f"[EXIT-ORPHAN] {symbol}: orden {_order_exit} ya no existe en IB (se limpió)"
                            )
                            self.preservation_state.pop(symbol, None)
                        else:
                            self._log_stock.error(f"[EXIT-ERR] {symbol}: no se pudo cancelar {_order_exit} → {_e}")
                continue

            base_limit = unrealizedpnl * proteccion_base

            self._preservation_logger.warning(f"Preservation({vehiculo}/{symbol}): ROI={roi:.1%} ≥ {roi_minimo:.0%} → evaluando")

            state = self.preservation_state.get(symbol, {})

            last = DataHub.preservation_get_price(symbol, positio)
            if not last or last <= 0:
                self._preservation_logger.warning(f"Preservation({vehiculo}/{symbol}): sin precio → SKIP")
                continue

            PRECIO_MINIMO = 50.0
            if last < PRECIO_MINIMO:
                continue

            atr, atr_error = DataHub.preservation_get_atr(symbol, vehiculo)
            if atr is None:
                self._preservation_logger.warning(f"Preservation({vehiculo}/{symbol}): {atr_error} → SKIP")
                continue

            sma_base, sma_error = DataHub.preservation_get_sma(symbol, vehiculo)
            if sma_base is None:
                sma_base = last
                self._log_stock.warning(
                    f"Preservation({vehiculo}/{symbol}): SMA20 no disponible ({sma_error}) → usando last={last:.2f}"
                )

            max_price_prev = state.get("max_price", last)
            max_price = max(max_price_prev, last)

            stop_distance = max(correccion_pct * sma_base, atr_mult * atr)
            stop_calculado = sma_base - stop_distance

            stop_anterior = state.get("stop_actual", 0)
            stop_final = max(stop_anterior, stop_calculado)

            ctx = {}
            claude_result = None
            if _claude_key:
                ctx = self._build_preservation_context(
                    symbol, account, roi, last, sma_base, max_price, stop_calculado, stop_anterior, atr, base_limit
                )
                claude_result = self._claude_preservation_eval(ctx, _claude_key)
                if claude_result:
                    stop_claude = claude_result.get("stop_sugerido", 0)
                    stop_final = max(stop_final, stop_claude)
                    try:
                        self.RepositorioOportunidades.insert_symbol_decision_history(
                            symbol=symbol,
                            agente="Preservation",
                            tag="CLAUDE",
                            mensaje=f"stop_sugerido={stop_claude:.2f} urgencia={claude_result.get('urgencia')}",
                            json_contexto={
                                "stop_sugerido": round(float(stop_claude), 4),
                                "urgencia": claude_result.get("urgencia"),
                                "roi": round(float(roi), 4),
                                "rsi_d": float(ctx.get("rsi_d")) if ctx.get("rsi_d") else None,
                                "razon": claude_result.get("razon")[:100] if claude_result.get("razon") else None
                            },
                            order_trader_id=None
                        )
                    except Exception as _e:
                        self._log_stock.debug(f"[SYMBOL_HISTORY] {symbol}: error registrando CLAUDE → {_e}")

            stop_max = round(last - atr, 2)
            if stop_final > stop_max:
                stop_final = stop_max

            qty = DataHub.preservation_calc_qty(self.account, vehiculo, symbol, last, base_limit, proteccion_qty_pct)
            if qty <= 0:
                continue

            trama = DataHub.preservation_build_trama(vehiculo, account, symbol, conid, stop_final, max_price, qty)

            order_id_prev = state.get("order_id")

            is_live = not self._preservation_dry_run and vehiculo == "Stock"

            if stop_final > stop_anterior or not order_id_prev:
                accion = "NUEVA" if not order_id_prev else "MODIFICADA (cancel+new)"
                msg = (
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | sma20={sma_base:.2f} | max={max_price:.2f} | "
                    f"ATR={atr:.2f} | stop_prev={stop_anterior:.2f} → stop_new={stop_final:.2f} | "
                    f"qty={qty} | base_limit={base_limit:.2f} | trama={trama} | {accion}"
                )
                if not is_live:
                    order_id = order_id_prev
                    self._log_stock.warning(f"[DRY-RUN] {msg}")
                else:
                    if order_id_prev:
                        DataHub.preservation_cancel_order(vehiculo, account, order_id_prev, symbol)
                    response = DataHub.preservation_send_order(vehiculo, trama)
                    order_id = DataHub.preservation_extract_order_id(response)
                    if not order_id and vehiculo == "Stock":
                        time.sleep(3)
                        try:
                            ib_client = DataHub.clients.get("Stock")
                            if ib_client:
                                stops = ib_client.get_preservation_stops()
                                matched = next(
                                    (s for s in stops if s.get("symbol") == symbol and abs((s.get("stop_price") or 0) - stop_final) < 0.02),
                                    None,
                                )
                                if matched:
                                    order_id = matched.get("order_id")
                                    self._log_stock.warning(
                                        f"[RETRY-OK] {symbol}: order_id recuperado de live orders → {order_id}"
                                    )
                                else:
                                    self._log_stock.error(
                                        f"[RETRY-FAIL] {symbol}: order_id sigue None tras reintento — "
                                        "se preserva estado anterior sin actualizar order_trader"
                                    )
                        except Exception as _retry_e:
                            self._log_stock.error(f"[RETRY-ERR] {symbol}: {_retry_e}")
                    self._log_stock.warning(f"[ENVIADA] {msg} | order_id={order_id}")
                    hash_id = self.RepositorioOportunidades.generar_hash_id(
                        account,
                        symbol,
                        vehiculo,
                    )
                    try:
                        _det = {
                            "tipo": "preservation_stop",
                            "decision": {
                                "roi": round(float(roi), 4),
                                "sma_base": round(float(sma_base), 4),
                                "max_price": round(float(max_price), 4),
                                "atr": round(float(atr), 4),
                                "stop_calculado_reglas": round(float(stop_calculado), 4),
                                "consenso_tag": ctx.get("consenso_tag") if claude_result else None,
                                "inst_score": float(ctx["inst_score"]) if claude_result and ctx.get("inst_score") is not None else None,
                                "fh_buy_ratio": float(ctx["fh_buy_ratio"]) if claude_result and ctx.get("fh_buy_ratio") is not None else None,
                                "sentiment_patron": ctx.get("patron") if claude_result else None,
                                "rsi_d": float(ctx["rsi_d"]) if claude_result and ctx.get("rsi_d") is not None else None,
                                "macd_estado": ctx.get("macd_estado") if claude_result else None,
                                "base_limit": round(float(base_limit), 4),
                            },
                            "claude": claude_result,
                            "resultado": {
                                "stop_final": round(float(stop_final), 4),
                                "qty_protegida": int(qty),
                                "ganancia_protegida_usd": round(float(base_limit), 4),
                            },
                        }
                        if order_id and str(order_id) not in ("None", "null", ""):
                            limit_price = float(round(stop_final * 0.99, 2))
                            values = {
                                "account": account,
                                "vehiculo": vehiculo,
                                "conid": int(conid),
                                "orderType": "STP LMT",
                                "price": limit_price,
                                "side": "SELL",
                                "intent": "PRESERV",
                                "tif": "GTC",
                                "quantity": float(qty),
                                "clientOrderId": str(order_id),
                                "stampPlace": datetime.now(),
                                "stampSubmit": datetime.now(),
                                "hash_id_oportunidad": hash_id,
                                "json_detalle": json.dumps(_det),
                            }
                            self.RepositorioOportunidades.insert_order_trader(values=values, symbol=symbol)
                            try:
                                tag_accion = "MODIFICADA" if order_id_prev else "ENVIADA"
                                self.RepositorioOportunidades.append_order_audit_log(
                                    order_id=str(order_id),
                                    tag=tag_accion,
                                    mensaje=f"Preservation({vehiculo}/{symbol}): STP LMT {qty} acc @ {stop_final:.2f}",
                                    data={
                                        "order_id": str(order_id),
                                        "stop_final": round(float(stop_final), 4),
                                        "qty": int(qty),
                                        "stop_anterior": round(float(stop_anterior), 4) if order_id_prev else None,
                                        "stop_calculado": round(float(stop_calculado), 4),
                                        "atr": round(float(atr), 4),
                                        "roi": round(float(roi), 4)
                                    }
                                )
                            except Exception as _e:
                                self._log_stock.debug(f"[ORDER_AUDIT] {symbol}: error registrando {tag_accion} → {_e}")
                            try:
                                tag_accion = "MODIFICADA" if order_id_prev else "ENVIADA"
                                self.RepositorioOportunidades.insert_symbol_decision_history(
                                    symbol=symbol,
                                    agente="Preservation",
                                    tag=tag_accion,
                                    mensaje=f"STP LMT {qty} acc @ {stop_final:.2f}",
                                    json_contexto={
                                        "order_id": int(order_id) if order_id else None,
                                        "stop_final": round(float(stop_final), 4),
                                        "qty": int(qty),
                                        "stop_anterior": round(float(stop_anterior), 4) if order_id_prev else None
                                    },
                                    order_trader_id=None
                                )
                            except Exception as _e:
                                self._log_stock.debug(f"[SYMBOL_HISTORY] {symbol}: error registrando ENVIADA → {_e}")
                        self.RepositorioOportunidades.insert_preservation_order(
                            account,
                            vehiculo,
                            symbol,
                            str(conid),
                            str(order_id),
                            float(stop_final),
                            float(qty),
                            json.dumps(_det),
                        )
                    except Exception as _e:
                        self._preservation_logger.error(f"insert_preservation_order({symbol}): {_e}")
            else:
                order_id = order_id_prev
                msg = (
                    f"Preservation({vehiculo}/{symbol}): "
                    f"ROI={roi:.1%} | last={last:.2f} | sma20={sma_base:.2f} | "
                    f"stop={stop_final:.2f} (sin cambio)"
                )
                self._log_stock.warning(msg)

            self.preservation_state[symbol] = {
                "max_price": float(max_price),
                "stop_actual": float(stop_final),
                "last_check": datetime.now().isoformat(),
                "order_id": order_id,
                "vehiculo": vehiculo,
            }
            _snap = {}
            for _sym, _sd in self.preservation_state.items():
                _lc = _sd.get("last_check")
                _snap[_sym] = {**_sd, "last_check": _lc.isoformat() if isinstance(_lc, datetime) else _lc}
            for _veh, _lr in self.preservation_last_run.items():
                _snap[f"_last_run_{_veh}"] = _lr.isoformat() if isinstance(_lr, datetime) else str(_lr)
            write_json_tmp("preservation_state.json", _snap)

    def register_threads(self):
        """Registra agentes de larga duración como threads independientes."""
        _threads = [
            ("Agente_MarketScreener", self.Agente_MarketScreener, 300),
            ("Agente_PriceSync", self.Agente_PriceSync, 300),
            ("Agente_InstitucionalScore", self.Agente_InstitucionalScore, 300),
            ("Agente_ConsensoCache", self.Agente_ConsensoCache, 300),
            ("Agente_EdgarFunds", self.Agente_EdgarFunds, 300),
            ("Agente_FundFilings", self.Agente_FundFilings, 300),
            ("Agente_13FHoldings", self.Agente_13FHoldings, 300),
            ("Agente_13FScores", self.Agente_13FScores, 300),
            ("Agente_AuditPortfolio", self.Agente_AuditPortfolio, 300),
            ("Agente_DividendStatusScreener", self.Agente_DividendStatusScreener, 300),
            ("Agente_ClasificadorETF", self.Agente_ClasificadorETF, 300),
            ("Agente_ClasificadorCrypto", self.Agente_ClasificadorCrypto, 300),
            ("Agente_ApiCostTracker", self.Agente_ApiCostTracker, 300),
            ("Agente_YouTubeScanner", self.Agente_YouTubeScanner, 300),
            ("Agente_YouTubeBackfill", self.Agente_YouTubeBackfill, 60),
            ("Agente_MonitorBooktrading", self.Agente_MonitorBooktrading, 300),
            ("Agente_BrowserFCI", self.Agente_BrowserFCI, 300),
            ("Agente_NtpCheck", self.Agente_NtpCheck, 300),
            ("Agente_IbFlex", self.Agente_IbFlex, 3600),
            ("Agente_LotesReconcile", self.Agente_LotesReconcile, 3600),
        ]
        for name, target, sleep in _threads:
            DataHub.procesos.append({"thread": {name: 1}})
            DataHub.manager_events.register_thread(name=name, target=target, loop_sleep=sleep)
