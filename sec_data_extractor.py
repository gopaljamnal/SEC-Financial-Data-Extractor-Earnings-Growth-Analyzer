"""
SEC Financial Data Extractor & Earnings Growth Analyzer

This module extracts quarterly financial data from SEC EDGAR XBRL filings (10-Q/10-K)
and calculates comprehensive financial metrics including earnings growth.

Author: Gopal Jamnal
Email: gopal.jamnal@gmail.com
License: MIT
"""

import os
import time
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# SEC API Configuration
# ============================================================================

USER_AGENT = os.environ.get("SEC_USER_AGENT", "Gopal Jamnal gopal.jamnal@gmail.com")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
REQS_PER_SEC = 9.0  # Stay under SEC's 10 requests/second limit

def throttle():
    """Rate limiting to comply with SEC API requirements."""
    time.sleep(1.0 / REQS_PER_SEC)

def GET(url: str, max_retries: int = 3) -> requests.Response:
    """
    Make rate-limited GET request to SEC API with retry logic.
    
    Args:
        url: The URL to request
        max_retries: Maximum number of retry attempts
        
    Returns:
        requests.Response object
        
    Raises:
        requests.HTTPError: If request fails after retries
    """
    throttle()
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Attempt {attempt + 1} failed for {url}, retrying...")
            time.sleep(2 ** attempt)  # Exponential backoff

# ============================================================================
# SEC Endpoints
# ============================================================================

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# ============================================================================
# XBRL Tag Mappings
# ============================================================================

# Duration tags (Income Statement & Cash Flow Statement)
DURATION_TAGS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "ebit": ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
    "tax_expense": ["IncomeTaxExpenseBenefit"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "cfi": ["NetCashProvidedByUsedInInvestingActivities"],
    "cff": ["NetCashProvidedByUsedInFinancingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpendituresIncurredButNotYetPaid"],
    "interest_exp": ["InterestExpense", "InterestAndDebtExpense"],
    "dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
    "rnd": ["ResearchAndDevelopmentExpense"],
    "sga": ["SellingGeneralAndAdministrativeExpense"]
}

# Instant tags (Balance Sheet - point-in-time)
INSTANT_TAGS = {
    "assets": ["Assets"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
    "equity": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "StockholdersEquity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "Cash"],
    "sti": ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesCurrent"],
    "ar": ["AccountsReceivableNetCurrent", "AccountsReceivableNet"],
    "ap": ["AccountsPayableCurrent", "AccountsPayable"],
    "inventory": ["InventoryNet", "Inventory"],
    "debt_lt_nc": ["LongTermDebtNoncurrent"],
    "debt_lt_cur": ["LongTermDebtCurrent"],
    "debt_st": ["ShortTermBorrowings"],
    "ppe": ["PropertyPlantAndEquipmentNet"],
    "goodwill": ["Goodwill"],
    "intangibles": ["FiniteLivedIntangibleAssetsNet", "IntangibleAssetsNetExcludingGoodwill"],
    "retained": ["RetainedEarningsAccumulatedDeficit"],
    "deferred_revenue": ["ContractWithCustomerLiabilityCurrent", "DeferredRevenue"],
    "treasury_stock": ["TreasuryStockValue"]
}

# Output feature list (62 features + target variable)
FEATURES_62 = [
    # Raw financial metrics (30)
    "revenue", "cogs", "ebit", "net_income", "eps_diluted", "da", "tax_expense", 
    "cfo", "cfi", "cff", "capex", "interest_exp", "dividends", "rnd", "sga",
    "ppe", "goodwill", "intangibles", "assets", "assets_current", "liabilities_current",
    "equity", "cash", "sti", "ar", "ap", "inventory", "debt", "retained", 
    "deferred_revenue", "treasury_stock",
    
    # Derived metrics (32)
    "gross_profit", "gross_margin", "op_margin", "net_margin", "ebitda", 
    "ebitda_margin", "eff_tax_rate", "current_ratio", "quick_ratio", "cash_ratio",
    "debt_to_equity", "asset_turnover", "inventory_turnover", "receivables_turnover",
    "payables_turnover", "dio", "dso", "dpo", "ccc", "fcf", "fcf_margin", 
    "cfo_margin", "ppe_to_assets", "goodwill_to_assets", "intang_to_assets",
    "cash_to_assets", "curr_assets_to_assets", "retained_to_assets", 
    "equity_multiplier", "tangible_book", "tangible_book_to_assets", "sales_growth",
    "working_capital", "sga_margin", "rnd_margin", "roe", "ocf_ratio", "cf_to_ni"
]

# ============================================================================
# XBRL Helper Functions
# ============================================================================

def select_units_prefer_usd(fact: Dict) -> Tuple[List, Optional[str]]:
    """
    Extract unit-specific data from XBRL fact, preferring USD.
    
    Args:
        fact: XBRL fact dictionary
        
    Returns:
        Tuple of (data_array, unit_string)
    """
    if not isinstance(fact, dict) or "units" not in fact:
        return [], None
    
    units = fact["units"]
    
    # Prefer USD currency
    if "USD" in units:
        return units["USD"], "USD"
    
    # Fallback to first available unit
    for unit_name, unit_data in units.items():
        return unit_data, unit_name
    
    return [], None

def pick_val(arr: List[Dict], fy: int, fp: str) -> Optional[float]:
    """
    Select the appropriate value for a given fiscal year and period.
    
    Args:
        arr: Array of XBRL fact values
        fy: Fiscal year
        fp: Fiscal period (Q1, Q2, Q3, Q4, FY)
        
    Returns:
        The selected value or None
    """
    candidates = [
        x for x in arr 
        if str(x.get("fy")) == str(fy) and x.get("fp") == fp
    ]
    
    if not candidates:
        return None
    
    # Sort by end date and value to get most recent/largest
    candidates = sorted(
        candidates, 
        key=lambda x: (x.get("end", ""), x.get("val", 0))
    )
    
    return candidates[-1].get("val")

def quarter_increment(usgaap: Dict, tag_list: List[str], fy: int) -> Dict[str, Optional[float]]:
    """
    Convert YTD values to quarterly increments.
    
    SEC filings report cumulative (YTD) values. This function decomposes them
    into individual quarters: Q1, Q2, Q3, Q4.
    
    Args:
        usgaap: US-GAAP taxonomy facts
        tag_list: List of possible XBRL tags for this metric
        fy: Fiscal year
        
    Returns:
        Dictionary with keys Q1, Q2, Q3, Q4, FY
    """
    # Find first available tag
    tag = next((t for t in tag_list if t in usgaap), None)
    if not tag:
        return {q: None for q in ["Q1", "Q2", "Q3", "Q4", "FY"]}
    
    arr, _unit = select_units_prefer_usd(usgaap[tag])
    
    # Extract YTD values
    ytd = {q: pick_val(arr, fy, q) for q in ["Q1", "Q2", "Q3"]}
    fy_val = pick_val(arr, fy, "FY")
    
    # Calculate quarterly increments
    q1 = ytd["Q1"]
    q2 = (ytd["Q2"] - ytd["Q1"]) if (ytd["Q2"] is not None and ytd["Q1"] is not None) else ytd["Q2"]
    q3 = (ytd["Q3"] - ytd["Q2"]) if (ytd["Q3"] is not None and ytd["Q2"] is not None) else ytd["Q3"]
    
    # Calculate Q4
    if fy_val is not None and None not in (q1, q2, q3):
        q4 = fy_val - (q1 or 0) - (q2 or 0) - (q3 or 0)
    else:
        q4 = pick_val(arr, fy, "Q4")
        if q4 is None and fy_val is not None:
            q4 = fy_val
    
    return dict(Q1=q1, Q2=q2, Q3=q3, Q4=q4, FY=fy_val)

def quarter_instant(usgaap: Dict, tag_list: List[str], fy: int, fq: str) -> Optional[float]:
    """
    Extract instant (point-in-time) value for a specific quarter.
    
    Args:
        usgaap: US-GAAP taxonomy facts
        tag_list: List of possible XBRL tags
        fy: Fiscal year
        fq: Fiscal quarter (Q1, Q2, Q3, Q4)
        
    Returns:
        The value or None
    """
    tag = next((t for t in tag_list if t in usgaap), None)
    if not tag:
        return None
    
    arr, _unit = select_units_prefer_usd(usgaap[tag])
    val = pick_val(arr, fy, fq)
    
    # Fallback: Q4 often reported as FY
    if val is None and fq == "Q4":
        val = pick_val(arr, fy, "FY")
    
    return val

def total_debt(usgaap: Dict, fy: int, fq: str) -> Optional[float]:
    """
    Calculate total debt (short-term + long-term).
    
    Args:
        usgaap: US-GAAP taxonomy facts
        fy: Fiscal year
        fq: Fiscal quarter
        
    Returns:
        Total debt or None
    """
    lt = quarter_instant(usgaap, INSTANT_TAGS["debt_lt_nc"], fy, fq)
    cur = quarter_instant(usgaap, INSTANT_TAGS["debt_lt_cur"], fy, fq)
    st = quarter_instant(usgaap, INSTANT_TAGS["debt_st"], fy, fq)
    
    values = [v for v in [lt, cur, st] if v is not None]
    return sum(values) if values else None

# ============================================================================
# Ticker Mapping
# ============================================================================

def load_ticker_map() -> Dict[str, str]:
    """
    Load official SEC ticker-to-CIK mapping.
    
    Returns:
        Dictionary mapping ticker symbols to zero-padded CIK strings
    """
    logger.info("Loading ticker-to-CIK mapping from SEC...")
    
    try:
        data = GET(TICKERS_URL).json()
        df = pd.DataFrame(list(data.values()))
        
        # Ensure CIK is 10-digit zero-padded string
        df["cik_str"] = df["cik_str"].astype(int).astype(str).str.zfill(10)
        df["ticker"] = df["ticker"].str.upper()
        
        ticker_map = dict(zip(df["ticker"], df["cik_str"]))
        logger.info(f"Loaded {len(ticker_map)} ticker-to-CIK mappings")
        
        return ticker_map
    
    except Exception as e:
        logger.error(f"Failed to load ticker map: {e}")
        raise

# ============================================================================
# Main Data Builder
# ============================================================================

def build_quarterly(
    tickers: List[str],
    start_year: int = 2014,
    end_year: int = 2024,
    usd_only: bool = True
) -> pd.DataFrame:
    """
    Extract quarterly financial data for specified tickers.
    
    This is the main function that orchestrates data extraction from SEC EDGAR
    and calculates comprehensive financial metrics.
    
    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT'])
        start_year: Beginning of data range (inclusive)
        end_year: End of data range (inclusive)
        usd_only: If True, only include USD-denominated filings
        
    Returns:
        DataFrame with columns: ['ticker', 'cik', 'fy', 'fq'] + FEATURES_62 + ['earning_growth']
        
    Example:
        >>> df = build_quarterly(['AAPL', 'MSFT'], start_year=2020, end_year=2023)
        >>> print(df.shape)
        (32, 67)  # 2 companies * 4 years * 4 quarters, 67 columns
    """
    logger.info(f"Starting data extraction for {len(tickers)} tickers ({start_year}-{end_year})")
    
    ticker_map = load_ticker_map()
    rows = []
    
    for idx, ticker in enumerate(tickers, 1):
        logger.info(f"Processing {ticker} ({idx}/{len(tickers)})...")
        
        cik = ticker_map.get(ticker.upper())
        if not cik:
            logger.warning(f"Ticker {ticker} not found in SEC database, skipping")
            continue
        
        try:
            # Fetch company facts
            facts_response = GET(FACTS_URL.format(cik=cik))
            facts = facts_response.json().get("facts", {})
            usgaap = facts.get("us-gaap", {})
            
            # Check for revenue tag to verify USD currency
            rev_tag = next((t for t in DURATION_TAGS["revenue"] if t in usgaap), None)
            rev_arr, rev_unit = select_units_prefer_usd(usgaap[rev_tag]) if rev_tag else ([], None)
            
            # Extract data for each year and quarter
            for fy in range(start_year, end_year + 1):
                # Get all duration metrics (income statement & cash flow)
                duration_data = {
                    key: quarter_increment(usgaap, tags, fy)
                    for key, tags in DURATION_TAGS.items()
                }
                
                for fq in ["Q1", "Q2", "Q3", "Q4"]:
                    # Extract raw metrics
                    revenue = duration_data["revenue"][fq]
                    
                    # Data quality filters
                    if revenue is None or revenue == 0:
                        continue
                    if usd_only and rev_unit != "USD":
                        continue
                    
                    # Build row with all raw financial data
                    row = {
                        "ticker": ticker,
                        "cik": cik,
                        "fy": fy,
                        "fq": fq,
                        "revenue": revenue,
                        "cogs": duration_data["cogs"][fq],
                        "ebit": duration_data["ebit"][fq],
                        "net_income": duration_data["net_income"][fq],
                        "eps_diluted": duration_data["eps_diluted"][fq],
                        "da": duration_data["da"][fq],
                        "tax_expense": duration_data["tax_expense"][fq],
                        "cfo": duration_data["cfo"][fq],
                        "cfi": duration_data["cfi"][fq],
                        "cff": duration_data["cff"][fq],
                        "capex": duration_data["capex"][fq],
                        "interest_exp": duration_data["interest_exp"][fq],
                        "dividends": duration_data["dividends"][fq],
                        "rnd": duration_data["rnd"][fq],
                        "sga": duration_data["sga"][fq],
                        "assets": quarter_instant(usgaap, INSTANT_TAGS["assets"], fy, fq),
                        "assets_current": quarter_instant(usgaap, INSTANT_TAGS["assets_current"], fy, fq),
                        "liabilities_current": quarter_instant(usgaap, INSTANT_TAGS["liabilities_current"], fy, fq),
                        "equity": quarter_instant(usgaap, INSTANT_TAGS["equity"], fy, fq),
                        "cash": quarter_instant(usgaap, INSTANT_TAGS["cash"], fy, fq),
                        "sti": quarter_instant(usgaap, INSTANT_TAGS["sti"], fy, fq),
                        "ar": quarter_instant(usgaap, INSTANT_TAGS["ar"], fy, fq),
                        "ap": quarter_instant(usgaap, INSTANT_TAGS["ap"], fy, fq),
                        "inventory": quarter_instant(usgaap, INSTANT_TAGS["inventory"], fy, fq),
                        "ppe": quarter_instant(usgaap, INSTANT_TAGS["ppe"], fy, fq),
                        "goodwill": quarter_instant(usgaap, INSTANT_TAGS["goodwill"], fy, fq),
                        "intangibles": quarter_instant(usgaap, INSTANT_TAGS["intangibles"], fy, fq),
                        "retained": quarter_instant(usgaap, INSTANT_TAGS["retained"], fy, fq),
                        "deferred_revenue": quarter_instant(usgaap, INSTANT_TAGS["deferred_revenue"], fy, fq),
                        "debt": total_debt(usgaap, fy, fq),
                        "treasury_stock": quarter_instant(usgaap, INSTANT_TAGS["treasury_stock"], fy, fq)
                    }
                    
                    rows.append(row)
        
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue
    
    # Convert to DataFrame
    df = pd.DataFrame(rows)
    
    if df.empty:
        logger.warning("No data extracted. Check ticker symbols and date range.")
        out_cols = ["ticker", "cik", "fy", "fq"] + FEATURES_62 + ["earning_growth"]
        return pd.DataFrame(columns=out_cols)
    
    logger.info(f"Extracted {len(df)} quarterly observations")
    
    # Sort by ticker and date
    df = df.sort_values(["ticker", "fy", "fq"]).reset_index(drop=True)
    
    # Calculate derived metrics
    df = calculate_derived_metrics(df)
    
    # Calculate target variable (earnings growth)
    df["earning_growth"] = (
        df.groupby("ticker")["net_income"]
        .pct_change(fill_method=None)
        .replace([float("inf"), float("-inf")], pd.NA)
        .fillna(0)
    )
    
    # Final data quality check
    df = df[(~df["revenue"].isna()) & (df["revenue"] > 0)].copy()
    
    # Fill remaining NaNs with 0 (except revenue, which is already validated)
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns.tolist()
    numeric_cols_no_rev = [c for c in numeric_cols if c != "revenue"]
    df[numeric_cols_no_rev] = df[numeric_cols_no_rev].fillna(0)
    
    # Select final output columns
    out_cols = ["ticker", "cik", "fy", "fq"] + FEATURES_62 + ["earning_growth"]
    
    logger.info(f"Final dataset: {len(df)} rows, {len(out_cols)} columns")
    
    return df[out_cols]

def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all derived financial metrics.
    
    This function computes 32+ financial ratios from raw accounting data,
    including profitability, liquidity, efficiency, and cash flow metrics.
    
    Args:
        df: DataFrame with raw financial data
        
    Returns:
        DataFrame with added derived metric columns
    """
    logger.info("Calculating derived financial metrics...")
    
    def safe_div(a, b):
        """Safe division handling None and zero."""
        try:
            return (a / b) if (a is not None and b not in (None, 0)) else 0.0
        except (TypeError, ZeroDivisionError):
            return 0.0
    
    # Add lags for turnover calculations (quarter-over-quarter averages)
    for col in ["assets", "inventory", "ar", "ap", "revenue", "cogs", "ppe", "net_income"]:
        df[f"{col}_lag"] = df.groupby("ticker")[col].shift(1)
    
    # Calculate averages
    df["assets_avg"] = (df["assets"] + df["assets_lag"]) / 2
    df["inventory_avg"] = (df["inventory"] + df["inventory_lag"]) / 2
    df["ar_avg"] = (df["ar"] + df["ar_lag"]) / 2
    df["ap_avg"] = (df["ap"] + df["ap_lag"]) / 2
    
    # Profitability Metrics
    df["gross_profit"] = df["revenue"].fillna(0) - df["cogs"].fillna(0)
    df["gross_margin"] = [safe_div(gp, r) for gp, r in zip(df["gross_profit"], df["revenue"])]
    df["op_margin"] = [safe_div(e, r) for e, r in zip(df["ebit"], df["revenue"])]
    df["net_margin"] = [safe_div(n, r) for n, r in zip(df["net_income"], df["revenue"])]
    df["ebitda"] = df["ebit"].fillna(0) + df["da"].fillna(0)
    df["ebitda_margin"] = [safe_div(e, r) for e, r in zip(df["ebitda"], df["revenue"])]
    df["eff_tax_rate"] = [safe_div(t, e) for t, e in zip(df["tax_expense"], df["ebit"])]
    df["roe"] = [safe_div(ni, e) for ni, e in zip(df["net_income"], df["equity"])]
    df["sga_margin"] = [safe_div(s, r) for s, r in zip(df["sga"], df["revenue"])]
    df["rnd_margin"] = [safe_div(r, rev) for r, rev in zip(df["rnd"], df["revenue"])]
    
    # Liquidity Metrics
    df["current_ratio"] = [safe_div(ca, cl) for ca, cl in zip(df["assets_current"], df["liabilities_current"])]
    df["quick_ratio"] = [
        safe_div((c or 0) + (s or 0) + (a or 0), l)
        for c, s, a, l in zip(df["cash"], df["sti"], df["ar"], df["liabilities_current"])
    ]
    df["cash_ratio"] = [safe_div(c, l) for c, l in zip(df["cash"], df["liabilities_current"])]
    df["working_capital"] = df["assets_current"].fillna(0) - df["liabilities_current"].fillna(0)
    
    # Leverage Metrics
    df["debt_to_equity"] = [safe_div(d, e) for d, e in zip(df["debt"], df["equity"])]
    df["equity_multiplier"] = [safe_div(a, e) for a, e in zip(df["assets"], df["equity"])]
    
    # Efficiency Metrics
    df["asset_turnover"] = [safe_div(r, avg) for r, avg in zip(df["revenue"], df["assets_avg"])]
    df["inventory_turnover"] = [safe_div(c, avg) for c, avg in zip(df["cogs"], df["inventory_avg"])]
    df["receivables_turnover"] = [safe_div(r, avg) for r, avg in zip(df["revenue"], df["ar_avg"])]
    df["payables_turnover"] = [safe_div(c, avg) for c, avg in zip(df["cogs"], df["ap_avg"])]
    
    # Working Capital Cycle (approximating 1 quarter = 90 days)
    df["dio"] = [safe_div(90.0, it) for it in df["inventory_turnover"]]
    df["dso"] = [safe_div(90.0, rt) for rt in df["receivables_turnover"]]
    df["dpo"] = [safe_div(90.0, pt) for pt in df["payables_turnover"]]
    df["ccc"] = df["dio"] + df["dso"] - df["dpo"]
    
    # Cash Flow Metrics
    df["fcf"] = df["cfo"].fillna(0) - df["capex"].fillna(0)
    df["cfo_margin"] = [safe_div(c, r) for c, r in zip(df["cfo"], df["revenue"])]
    df["fcf_margin"] = [safe_div(f, r) for f, r in zip(df["fcf"], df["revenue"])]
    df["ocf_ratio"] = [safe_div(cfo, r) for cfo, r in zip(df["cfo"], df["revenue"])]
    df["cf_to_ni"] = [safe_div(cfo, ni) for cfo, ni in zip(df["cfo"], df["net_income"])]
    
    # Balance Sheet Composition
    df["ppe_to_assets"] = [safe_div(p, a) for p, a in zip(df["ppe"], df["assets"])]
    df["goodwill_to_assets"] = [safe_div(g, a) for g, a in zip(df["goodwill"], df["assets"])]
    df["intang_to_assets"] = [safe_div(i, a) for i, a in zip(df["intangibles"], df["assets"])]
    df["cash_to_assets"] = [safe_div(c, a) for c, a in zip(df["cash"], df["assets"])]
    df["curr_assets_to_assets"] = [safe_div(ca, a) for ca, a in zip(df["assets_current"], df["assets"])]
    df["retained_to_assets"] = [safe_div(re, a) for re, a in zip(df["retained"], df["assets"])]
    df["tangible_book"] = df["equity"].fillna(0) - df["goodwill"].fillna(0) - df["intangibles"].fillna(0)
    df["tangible_book_to_assets"] = [safe_div(tb, a) for tb, a in zip(df["tangible_book"], df["assets"])]
    
    # Growth Metrics
    df["sales_growth"] = (
        df.groupby("ticker")["revenue"]
        .pct_change(fill_method=None)
        .replace([float("inf"), float("-inf")], pd.NA)
        .fillna(0)
    )
    
    logger.info("Derived metrics calculation complete")
    
    return df

# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    # Sample tickers (S&P 500 subset)
    SAMPLE_TICKERS = [
        "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "BAC", "WFC",
        "V", "MA", "KO", "PEP", "PG", "CSCO", "ORCL", "INTC", "T", "VZ",
        "CMCSA", "PFE", "MRK", "WMT", "HD", "COST", "DIS", "NKE", "CAT", "MCD",
        "UNH", "ABBV", "CVX", "XOM", "BA", "IBM", "ADBE", "NFLX", "CRM", "TXN",
        "QCOM", "AVGO", "UPS", "FDX", "LMT", "GM", "F", "GE", "MMM", "HON",
        "UNP", "MDT", "DHR", "AMGN", "EL", "SBUX", "BK", "BLK", "TGT", "LOW",
        "DE", "MS", "C", "GS", "USB", "AXP", "PLD", "O", "SPG", "CB",
        "AIG", "MET", "HUM", "CI", "INTU", "MU", "AMD", "KLAC"
    ]
    
    logger.info("=" * 80)
    logger.info("SEC Financial Data Extractor & Earnings Growth Analyzer")
    logger.info("=" * 80)
    
    # Extract data
    df_output = build_quarterly(
        tickers=SAMPLE_TICKERS,
        start_year=2014,
        end_year=2024,
        usd_only=True
    )
    
    # Display summary
    logger.info(f"\nDataset Summary:")
    logger.info(f"  Total Rows: {len(df_output)}")
    logger.info(f"  Unique Tickers: {df_output['ticker'].nunique()}")
    logger.info(f"  Date Range: {df_output['fy'].min()}-{df_output['fy'].max()}")
    logger.info(f"  Total Columns: {len(df_output.columns)}")
    
    # Display sample
    print("\n" + "=" * 80)
    print("Sample Data (First 5 Rows)")
    print("=" * 80)
    print(df_output.head().to_string())
    
    # Save to CSV
    output_file = "sec_quarterly_raw_data.csv"
    df_output.to_csv(output_file, index=False)
    logger.info(f"\nData saved to: {output_file}")
    
    logger.info("\nExecution complete!")
