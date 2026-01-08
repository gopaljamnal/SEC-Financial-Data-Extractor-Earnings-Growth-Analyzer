# Methodology: SEC Financial Data Extraction & Earnings Growth Analysis

## Table of Contents
1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [Extraction Pipeline](#extraction-pipeline)
4. [Metric Calculations](#metric-calculations)
5. [Data Quality & Edge Cases](#data-quality--edge-cases)
6. [Limitations](#limitations)

---

## Overview

This document details the quantitative methodology used to extract quarterly financial data from SEC EDGAR XBRL filings and calculate earnings growth metrics for U.S. publicly-traded companies.

**Primary Objective**: Build a systematic dataset for fundamental analysis and earnings growth modeling.

**Target Use Case**: Quantitative investment research, factor modeling, and earnings surprise prediction.

---

## Data Sources

### SEC EDGAR API
- **Endpoint**: `https://data.sec.gov/api/xbrl/companyfacts/`
- **Format**: JSON (XBRL taxonomy facts)
- **Coverage**: 10-Q and 10-K filings
- **Update Frequency**: Real-time (as companies file)

### Ticker-to-CIK Mapping
- **Source**: `https://www.sec.gov/files/company_tickers.json`
- **Purpose**: Convert stock tickers to SEC Central Index Key (CIK) identifiers

### Compliance
- **User-Agent Header**: Required (name + email)
- **Rate Limit**: 9 requests/second (below 10/sec SEC threshold)
- **Timeout**: 30 seconds per request

---

## Extraction Pipeline

### Step 1: Ticker-to-CIK Resolution
```python
Load official SEC ticker mapping → Convert to zero-padded 10-digit CIK
Example: AAPL → 0000320193
```

### Step 2: XBRL Fact Retrieval
For each company:
1. Request company-specific facts via CIK
2. Parse `us-gaap` taxonomy (U.S. Generally Accepted Accounting Principles)
3. Extract facts for duration (income statement, cash flow) and instant (balance sheet) tags

### Step 3: Quarterly Decomposition
**Challenge**: SEC filings report Year-to-Date (YTD) values, not quarterly increments.

**Solution**: Derive quarterly values through subtraction:
```
Q1 = Q1_YTD
Q2 = Q2_YTD - Q1_YTD
Q3 = Q3_YTD - Q2_YTD
Q4 = FY - (Q1 + Q2 + Q3)
```

**Example** (Revenue):
- Q1 YTD: $10M → Q1 = $10M
- Q2 YTD: $25M → Q2 = $25M - $10M = $15M
- Q3 YTD: $45M → Q3 = $45M - $25M = $20M
- FY: $70M → Q4 = $70M - ($10M + $15M + $20M) = $25M

### Step 4: Unit Standardization
- **Currency Filter**: `usd_only=True` enforces USD reporting
- **Rationale**: Avoids foreign exchange complications for multinational companies
- **Consequence**: Excludes foreign filers (Canadian, European companies)

### Step 5: Tag Selection
**Multiple XBRL tags** may represent the same concept (e.g., revenue):
- `RevenueFromContractWithCustomerExcludingAssessedTax`
- `SalesRevenueNet`

**Strategy**: Use hierarchical fallback logic (preferred tag → alternative tag).

---

## Metric Calculations

### Raw Financial Data (30 metrics)
Extracted directly from XBRL facts:
- **Income Statement**: Revenue, COGS, EBIT, Net Income, EPS, D&A, Tax Expense, Interest Expense, R&D, SG&A, Dividends
- **Cash Flow Statement**: Operating CF, Investing CF, Financing CF, CapEx
- **Balance Sheet**: Assets, Current Assets/Liabilities, Equity, Cash, Marketable Securities, AR, AP, Inventory, PPE, Goodwill, Intangibles, Retained Earnings, Deferred Revenue

### Derived Metrics (32+ ratios)

#### 1. Profitability Ratios
```
Gross Profit = Revenue - COGS
Gross Margin = Gross Profit / Revenue

Operating Margin = EBIT / Revenue
Net Margin = Net Income / Revenue

EBITDA = EBIT + Depreciation & Amortization
EBITDA Margin = EBITDA / Revenue

Effective Tax Rate = Tax Expense / EBIT
ROE = Net Income / Equity
```

#### 2. Liquidity Ratios
```
Current Ratio = Current Assets / Current Liabilities
Quick Ratio = (Cash + Marketable Securities + AR) / Current Liabilities
Cash Ratio = Cash / Current Liabilities
Working Capital = Current Assets - Current Liabilities
```

#### 3. Leverage Ratios
```
Total Debt = Long-Term Debt (Non-Current) + Long-Term Debt (Current) + Short-Term Borrowings
Debt-to-Equity = Total Debt / Equity
Equity Multiplier = Assets / Equity
```

#### 4. Efficiency Ratios
**Turnover Calculations** (using quarter-over-quarter averages):
```
Assets_avg = (Assets_t + Assets_t-1) / 2
Asset Turnover = Revenue / Assets_avg

Inventory Turnover = COGS / Inventory_avg
Receivables Turnover = Revenue / AR_avg
Payables Turnover = COGS / AP_avg
```

**Working Capital Cycle** (approximating 1 quarter = 90 days):
```
DIO (Days Inventory Outstanding) = 90 / Inventory Turnover
DSO (Days Sales Outstanding) = 90 / Receivables Turnover
DPO (Days Payable Outstanding) = 90 / Payables Turnover

Cash Conversion Cycle = DIO + DSO - DPO
```

**Interpretation**:
- Lower CCC = More efficient working capital management
- Negative CCC = Company receives cash before paying suppliers (e.g., Amazon, Apple)

#### 5. Cash Flow Metrics
```
Free Cash Flow (FCF) = Operating CF - CapEx
FCF Margin = FCF / Revenue
CFO Margin = Operating CF / Revenue

Cash Flow to Net Income = Operating CF / Net Income
OCF Ratio = Operating CF / Revenue
```

**Earnings Quality Indicator**: CF/NI Ratio > 1.0 suggests high-quality earnings backed by cash generation.

#### 6. Balance Sheet Composition
```
PPE-to-Assets = PPE / Assets  (capital intensity)
Goodwill-to-Assets = Goodwill / Assets  (acquisition history)
Intangibles-to-Assets = Intangibles / Assets
Cash-to-Assets = Cash / Assets  (liquidity cushion)
Tangible Book Value = Equity - Goodwill - Intangibles
```

### Target Variable: Earnings Growth
```
Earnings Growth (QoQ) = (Net Income_t - Net Income_t-1) / Net Income_t-1
```

**Implementation Details**:
- Grouping: By ticker (company-specific sequential quarters)
- Missing Data: Infinite values (division by zero) replaced with 0
- First quarter per company: Growth = 0 (no prior quarter for comparison)

---

## Data Quality & Edge Cases

### Quality Filters
1. **Revenue Validation**: 
   - Drop rows where `revenue IS NULL` or `revenue = 0`
   - Rationale: Invalid/incomplete filings

2. **Currency Enforcement**:
   - When `usd_only=True`, reject non-USD filings
   - Identified via XBRL unit metadata

3. **Missing Data Handling**:
   - Balance sheet items: Use `None` if unavailable
   - Derived ratios: Return 0.0 for divisions by zero/None
   - Turnover ratios: Require prior quarter data (first quarter per company excluded from some metrics)

### Edge Cases Handled

#### 1. One-Time Charges & Restructuring
**Problem**: Negative net income can cause misleading growth calculations.

**Example**:
- Q1 Net Income: -$500M (restructuring charge)
- Q2 Net Income: $100M
- Naive Growth: (-500 → 100) / -500 = -120% (misleading)

**Current Approach**: Report raw calculation; users can winsorize or filter extreme values.

**Future Enhancement**: Flag quarters with abnormal items (search for keywords in 10-Q/K text).

#### 2. Fiscal Year Misalignment
**Problem**: Some companies have non-calendar fiscal years (e.g., Walmart: FY ends Jan 31).

**Handling**: 
- Data stored by fiscal year (FY) + fiscal quarter (FQ)
- Users should be aware when comparing across companies

#### 3. M&A Activity
**Problem**: Acquisitions distort quarter-over-quarter comparisons.

**Example**:
- Company A acquires Company B mid-Q2
- Q2 revenue jumps 150% (partly inorganic)

**Limitation**: No automatic detection of M&A; users should cross-reference with 8-K filings.

#### 4. Stock Splits
**Problem**: EPS values can appear distorted post-split.

**Handling**: SEC data is retroactively adjusted; no manual intervention needed.

---

## Limitations

### 1. XBRL Tag Variability
- Companies use different tag combinations
- Some use custom extensions not in `us-gaap` taxonomy
- **Mitigation**: Use multi-tag fallback logic

### 2. Delayed Filings
- 10-Q deadline: 40-45 days after quarter-end (large accelerated filers)
- Real-time earnings data requires alternative sources (press releases, Bloomberg)

### 3. International Standards
- Non-U.S. companies use IFRS (different taxonomy)
- Foreign filings on SEC (e.g., Form 20-F) not currently supported

### 4. Non-GAAP Adjustments
- Companies report non-GAAP earnings (exclude one-time items)
- This tool uses GAAP figures only
- **Future Enhancement**: Parse MD&A section for non-GAAP reconciliations

### 5. Industry-Specific Metrics
- Missing sector-specific KPIs:
  - Retail: Same-store sales
  - Banking: Net Interest Margin, Loan Loss Provisions
  - Insurance: Combined Ratio
- **Enhancement Opportunity**: Add industry overlays

---

## Validation & Quality Checks

### Cross-Verification
Spot-check against public sources:
1. **Yahoo Finance**: Quarterly revenue, EPS
2. **SEC.gov**: Direct 10-Q/10-K viewing
3. **Bloomberg Terminal**: If available

### Statistical Sanity Checks
- Margins should be bounded: 0% ≤ Gross Margin ≤ 100%
- Current ratio typically: 0.5 - 3.0 (extreme values warrant investigation)
- Debt-to-Equity: Industry-specific norms (utilities high, tech low)

---

## Future Enhancements

1. **Sentiment Analysis**: Parse MD&A text for management tone
2. **Analyst Estimates Integration**: Calculate earnings surprises
3. **Peer Benchmarking**: Automatic sector classification + percentile rankings
4. **Real-Time Alerts**: Monitor filing timestamps + alert on new 10-Qs
5. **Machine Learning**: Predict next-quarter earnings based on historical patterns
6. **Custom Taxonomy Support**: Handle company-specific XBRL extensions

---

## References

- [SEC EDGAR API Specification](https://www.sec.gov/edgar/sec-api-documentation)
- [XBRL US GAAP Taxonomy](https://xbrl.us/xbrl-taxonomy/2023-us-gaap/)
- [Financial Ratio Formulas](https://www.investopedia.com/financial-ratios-4689817)
- [Accounting Research Manager (ARM)](https://dart.deloitte.com/USDART/home)

---

**Author**: Gopal Jamnal  
**Contact**: gopal.jamnal@gmail.com  
**Last Updated**: January 2026
