# ============================================================
# Script: get_data_growth_gurufocus.py
# Autor: Wilmer Gutierrez
# Fecha: Octubre 2025
# Descripción:
#   Calcula valoraciones DDM y DCF e integra modelo FFO/AFFO
#   para REITs, usando datos de yfinance.
# ============================================================

import yfinance as yf
import numpy as np

class StockValuation:
    def __init__(self, ticker):
        self.ticker = ticker
        self.stock = yf.Ticker(ticker)
        self.info = self.stock.info or {}

    # ============================================================
    # === Detección de REIT ===
    # ============================================================
    def is_reit(self):
        """
        Detección avanzada de REITs basada en texto, métricas y palabras clave.
        """
        info = self.info
        name = info.get("longName", "") or ""
        sector = info.get("sector", "") or ""
        industry = info.get("industry", "") or ""
        summary = info.get("longBusinessSummary", "") or ""
        yield_ratio = info.get("dividendYield", 0)
        payout_ratio = info.get("payoutRatio", 0)

        text = f"{name} {sector} {industry} {summary}".upper()

        keywords_reit = [
            "REIT", "REAL ESTATE", "PROPERTY", "PROPERTIES", "TRUST",
            "INFRASTRUCTURE CAPITAL", "SUSTAINABLE INFRASTRUCTURE",
            "EQUITY REIT", "MORTGAGE REIT", "INVESTMENT TRUST"
        ]

        text_match = any(k in text for k in keywords_reit)
        reit_like = (yield_ratio and yield_ratio > 0.04) or (payout_ratio and payout_ratio > 0.6)
        is_reit = text_match or reit_like

        return is_reit

    # ============================================================
    # === Modelo de Dividendos (DDM)
    # ============================================================
    def ddm_value(self, g=None, r=0.10):
        """
        Modelo de Dividendos Descontados (Gordon)
        """
        dividend = self.info.get("dividendRate", 0)
        price = self.info.get("currentPrice", 0)
        eps_growth = self.info.get("earningsGrowth", None)
        results = []

        # Modo automático (crecimiento estimado)
        if eps_growth and eps_growth > 0:
            g_auto = round(eps_growth * 100, 1)
            g_auto = min(g_auto, 10)  # limitar crecimiento a 10 %
            g_auto /= 100
            if r > g_auto:
                intrinsic = dividend * (1 + g_auto) / (r - g_auto)
                margin = (intrinsic - price) / price * 100
                results.append({
                    "Model": "DDM",
                    "Growth Source": "EPS Growth (auto)",
                    "Growth (g)": round(g_auto * 100, 1),
                    "Discount Rate (r)": round(r * 100, 1),
                    "Intrinsic Value": round(intrinsic, 2),
                    "Current Price": price,
                    "Margin of Safety (%)": round(margin, 2),
                })
            else:
                results.append({"error": "r debe ser mayor que g para un modelo DDM válido."})

        # Modo fijo (g manual)
        if g is None:
            g = 0.04
        if r > g:
            intrinsic = dividend * (1 + g) / (r - g)
            margin = (intrinsic - price) / price * 100
            results.append({
                "Model": "DDM",
                "Growth Source": "Manual (fijo)    ",
                "Growth (g)": round(g * 100, 1),
                "Discount Rate (r)": round(r * 100, 1),
                "Intrinsic Value": round(intrinsic, 2),
                "Current Price": price,
                "Margin of Safety (%)": round(margin, 2),
            })
        return results

    # ============================================================
    # === Estimación FFO (para REITs)
    # ============================================================
    def estimate_ffo(self):
        """
        Estima el FFO (Funds From Operations) de forma robusta.
        - Si el ticker es REIT y el Net Income es negativo, ajusta el signo.
        - Usa varias fuentes: financials, cashflow, info.
        - Retorna valores en USD y por acción.
        """
        is_reit = self.is_reit()
        info = self.info or {}
        shares = info.get("sharesOutstanding", 1)
        net_income = None
        depreciation = 0.0
        gains_on_sale = 0.0
        debug_notes = {}

        # === 1. Net Income ===
        try:
            fin = self.stock.financials
            key_income = next((k for k in fin.index if "Net Income" in k), None)
            if key_income:
                net_income = float(fin.loc[key_income].iloc[0])
                debug_notes["net_income_source"] = "financials"
        except Exception:
            net_income = info.get("netIncomeToCommon") or info.get("netIncome")
            debug_notes["net_income_source"] = "info fallback"

        # === 2. Depreciación / Amortización ===
        try:
            cf = self.stock.cashflow
            dep_keys = [k for k in cf.index if any(
                term in k for term in ["Depreciation", "Amortization", "Depletion", "Non Cash"]
            )]
            depreciation = sum(float(cf.loc[k].iloc[0]) for k in dep_keys)
            debug_notes["depreciation_source"] = ", ".join(dep_keys) if dep_keys else "none found"
        except Exception:
            depreciation = 0.0
            debug_notes["depreciation_source"] = "not found"

        # === 3. Ganancias por venta de activos ===
        try:
            gain_key = next((k for k in fin.index if "Gain" in k or "Sale" in k or "Disposition" in k), None)
            if gain_key:
                gains_on_sale = float(fin.loc[gain_key].iloc[0])
                debug_notes["gain_source"] = gain_key
        except Exception:
            gains_on_sale = 0.0
            debug_notes["gain_source"] = "none"

        # === 4. Calcular FFO base ===
        if net_income is None:
            return {"error": "No Net Income data available", "method": "none"}

        ffo = net_income + depreciation - gains_on_sale

        # === 5. Corrección especial para REITs (regla relajada) ===
        if is_reit:
            if net_income < 0 and depreciation > 0.3 * abs(net_income):
                ffo = abs(net_income) + depreciation - gains_on_sale
                debug_notes["reit_adjustment"] = "applied (relaxed rule)"
            else:
                debug_notes["reit_adjustment"] = "not needed"
        else:
            debug_notes["reit_adjustment"] = "not reit"

        # === 6. Calcular FFO por acción ===
        try:
            ffo_per_share = ffo / shares
        except Exception:
            ffo_per_share = None

        return {
            "ffo": ffo,
            "ffo_per_share": ffo_per_share,
            "method": "enhanced_net_plus_dep_minus_gains",
            "notes": {
                **debug_notes,
                "net_income": net_income,
                "depreciation": depreciation,
                "gains_on_sale": gains_on_sale,
                "shares_outstanding": shares,
            },
        }

    # ============================================================
    # === Valoración basada en FFO ===
    # ============================================================
    def valuation_pffo(self, ffo_per_share, pffo_multiple=12.0):
        """
        Valoración por múltiplo P/FFO.
        """
        if not ffo_per_share:
            return {"error": "ffo_per_share no disponible"}
        value = ffo_per_share * pffo_multiple
        return {"value_per_share": value, "pffo": pffo_multiple}

    def valuation_ffo_gordon(self, ffo_per_share, r=0.09, g=0.03):
        """
        Modelo Gordon aplicado a FFO.
        """
        if not ffo_per_share:
            return {"error": "ffo_per_share no disponible"}
        if r <= g:
            return {"error": "r debe ser mayor que g"}
        ffo1 = ffo_per_share * (1 + g)
        value = ffo1 / (r - g)
        return {"value_per_share": value, "ffo1": ffo1, "r": r, "g": g}

# ============================================================
# Ejemplo de uso
# ============================================================
if __name__ == "__main__":
    ticker = "CCI"
    model = StockValuation(ticker)

    print("=" * 50)
    print(f"Valoración ${ticker}: {model.info.get('longName', ticker)} - Precio: {model.info.get('currentPrice', 'N/A')}\n")

    # === Modelo DDM ===
    ddm_results = model.ddm_value(g=0.04, r=0.10)
    for r in ddm_results:
        print(r)

    # === Detectar REIT y calcular FFO ===
    if model.is_reit():
        print(f"\n{ticker} es un REIT según los criterios analizados.")
        ffo_data = model.estimate_ffo()
        print(ffo_data)

        if ffo_data.get("ffo_per_share"):
            ffo_per_share = ffo_data["ffo_per_share"]
            print(model.valuation_pffo(ffo_per_share))
            print(model.valuation_ffo_gordon(ffo_per_share))
    else:
        print(f"\n{ticker} no es REIT. Usar DCF o DDM.")
