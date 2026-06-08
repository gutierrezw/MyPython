---
name: analyzing-financial-statements
description: >
  Calculate, interpret, and benchmark financial ratios from income statements, balance sheets,
  and cash flow data. Use this skill whenever the user mentions financial ratios, fundamental
  analysis, company valuation, stock screening, or wants to evaluate a company's financial health.
  Triggers on: "calculate ratios", "analyze financials", "P/E ratio", "ROE", "ROA", "debt to equity",
  "liquidity analysis", "analyze balance sheet", "valuation metrics", "is this stock undervalued",
  "compare to industry benchmarks", "financial health check", "fundamentals of [company]",
  "gross margin", "operating margin", "EPS", "EV/EBITDA", or any request involving financial
  statement data — even if the user doesn't explicitly say "ratios". Also use when the user
  pastes raw financial figures and asks what they mean or whether a company looks attractive.
---

# Financial Ratio Calculator Skill

Comprehensive financial ratio analysis: calculate, interpret, and benchmark key metrics
from financial statement data for investment decision-making.

---

## What this skill does

Given financial data (income statement, balance sheet, cash flow, market data), this skill:

1. **Calculates** all major ratio categories
2. **Interprets** each ratio with qualitative ratings
3. **Benchmarks** against industry-specific norms (tech, retail, financial, manufacturing, healthcare)
4. **Identifies trends** if multi-period data is provided
5. **Generates** prioritized recommendations and an overall health score

---

## Ratio categories covered

| Category       | Ratios                                                            |
|----------------|-------------------------------------------------------------------|
| Profitability  | ROE, ROA, Gross Margin, Operating Margin, Net Margin             |
| Liquidity      | Current Ratio, Quick Ratio, Cash Ratio                           |
| Leverage       | Debt/Equity, Interest Coverage, Debt Service Coverage            |
| Efficiency     | Asset Turnover, Inventory Turnover, Receivables Turnover, DSO    |
| Valuation      | P/E, P/B, P/S, EV/EBITDA, PEG, EPS, Book Value per Share        |

---

## How to use

### Step 1 — Gather input data

Ask the user for financial data in any of these formats:
- **JSON** with structured financial statements (preferred)
- **CSV** or **Excel** with line items
- **Free text** with key figures (e.g. "revenue 1B, net income 120M, share price 45, shares 50M")
- **Ticker symbol** — if a web search tool is available, retrieve data automatically

Minimum viable input:
- At least one of: income statement OR balance sheet
- Market data (share price + shares outstanding) for valuation ratios

### Step 2 — Identify industry sector

Ask: "What industry/sector is this company in?" Options: `technology`, `retail`, `financial`,
`manufacturing`, `healthcare`, or `general` (default if unknown).

### Step 3 — Run the scripts

```python
# Execute calculate_ratios.py first
from scripts.calculate_ratios import calculate_ratios_from_data

results = calculate_ratios_from_data(financial_data)
ratios = results["ratios"]

# Then run interpret_ratios.py with industry context
from scripts.interpret_ratios import perform_comprehensive_analysis

analysis = perform_comprehensive_analysis(ratios, industry="technology")
print(analysis["report"])
```

### Step 4 — Present results

Structure the output as:

1. **Overall Health Score** (e.g. "Good — 2.8/4.0")
2. **Key metrics table** grouped by category
3. **Highlights**: top 2–3 strengths and top 2–3 concerns
4. **Recommendations**: from `analysis["recommendations"]`
5. **Trend note** if historical data was provided

---

## Input JSON format reference

```json
{
  "income_statement": {
    "revenue": 1000000,
    "cost_of_goods_sold": 600000,
    "operating_income": 200000,
    "ebit": 180000,
    "ebitda": 250000,
    "interest_expense": 20000,
    "net_income": 150000
  },
  "balance_sheet": {
    "total_assets": 2000000,
    "current_assets": 800000,
    "cash_and_equivalents": 200000,
    "accounts_receivable": 150000,
    "inventory": 250000,
    "current_liabilities": 400000,
    "total_debt": 500000,
    "current_portion_long_term_debt": 50000,
    "shareholders_equity": 1500000
  },
  "cash_flow": {
    "operating_cash_flow": 180000,
    "investing_cash_flow": -100000,
    "financing_cash_flow": -50000
  },
  "market_data": {
    "share_price": 50,
    "shares_outstanding": 100000,
    "earnings_growth_rate": 0.10
  }
}
```

---

## Handling missing data

| Missing field          | Action                                              |
|------------------------|-----------------------------------------------------|
| Inventory              | Skip Quick Ratio or use Current Ratio only          |
| Market data            | Skip all valuation ratios; note in output           |
| EBITDA                 | Skip EV/EBITDA; estimate if EBIT + D&A available    |
| Earnings growth rate   | Skip PEG ratio                                      |
| Multiple periods       | Skip trend analysis; flag for the user              |

Always calculate what you can and clearly note what was skipped and why.

---

## Scripts

- `scripts/calculate_ratios.py` — Core calculation engine. Entry point: `calculate_ratios_from_data()`
- `scripts/interpret_ratios.py` — Industry benchmarking and interpretation. Entry point: `perform_comprehensive_analysis()`

---

## Best practices

- Always validate data completeness before running calculations
- Mention industry context when interpreting — a D/E of 4 is normal in banking, alarming in tech
- For investment decisions: combine ratio analysis with qualitative factors (moat, management, macro)
- If the user is evaluating a stock for their portfolio, highlight dividend-relevant ratios (payout ratio, yield) if dividend data is available
- Flag any ratio that is an outlier (>2 standard deviations from benchmark) with a ⚠️ warning
