# SEC Financial Data Extractor & Earnings Growth Analyzer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Quantitative Finance Tool for Systematic Fundamental Analysis**

A production-ready Python framework for extracting, processing, and analyzing quarterly financial data from SEC EDGAR XBRL filings (10-Q/10-K). Designed for quantitative researchers to build earnings growth models and identify investment signals.

🔗 **[Live Dashboard](your-streamlit-url-here)** | 📊 **[Sample Analysis](link-to-notebook)**

---

## 🎯 Key Features

- **Automated SEC EDGAR Data Extraction**: Direct API integration with SEC's XBRL database
- **62+ Financial Metrics**: Income statement, balance sheet, cash flow, and derived ratios
- **Quarterly Earnings Growth Calculation**: QoQ growth rates with robust handling of edge cases
- **Multi-Company Analysis**: Batch processing of 75+ S&P 500 companies
- **Production-Ready Code**: Rate limiting, error handling, and SEC compliance built-in
- **Quality Metrics**: Earnings quality indicators (cash flow vs. net income, accruals)
- **Turnover Ratios**: DIO, DSO, DPO, and Cash Conversion Cycle calculations

---

## 📊 Sample Output

The tool generates a structured dataset with **62 features + target variable**:

| Category | Metrics |
|----------|---------|
| **Raw Financials** | Revenue, COGS, EBIT, Net Income, EPS, D&A, Tax Expense, CFO/CFI/CFF, CapEx, Interest Expense, Dividends, R&D, SG&A, PPE, Goodwill, Intangibles, Assets, Current Assets/Liabilities, Equity, Cash, Marketable Securities, AR, AP, Inventory, Debt, Retained Earnings, Deferred Revenue |
| **Profitability** | Gross Profit, Gross Margin, Operating Margin, Net Margin, EBITDA, EBITDA Margin, Effective Tax Rate, ROE, SG&A Margin, R&D Margin |
| **Liquidity** | Current Ratio, Quick Ratio, Cash Ratio, Working Capital, Cash-to-Assets |
| **Leverage** | Debt-to-Equity, Equity Multiplier |
| **Efficiency** | Asset Turnover, Inventory Turnover, Receivables Turnover, Payables Turnover, DIO, DSO, DPO, Cash Conversion Cycle |
| **Cash Flow** | Free Cash Flow, FCF Margin, CFO Margin, OCF Ratio, Cash Flow to Net Income |
| **Growth** | Sales Growth (QoQ), **Earnings Growth (QoQ)** [Target Variable] |

---

## 🚀 Quick Start

### Prerequisites

```bash
python >= 3.8
pandas >= 1.3.0
requests >= 2.26.0
```

### Installation

```bash
git clone https://github.com/yourusername/sec-earnings-analyzer.git
cd sec-earnings-analyzer
pip install -r requirements.txt
```

### Basic Usage

```python
from sec_data_extractor import build_quarterly

# Extract data for specific tickers
tickers = ["AAPL", "MSFT", "GOOGL"]
df = build_quarterly(tickers, start_year=2019, end_year=2024)

# Save results
df.to_csv("financial_data.csv", index=False)
```

### Running the Full Analysis

```bash
python sec_data_extractor.py
```

This will:
1. Extract financial data for 75+ companies (2014-2024)
2. Calculate 62 financial metrics + earnings growth
3. Generate `sec_quarterly_raw_data.csv`

---

## 📈 Methodology

### Data Extraction Pipeline

1. **Ticker-to-CIK Mapping**: Official SEC ticker lookup
2. **XBRL Fact Retrieval**: Company-specific financial facts via SEC API
3. **Quarterly Decomposition**: Convert YTD values to quarterly increments (Q1, Q2, Q3, Q4)
4. **Unit Standardization**: Enforce USD-only reporting for consistency
5. **Metric Derivation**: Calculate 32+ derived ratios and growth metrics

### Earnings Growth Calculation

```
Earnings Growth (QoQ) = (Net Income_t - Net Income_t-1) / Net Income_t-1
```

**Key Features:**
- Handles missing data gracefully (replaces inf/-inf with 0)
- Company-specific grouping for accurate sequential quarters
- Robust to accounting irregularities and one-time charges

### Data Quality Controls

- ✅ **Revenue Validation**: Drops rows with null or zero revenue
- ✅ **Currency Filtering**: USD-only option to avoid FX complications
- ✅ **Averaging for Turnover Ratios**: Uses quarter-over-quarter averages for balance sheet items
- ✅ **SEC Rate Limiting**: 9 requests/second (below 10/sec threshold)
- ✅ **Timeout Handling**: 30-second timeout with exponential backoff

---

## 🧮 Advanced Metrics

### Cash Conversion Cycle (CCC)
```
CCC = DIO + DSO - DPO
```
Lower CCC indicates more efficient working capital management.

### Earnings Quality Indicator
```
Cash Flow to Net Income Ratio = Operating Cash Flow / Net Income
```
Ratio > 1.0 suggests high-quality earnings backed by actual cash generation.

### Tangible Book Value
```
Tangible Book = Equity - Goodwill - Intangibles
```
Conservative measure of book value excluding intangible assets.

---

## 📂 Project Structure

```
sec-earnings-analyzer/
├── sec_data_extractor.py      # Core extraction & processing logic
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── notebooks/
│   ├── exploratory_analysis.ipynb
│   └── sector_comparison.ipynb
├── dashboard/
│   └── streamlit_app.py       # Interactive dashboard
├── outputs/
│   └── sec_quarterly_raw_data.csv
└── docs/
    └── methodology.md         # Detailed documentation
```

---

## 🎨 Interactive Dashboard

Explore the data through an interactive Streamlit dashboard:

```bash
cd dashboard
streamlit run streamlit_app.py
```

**Features:**
- Company search and filtering
- Time-series earnings growth visualization
- Sector comparison
- Financial ratio heatmaps
- Downloadable filtered datasets

---

## 📚 Use Cases

### For Quantitative Researchers
- Build earnings surprise models
- Backtest fundamental factor strategies
- Identify earnings momentum signals
- Analyze cash flow quality trends

### For Financial Analysts
- Compare companies within sectors
- Track margin evolution over time
- Assess working capital efficiency
- Evaluate debt sustainability

### For Data Scientists
- Feature engineering for ML models
- Time-series forecasting of earnings
- Anomaly detection in financial statements
- Natural language processing on 10-K text (future enhancement)

---

## 🔧 Configuration

Edit these parameters in `sec_data_extractor.py`:

```python
# SEC API Configuration
USER_AGENT = "your-name your-email@example.com"  # REQUIRED by SEC
REQS_PER_SEC = 9.0  # Rate limit (max 10/sec)

# Data Parameters
start_year = 2014
end_year = 2024
usd_only = True  # Enforce USD reporting
```

---

## 📊 Sample Results

**Companies Analyzed:** 75+ (S&P 500 sample)  
**Time Period:** Q1 2014 - Q4 2024  
**Total Observations:** ~2,800 quarterly data points  
**Missing Data Rate:** <5% after quality filters

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Potential Enhancements:**
- [ ] Add industry-specific metrics (e.g., same-store sales for retail)
- [ ] Integrate analyst estimates for surprise calculation
- [ ] Build predictive models for next-quarter earnings
- [ ] Add support for international filings (IFRS)
- [ ] Real-time alerting for earnings announcements

---

## 📖 Resources

- [SEC EDGAR API Documentation](https://www.sec.gov/edgar/sec-api-documentation)
- [XBRL Specification](https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html)
- [Financial Ratio Definitions](https://www.investopedia.com/financial-ratios-4689817)

---

## 📧 Contact

**Gopal Jamnal**  
📧 gopal.jamnal@gmail.com  
🔗 [LinkedIn](your-linkedin-url) | [Portfolio](your-portfolio-url)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for educational and research purposes only. It does not constitute financial advice. Always perform your own due diligence before making investment decisions.

---

**⭐ If this project helps your research, please consider giving it a star!**
