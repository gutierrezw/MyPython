"""
Class_AgentManager.py - Administrador de agentes síncronos
Dominios: Stock | Crypto | IA | Infra
"""

from Modulos_python import logging, json, datetime, yf, requests, textwrap, Path
from Modulos_Utilitarios import wait_rate, read_json_tmp, write_json_tmp, track_claude_usage
from Modulos_Mysql import (
    RepositorioOportunidadesBuySell,
    BDsystem,
    PlanInversion,
    MarketScreen,
    EstrategiaInversion,
    IPerformance,
)
from Class_Finance import scan_extractos
from Class_Screener import sync_market, sync_prices, audit_portfolio, refresh_consenso_tags
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

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_params(self, vehiculo: str):
        if vehiculo not in self._params_cache:
            sesion = self.PlanInversion.get_sesion_by_vehiculo(vehiculo)
            params_raw = sesion.get("parameters")
            if not params_raw:
                self._params_cache[vehiculo] = None
            else:
                self._params_cache[vehiculo] = json.loads(
                    params_raw.decode("utf-8") if isinstance(params_raw, bytes) else params_raw
                )
        return self._params_cache.get(vehiculo)

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
            self._log_stock.warning(
                f"InstitucionalScore: procesados={result['symbols_processed']} actualizados={result['updated']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_InstitucionalScore(): {e}")

    @wait_rate(300, persist=True)
    def Agente_ConsensoCache(self):
        try:
            result = refresh_consenso_tags(account=self.account)
            self._log_stock.warning(f"ConsensoCache: actualizados={result['actualizados']}/{result['total']}")
        except Exception as e:
            self._log_stock.error(f"Agente_ConsensoCache(): {e}")

    @wait_rate(2592000, persist=True)
    def Agente_EdgarFunds(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_EdgarFunds._overdue:
            return
        try:
            result = sync_edgar_funds()
            self._log_stock.warning(f"EdgarFunds: total={result['total']} insertados={result['inserted']}")
        except Exception as e:
            self._log_stock.error(f"Agente_EdgarFunds(): {e}")

    @wait_rate(604800, persist=True)
    def Agente_FundFilings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_FundFilings._overdue:
            return
        try:
            task_name = "Agente_FundFilings()"

            def _progress(i, total):
                DataHub.update_self_procesos(proces="thread", tarea=task_name, itera=i)

            result = sync_fund_filings(account=self.account, progress_cb=_progress)
            self._log_stock.warning(
                f"FundFilings: fondos={result['funds']} descargados={result['downloaded']} "
                f"skipped={result['skipped']} fallidos={result['failed']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_FundFilings(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_13FScores(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FScores._overdue:
            return
        try:
            result = sync_13f_scores(account=self.account)
            self._log_stock.warning(
                f"13FScores: símbolos={result['symbols']} actualizados={result['updated']} skipped={result['skipped']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_13FScores(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_13FHoldings(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_13FHoldings._overdue:
            return
        try:
            result = sync_13f_holdings(account=self.account)
            self._log_stock.warning(
                f"13FHoldings: archivos={result['xml_files']} "
                f"holdings={result['inserted_holdings']} opciones={result['inserted_options']}"
            )
            deleted = MarketScreen().cleanup_fund_holdings_nulls()
            self._log_stock.warning(f"13FHoldings cleanup: eliminadas={deleted} filas NULL")
        except Exception as e:
            self._log_stock.error(f"Agente_13FHoldings(): {e}")

    @wait_rate(2592000, persist=True)
    def Agente_AuditPortfolio(self):
        if not (0 <= datetime.now().hour < 6) and not type(self).Agente_AuditPortfolio._overdue:
            return
        try:
            result = audit_portfolio(account=self.account)
            self._log_stock.warning(
                f"AuditPortfolio: total={result['total']} delistados={result['delistados']} "
                f"nombres_upd={result['nombres_upd']} cusips_upd={result['cusips_upd']} "
                f"etfs_upd={result['etfs_upd']} sin_precio={result['sin_precio']} errores={result['errores']}"
            )
        except Exception as e:
            self._log_stock.error(f"Agente_AuditPortfolio(): {e}")

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
            self._log_stock.warning(f"StockBeta: β={beta_port:.3f}  ({len(positions)} posiciones)")
        except Exception as e:
            self._log_stock.error(f"Agente_StockBeta(): {e}")

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
            self._log_stock.warning(
                f"PerformaValidator: cache size={st['size']}/{st['maxsize']} "
                f"hits={st['hits']} misses={st['misses']} bypass={st['bypass']}"
            )
            result = self.Performa.validate_performa(account=self.account, vehiculo=self.vehiculo)
            if result["purgados"]:
                for a in result["anomalias"]:
                    sym, fecha, ratio = a["symbol"], a["fecha"], a["ratio"]
                    if a.get("quarantined"):
                        self._log_stock.critical(
                            f"PerformaValidator: {sym} CUARENTENA — purgado 3+ veces en 6h, ratio={ratio:.2f}x"
                        )
                    else:
                        self._log_stock.warning(
                            f"PerformaValidator: {sym} {fecha} ratio={ratio:.2f}x purgado — bypass cache"
                        )
                        CacheHut.add_bypass(sym)
        except Exception as e:
            self._log_stock.error(f"Agente_PerformaValidator(): {e}")

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

    @wait_rate(3600, persist=True)
    def Agente_Sentimiento(self):
        if datetime.now().weekday() >= 5:
            return
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIS")
            api_key = sesion["userapi"].decode("utf-8") if sesion else ""
            result = scan_sentimiento(account=self.account, api_key=api_key)
            self._log_ia.warning(
                f"Sentimiento: símbolos={result['symbols']} con_noticias={result['with_news']} "
                f"clasificados={result['classified']}"
            )
        except Exception as e:
            self._log_ia.error(f"Agente_Sentimiento(): {e}")

    @wait_rate(86400, persist=True)
    def Agente_InterpreteSentimiento(self):
        if datetime.now().weekday() >= 5:
            return
        try:
            sesion = BDsystem.get_sesion_by_vehiculo("ClaudeAPIS")
            api_key = sesion["userapi"].decode("utf-8") if sesion else ""
            result = interpretar_sentimiento(account=self.account, api_key=api_key)
            self._log_ia.warning(f"InterpreteSentimiento: {len(result)} símbolos interpretados")
        except Exception as e:
            self._log_ia.error(f"Agente_InterpreteSentimiento(): {e}")

    @wait_rate(604800, persist=True)
    def Agente_ClasificadorETF(self):
        try:
            estrategia_svc = EstrategiaInversion()
            opciones = estrategia_svc.select(accion="vehiculo", ivehiculo="Balance")
            etfs = estrategia_svc.get_etfs_pendientes(self.account)
            clasificados = sin_info = 0
            for etf in etfs:
                symbol = etf["symbol"]
                yf_info = DataHub.info.get(symbol, {}).get("activos", {})
                if not yf_info:
                    sin_info += 1
                    continue
                codigo = self._clasificar_etf_claude(yf_info, opciones)
                if codigo:
                    estrategia_svc.update_estrategia_etf(symbol, self.account, codigo)
                    clasificados += 1
            self._log_ia.warning(
                f"ClasificadorETF: pendientes={len(etfs)} clasificados={clasificados} sin_info={sin_info}"
            )
        except Exception as e:
            self._log_ia.error(f"Agente_ClasificadorETF(): {e}")

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
                DataHub.system_alerts.append(
                    "⚠️ Monitor Booktrading: {} residuales\n{}".format(
                        len(pendientes),
                        "\n".join(
                            "  • {} [{}] stock={:.4f} mktval=${:.2f} — {}".format(
                                a["symbol"], a["account"], a["book_stock"], a["mktvalue"], a["motivo"]
                            )
                            for a in pendientes
                        ),
                    )
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
            f"⚠️ BrowserFCI BLOQUEADO\n"
            f"Razón: {data.get('reason', '?')}\n"
            f"Desde: {data.get('timestamp', '?')}\n"
            f"FCI desactualizado — ejecutá BrowserFCI().reset_blocked() para liberar."
        )
        if alerta not in DataHub.system_alerts:
            DataHub.system_alerts.append(alerta)

    @wait_rate(3600, persist=True, desc="BrowserFCI descarga FCI BBVA+Santander (L-V 8:30)", nivel=2)
    def Agente_BrowserFCI(self):
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
        if now.weekday() >= 5:  # sábado=5, domingo=6
            return
        if not (now.hour == 8 and now.minute >= 30) and not (now.hour == 9):
            return
        try:
            from Class_FondosInversion import sync_fci_browser  # import diferido — evita ciclo

            result = sync_fci_browser()
            self._log_infra.warning(f"Agente_BrowserFCI: procesados={result}")
        except Exception as e:
            self._log_infra.error(f"Agente_BrowserFCI(): {e}")

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
            ("Agente_ClasificadorETF", self.Agente_ClasificadorETF, 300),
            ("Agente_Sentimiento", self.Agente_Sentimiento, 300),
            ("Agente_InterpreteSentimiento", self.Agente_InterpreteSentimiento, 300),
            ("Agente_ApiCostTracker", self.Agente_ApiCostTracker, 300),
            ("Agente_YouTubeScanner", self.Agente_YouTubeScanner, 300),
            ("Agente_YouTubeBackfill", self.Agente_YouTubeBackfill, 60),
            ("Agente_MonitorBooktrading", self.Agente_MonitorBooktrading, 300),
            ("Agente_BrowserFCI", self.Agente_BrowserFCI, 300),
        ]
        for name, target, sleep in _threads:
            DataHub.procesos.append({"thread": {name: 1}})
            DataHub.manager_events.register_thread(name=name, target=target, loop_sleep=sleep)
