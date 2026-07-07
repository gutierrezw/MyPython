# ================================================
# valuation_xbrl_api.py (FIXED VERSION)
# Capa: API estándar para el motor
# ================================================
from Modulos_python import os, sys, json, yf, pd, datetime, dataclass, Path, ZipFile
from valuation_arelle_parser import (
    load_xbrl_with_arelle,
    extract_facts,
    extract_contexts,
    extract_units,
)


# -----------------------------------------------------
# Filing (representa un filing cargado con Arelle)
# -----------------------------------------------------
@dataclass
class Filing:
    path: str
    model: object
    facts: dict
    contexts: dict
    units: dict

    def get_facts(self, name):
        """Retorna la lista de hechos tal como vienen de Arelle."""
        return self.facts.get(name, [])


# -----------------------------------------------------
# dividend_history.py
# Análisis histórico de dividendos usando yfinance
# -----------------------------------------------------
def analyze_dividend_history(ticker, years=10, display_log=False):
    """
    Analiza histórico de dividendos y calcula CAGR
    """
    if display_log:
        print("=" * 70)
        print(f"📊 ANÁLISIS DE DIVIDENDOS - {ticker}")
        print("=" * 70)

    # Descargar datos
    stock = yf.Ticker(ticker)
    dividends = stock.dividends

    if dividends.empty:
        print(f"\n❌ No hay datos de dividendos para {ticker}")
        return None

    # Agrupar por año
    dividends_annual = dividends.groupby(dividends.index.year).sum()

    # ✅ NUEVO: Filtrar año actual si está incompleto
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Si estamos antes de noviembre, excluir año actual
    # O si el año actual tiene dividendos sospechosamente bajos
    if current_year in dividends_annual.index:
        if len(dividends_annual) > 1:
            current_year_div = dividends_annual[current_year]
            previous_year_div = dividends_annual.iloc[-2]  # Penúltimo

            # Si el dividendo actual es < 80% del año anterior, probablemente incompleto
            if current_month < 12 or current_year_div < (previous_year_div * 0.80):
                if display_log:
                    print(f"\n⚠️  Excluyendo {current_year} (año incompleto: ${current_year_div:.4f})")
                dividends_annual = dividends_annual[:-1]  # Remover último año

    # Limitar a últimos N años
    dividends_annual = dividends_annual.tail(years)

    if display_log:
        print(f"\n💰 DIVIDENDOS ANUALES (últimos {years} años):")
        print("-" * 70)

        for year, amount in dividends_annual.items():
            print(f"  {year}: ${amount:.4f}")

    # Calcular CAGR (Compound Annual Growth Rate)
    if len(dividends_annual) >= 2:
        start_div = dividends_annual.iloc[0]
        end_div = dividends_annual.iloc[-1]
        years_diff = len(dividends_annual) - 1

        if start_div > 0:
            cagr = ((end_div / start_div) ** (1 / years_diff)) - 1

            if display_log:
                print(f"\n📈 CRECIMIENTO:")
                print("-" * 70)
                print(f"  Dividendo inicial ({dividends_annual.index[0]}): ${start_div:.4f}")
                print(f"  Dividendo final ({dividends_annual.index[-1]}): ${end_div:.4f}")
                print(f"  Período: {years_diff} años")
                print(f"  CAGR: {cagr*100:.2f}% anual")

                # Proyección simple
                print(f"\n🔮 PROYECCIÓN (si mantiene CAGR {cagr*100:.2f}%):")
                print("-" * 70)
                for i in range(1, 6):
                    future_div = end_div * ((1 + cagr) ** i)
                    print(f"  {dividends_annual.index[-1] + i}: ${future_div:.4f}")

            # Recomendación DDM
            if display_log:
                print(f"\n💡 RECOMENDACIÓN PARA DDM:")
                print("-" * 70)

            message = ""
            escenario = ""

            if cagr < 0:
                message = f"  ⚠️  Dividendos han DECRECIDO {abs(cagr)*100:.2f}%/año"
                escenario = f"  💭 Usar escenario conservador: 0-2%"
            elif cagr < 0.03:
                message = f"  📊 Crecimiento bajo: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario conservador: 2-3%"
            elif cagr < 0.06:
                message = f"  ✅ Crecimiento moderado: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario moderado: 3-5%"
            else:
                message = f"  🚀 Crecimiento alto: {cagr*100:.2f}%/año"
                escenario = f"  💭 Usar escenario optimista: 5-7%"

            if display_log:
                print(message)
                print(escenario)

            return {
                "ticker": ticker,
                "annual_dividends": dividends_annual.to_dict(),
                "cagr": cagr,
                "message": message,
                "escenario": escenario,
                "start_year": int(dividends_annual.index[0]),
                "end_year": int(dividends_annual.index[-1]),
                "start_dividend": float(start_div),
                "end_dividend": float(end_div),
            }

    return None


# -----------------------------------------------------
# ✅ Compara histórico de dividendos de múltiples tickers
# -----------------------------------------------------
def compare_tickers(tickers, years=10, display_log=False):
    """
    Compara histórico de dividendos de múltiples tickers
    """
    if display_log:
        print("\n" + "=" * 70)
        print("📊 COMPARACIÓN DE CRECIMIENTO DE DIVIDENDOS")
        print("=" * 70)

    results = []

    for ticker in tickers:
        result = analyze_dividend_history(ticker, years)
        if result:
            results.append(result)

    # Tabla comparativa
    if results:
        if display_log:
            print("\n" + "=" * 70)
            print("📋 RESUMEN COMPARATIVO:")
            print("=" * 70)
            print(f"{'Ticker':<10} {'CAGR':<10} {'Div Actual':<15} {'Recomendación DDM':<20}")
            print("-" * 70)

        for r in results:
            cagr_pct = r["cagr"] * 100
            if r["cagr"] < 0.03:
                rec = "2-3% (conservador)"
            elif r["cagr"] < 0.06:
                rec = "3-5% (moderado)"
            else:
                rec = "5-7% (optimista)"

            if display_log:
                print(f"{r['ticker']:<10} {cagr_pct:>6.2f}%    ${r['end_dividend']:<12.4f}  {rec:<20}")

    return results


# -----------------------------------------------------
# ✅ coordindador de analisis de dividendos
# -----------------------------------------------------
def Analyze_options(ticker=None, years=10, _input_mode=False):

    # Si pasan ticker como argumento
    if len(ticker) == 1:
        ticker = ticker.upper()
        results = analyze_dividend_history(ticker, years=10)
    else:
        # input("📊 Ingrese tickers separados por coma (ej: KHC,HASI,O): ")
        tickers = [t.strip() for t in ticker.split(",")]
        results = compare_tickers(tickers, years=10)

    return results


# -----------------------------------------------------
# ✅ FIX: Obtener valor del fact (múltiples métodos)
# -----------------------------------------------------
def get_fact_value(fact):
    """
    Intenta obtener el valor de un fact usando diferentes métodos.
    Inline XBRL puede tener el valor en diferentes atributos.
    """
    # Método 1: xValue
    if hasattr(fact, "xValue") and fact.xValue is not None:
        return fact.xValue

    # Método 2: value
    if hasattr(fact, "value") and fact.value is not None:
        try:
            return float(str(fact.value).replace(",", ""))
        except:
            return fact.value

    # Método 3: text
    if hasattr(fact, "text") and fact.text:
        try:
            return float(str(fact.text).replace(",", ""))
        except:
            return fact.text

    return None


# -----------------------------------------------------
# ✅ Usa metadata.json para retornar los filings:
# -----------------------------------------------------
def get_zip_files(ticker_dir, display_logs=False):
    """
    Usa metadata.json para retornar los filings relevantes:
    - ZIP → con lista de INSTANCE FILES internos
    - HTM → se marca como INLINE XBRL
    - XML sueltos → se toman directamente

    Retorna lista: [ (path, instance_list), ... ] ordenados por fecha.
    """

    metadata_path = os.path.join(ticker_dir, "metadata.json")
    if not os.path.exists(metadata_path):
        if display_logs:
            print("⚠ No existe metadata.json")
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    files = []
    for item in meta.get("downloaded_files", []):
        date_str = item.get("date", "1900-01-01")
        try:
            dt = datetime.fromisoformat(date_str)
        except:
            dt = datetime.min

        path = item.get("path")
        if not path or not os.path.exists(path):
            continue

        if item.get("is_zip", False):
            # inspeccionar ZIP
            inst = []
            try:
                with ZipFile(path, "r") as z:
                    for name in z.namelist():
                        low = name.lower()
                        if low.endswith(".xml") and not any(k in low for k in ["cal", "pre", "def", "lab"]):
                            inst.append(name)
            except:
                pass

            files.append((dt, path, inst))

        else:
            # HTM inline XBRL
            if path.lower().endswith(".htm"):
                files.append((dt, path, ["INLINE"]))
            # XML suelto
            elif path.lower().endswith(".xml"):
                files.append((dt, path, [path]))

    # ordenar por fecha
    files.sort(key=lambda x: x[0], reverse=True)

    # devolver (path, instance_list)
    return [(p, inst) for _, p, inst in files]


# -----------------------------------------------------
# Función de carga principal
# -----------------------------------------------------
def load_filing(path, instance=None):
    """
    path: ruta al archivo (htm, xml o zip)
    instance: si es ZIP, el nombre del XML que contiene la instancia
    """
    model = load_xbrl_with_arelle(path, instance, display_logs=False)

    facts = extract_facts(model)
    contexts = extract_contexts(model)
    units = extract_units(model)

    return Filing(
        path=str(path),
        model=model,
        facts=facts,
        contexts=contexts,
        units=units,
    )


# -----------------------------------------------------
# ✅ FIX: Selecciona el hecho más apropiado
# -----------------------------------------------------
def select_best_fact(facts, contexts, prefer="duration"):
    """
    Dado un conjunto de facts del mismo nombre:
      - elige INSTANT o DURATION según preferencia
      - elige el más reciente
      - devuelve el valor como float
    """

    if not facts:
        return None

    candidates = []

    for f in facts:
        ctx_id = f.contextID
        ctx = contexts.get(ctx_id)
        if ctx is None:
            continue

        # seleccionar instant o duration
        if prefer == "instant" and "instant" not in ctx:
            continue
        if prefer == "duration" and ("start" not in ctx or "end" not in ctx):
            continue

        # obtener fecha de referencia
        if "instant" in ctx:
            refdate = ctx["instant"]
        else:
            refdate = ctx["end"]

        # A veces Arelle devuelve strings en vez de datetime
        if isinstance(refdate, str):
            try:
                refdate = datetime.fromisoformat(refdate)
            except:
                continue

        # ✅ FIX: Usar get_fact_value()
        val = get_fact_value(f)
        if val is None:
            continue

        try:
            val = float(val)
        except:
            continue

        candidates.append((refdate, val))

    if not candidates:
        return None

    # ordenar por fecha descendente
    candidates.sort(key=lambda x: x[0], reverse=True)

    # devolver valor más reciente
    return candidates[0][1]


# -----------------------------------------------------
# ✅ NUEVO: Extrae todos los valores con fechas
# -----------------------------------------------------
def get_all_facts_with_dates(facts, contexts, prefer="duration"):
    """
    Extrae todos los facts con sus fechas para calcular TTM.

    Returns:
        list of tuples: [(date, value), ...] ordenados por fecha descendente
    """
    if not facts:
        return []

    candidates = []

    for f in facts:
        ctx_id = f.contextID
        ctx = contexts.get(ctx_id)
        if ctx is None:
            continue

        # Seleccionar instant o duration
        if prefer == "instant" and "instant" not in ctx:
            continue
        if prefer == "duration" and ("start" not in ctx or "end" not in ctx):
            continue

        # Obtener fecha de referencia
        if "instant" in ctx:
            refdate = ctx["instant"]
        else:
            refdate = ctx["end"]

        # Convertir string a datetime
        if isinstance(refdate, str):
            try:
                refdate = datetime.fromisoformat(refdate)
            except:
                continue

        # Obtener valor
        val = get_fact_value(f)
        if val is None:
            continue

        try:
            val = float(val)
        except:
            continue

        candidates.append((refdate, val))

    # Ordenar por fecha descendente
    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates


# -----------------------------------------------------
# ✅ CORREGIDO: Calcula TTM sumando últimos 4 trimestres REALES
# -----------------------------------------------------
def calculate_ttm_sum(facts, contexts, prefer="duration"):
    """
    Calcula TTM sumando los últimos 4 trimestres disponibles.

    Lógica mejorada:
    1. Filtra períodos por duración (~90 días para trimestres, ~365 para años)
    2. Elimina duplicados (misma fecha de fin)
    3. Valida que sean consecutivos (gap < 120 días)
    4. Si no hay 4 trimestres válidos, usa el año más reciente

    Returns:
        dict: {
            "ttm_value": float,
            "ttm_end_date": datetime,
            "quarters": [...]
        } o None
    """
    all_values = get_all_facts_with_dates(facts, contexts, prefer)

    if not all_values:
        return None

    # ===================================================================
    # Paso 1: Clasificar períodos por duración
    # ===================================================================
    periods_with_duration = []

    for date, value in all_values:
        # Buscar el contexto para obtener start date
        ctx = None
        for f in facts:
            fact_ctx = contexts.get(f.contextID)
            if not fact_ctx:
                continue

            # Comparar fechas (pueden ser datetime o string)
            ctx_end = fact_ctx.get("end")
            if ctx_end:
                if isinstance(ctx_end, str):
                    ctx_end = datetime.fromisoformat(ctx_end)
                if isinstance(date, str):
                    date_cmp = datetime.fromisoformat(date)
                else:
                    date_cmp = date

                # Comparar solo la fecha (ignorar hora)
                if ctx_end.date() == date_cmp.date():
                    ctx = fact_ctx
                    break

        if ctx and "start" in ctx and "end" in ctx:
            start = ctx["start"]
            end = ctx["end"]

            # Convertir strings a datetime si es necesario
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            if isinstance(end, str):
                end = datetime.fromisoformat(end)

            duration_days = (end - start).days

            # Solo agregar si la duración es razonable (> 30 días)
            if duration_days > 30:
                periods_with_duration.append(
                    {"end": end, "start": start, "value": value, "duration_days": duration_days}
                )

    if not periods_with_duration:
        return None

    # ===================================================================
    # Paso 2: Separar trimestres (60-120 días) vs años (300-400 días)
    # ===================================================================
    quarters = [p for p in periods_with_duration if 60 <= p["duration_days"] <= 120]
    annuals = [p for p in periods_with_duration if 300 <= p["duration_days"] <= 400]

    # ===================================================================
    # Paso 3: Eliminar duplicados (mismo end date)
    # ===================================================================
    def deduplicate_periods(periods):
        """Elimina duplicados manteniendo el de mayor duración"""
        seen_dates = {}
        for p in periods:
            end_str = p["end"].isoformat()
            if end_str not in seen_dates or p["duration_days"] > seen_dates[end_str]["duration_days"]:
                seen_dates[end_str] = p
        return sorted(seen_dates.values(), key=lambda x: x["end"], reverse=True)

    quarters = deduplicate_periods(quarters)
    annuals = deduplicate_periods(annuals)

    # ===================================================================
    # Paso 4: Intentar construir TTM con 4 trimestres consecutivos
    # ===================================================================
    if len(quarters) >= 4:
        # Validar que sean consecutivos (gap < 120 días entre períodos)
        valid_quarters = [quarters[0]]

        for i in range(1, len(quarters)):
            prev_start = valid_quarters[-1]["start"]
            curr_end = quarters[i]["end"]

            # Gap entre períodos
            gap_days = abs((prev_start - curr_end).days)

            # Aceptar si gap < 120 días (permite pequeños overlaps o gaps)
            if gap_days < 120:
                valid_quarters.append(quarters[i])

                if len(valid_quarters) == 4:
                    break

        # Si encontramos 4 trimestres consecutivos, usarlos
        if len(valid_quarters) == 4:
            ttm_sum = sum(q["value"] for q in valid_quarters)
            ttm_end_date = valid_quarters[0]["end"]

            return {
                "ttm_value": ttm_sum,
                "ttm_end_date": ttm_end_date,
                "quarters": [
                    {"date": q["end"].isoformat(), "value": q["value"], "duration_days": q["duration_days"]}
                    for q in valid_quarters
                ],
            }

    # ===================================================================
    # Paso 5: Fallback - usar el año más reciente si no hay 4 trimestres
    # ===================================================================
    if annuals:
        most_recent_annual = annuals[0]
        return {
            "ttm_value": most_recent_annual["value"],
            "ttm_end_date": most_recent_annual["end"],
            "quarters": [
                {
                    "date": most_recent_annual["end"].isoformat(),
                    "value": most_recent_annual["value"],
                    "duration_days": most_recent_annual["duration_days"],
                }
            ],
        }

    # Si no hay ni trimestres ni años válidos, retornar None
    return None


# -----------------------------------------------------
# Interfaz simple para el motor: get_fact()
# -----------------------------------------------------
def get_fact(filing, name, prefer="duration"):
    """
    name = "us-gaap:NetIncomeLoss"
    prefer = "duration" | "instant"
    """
    facts = filing.get_facts(name)
    return select_best_fact(facts, filing.contexts, prefer)


# -----------------------------------------------------
# ✅ NUEVO: Extrae TTM data con metadatos de fechas
# -----------------------------------------------------
def get_ttm_fact(filings, concept_names, prefer="duration"):
    """
    Extrae un concepto con cálculo TTM real.

    Returns:
        dict: {
            "value": float,  # Valor TTM (suma de 4 trimestres)
            "end_date": str,  # Fecha del período más reciente (ISO format)
            "quarters": list,  # Detalles de cada trimestre
            "method": str  # "ttm_sum" o "single_value"
        }
    """
    for concept in concept_names:
        for filing in filings:
            facts = filing.get_facts(concept)
            if not facts:
                continue

            # Intentar calcular TTM
            ttm_data = calculate_ttm_sum(facts, filing.contexts, prefer)
            if ttm_data:
                return {
                    "value": ttm_data["ttm_value"],
                    "end_date": ttm_data["ttm_end_date"].isoformat(),
                    "quarters": ttm_data["quarters"],
                    "method": "ttm_sum",
                    "concept": concept,
                }

            # Fallback: usar el valor más reciente
            single_value = select_best_fact(facts, filing.contexts, prefer)
            if single_value is not None:
                all_values = get_all_facts_with_dates(facts, filing.contexts, prefer)
                if all_values:
                    return {
                        "value": single_value,
                        "end_date": all_values[0][0].isoformat(),
                        "quarters": [],
                        "method": "single_value",
                        "concept": concept,
                    }

    return None


# -----------------------------------------------------
# ✅ NUEVO: Extrae valor instant (Balance Sheet)
# -----------------------------------------------------
def get_instant_fact(filings, concept_names):
    """
    Extrae un concepto instant (balance sheet).

    Returns:
        dict: {
            "value": float,
            "date": str,  # Fecha del snapshot (ISO format)
            "concept": str
        }
    """
    for concept in concept_names:
        for filing in filings:
            facts = filing.get_facts(concept)
            if not facts:
                continue

            all_values = get_all_facts_with_dates(facts, filing.contexts, prefer="instant")
            if all_values:
                return {
                    "value": all_values[0][1],  # Valor más reciente
                    "date": all_values[0][0].isoformat(),  # Fecha más reciente
                    "concept": concept,
                }

    return None


# -----------------------------------------------------
# ✅ REESCRITO: Build TTM con cálculo real de 4 trimestres
# -----------------------------------------------------
def build_ttm(filings):
    """
    Calcula TTM real sumando los últimos 4 trimestres para income/cash flow.
    Para balance sheet, toma el snapshot más reciente.

    Returns:
        dict con estructura:
        {
            "NetIncome": float,  # Valor TTM/más reciente
            "_metadata": {  # Metadatos de fechas y método
                "NetIncome": {"end_date": "2024-09-30", "method": "ttm_sum", ...}
            }
        }
    """

    def try_ttm_names(primary, fallback=None, prefer="duration"):
        """Busca el primer concepto disponible con TTM"""
        all_names = primary + (fallback if fallback else [])
        result = get_ttm_fact(filings, all_names, prefer)
        return result

    def try_instant_names(primary, fallback=None):
        """Busca el primer concepto instant disponible"""
        all_names = primary + (fallback if fallback else [])
        result = get_instant_fact(filings, all_names)
        return result

    # ✅ EXTRACCIÓN CON TTM REAL (suma de 4 trimestres)
    # Income Statement & Cash Flow: TTM (duration)
    net_income = try_ttm_names(
        [
            "us-gaap:ProfitLoss",
            "us-gaap:NetIncomeLoss",
            "ifrs-full:ProfitLoss",
        ]
    )

    depreciation = try_ttm_names(
        [
            "us-gaap:DepreciationDepletionAndAmortization",
            "us-gaap:Depreciation",
            "us-gaap:DepreciationAndAmortization",
            "ifrs-full:DepreciationAndAmortisationExpense",
        ]
    )

    gains_on_sales = try_ttm_names(
        [
            "us-gaap:ProceedsFromSaleOfRealEstateHeldforinvestment",
            "us-gaap:GainLossOnSaleOfProperties",
            "us-gaap:GainLossOnSaleOfPropertyPlantEquipment",
            "ifrs-full:GainsLossesOnDisposalsOfPropertyPlantAndEquipment",
        ]
    )

    operating_cf = try_ttm_names(
        [
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
            "us-gaap:CashProvidedByUsedInOperatingActivities",
            "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "ifrs-full:CashFlowsFromUsedInOperatingActivities",
        ],
        fallback=[
            "vale:CashFlowsFromUsedInOperatingActivitiesContinuingOperation",
            "ifrs-full:CashFlowsFromUsedInOperatingActivitiesContinuingOperations",
        ],
    )

    capex = try_ttm_names(
        [
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
            "us-gaap:CapitalExpenditures",
            "ifrs-full:PurchaseOfPropertyPlantAndEquipment",
        ],
        fallback=[
            "vale:AcquisitionOfPropertyPlantAndEquipmentAndIntangibleAssets",
        ],
    )

    dividends = try_ttm_names(
        [
            "us-gaap:DividendsCommonStockCash",
            "us-gaap:PaymentsOfDividends",
            "us-gaap:PaymentsOfDividendsCommonStock",
            "ifrs-full:DividendsPaidToEquityHoldersOfParentClassifiedAsFinancingActivities",
            "ifrs-full:DividendsPaidClassifiedAsFinancingActivities",
            "ifrs-full:DividendsRecognisedAsDistributionsToOwnersOfParent",
        ]
    )

    revenues = try_ttm_names(
        [
            "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
            "us-gaap:Revenues",
            "us-gaap:SalesRevenueNet",
            "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
            "ifrs-full:Revenue",
        ]
    )

    ffo = try_ttm_names(
        [
            "us-gaap:FundsFromOperations",
            "hasi:FundsFromOperations",
        ]
    )

    affo = try_ttm_names(
        [
            "us-gaap:AdjustedFundsFromOperations",
            "hasi:AdjustedFundsFromOperations",
        ]
    )

    adjusted_earnings = try_ttm_names(
        [
            "hasi:AdjustedNetIncome",
            "hasi:AdjustedEarnings",
            "us-gaap:AdjustedNetIncome",
            "us-gaap:NonGAAPNetIncome",
        ]
    )

    # Balance Sheet: Instant (snapshot más reciente)
    shares = try_instant_names(
        [
            "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
            "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
            "dei:EntityCommonStockSharesOutstanding",
            "ifrs-full:WeightedAverageNumberOfOrdinarySharesOutstanding",
        ]
    )

    total_assets = try_instant_names(
        [
            "us-gaap:Assets",
            "ifrs-full:Assets",
        ]
    )

    total_equity = try_instant_names(
        [
            "us-gaap:StockholdersEquity",
            "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            "us-gaap:Equity",
            "ifrs-full:Equity",
        ]
    )

    short_term_debt = try_instant_names(
        [
            "us-gaap:ShortTermBorrowings",
            "us-gaap:DebtCurrent",
            "us-gaap:LongTermDebtCurrent",
            "ifrs-full:ShorttermBorrowings",
            "ifrs-full:CurrentBorrowings",
            "ifrs-full:CurrentPortionOfLongtermBorrowings",
        ],
        fallback=[
            "vale:CurrentBorrowingsAndCurrentPortionOfNonCurrentBorrowingsGross",
            "vale:LoansBorrowingsAndCurrent",
        ],
    )

    long_term_debt = try_instant_names(
        [
            "us-gaap:LongTermDebtNoncurrent",
            "us-gaap:LongTermDebt",
            "us-gaap:DebtNoncurrent",
            "ifrs-full:LongtermBorrowings",
            "ifrs-full:NoncurrentBorrowings",
        ],
        fallback=[
            "vale:LoansBorrowingsAndNonCurrent",
            "vale:LongtermBorrowingsGross",
            "vale:LongtermUnsecuredDebt",
        ],
    )

    cash = try_instant_names(
        [
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:Cash",
            "us-gaap:CashCashEquivalentsAndShortTermInvestments",
            "ifrs-full:CashAndCashEquivalents",
        ]
    )

    # Construir el diccionario con valores y metadata
    result = {
        # Valores extraídos (TTM o más reciente)
        "NetIncome": net_income["value"] if net_income else None,
        "Depreciation": depreciation["value"] if depreciation else None,
        "GainsOnRealEstateSales": gains_on_sales["value"] if gains_on_sales else None,
        "OperatingCF": operating_cf["value"] if operating_cf else None,
        "CapEx": capex["value"] if capex else None,
        "DividendsPaid": dividends["value"] if dividends else None,
        "Revenues": revenues["value"] if revenues else None,
        "FFO": ffo["value"] if ffo else None,
        "AFFO": affo["value"] if affo else None,
        "AdjustedEarnings": adjusted_earnings["value"] if adjusted_earnings else None,
        "Shares": shares["value"] if shares else None,
        "TotalAssets": total_assets["value"] if total_assets else None,
        "TotalEquity": total_equity["value"] if total_equity else None,
        "ShortTermDebt": short_term_debt["value"] if short_term_debt else None,
        "LongTermDebt": long_term_debt["value"] if long_term_debt else None,
        "CashAndEquivalents": cash["value"] if cash else None,
        # ✅ NUEVO: Metadata con fechas y método de cálculo
        "_metadata": {
            "NetIncome": net_income,
            "Depreciation": depreciation,
            "GainsOnRealEstateSales": gains_on_sales,
            "OperatingCF": operating_cf,
            "CapEx": capex,
            "DividendsPaid": dividends,
            "Revenues": revenues,
            "FFO": ffo,
            "AFFO": affo,
            "AdjustedEarnings": adjusted_earnings,
            "Shares": shares,
            "TotalAssets": total_assets,
            "TotalEquity": total_equity,
            "ShortTermDebt": short_term_debt,
            "LongTermDebt": long_term_debt,
            "CashAndEquivalents": cash,
        },
    }

    return result
