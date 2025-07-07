# StockAnalysis

This repository contains a simple Python script for screening stocks using data from the [Financial Modeling Prep](https://financialmodelingprep.com/) API. The script applies a set of quantitative filters inspired by Buffett & Munger principles.

## Requirements
- Python 3.8+
- `requests` library
- A Financial Modeling Prep API key. Set it in the environment variable `FMP_API_KEY`.

Install dependencies:
```bash
pip install requests
```

## Usage
Run the analysis for one or more tickers by providing the symbols as arguments:
```bash
python stock_analysis.py AAPL MSFT
```
If no tickers are provided, the script defaults to `AAPL`.
