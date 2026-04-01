"""
Class_ServiciosCrypto.py - Servicios auxiliares Crypto (Simple Earn ↔ Spot)

Clases:
- ServiciosCrypto: Operaciones earn/spot (subscribe, redeem, balances combinados)
"""
import logging


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
        spot_data  = self._spot.account_spot() or {}
        earn_data  = self._spot.Myget_flexible_product_position() or {}
        prices_raw = self._spot.ticker_price() or []

        price_map = {p["symbol"]: float(p["price"]) for p in prices_raw if isinstance(p, dict)}

        def _price_usdt(asset):
            if asset == "USDT":
                return 1.0
            return price_map.get(f"{asset}USDT", 0.0)

        spot_balances = {
            b["asset"]: float(b.get("free", 0))
            for b in spot_data.get("balances", [])
            if float(b.get("free", 0)) > 0
        }

        earn_positions = {}
        for row in earn_data.get("rows", []):
            amt = float(row.get("totalAmount", 0))
            if amt > 0:
                earn_positions[row["asset"]] = {
                    "amount":    amt,
                    "apr":       float(row.get("latestAnnualPercentageRate", 0)),
                    "productId": row.get("productId", ""),
                    "canRedeem": bool(row.get("canRedeem", False)),
                }

        all_assets = sorted(set(earn_positions))
        result = []
        for asset in all_assets:
            earn_info  = earn_positions.get(asset, {})
            spot_free  = spot_balances.get(asset, 0.0)
            total      = spot_free + earn_info.get("amount", 0.0)
            price      = _price_usdt(asset)
            earn_amt = earn_info.get("amount", 0.0)
            result.append({
                "asset":           asset,
                "spot_free":       spot_free,
                "earn_amount":     earn_amt,
                "earn_apr":        earn_info.get("apr", 0.0),
                "earn_product_id": earn_info.get("productId", ""),
                "can_redeem":      earn_info.get("canRedeem", False),
                "total":           total,
                "usdt_value":      total * price,       # spot + earn en USDT (para tabla UI)
                "earn_usdt":       earn_amt * price,    # solo earn en USDT (para LTV)
            })
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

            analisis.append({
                "loanCoin": loan_coin,
                "collateralCoin": collateral_coin,
                "ltv_actual": ltv_actual,
                "loan_usd": loan_usd,
                "collateral_amount": collateral_amount,
                "collateral_usd": collateral_usd,
                "estado": estado,
                "ajuste_direction": ajuste_direction,
                "ajuste_coin": round(ajuste_coin, 6),
            })
        return analisis
