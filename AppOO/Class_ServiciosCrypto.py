"""
Class_ServiciosCrypto.py - Servicios auxiliares Crypto (Simple Earn ↔ Spot)

Clases:
- ServiciosCrypto: Operaciones earn/spot (subscribe, redeem, balances combinados)
"""

import json
import logging
import time


class ServiciosCrypto:
    """Servicios auxiliares Crypto: Simple Earn ↔ Spot."""

    def __init__(self):
        from Class_ApiBinnace import BinanceClient  # import diferido — evita ciclo con Modulos_python chain

        self._spot = BinanceClient(vehiculo="Crypto").spot
        self._logger = logging.getLogger("BinanceClient")

    def earn_spot_balances(self):
        """Combina saldos Spot libres + posiciones Earn flexible por moneda.

        Retorna lista de dicts:
            asset, spot_free, earn_amount, earn_apr, earn_product_id, can_redeem, total, usdt_value
        Solo incluye monedas con saldo > 0 en al menos una ubicación.
        """
        spot_data = self._spot.account_spot() or {}
        earn_data = self._spot.Myget_flexible_product_position() or {}
        prices_raw = self._spot.ticker_price() or []

        price_map = {p["symbol"]: float(p["price"]) for p in prices_raw if isinstance(p, dict)}

        def _price_usdt(asset):
            if asset == "USDT":
                return 1.0
            return price_map.get(f"{asset}USDT", 0.0)

        spot_balances = {
            b["asset"]: float(b.get("free", 0)) for b in spot_data.get("balances", []) if float(b.get("free", 0)) > 0
        }

        earn_positions = {}
        for row in earn_data.get("rows", []):
            amt = float(row.get("totalAmount", 0))
            if amt > 0:
                earn_positions[row["asset"]] = {
                    "amount": amt,
                    "apr": float(row.get("latestAnnualPercentageRate", 0)),
                    "productId": row.get("productId", ""),
                    "canRedeem": bool(row.get("canRedeem", False)),
                }

        all_assets = sorted(set(earn_positions))
        result = []
        for asset in all_assets:
            earn_info = earn_positions.get(asset, {})
            spot_free = spot_balances.get(asset, 0.0)
            total = spot_free + earn_info.get("amount", 0.0)
            price = _price_usdt(asset)
            earn_amt = earn_info.get("amount", 0.0)
            result.append(
                {
                    "asset": asset,
                    "spot_free": spot_free,
                    "earn_amount": earn_amt,
                    "earn_apr": earn_info.get("apr", 0.0),
                    "earn_product_id": earn_info.get("productId", ""),
                    "can_redeem": earn_info.get("canRedeem", False),
                    "total": total,
                    "usdt_value": total * price,  # spot + earn en USDT (para tabla UI)
                    "earn_usdt": earn_amt * price,  # solo earn en USDT (para LTV)
                }
            )
        return result

    def earn_subscribe(self, productId: str, amount: float):
        """Mueve fondos de Spot → Earn (suscribir). Retorna respuesta API o None."""
        try:
            return self._spot.Mysubscribe_flexible_product(productId=productId, amount=amount)
        except Exception as e:
            self._logger.error(f"earn_subscribe({productId}, {amount}): {e}")
            return None

    def earn_redeem(self, productId: str, amount: float):
        """Mueve fondos de Earn → Spot (canjear). Retorna respuesta API o None."""
        try:
            return self._spot.get_redeem_flexible_product(productId=productId, amount=amount)
        except Exception as e:
            self._logger.error(f"earn_redeem({productId}, {amount}): {e}")
            return None

    def repay_venta(self, importe, symbol=""):
        """Paga deuda flexible con un porcentaje del importe de una venta Crypto.

        Solo paga si hay deuda viva y nunca mas que ella: el monto se acota por la deuda total y
        por el USDT libre en spot. El reparto entre prestamos lo hace loan_repay_distribuir(), el
        mismo que ejecuta el boton Pagar de Analisis Crypto. Se configura en
        sesion.parameters(Crypto).loan.repay_pct_venta; 0 lo desactiva.
        Retorna dict con lo pagado o None si no correspondia.
        """
        lconfig, _ = self._loan_config()
        pct = float(lconfig.get("repay_pct_venta", 0) or 0)
        minimo = float(lconfig.get("delta_minimo", 1.0))
        importe = float(importe or 0)
        if pct <= 0 or importe <= 0:
            return None

        prestamos = self.loan_ongoing()
        if not prestamos:
            self._logger.warning(f"repay_venta({symbol}): venta de ${importe:,.2f} sin deuda viva - sin repago")
            return None

        deuda_total = sum(p["deuda"] for p in prestamos)
        usdt_libre = self._usdt_free()
        monto = min(importe * pct, deuda_total, usdt_libre)
        if monto < minimo:
            self._logger.warning(
                f"repay_venta({symbol}): {pct:.0%} de ${importe:,.2f} = ${importe * pct:,.2f} bajo el minimo "
                f"${minimo:,.2f} | deuda ${deuda_total:,.2f} | USDT libre ${usdt_libre:,.2f} - sin repago"
            )
            return None

        resultado = self.loan_repay_distribuir(monto, prestamos=prestamos)
        if not resultado or resultado["pagado"] <= 0:
            return None

        self._logger.warning(
            f"repay_venta({symbol}): pagados ${resultado['pagado']:,.2f} ({pct:.0%} de ${importe:,.2f}) | "
            f"deuda previa ${deuda_total:,.2f} | {resultado['detalle']}"
        )
        return {"importe": importe, "pct": pct, "deuda_previa": deuda_total, **resultado}

    def loan_ongoing(self):
        """Prestamos flexibles vivos, normalizados igual que _get_loan_data() de Analisis Crypto."""
        try:
            resultado = self._spot.get_flexible_loan_ongoing_orders()
            rows = resultado.get("rows", []) if resultado else []
        except Exception as e:
            self._logger.error(f"loan_ongoing(): {e}")
            return []

        prestamos = []
        for r in rows:
            ltv = float(r.get("currentLTV", 0))
            if ltv == 0:
                continue
            loan_usd = float(r.get("loanValueInUSD") or r.get("totalDebt", 0))
            col_usd = float(r.get("collateralValueInUSD", 0)) or (loan_usd / ltv)
            prestamos.append(
                {
                    "activo": r.get("collateralCoin", ""),
                    "loan_coin": r.get("loanCoin", "USDT"),
                    "col_usd": col_usd,
                    "ltv": ltv,
                    "deuda": loan_usd,
                    "col_amount": float(r.get("collateralAmount", 0)),
                }
            )
        return prestamos

    def loan_repay_distribuir(self, monto, prestamos=None):
        """Reparte un pago entre los prestamos vivos nivelando deudas y lo ejecuta en Binance.

        Cada prestamo recibe en proporcion a cuanto excede la deuda media que quedaria tras el
        pago: paga mas donde mas deuda hay. Es el criterio del boton Pagar de Analisis Crypto, que
        ahora entra por aca. Retorna dict con pagado, ok, errores y detalle.
        """
        prestamos = self.loan_ongoing() if prestamos is None else prestamos
        monto = float(monto or 0)
        if monto <= 0 or not prestamos:
            return {"pagado": 0.0, "ok": 0, "errores": [], "detalle": []}

        total_deuda = sum(p["deuda"] for p in prestamos)
        objetivo = (total_deuda - monto) / len(prestamos)
        exceso = [max(0.0, p["deuda"] - objetivo) for p in prestamos]
        cuotas = self._reparte_cuotas(monto, prestamos, exceso)

        errores, ok, pagado, detalle = [], 0, 0.0, []
        for p, cuota in zip(prestamos, cuotas):
            if cuota <= 0:
                continue
            time.sleep(2)
            resp = self._spot.get_flexible_loan_repay(
                loanCoin=p["loan_coin"], collateralCoin=p["activo"], amount=cuota
            )
            self._logger.warning(f"loan_repay [{p['activo']}] ${cuota:.2f} → {resp}")
            if not resp:
                errores.append(f"{p['activo']}:sin respuesta")
            elif "code" in resp and int(resp["code"]) < 0:
                errores.append(f"{p['activo']}:{resp.get('msg', resp['code'])}")
            else:
                ok += 1
                pagado += cuota
                detalle.append({"activo": p["activo"], "monto": cuota, "ltv_previo": round(p["ltv"], 4)})
        return {"pagado": pagado, "ok": ok, "errores": errores, "detalle": detalle}

    def ltv_check_and_adjust(self, lconfig):
        """Analiza el LTV de cada préstamo flexible activo y calcula el ajuste necesario.
        DRY RUN — solo calcula y retorna, no ejecuta ninguna llamada de ajuste.

        Retorna lista de dicts con: loanCoin, collateralCoin, ltv_actual,
        loan_usd, collateral_usd, estado, ajuste_direction, ajuste_coin.
        """
        target = float(lconfig.get("target", 0.50))
        tolerance = float(lconfig.get("tolerance", 0.05))
        critical = float(lconfig.get("critical", 0.65))
        rebalance_step = float(lconfig.get("rebalance_step", 0.25))
        ltv_lower = target * (1 - tolerance)
        ltv_upper = target * (1 + tolerance)

        resultado = self._spot.get_flexible_loan_ongoing_orders()
        if not resultado:
            return []
        rows = resultado.get("rows", [])
        if not rows:
            return []

        analisis = []
        for row in rows:
            if float(row.get("currentLTV", 0)) == 0:
                continue
            loan_coin = row.get("loanCoin", "")
            collateral_coin = row.get("collateralCoin", "")
            ltv_actual = float(row.get("currentLTV", 0))
            collateral_amount = float(row.get("collateralAmount", 0))
            loan_usd = float(row.get("loanValueInUSD") or row.get("totalDebt", 0))
            collateral_usd = float(row.get("collateralValueInUSD", 0))
            if collateral_usd == 0 and ltv_actual > 0:
                collateral_usd = loan_usd / ltv_actual

            if ltv_actual >= critical:
                estado = "CRITICO"
            elif ltv_actual > ltv_upper:
                estado = "ALTO"
            elif ltv_actual < ltv_lower:
                estado = "BAJO"
            else:
                estado = "NORMAL"

            ajuste_direction = None
            ajuste_coin = 0.0
            if estado in ("ALTO", "CRITICO"):
                colateral_obj_usd = loan_usd / target if target > 0 else 0
                delta_usd = (colateral_obj_usd - collateral_usd) * rebalance_step
                precio_col = collateral_usd / collateral_amount if collateral_amount > 0 else 0
                ajuste_coin = delta_usd / precio_col if precio_col > 0 else 0
                ajuste_direction = "ADDITIONAL"
            elif estado == "BAJO":
                colateral_obj_usd = loan_usd / target if target > 0 else 0
                delta_usd = (collateral_usd - colateral_obj_usd) * rebalance_step
                precio_col = collateral_usd / collateral_amount if collateral_amount > 0 else 0
                ajuste_coin = delta_usd / precio_col if precio_col > 0 else 0
                ajuste_direction = "REDUCED"

            analisis.append(
                {
                    "loanCoin": loan_coin,
                    "collateralCoin": collateral_coin,
                    "ltv_actual": ltv_actual,
                    "loan_usd": loan_usd,
                    "collateral_amount": collateral_amount,
                    "collateral_usd": collateral_usd,
                    "estado": estado,
                    "ajuste_direction": ajuste_direction,
                    "ajuste_coin": round(ajuste_coin, 6),
                }
            )
        return analisis

    def _reparte_cuotas(self, monto, prestamos, exceso):
        """Reparte monto entre prestamos proporcional al exceso, descartando cuotas bajo el minimo.

        Binance rechaza los repagos dust, asi que una cuota bajo loan.delta_minimo es una llamada
        perdida y una linea de error en el log. Se descarta y su parte se redistribuye entre los
        que quedan; si todas caen bajo el minimo sobrevive la de mayor exceso, que se lleva el
        monto entero topeado por su deuda.
        Devuelve una lista de cuotas alineada posicion a posicion con prestamos.
        """
        minimo = float(self._loan_config()[0].get("delta_minimo", 1.0))
        elegibles = [i for i, e in enumerate(exceso) if e > 0]
        cuotas = [0.0] * len(prestamos)

        while elegibles:
            total_exceso = sum(exceso[i] for i in elegibles) or 1.0
            calculo = {i: round(monto * (exceso[i] / total_exceso), 2) for i in elegibles}
            chicas = [i for i in elegibles if calculo[i] < minimo]
            if not chicas or len(elegibles) == 1:
                for i in elegibles:
                    if calculo[i] >= minimo:
                        cuotas[i] = round(min(calculo[i], prestamos[i]["deuda"]), 2)
                break
            # si todas son chicas hay que quedarse con una, si no el pago entero se pierde
            elegibles = [i for i in elegibles if i not in chicas] or [max(elegibles, key=lambda i: exceso[i])]

        return cuotas

    def _loan_config(self):
        """Lee los bloques loan y ltv de sesion.parameters(Crypto). Devuelve (loan, ltv)."""
        from Modulos_Mysql import BDsystem  # import diferido — evita ciclo con Modulos_python chain

        try:
            sesion = BDsystem.get_sesion_by_vehiculo("Crypto")
            raw = sesion.get("parameters") if sesion else None
            params = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw) if raw else {}
        except Exception as e:
            self._logger.error(f"_loan_config(): {e}")
            return {}, {}
        return params.get("loan", {}), params.get("ltv", {})

    def _usdt_free(self):
        """USDT libre en spot, que es con lo que se paga la deuda."""
        try:
            data = self._spot.account_spot() or {}
            for b in data.get("balances", []):
                if b.get("asset") == "USDT":
                    return float(b.get("free", 0))
        except Exception as e:
            self._logger.error(f"_usdt_free(): {e}")
        return 0.0
