import os, time, requests, pandas as pd
# from sklearn.preprocessing import StandardScaler # Removed as regularization is no longer needed

# ============ SEC fair-access configuration ============
USER_AGENT = os.environ.get("Gopal Jamnal", "gopal.jamnal@gmail.com")  # <-- REQUIRED: set this
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}
REQS_PER_SEC = 9.0  # stay under 10/sec per SEC guidance

def throttle(): time.sleep(1.0 / REQS_PER_SEC)
def GET(url):
    throttle()
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r

# ============ SEC endpoints ============
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL   = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# ============ Ticker → CIK (official SEC JSON) ============
def load_ticker_map():
    data = GET(TICKERS_URL).json()
    df = pd.DataFrame(list(data.values()))
    df["cik_str"] = df["cik_str"].astype(int).astype(str).str.zfill(10)
    df["ticker"]  = df["ticker"].str.upper()
    return dict(zip(df["ticker"], df["cik_str"]))

# ============ Tag sets ============
DURATION = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "cogs": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "ebit": ["OperatingIncomeLoss", "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"],
    "net_income": ["NetIncomeLoss"],
    "eps_diluted": ["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"],
    "da": ["DepreciationDepletionAndAmortization"],
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

INSTANT = {
    "assets": ["Assets"],
    "assets_current": ["AssetsCurrent"],
    "liabilities_current": ["LiabilitiesCurrent"],
    "equity": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "StockholdersEquity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "sti": ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesCurrent"],
    "ar": ["AccountsReceivableNetCurrent"],
    "ap": ["AccountsPayableCurrent"],
    "inventory": ["InventoryNet"],
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

# Keep 62 features + target (moved to global scope for reuse)
FEATURES_62 = [
    # 30 raw
    "revenue","cogs","ebit","net_income","eps_diluted","da","tax_expense","cfo","cfi","cff",
    "capex","interest_exp","dividends","rnd","sga","ppe","goodwill","intangibles","assets",
    "assets_current","liabilities_current","equity","cash","sti","ar","ap","inventory","debt",
    "retained","deferred_revenue","treasury_stock",
    # 32 derived (now more with new additions)
    "gross_profit","gross_margin","op_margin","net_margin","ebitda","ebitda_margin","eff_tax_rate",
    "current_ratio","quick_ratio","cash_ratio","debt_to_equity","asset_turnover","inventory_turnover",
    "receivables_turnover","payables_turnover","dio","dso","dpo","ccc","fcf","fcf_margin","cfo_margin",
    "ppe_to_assets","goodwill_to_assets","intang_to_assets","cash_to_assets",
    "curr_assets_to_assets","retained_to_assets","equity_multiplier","tangible_book",
    "tangible_book_to_assets","sales_growth",
    # New derived metrics
    "working_capital", "sga_margin", "rnd_margin", "roe", "ocf_ratio", "cf_to_ni"
]

# ============ XBRL helpers ============
def select_units_prefer_usd(fact):
    if not isinstance(fact, dict) or "units" not in fact:
        return [], None
    units = fact["units"]
    if "USD" in units:
        return units["USD"], "USD"
    for u, arr in units.items():
        return arr, u
    return [], None

def pick_val(arr, fy, fp):
    cand = [x for x in arr if str(x.get("fy")) == str(fy) and x.get("fp") == fp]
    if not cand: return None
    cand = sorted(cand, key=lambda x: (x.get("end","",), x.get("val", 0)))
    return cand[-1].get("val")

def quarter_increment(usgaap, tag_list, fy):
    tag = next((t for t in tag_list if t in usgaap), None)
    if not tag: return {q: None for q in ["Q1","Q2","Q3","Q4","FY"]}
    arr, _unit = select_units_prefer_usd(usgaap[tag])
    ytd = {q: pick_val(arr, fy, q) for q in ["Q1","Q2","Q3"]}
    fy_v = pick_val(arr, fy, "FY")
    q1 = ytd["Q1"]
    q2 = (ytd["Q2"] - ytd["Q1"]) if (ytd["Q2"] is not None and ytd["Q1"] is not None) else ytd["Q2"]
    q3 = (ytd["Q3"] - ytd["Q2"]) if (ytd["Q3"] is not None and ytd["Q2"] is not None) else ytd["Q3"]
    if fy_v is not None and None not in (q1, q2, q3):
        q4 = fy_v - (q1 or 0) - (q2 or 0) - (q3 or 0)
    else:
        q4 = pick_val(arr, fy, "Q4")
        if q4 is None and fy_v is not None:
            q4 = fy_v
    return dict(Q1=q1, Q2=q2, Q3=q3, Q4=q4, FY=fy_v)

def quarter_instant(usgaap, tag_list, fy, fq):
    tag = next((t for t in tag_list if t in usgaap), None)
    if not tag: return None
    arr, _unit = select_units_prefer_usd(usgaap[tag])
    v = pick_val(arr, fy, fq)
    if v is None and fq == "Q4":
        v = pick_val(arr, fy, "FY")
    return v

def total_debt(usgaap, fy, fq):
    lt  = quarter_instant(usgaap, INSTANT["debt_lt_nc"], fy, fq)
    cur = quarter_instant(usgaap, INSTANT["debt_lt_cur"], fy, fq)
    st  = quarter_instant(usgaap, INSTANT["debt_st"], fy, fq)
    vals = [v for v in [lt, cur, st] if v is not None]
    return sum(vals) if vals else None

# ============ Builder ============
def build_quarterly(tickers, start_year=2014, end_year=2024, usd_only=True):
    tmap = load_ticker_map()
    rows = []
    for tk in tickers:
        cik = tmap.get(tk.upper())
        if not cik: continue
        facts = GET(FACTS_URL.format(cik=cik)).json().get("facts", {})
        usgaap = facts.get("us-gaap", {})

        rev_tag = next((t for t in DURATION["revenue"] if t in usgaap), None)
        rev_arr, rev_unit = select_units_prefer_usd(usgaap[rev_tag]) if rev_tag else ([], None)

        for fy in range(start_year, end_year+1):
            dur = {k: quarter_increment(usgaap, v, fy) for k, v in DURATION.items()}
            for fq in ["Q1","Q2","Q3","Q4"]:
                # duration
                R   = dur["revenue"][fq]
                COGS= dur["cogs"][fq]
                EBIT= dur["ebit"][fq]
                NI  = dur["net_income"][fq]
                EPS = dur["eps_diluted"][fq]
                DA  = dur["da"][fq]
                TAX = dur["tax_expense"][fq]
                CFO = dur["cfo"][fq]
                CFI = dur["cfi"][fq]
                CFF = dur["cff"][fq]
                CAPEX = dur["capex"][fq]
                INTEXP= dur["interest_exp"][fq]
                DIV  = dur["dividends"][fq]
                RND  = dur["rnd"][fq]
                SGA  = dur["sga"][fq]
                # instant
                A   = quarter_instant(usgaap, INSTANT["assets"], fy, fq)
                CA  = quarter_instant(usgaap, INSTANT["assets_current"], fy, fq)
                CL  = quarter_instant(usgaap, INSTANT["liabilities_current"], fy, fq)
                E   = quarter_instant(usgaap, INSTANT["equity"], fy, fq)
                CASH= quarter_instant(usgaap, INSTANT["cash"], fy, fq)
                STI = quarter_instant(usgaap, INSTANT["sti"], fy, fq)
                AR  = quarter_instant(usgaap, INSTANT["ar"], fy, fq)
                AP  = quarter_instant(usgaap, INSTANT["ap"], fy, fq)
                INV = quarter_instant(usgaap, INSTANT["inventory"], fy, fq)
                PPE = quarter_instant(usgaap, INSTANT["ppe"], fy, fq)
                GW  = quarter_instant(usgaap, INSTANT["goodwill"], fy, fq)
                INTANG = quarter_instant(usgaap, INSTANT["intangibles"], fy, fq)
                RETE   = quarter_instant(usgaap, INSTANT["retained"], fy, fq)
                DEFREV = quarter_instant(usgaap, INSTANT["deferred_revenue"], fy, fq)
                DEBT   = total_debt(usgaap, fy, fq)
                TRSY_STK = quarter_instant(usgaap, INSTANT["treasury_stock"], fy, fq)

                # enforce revenue constraints: must be present, >0, and (optionally) USD
                if R is None or R == 0:
                    continue
                if usd_only and rev_unit != "USD":
                    continue

                row = dict(ticker=tk, cik=cik, fy=fy, fq=fq,
                           revenue=R, cogs=COGS, ebit=EBIT, net_income=NI, eps_diluted=EPS,
                           da=DA, tax_expense=TAX, cfo=CFO, cfi=CFI, cff=CFF, capex=CAPEX,
                           interest_exp=INTEXP, dividends=DIV, rnd=RND, sga=SGA,
                           assets=A, assets_current=CA, liabilities_current=CL, equity=E,
                           cash=CASH, sti=STI, ar=AR, ap=AP, inventory=INV, ppe=PPE,
                           goodwill=GW, intangibles=INTANG, retained=RETE,
                           deferred_revenue=DEFREV, debt=DEBT, treasury_stock=TRSY_STK)
                rows.append(row)

    df = pd.DataFrame(rows)

    # Handle case where no data meets strict criteria, resulting in an empty DataFrame
    if df.empty:
        out_cols = ["ticker","cik","fy","fq"] + FEATURES_62 + ["earning_growth"]
        return pd.DataFrame(columns=out_cols)

    df = df.sort_values(["ticker","fy","fq"]).reset_index(drop=True)

    # add lags for turnover (quarter ~ 90 days)
    for col in ["assets","inventory","ar","ap","revenue","cogs","ppe","net_income"]:
        df[f"{col}_lag"] = df.groupby("ticker")[col].shift(1)

    df["assets_avg"]    = (df["assets"]    + df["assets_lag"])    / 2
    df["inventory_avg"] = (df["inventory"] + df["inventory_lag"]) / 2
    df["ar_avg"]        = (df["ar"]        + df["ar_lag"])        / 2
    df["ap_avg"]        = (df["ap"]        + df["ap_lag"])        / 2

    def safe_div(a,b):
        try:
            return (a/b) if (a is not None and b not in (None,0)) else 0.0
        except Exception:
            return 0.0

    # derived
    df["gross_profit"]   = df["revenue"].fillna(0) - df["cogs"].fillna(0)
    df["gross_margin"]   = [safe_div(gp, r) for gp, r in zip(df["gross_profit"], df["revenue"])]
    df["op_margin"]      = [safe_div(e, r)  for e, r in zip(df["ebit"], df["revenue"])]
    df["net_margin"]     = [safe_div(n, r)  for n, r in zip(df["net_income"], df["revenue"])]
    df["ebitda"]         = df["ebit"].fillna(0) + df["da"].fillna(0)
    df["ebitda_margin"]  = [safe_div(e, r)  for e, r in zip(df["ebitda"], df["revenue"])]
    df["eff_tax_rate"]   = [safe_div(t, e if e else None) for t, e in zip(df["tax_expense"], df["ebit"])]
    df["current_ratio"]  = [safe_div(ca, cl) for ca, cl in zip(df["assets_current"], df["liabilities_current"])]
    df["quick_ratio"]    = [safe_div((c or 0)+(s or 0)+(a or 0), l)
                            for c,s,a,l in zip(df["cash"], df["sti"], df["ar"], df["liabilities_current"])]
    df["cash_ratio"]     = [safe_div(c, l) for c,l in zip(df["cash"], df["liabilities_current"])]
    df["debt_to_equity"] = [safe_div(d, e) for d,e in zip(df["debt"], df["equity"])]
    df["asset_turnover"]       = [safe_div(r, avg) for r,avg in zip(df["revenue"], df["assets_avg"])]
    df["inventory_turnover"]   = [safe_div(c, avg) for c,avg in zip(df["cogs"], df["inventory_avg"])]
    df["receivables_turnover"] = [safe_div(r, avg) for r,avg in zip(df["revenue"], df["ar_avg"])]
    df["payables_turnover"]    = [safe_div(c, avg) for c,avg in zip(df["cogs"], df["ap_avg"])]
    df["dio"] = [safe_div(90.0, it) for it in df["inventory_turnover"]]     # quarter ≈ 90 days
    df["dso"] = [safe_div(90.0, rt) for rt in df["receivables_turnover"]]
    df["dpo"] = [safe_div(90.0, pt) for pt in df["payables_turnover"]]
    df["ccc"] = df["dio"] + df["dso"] - df["dpo"]
    df["fcf"] = df["cfo"].fillna(0) - df["capex"].fillna(0)
    df["cfo_margin"] = [safe_div(c, r) for c,r in zip(df["cfo"], df["revenue"])]
    df["fcf_margin"] = [safe_div(f, r) for f,r in zip(df["fcf"], df["revenue"])]
    df["ppe_to_assets"]       = [safe_div(p,a) for p,a in zip(df["ppe"], df["assets"])]
    df["goodwill_to_assets"]  = [safe_div(g,a) for g,a in zip(df["goodwill"], df["assets"])]
    df["intang_to_assets"]    = [safe_div(i,a) for i,a in zip(df["intangibles"], df["assets"])]
    df["cash_to_assets"]      = [safe_div(c,a) for c,a in zip(df["cash"], df["assets"])]
    df["curr_assets_to_assets"]= [safe_div(ca,a) for ca,a in zip(df["assets_current"], df["assets"])]
    df["retained_to_assets"]  = [safe_div(re,a) for re,a in zip(df["retained"], df["assets"])]
    df["equity_multiplier"]   = [safe_div(a,e) for a,e in zip(df["assets"], df["equity"])]
    df["tangible_book"]       = df["equity"].fillna(0) - df["goodwill"].fillna(0) - df["intangibles"].fillna(0)
    df["tangible_book_to_assets"] = [safe_div(tb,a) for tb,a in zip(df["tangible_book"], df["assets"])]

    # New Derived Metrics:
    df["working_capital"] = df["assets_current"].fillna(0) - df["liabilities_current"].fillna(0)
    df["sga_margin"]      = [safe_div(s, r) for s, r in zip(df["sga"], df["revenue"])]
    df["rnd_margin"]      = [safe_div(r, rev) for r, rev in zip(df["rnd"], df["revenue"])]
    df["roe"]             = [safe_div(ni, e) for ni, e in zip(df["net_income"], df["equity"])]
    df["ocf_ratio"]       = [safe_div(cfo, r) for cfo, r in zip(df["cfo"], df["revenue"])]
    df["cf_to_ni"]        = [safe_div(cfo, ni) for cfo, ni in zip(df["cfo"], df["net_income"])]

    # QoQ growth (net income)
    df["earning_growth"] = df.groupby("ticker")["net_income"].pct_change(fill_method=None).replace([float("inf"), float("-inf")], pd.NA).fillna(0)

    # Calculate QoQ sales growth
    df["sales_growth"] = df.groupby("ticker")["revenue"].pct_change(fill_method=None).replace([float("inf"), float("-inf")], pd.NA).fillna(0)

    # STRICT: revenue must be real and >0 (already enforced above); drop rows if somehow violated
    df = df[(~df["revenue"].isna()) & (df["revenue"] > 0)].copy()

    # Fill remaining numeric NaNs with 0 (do NOT touch revenue)
    numeric_cols = df.select_dtypes(include=["float","int"]).columns.tolist()
    numeric_cols_no_rev = [c for c in numeric_cols if c not in ["revenue"]]
    df[numeric_cols_no_rev] = df[numeric_cols_no_rev].fillna(0)

    out_cols = ["ticker","cik","fy","fq"] + FEATURES_62 + ["earning_growth"]
    return df[out_cols]

# ============ Imputation Function ============ # Removed
# def impute_data(df_input):
#     df_cleaned = df_input.copy()
#     id_cols = ['ticker', 'cik', 'fy', 'fq']
#     numeric_cols_for_imputation = [col for col in df_cleaned.select_dtypes(include=['float64', 'int64']).columns if col not in id_cols]

#     for col in numeric_cols_for_imputation:
#         non_zero_non_na_values = df_cleaned[col][(df_cleaned[col] != 0) & (df_cleaned[col].notna())]
#         if not non_zero_non_na_values.empty:
#             col_mean = non_zero_non_na_values.mean()
#             df_cleaned[col] = df_cleaned[col].replace(0, col_mean)
#             df_cleaned[col] = df_cleaned[col].fillna(col_mean)
#         else:
#             df_cleaned[col] = df_cleaned[col].fillna(0)
#     return df_cleaned

# ============ Regularization Function ============ # Removed
# def regularize_data(df, target_column='earning_growth', id_columns=['ticker', 'cik', 'fy', 'fq'], scaler_model=None):
#     if scaler_model is None:
#         scaler_model = StandardScaler()

#     df_copy = df.copy()
#     cols_to_exclude_from_scaling = [col for col in id_columns + [target_column] if col in df_copy.columns]
#     features_to_scale_df = df_copy.drop(columns=cols_to_exclude_from_scaling, errors='ignore')
#     non_numeric_features_df = features_to_scale_df.select_dtypes(exclude=['number'])
#     numeric_features_to_scale = features_to_scale_df.select_dtypes(include=['number']).columns

#     if numeric_features_to_scale.empty:
#         print("No numeric features found for scaling.")
#         return df_copy, scaler_model

#     scaled_features_array = scaler_model.fit_transform(df_copy[numeric_features_to_scale])
#     scaled_features_df = pd.DataFrame(scaled_features_array, columns=numeric_features_to_scale, index=df_copy.index)
#     df_scaled = pd.concat([df_copy[cols_to_exclude_from_scaling], scaled_features_df], axis=1)

#     if not non_numeric_features_df.empty:
#         df_scaled = pd.concat([df_scaled, non_numeric_features_df], axis=1)

#     return df_scaled, scaler_model

# ============ Main Execution ============

# 1. Data Loading
sample_tickers = [
    "AAPL","MSFT","AMZN","GOOGL","META","TSLA","NVDA","JPM","BAC","WFC","V","MA","KO","PEP","PG",
    "CSCO","ORCL","INTC","T","VZ","CMCSA","PFE","MRK","WMT","HD","COST","DIS","NKE","CAT","MCD",
    "UNH","ABBV","CVX","XOM","BA","IBM","ADBE","NFLX","CRM","TXN","QCOM","AVGO","UPS","FDX","LMT",
    "GM","F","GE","MMM","HON","UNP","MDT","DHR","AMGN","EL","SBUX","BK","BLK","TGT","LOW","DE",
    "MS","C","GS","USB","AXP","PLD","O","SPG","CB","AIG","MET","HUM","CI","INTU","MU","AMD","KLAC"
]
df_out = build_quarterly(sample_tickers, start_year=2014, end_year=2024, usd_only=True)
print(f"Initial DataFrame `df_out` Rows: {len(df_out)}  |  Tickers: {df_out['ticker'].nunique()}")

# 2. Impute Zeros and Nulls # Removed
# df_cleaned = impute_data(df_out)
# print(f"Cleaned DataFrame `df_cleaned` Rows: {len(df_cleaned)}")

# 3. Regularize Data # Removed
# df_regularized, scaler = regularize_data(df_cleaned.copy())
# print(f"Regularized DataFrame `df_regularized` Rows: {len(df_regularized)}")

print("\nFirst 5 rows of the Raw DataFrame:")
display(df_out.head())

# Save raw dataframe to CSV
df_out.to_csv("sec_quarterly_raw_data.csv", index=False)
print("Saved: sec_quarterly_raw_data.csv")
# Removed saving of imputed and regularized data
# df_regularized.to_csv("sec_quarterly_imputed_regularized_data.csv", index=False)
# print("Saved: sec_quarterly_imputed_regularized_data.csv")
