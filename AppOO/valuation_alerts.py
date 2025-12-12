# ================================================
# valuation_alerts.py
# Sistema de alertas para detectar banderas rojas
# ================================================


def generate_alerts(
    ttm: dict, vals: dict, reit_metrics: dict, dividend_analysis: dict = None
):
    """
    Genera alertas automáticas basadas en métricas clave.

    Returns:
        dict con 'critical', 'warnings', 'info'
    """
    alerts = {
        "critical": [],  # Banderas rojas graves
        "warnings": [],  # Advertencias moderadas
        "info": [],  # Información relevante
    }

    is_reit = reit_metrics.get("is_reit", False)

    # Extraer variables comunes al inicio
    dividends = vals.get("Dividends_Total")
    net_income = vals.get("NetIncome_Total")
    ocf = vals.get("OperatingCF_Total")
    revenues = vals.get("Revenues_Total")

    # ✅ NUEVO: Detectar empresas de capital intensivo (petroleras, mineras, utilities)
    # Estas empresas tienen OCF >> Net Income por alto D&A
    is_capital_intensive = False
    if ocf and net_income and revenues:
        # Si OCF es significativamente mayor que Net Income (>1.5x), es capital intensivo
        if ocf > net_income * 1.5 and net_income > 0:
            is_capital_intensive = True

    # ============================================================
    # ALERTAS CRÍTICAS
    # ============================================================

    # 1. FFO negativo para REITs
    if is_reit:
        ffo = reit_metrics.get("ffo_total")

        # Solo alertar si FFO negativo Y OCF también es bajo/negativo
        if ffo is not None and ffo < 0:
            # Si OCF positivo y cubre dividendos, degradar a warning
            if ocf and ocf > 0 and dividends and ocf > dividends:
                alerts["warnings"].append(
                    {
                        "type": "FFO_NEGATIVE_OCF_POSITIVE",
                        "message": f"⚠️ FFO negativo (${ffo/1e9:.1f}B) pero OCF positivo (${ocf/1e9:.1f}B)",
                        "severity": "WARNING",
                        "ffo": ffo,
                        "ocf": ocf,
                        "recommendation": "Revisar cargos no-cash (impairments, write-downs). OCF positivo es buena señal.",
                    }
                )
            else:
                # FFO negativo y OCF bajo = problema real
                alerts["critical"].append(
                    {
                        "type": "FFO_NEGATIVE",
                        "message": "🚨 FFO NEGATIVO - El REIT no genera suficiente cash operativo",
                        "severity": "CRITICAL",
                        "value": ffo,
                        "recommendation": "Investigar causas: ¿Cargos one-time o problema estructural?",
                    }
                )

    # 2. Net Income negativo pero paga dividendos
    if net_income and dividends and net_income < 0 and dividends > 0:
        # Si es REIT con OCF positivo que cubre dividendos, degradar a warning
        if is_reit and ocf and ocf > 0 and ocf > dividends:
            alerts["warnings"].append(
                {
                    "type": "NEGATIVE_EARNINGS_OCF_POSITIVE",
                    "message": f"⚠️ Pérdidas contables (${net_income/1e9:.1f}B) pero OCF cubre dividendos",
                    "severity": "WARNING",
                    "net_income": net_income,
                    "ocf": ocf,
                    "dividends": dividends,
                    "recommendation": "Para REITs, pérdidas contables pueden ser cargos no-cash. OCF positivo es buena señal.",
                }
            )
        else:
            # No REIT o OCF no cubre dividendos = problema real
            alerts["critical"].append(
                {
                    "type": "NEGATIVE_EARNINGS_PAYING_DIVIDENDS",
                    "message": "🚨 Pérdidas contables pero paga dividendos",
                    "severity": "CRITICAL",
                    "net_income": net_income,
                    "dividends": dividends,
                    "recommendation": "Verificar sostenibilidad del dividendo",
                }
            )

    # 3. Payout ratio > 100% (para empresas normales)
    if not is_reit:
        # ✅ MEJORA: Para empresas de capital intensivo, usar OCF en lugar de Net Income
        if is_capital_intensive and dividends and ocf and ocf > 0:
            # Usar Operating Cash Flow para payout
            payout_ocf = (dividends / ocf) * 100
            if payout_ocf > 90:  # 90% de OCF es alto pero aceptable para petroleras
                alerts["critical"].append(
                    {
                        "type": "UNSUSTAINABLE_PAYOUT",
                        "message": f"🚨 Payout ratio {payout_ocf:.1f}% del OCF - Dividendo insostenible",
                        "severity": "CRITICAL",
                        "value": payout_ocf,
                        "recommendation": "Riesgo alto de recorte de dividendo",
                    }
                )
            elif payout_ocf > 70:  # Advertencia entre 70-90%
                alerts["warnings"].append(
                    {
                        "type": "HIGH_PAYOUT_OCF",
                        "message": f"⚠️ Payout alto: {payout_ocf:.1f}% del Operating Cash Flow",
                        "severity": "WARNING",
                        "value": payout_ocf,
                        "recommendation": "Monitorear sostenibilidad del dividendo",
                    }
                )
        else:
            # Empresas normales: usar Net Income
            payout = vals.get("Payout_Ratio_Percent")
            if payout and payout > 100:
                alerts["critical"].append(
                    {
                        "type": "UNSUSTAINABLE_PAYOUT",
                        "message": f"🚨 Payout ratio {payout:.1f}% - Dividendo NO sostenible",
                        "severity": "CRITICAL",
                        "value": payout,
                        "recommendation": "Riesgo alto de recorte de dividendo",
                    }
                )

    # 4. Dividendos decrecientes
    if dividend_analysis:
        cagr = dividend_analysis.get("cagr", 0)
        if cagr < 0:
            alerts["critical"].append(
                {
                    "type": "DIVIDEND_DECLINE",
                    "message": f"🚨 Dividendos DECRECIENDO {abs(cagr)*100:.2f}%/año",
                    "severity": "CRITICAL",
                    "cagr": cagr,
                    "recommendation": "Empresa en deterioro - evitar para income investing",
                }
            )

    # ============================================================
    # ADVERTENCIAS
    # ============================================================

    # 1. Payout ratio muy alto para REITs
    # Usar FFO si está disponible, sino OCF
    if is_reit:
        ffo = reit_metrics.get("ffo_total")
        ocf = vals.get("OperatingCF_Total")

        # Preferir FFO sobre OCF para REITs
        if ffo and dividends and ffo > 0:
            payout_ffo = (dividends / ffo) * 100
            if payout_ffo > 95:
                alerts["warnings"].append(
                    {
                        "type": "HIGH_PAYOUT_FFO",
                        "message": f"⚠️ Payout {payout_ffo:.1f}% del FFO - margen muy ajustado",
                        "severity": "WARNING",
                        "value": payout_ffo,
                        "recommendation": "Poco margen para crecimiento del dividendo",
                    }
                )
        elif ocf and dividends and ocf > 0:
            payout_ocf = (dividends / ocf) * 100
            # Solo alertar si OCF > $50M (evita REITs de financiamiento con OCF bajo)
            if payout_ocf > 95 and ocf > 50_000_000:
                alerts["warnings"].append(
                    {
                        "type": "HIGH_PAYOUT_OCF",
                        "message": f"⚠️ Payout {payout_ocf:.1f}% del Operating CF - margen muy ajustado",
                        "severity": "WARNING",
                        "value": payout_ocf,
                        "recommendation": "Poco margen para crecimiento del dividendo",
                    }
                )

    # 2. P/E muy alto (>30x para empresas normales)
    if not is_reit:
        pe = vals.get("PE_Ratio")
        if pe and pe > 30:
            alerts["warnings"].append(
                {
                    "type": "HIGH_PE",
                    "message": f"⚠️ P/E {pe:.1f}x muy alto - posible sobrevaloración",
                    "severity": "WARNING",
                    "value": pe,
                    "recommendation": "Comparar con industria y crecimiento esperado",
                }
            )

    # 3. P/FFO muy alto para REITs (>20x)
    if is_reit:
        p_ffo = vals.get("P_FFO")
        if p_ffo and p_ffo > 20:
            alerts["warnings"].append(
                {
                    "type": "HIGH_P_FFO",
                    "message": f"⚠️ P/FFO {p_ffo:.1f}x - caro para un REIT",
                    "severity": "WARNING",
                    "value": p_ffo,
                    "recommendation": "REITs típicamente cotizan a 12-18x FFO",
                }
            )

    # 4. Crecimiento de dividendos estancado (<2%)
    if dividend_analysis:
        cagr = dividend_analysis.get("cagr", 0)
        if 0 <= cagr < 0.02:
            alerts["warnings"].append(
                {
                    "type": "STAGNANT_DIVIDEND_GROWTH",
                    "message": f"⚠️ Dividendos estancados: {cagr*100:.2f}%/año",
                    "severity": "WARNING",
                    "cagr": cagr,
                    "recommendation": "Buscar catalizadores de crecimiento",
                }
            )

    # 5. FCF negativo
    fcf = vals.get("FCF_Total")
    if fcf and fcf < 0:
        alerts["warnings"].append(
            {
                "type": "NEGATIVE_FCF",
                "message": "⚠️ Free Cash Flow negativo",
                "severity": "WARNING",
                "value": fcf,
                "recommendation": "Empresa consume más cash del que genera",
            }
        )

    # 6. Debt muy alto (Assets/Equity ratio)
    total_assets = vals.get("Total_Assets")
    total_equity = vals.get("Total_Equity")

    if total_assets and total_equity and total_equity > 0:
        leverage = total_assets / total_equity
        if leverage > 3:
            alerts["warnings"].append(
                {
                    "type": "HIGH_LEVERAGE",
                    "message": f"⚠️ Alto apalancamiento: Assets/Equity = {leverage:.1f}x",
                    "severity": "WARNING",
                    "value": leverage,
                    "recommendation": "Verificar carga de deuda y cobertura de intereses",
                }
            )

    # ============================================================
    # INFORMACIÓN POSITIVA
    # ============================================================

    # 1. Dividend yield atractivo (>5%)
    div_yield = vals.get("Dividend_Yield_Percent")
    if div_yield and div_yield > 5:
        alerts["info"].append(
            {
                "type": "ATTRACTIVE_YIELD",
                "message": f"💰 Dividend Yield atractivo: {div_yield:.2f}%",
                "severity": "INFO",
                "value": div_yield,
            }
        )

    # 2. Crecimiento consistente de dividendos (>5%)
    if dividend_analysis:
        cagr = dividend_analysis.get("cagr", 0)
        if cagr > 0.05:
            alerts["info"].append(
                {
                    "type": "STRONG_DIVIDEND_GROWTH",
                    "message": f"📈 Fuerte crecimiento de dividendos: {cagr*100:.2f}%/año",
                    "severity": "INFO",
                    "cagr": cagr,
                }
            )

    # 3. P/E bajo (<15x)
    if not is_reit:
        pe = vals.get("PE_Ratio")
        if pe and 0 < pe < 15:
            alerts["info"].append(
                {
                    "type": "LOW_PE",
                    "message": f"💎 P/E bajo: {pe:.1f}x - posible value opportunity",
                    "severity": "INFO",
                    "value": pe,
                }
            )

    # 4. FFO fuerte para REITs
    if is_reit:
        ffo_per_share = reit_metrics.get("ffo_per_share")
        price = vals.get("Price")

        if ffo_per_share and price and ffo_per_share > 0:
            p_ffo = price / ffo_per_share
            if p_ffo < 15:
                alerts["info"].append(
                    {
                        "type": "ATTRACTIVE_P_FFO",
                        "message": f"💎 P/FFO atractivo: {p_ffo:.1f}x",
                        "severity": "INFO",
                        "value": p_ffo,
                    }
                )

    return alerts


def format_alerts_text(alerts: dict) -> str:
    """
    Formatea alertas para output legible
    """
    output = []

    if alerts["critical"]:
        output.append("\n🚨 ALERTAS CRÍTICAS:")
        output.append("-" * 70)
        for alert in alerts["critical"]:
            output.append(f"  {alert['message']}")
            if "recommendation" in alert:
                output.append(f"    💡 {alert['recommendation']}")

    if alerts["warnings"]:
        output.append("\n⚠️  ADVERTENCIAS:")
        output.append("-" * 70)
        for alert in alerts["warnings"]:
            output.append(f"  {alert['message']}")
            if "recommendation" in alert:
                output.append(f"    💡 {alert['recommendation']}")

    if alerts["info"]:
        output.append("\n✅ PUNTOS POSITIVOS:")
        output.append("-" * 70)
        for alert in alerts["info"]:
            output.append(f"  {alert['message']}")

    if not (alerts["critical"] or alerts["warnings"] or alerts["info"]):
        output.append("\n✅ No se detectaron alertas significativas")

    return "\n".join(output)


def get_overall_risk_level(alerts: dict) -> dict:
    """
    Calcula nivel de riesgo general
    """
    critical_count = len(alerts["critical"])
    warning_count = len(alerts["warnings"])

    if critical_count >= 2:
        level = "VERY_HIGH"
        message = "🔴 RIESGO MUY ALTO - Evitar inversión"
    elif critical_count == 1:
        level = "HIGH"
        message = "🟠 RIESGO ALTO - Invertir con precaución extrema"
    elif warning_count >= 3:
        level = "MODERATE"
        message = "🟡 RIESGO MODERADO - Investigar más antes de invertir"
    elif warning_count >= 1:
        level = "LOW"
        message = "🟢 RIESGO BAJO - Revisar advertencias puntuales"
    else:
        level = "MINIMAL"
        message = "🟢 RIESGO MÍNIMO - Fundamentales sólidos"

    return {
        "level": level,
        "message": message,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": len(alerts["info"]),
    }
