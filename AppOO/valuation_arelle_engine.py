# ================================================
# valuation_arelle_engine.py (DB READY VERSION)
# Output estructurado para base de datos
# ================================================
from Modulos_python import (
    os,
    sys,
    json,
    datetime,
    dataclass,
    Path,
    time,
    requests,
    np,
    ZipFile,
)
from valuation_xbrl_api import load_filing, build_ttm, analyze_dividend_history
from valuation_ddm import DividendDiscountModel
from valuation_alerts import generate_alerts, get_overall_risk_level, format_alerts_text


def is_reit(ttm: dict):
    """
    Detecta si la empresa es un REIT basándose en señales algorítmicas.
    Versión mejorada para evitar falsos positivos.
    """

    # ============================================================
    # Señal 1: Si reporta FFO/AFFO nativo en los filings
    # ============================================================
    if ttm.get("FFO") is not None or ttm.get("AFFO") is not None:
        return True

    depreciation = ttm.get("Depreciation") or 0
    revenues = ttm.get("Revenues") or 0
    gains = ttm.get("GainsOnRealEstateSales") or 0

    # ============================================================
    # Señal 2 (MEJORADA): Gains significativos en ventas de Real Estate
    # PERO solo si son materiales relativos a revenues
    # ============================================================
    if revenues > 0 and gains != 0:
        gains_ratio = abs(gains) / revenues
        # Solo si gains > 5% de revenues (evita ventas corporativas ocasionales)
        if gains_ratio > 0.05 and abs(gains) > 10_000_000:
            return True

    # ============================================================
    # Señal 3: Depreciation muy alta relativa a revenues
    # REITs deprecian mucho porque tienen muchas propiedades
    # ============================================================
    if revenues > 0 and depreciation > 0:
        depreciation_ratio = abs(depreciation) / revenues
        # Si depreciation > 35% de revenues, es casi seguro un REIT
        # (Aumentado de 30% a 35% para ser más conservador)
        if depreciation_ratio > 0.35:
            return True

    # ============================================================
    # Señal 4 (MEJORADA): Payout alto + Depreciation alta
    # AMBAS condiciones deben cumplirse para evitar falsos positivos
    # ============================================================
    dividends = ttm.get("DividendsPaid") or 0
    ocf = ttm.get("OperatingCF") or 0

    if ocf > 0 and dividends > 0 and revenues > 0:
        payout = dividends / ocf
        depreciation_ratio = abs(depreciation) / revenues

        # ✅ CAMBIO CLAVE: Requiere AMBAS condiciones
        # Payout alto (>80%) Y depreciation alta (>25%)
        # Aumentado umbrales para ser más estricto
        if payout > 0.80 and depreciation_ratio > 0.25:
            return True

    # ============================================================
    # Señal 5: REITs de infraestructura (torres, data centers)
    # Tienen payout muy alto pero depreciation moderada
    # ============================================================
    net_income = ttm.get("NetIncome") or 0

    # Recalcular variables para Señal 5
    if ocf > 0 and dividends > 0 and revenues > 0:
        payout_ocf = dividends / ocf
        depreciation_ratio = abs(depreciation) / revenues

        # REITs de infraestructura: payout altísimo (>90%) + depreciation moderada (>15%)
        # Y típicamente tienen pérdidas contables (net income negativo)
        if payout_ocf > 0.90 and depreciation_ratio > 0.15 and net_income < 0:
            return True

    return False


def get_ticker_dir(BASE_DIR: Path, ticker: str) -> Path:
    return BASE_DIR / f"{ticker.upper()}_EDGAR_Files"


def load_metadata(ticker_dir: Path):
    meta_path = ticker_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No existe metadata.json en: {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_instances_from_zip(zip_path: str):
    instances = []
    try:
        with ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                low = name.lower()
                if low.endswith(".xml") and not any(
                    k in low for k in ["cal", "pre", "def", "lab"]
                ):
                    instances.append(name)
    except Exception as e:
        print(f"⚠ Error leyendo ZIP {zip_path}: {e}")
    return instances


def build_file_list(BASE_DIR: Path, ticker: str, display_logs=False):
    ticker_dir = get_ticker_dir(BASE_DIR, ticker)
    meta = load_metadata(ticker_dir)

    items_10k = []
    items_10q = []

    for entry in meta.get("downloaded_files", []):
        date_str = entry.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = entry.get("path")
        if not path or not os.path.exists(path):
            continue

        form = entry.get("form", "")
        low = path.lower()

        if entry.get("is_zip"):
            insts = extract_instances_from_zip(path)
            for inst in insts:
                if form == "10-K":
                    items_10k.append((dt, path, inst))
                else:
                    items_10q.append((dt, path, inst))
            continue

        if low.endswith(".htm"):
            if form == "10-K":
                items_10k.append((dt, path, None))
            else:
                items_10q.append((dt, path, None))
            continue

        if low.endswith(".xml"):
            if form == "10-K":
                items_10k.append((dt, path, None))
            else:
                items_10q.append((dt, path, None))
            continue

    items_10k.sort(key=lambda x: x[0], reverse=True)
    items_10q.sort(key=lambda x: x[0], reverse=True)

    out = []
    if items_10k:
        out.append((items_10k[0][1], items_10k[0][2]))

    for dt, p, inst in items_10q[:3]:
        out.append((p, inst))

    if display_logs:
        print("\n📄 Archivos a procesar:")
        for p, inst in out:
            print(f" - {Path(p).name}")

    return out


def get_yf_data(ticker: str):
    """
    Obtiene precio actual y nombre de la compañía desde Yahoo Finance.
    Retorna: (price: float, company_name: str) o (None, None) si falla
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
    urls = [
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
        f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}",
    ]

    price = None
    company_name = None

    # Intento 1: obtener desde /v8/finance/chart (más confiable para precio)
    for attempt in range(3):
        for url in urls:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 429:
                    time.sleep(1 + attempt)
                    continue
                r.raise_for_status()
                data = r.json()

                # Extrae precio
                try:
                    price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                except:
                    pass

                # Extrae nombre de la compañía
                try:
                    company_name = data["chart"]["result"][0]["meta"]["longName"]
                except:
                    try:
                        company_name = data["chart"]["result"][0]["meta"]["shortName"]
                    except:
                        pass

                if price:
                    break

            except:
                time.sleep(0.5 + attempt)

        if price:
            break

    # Intento 2: Fallback a /v10/finance/quoteSummary si el anterior falló
    if not price or not company_name:
        try:
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=price,assetProfile"
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()

            if not price:
                try:
                    price = data["quoteSummary"]["result"][0]["price"][
                        "regularMarketPrice"
                    ]["raw"]
                except:
                    pass

            if not company_name:
                try:
                    company_name = data["quoteSummary"]["result"][0]["assetProfile"][
                        "longBusinessSummary"
                    ]
                    # Si es muy largo, intenta obtener el nombre corto
                    try:
                        company_name = data["quoteSummary"]["result"][0]["price"][
                            "longName"
                        ]
                    except:
                        pass
                except:
                    try:
                        company_name = data["quoteSummary"]["result"][0]["price"][
                            "shortName"
                        ]
                    except:
                        pass

        except:
            pass

    # Intento 3: Fallback a yfinance como último recurso
    if not price or not company_name:
        try:
            import yfinance as yf

            tk = yf.Ticker(ticker)
            info = tk.info

            if not price and "regularMarketPrice" in info:
                price = info["regularMarketPrice"]

            if not company_name and "longName" in info:
                company_name = info["longName"]
            elif not company_name and "shortName" in info:
                company_name = info["shortName"]

        except:
            pass

    return price, company_name


def compute_reit_metrics(ttm: dict):
    """
    Calcula FFO y AFFO según fórmula NAREIT.
    ⚠️ Solo aplica a REITs - para empresas normales devuelve None
    """
    # ✅ Solo calcular para REITs
    if not is_reit(ttm):
        return {
            "FFO": None,
            "AFFO": None,
            "is_reit": False,
        }

    net_income = ttm.get("NetIncome")
    depreciation = ttm.get("Depreciation") or 0
    gains_on_sales = ttm.get("GainsOnRealEstateSales") or 0
    capex = ttm.get("CapEx") or 0

    ffo = None
    if net_income is not None:
        ffo = net_income + depreciation - gains_on_sales

    affo = None
    if ffo is not None and capex != 0:
        maintenance_capex = abs(capex) * 0.20
        affo = ffo - maintenance_capex

    return {
        "FFO": ffo,
        "AFFO": affo,
        "is_reit": True,
    }


def compute_valuations(ttm: dict, price: float):
    net_income = ttm.get("NetIncome")
    ocf = ttm.get("OperatingCF")
    capex = ttm.get("CapEx")
    dividends = ttm.get("DividendsPaid")
    shares = ttm.get("Shares")
    revenues = ttm.get("Revenues")

    reit_metrics = compute_reit_metrics(ttm)
    ffo = reit_metrics["FFO"]
    affo = reit_metrics["AFFO"]

    fcf = None
    if ocf is not None and capex is not None:
        fcf = ocf - abs(capex)

    # Métricas por acción
    eps = net_income / shares if (net_income and shares) else None
    ocf_per_share = ocf / shares if (ocf and shares) else None
    fcf_per_share = fcf / shares if (fcf and shares) else None
    revenue_per_share = revenues / shares if (revenues and shares) else None
    dividend_per_share = dividends / shares if (dividends and shares) else None
    ffo_per_share = ffo / shares if (ffo and shares) else None
    affo_per_share = affo / shares if (affo and shares) else None

    # Ratios de valuación
    pe_ratio = price / eps if eps else None
    p_fcf = price / fcf_per_share if fcf_per_share else None
    p_s = price / revenue_per_share if revenue_per_share else None
    p_ffo = price / ffo_per_share if ffo_per_share else None
    p_affo = price / affo_per_share if affo_per_share else None

    div_yield = (dividend_per_share / price * 100) if dividend_per_share else None
    payout_ratio = (
        (dividends / net_income * 100) if (dividends and net_income) else None
    )

    # ✅ Convertir NaN a None para JSON/DB
    def clean_value(v):
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    return {
        "Price": clean_value(price),
        "Shares": clean_value(shares),
        # Totales
        "NetIncome_Total": clean_value(net_income),
        "OperatingCF_Total": clean_value(ocf),
        "CapEx_Total": clean_value(capex),
        "FCF_Total": clean_value(fcf),
        "Dividends_Total": clean_value(dividends),
        "Revenues_Total": clean_value(revenues),
        "FFO_Total": clean_value(ffo),
        "AFFO_Total": clean_value(affo),
        # Por acción
        "EPS": clean_value(eps),
        "OCF_Per_Share": clean_value(ocf_per_share),
        "FCF_Per_Share": clean_value(fcf_per_share),
        "Revenue_Per_Share": clean_value(revenue_per_share),
        "Dividend_Per_Share": clean_value(dividend_per_share),
        "FFO_Per_Share": clean_value(ffo_per_share),
        "AFFO_Per_Share": clean_value(affo_per_share),
        # Ratios de valuación
        "PE_Ratio": clean_value(pe_ratio),
        "P_FCF": clean_value(p_fcf),
        "P_S": clean_value(p_s),
        "P_FFO": clean_value(p_ffo),
        "P_AFFO": clean_value(p_affo),
        "Dividend_Yield_Percent": clean_value(div_yield),
        "Payout_Ratio_Percent": clean_value(payout_ratio),
        # Balance Sheet
        "Total_Assets": clean_value(ttm.get("TotalAssets")),
        "Total_Equity": clean_value(ttm.get("TotalEquity")),
    }


def run_ddm_analysis(dividend_per_share, price, required_return=0.10):
    """Ejecuta múltiples escenarios de DDM"""
    if not dividend_per_share or dividend_per_share <= 0:
        return None

    ddm = DividendDiscountModel(dividend_per_share, required_return)

    results = {}

    # Gordon Growth - Múltiples escenarios
    for growth in [0.02, 0.03, 0.04, 0.05]:
        if growth < required_return:
            result = ddm.gordon_growth(growth)
            iv = result.get("intrinsic_value")
            if iv:
                mos = ddm.margin_of_safety(iv, price)
                results[f"Gordon_{int(growth*100)}pct"] = {
                    "model": "Gordon Growth Model",
                    "growth_rate": growth,
                    "intrinsic_value": iv,
                    "margin_of_safety_percent": mos["margin_of_safety_%"],
                    "recommendation": mos["recommendation"],
                }

    # Two-Stage DDM
    result = ddm.two_stage(
        high_growth_rate=0.07, high_growth_years=5, stable_growth_rate=0.03
    )
    iv = result.get("intrinsic_value")
    if iv:
        mos = ddm.margin_of_safety(iv, price)
        results["TwoStage_7pct_5y"] = {
            "model": "Two-Stage DDM",
            "high_growth_rate": 0.07,
            "high_growth_years": 5,
            "stable_growth_rate": 0.03,
            "intrinsic_value": iv,
            "margin_of_safety_percent": mos["margin_of_safety_%"],
            "recommendation": mos["recommendation"],
        }

    # Three-Stage DDM
    result = ddm.three_stage(
        high_growth_rate=0.08,
        high_growth_years=3,
        transition_years=4,
        stable_growth_rate=0.03,
    )
    iv = result.get("intrinsic_value")
    if iv:
        mos = ddm.margin_of_safety(iv, price)
        results["ThreeStage_8pct_3y"] = {
            "model": "Three-Stage DDM",
            "high_growth_rate": 0.08,
            "high_growth_years": 3,
            "transition_years": 4,
            "stable_growth_rate": 0.03,
            "intrinsic_value": iv,
            "margin_of_safety_percent": mos["margin_of_safety_%"],
            "recommendation": mos["recommendation"],
        }

    return results


def run_valuation(file_list, ticker, price, company_name):
    """
    ✅ RETORNA DICCIONARIO COMPLETO - LISTO PARA DB
    """
    filings = []

    for path, instance in file_list:
        try:
            model = load_filing(path, instance)
            filings.append(model)
        except Exception as e:
            print(f"[ERROR] al cargar filing {path}: {e}")

    if not filings:
        return {"error": "No se cargó ningún filing."}

    ttm = build_ttm(filings)
    vals = compute_valuations(ttm, price)
    reit_metrics = {}
    alerts = []
    risk_assessment = {}
    analyze_divideds = []

    # Ejecutar análisis DDM
    ddm_results = None
    if vals.get("Dividend_Per_Share"):
        ddm_results = run_ddm_analysis(vals["Dividend_Per_Share"], price)
        analyze_divideds = analyze_dividend_history(ticker)

        # ✅ NUEVO: Generar alertas
        reit_metrics = {
            "is_reit": is_reit(ttm),  # ✅ AGREGADO
            "ffo_total": vals["FFO_Total"],
            "affo_total": vals["AFFO_Total"],
            "ffo_per_share": vals["FFO_Per_Share"],
            "affo_per_share": vals["AFFO_Per_Share"],
        }

        alerts = generate_alerts(ttm, vals, reit_metrics, analyze_divideds)
        risk_assessment = get_overall_risk_level(alerts)

    # ✅ ESTRUCTURA PARA DB
    return {
        "metadata": {
            "ticker": ticker,
            "company_name": company_name,
            "is_reit": is_reit(ttm),
            "analysis_date": datetime.now().isoformat(),
            "price_date": datetime.now().date().isoformat(),
            "files_processed": [Path(p).name for p, _ in file_list],
        },
        "market_data": {
            "current_price": vals["Price"],
            "shares_outstanding": vals["Shares"],
        },
        "fundamentals": {
            "income_statement": {
                "net_income": vals["NetIncome_Total"],
                "revenues": vals["Revenues_Total"],
                "operating_cash_flow": vals["OperatingCF_Total"],
            },
            "cash_flow": {
                "operating_cf": vals["OperatingCF_Total"],
                "capex": vals["CapEx_Total"],
                "free_cash_flow": vals["FCF_Total"],
                "dividends_paid": vals["Dividends_Total"],
            },
            "balance_sheet": {
                "total_assets": vals["Total_Assets"],
                "total_equity": vals["Total_Equity"],
            },
        },
        "reit_metrics": reit_metrics,
        "alerts": alerts,
        "risk_assessment": risk_assessment,
        "per_share_metrics": {
            "eps": vals["EPS"],
            "revenue_per_share": vals["Revenue_Per_Share"],
            "dividend_per_share": vals["Dividend_Per_Share"],
            "ocf_per_share": vals["OCF_Per_Share"],
            "fcf_per_share": vals["FCF_Per_Share"],
            "ffo_per_share": vals["FFO_Per_Share"],
            "affo_per_share": vals["AFFO_Per_Share"],
        },
        "valuation_ratios": {
            "pe_ratio": vals["PE_Ratio"],
            "p_s_ratio": vals["P_S"],
            "p_fcf_ratio": vals["P_FCF"],
            "p_ffo_ratio": vals["P_FFO"],
            "p_affo_ratio": vals["P_AFFO"],
            "dividend_yield_percent": vals["Dividend_Yield_Percent"],
            "payout_ratio_percent": vals["Payout_Ratio_Percent"],
        },
        "raw_ttm_data": ttm,
        "dividend_analysis": analyze_divideds,
        "ddm_valuation": ddm_results,
    }


def print_summary(result):
    """
    ✅ FUNCIÓN OPCIONAL - Imprime resumen legible
    """
    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return

    meta = result["metadata"]
    market = result["market_data"]
    per_share = result["per_share_metrics"]
    ratios = result["valuation_ratios"]
    reit = result["reit_metrics"]
    ddm = result.get("ddm_valuation")

    print("\n" + "=" * 70)
    print(f"📊 ANÁLISIS DE VALORACIÓN - {meta['ticker']}")
    print(f"📅 Fecha: {meta['analysis_date'][:10]}")
    print("=" * 70)

    print(f"\n💰 Precio Actual: ${market['current_price']:.2f}")
    print(f"📈 Shares: {market['shares_outstanding']:,.0f}")

    # ✅ Solo mostrar métricas REIT si es REIT
    if reit.get("is_reit") and reit["ffo_per_share"]:
        print("\n🏢 MÉTRICAS REIT:")
        print(f"  FFO/share: ${reit['ffo_per_share']:.2f}")
        if ratios["p_ffo_ratio"]:
            print(f"  P/FFO: {ratios['p_ffo_ratio']:.2f}x")
        if reit["affo_per_share"]:
            print(f"  AFFO/share: ${reit['affo_per_share']:.2f}")

    print("\n📉 FUNDAMENTALES:")
    if per_share["eps"]:
        print(f"  EPS: ${per_share['eps']:.2f}")
    if per_share["dividend_per_share"]:
        print(f"  Dividend/share: ${per_share['dividend_per_share']:.2f}")
    if ratios["dividend_yield_percent"]:
        print(f"  Dividend Yield: {ratios['dividend_yield_percent']:.2f}%")
    if ratios["pe_ratio"]:
        print(f"  P/E: {ratios['pe_ratio']:.2f}x")

    if ddm:
        print("\n💎 VALORACIÓN DDM:")
        for key, data in ddm.items():
            print(f"\n  {key.replace('_', ' ')}:")
            print(f"    Valor Intrínseco: ${data['intrinsic_value']:.2f}")
            print(f"    Margen: {data['margin_of_safety_percent']:+.1f}%")
            print(f"    📌 {data['recommendation']}")

    # ✅ NUEVO: Mostrar alertas
    if "alerts" in result:
        print(format_alerts_text(result["alerts"]))

    # ✅ NUEVO: Mostrar evaluación de riesgo
    if "risk_assessment" in result:
        risk = result["risk_assessment"]
        print("\n" + "=" * 70)
        print("⚖️  EVALUACIÓN DE RIESGO")
        print("=" * 70)
        print(f"\n{risk['message']}")
        print(f"  Alertas críticas: {risk['critical_count']}")
        print(f"  Advertencias: {risk['warning_count']}")
        print(f"  Puntos positivos: {risk['info_count']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    BASE_DIR = Path(r"C:\Users\InversionesWildaga\Documents\MyPython\AppOO\EDGAR")

    ticker = input("💼 Ingrese el ticker: ").strip().upper()
    price, company_name = get_yf_data(ticker)  # ✅ Desempaca tupla

    if not price:
        print("❌ No se pudo obtener el precio de Yahoo Finance")
    elif price > 0:

        file_list = build_file_list(BASE_DIR, ticker, display_logs=False)
        result = run_valuation(file_list, ticker, price, company_name)

        # Resumen en pantalla
        # print_summary(result)

        # ✅ DICCIONARIO IDENTADO LISTO PARA DB
        print("\n" + "=" * 70)
        print("💾 ESTRUCTURA DE DATOS (lista para DB):")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Crear carpeta valuations si no existe
        valuations_dir = BASE_DIR / f"{ticker.upper()}_EDGAR_Files" / "valuations"
        valuations_dir.mkdir(parents=True, exist_ok=True)

        # Guardar archivo
        filename = f"{ticker}_valuation_{datetime.now().strftime('%Y%m%d')}.json"
        output_file = valuations_dir / filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ Guardado en: {output_file}")
