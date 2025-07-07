import os
import requests
import statistics
from typing import List, Dict, Any

BASE_URL = "https://financialmodelingprep.com/api/v3"
API_KEY = os.getenv("FMP_API_KEY", "demo")

COMPETENCE_SECTORS = {
    "Consumer Staples",
    "Financial Services",
    "Healthcare",
}


def _get_json(path: str, **params) -> Any:
    params["apikey"] = API_KEY
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_profile(ticker: str) -> Dict[str, Any]:
    data = _get_json(f"/profile/{ticker}")
    return data[0] if data else {}


def get_ratios(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
    return _get_json(f"/ratios/{ticker}", period="annual", limit=limit)


def get_income_statements(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    return _get_json(f"/income-statement/{ticker}", period="annual", limit=limit)


def get_cash_flows(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    return _get_json(f"/cash-flow-statement/{ticker}", period="annual", limit=limit)


def get_enterprise_value(ticker: str) -> float:
    data = _get_json(f"/enterprise-values/{ticker}", period="annual", limit=1)
    if data:
        return float(data[0]["enterpriseValue"])
    return 0.0


def get_insider_ownership(ticker: str) -> float:
    data = _get_json(f"/insider-ownership/{ticker}")
    if data:
        return float(data[0].get("percentage", 0)) / 100.0
    return 0.0


def get_insider_trading(ticker: str, limit: int = 12) -> List[Dict[str, Any]]:
    return _get_json("/insider-trading", symbol=ticker, limit=limit)


def get_discounted_cash_flow(ticker: str) -> float:
    data = _get_json(f"/discounted-cash-flow/{ticker}")
    if data:
        return float(data[0].get("dcf", 0))
    return 0.0


def get_dividends(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    data = _get_json(f"/historical-price-full/stock_dividend/{ticker}", limit=limit)
    return data.get("historical", [])


def get_sp500_tickers() -> List[str]:
    """Return a list of S&P 500 tickers from FMP."""
    data = _get_json("/sp500_constituent")
    return [d.get("symbol") for d in data]


def circle_of_competence(profile: Dict[str, Any]) -> bool:
    return profile.get("sector") in COMPETENCE_SECTORS


def durable_economic_moat(ratios: List[Dict[str, Any]]) -> bool:
    roic_values = [float(r.get("returnOnInvestedCapital", 0)) for r in ratios[:5]]
    if not roic_values:
        return False
    avg_roic = sum(roic_values) / len(roic_values)
    return avg_roic > 0.15


def owner_earnings(cash_flows: List[Dict[str, Any]], income_statements: List[Dict[str, Any]]) -> float:
    if not cash_flows:
        return 0.0
    cf = cash_flows[0]
    cfo = float(cf.get("netCashProvidedByOperatingActivities", 0))
    da = float(cf.get("depreciationAndAmortization", 0))
    if not da and income_statements:
        da = float(income_statements[0].get("depreciationAndAmortization", 0))
    capex = float(cf.get("capitalExpenditure", 0))
    return cfo + da - capex


def owner_earnings_yield(owner_earnings_value: float, enterprise_value: float) -> float:
    if enterprise_value == 0:
        return 0.0
    return owner_earnings_value / enterprise_value


def earnings_predictability(income_statements: List[Dict[str, Any]]) -> Dict[str, bool]:
    eps_list = []
    for inc in income_statements[:10]:
        val = inc.get("eps") or inc.get("epsdiluted")
        if val is not None:
            eps_list.append(float(val))
    if len(eps_list) < 2:
        return {"eps_growth": False, "eps_cv": False}
    increases = sum(1 for i in range(1, len(eps_list)) if eps_list[i] > eps_list[i - 1])
    eps_growth = increases >= 8
    mean_eps = statistics.mean(eps_list)
    if mean_eps == 0:
        eps_cv = False
    else:
        eps_cv = statistics.stdev(eps_list) / abs(mean_eps) <= 0.20
    return {"eps_growth": eps_growth, "eps_cv": eps_cv}


def management_alignment(ticker: str) -> Dict[str, bool]:
    insider_pct = get_insider_ownership(ticker)
    trades = get_insider_trading(ticker, limit=12)
    net_shares = 0.0
    for t in trades:
        qty = float(t.get("securitiesTransacted", 0))
        if t.get("transactionType") == "Buy":
            net_shares += qty
        elif t.get("transactionType") == "Sale":
            net_shares -= qty
    return {
        "insider_ownership": insider_pct >= 0.05,
        "net_insider_buying": net_shares > 0,
    }


def margin_of_safety(profile: Dict[str, Any], dcf_value: float) -> bool:
    price = float(profile.get("price", 0))
    return price <= dcf_value * 0.75


def long_term_orientation(income_statements: List[Dict[str, Any]], dividends: List[Dict[str, Any]]) -> Dict[str, bool]:
    if len(income_statements) < 5:
        share_change_ok = False
    else:
        latest = float(income_statements[0].get("weightedAverageShsOut", 0))
        five_years_ago = float(income_statements[4].get("weightedAverageShsOut", latest))
        if five_years_ago == 0:
            share_change_ok = False
        else:
            change = abs(latest - five_years_ago) / five_years_ago
            share_change_ok = change <= 0.02 * 5
    streak = 0
    last = None
    for div in dividends:
        if last and div["dividend"] >= last:
            streak += 1
        else:
            streak = 1
        last = div["dividend"]
    dividend_growth_ok = streak >= 5
    return {"shares_stable": share_change_ok, "dividend_growth": dividend_growth_ok}


def analyze_ticker(ticker: str) -> Dict[str, Any]:
    profile = get_profile(ticker)
    ratios = get_ratios(ticker)
    income_statements = get_income_statements(ticker)
    cash_flows = get_cash_flows(ticker)
    owner_earnings_value = owner_earnings(cash_flows, income_statements)
    ev = get_enterprise_value(ticker)
    dcf_value = get_discounted_cash_flow(ticker)
    dividends = get_dividends(ticker)

    results = {
        "circle_of_competence": circle_of_competence(profile),
        "durable_moat": durable_economic_moat(ratios),
        "owner_earnings_yield": owner_earnings_yield(owner_earnings_value, ev) >= 0.08,
        "earnings_predictability": earnings_predictability(income_statements),
        "management_alignment": management_alignment(ticker),
        "margin_of_safety": margin_of_safety(profile, dcf_value),
        "long_term_orientation": long_term_orientation(income_statements, dividends),
    }
    return results


def meets_all_criteria(results: Dict[str, Any]) -> bool:
    """Return True if the result dict satisfies all screening checks."""
    if not results["circle_of_competence"]:
        return False
    if not results["durable_moat"]:
        return False
    if not results["owner_earnings_yield"]:
        return False
    ep = results.get("earnings_predictability", {})
    if not ep.get("eps_growth") or not ep.get("eps_cv"):
        return False
    mgmt = results.get("management_alignment", {})
    if not mgmt.get("insider_ownership") or not mgmt.get("net_insider_buying"):
        return False
    if not results["margin_of_safety"]:
        return False
    lt = results.get("long_term_orientation", {})
    if not lt.get("shares_stable") or not lt.get("dividend_growth"):
        return False
    return True


def screen_sp500() -> List[str]:
    """Run the analysis for all S&P 500 tickers and return the ones that pass."""
    tickers = get_sp500_tickers()
    passing = []
    for symbol in tickers:
        try:
            res = analyze_ticker(symbol)
            if meets_all_criteria(res):
                passing.append(symbol)
        except Exception:
            # Skip tickers that fail API requests or parsing
            continue
    return passing


if __name__ == "__main__":
    import sys
    if "--sp500" in sys.argv:
        tickers = screen_sp500()
        print("Stocks meeting all criteria:")
        for t in tickers:
            print(t)
    else:
        tickers = [t for t in sys.argv[1:] if not t.startswith("-")] or ["AAPL"]
        for symbol in tickers:
            try:
                analysis = analyze_ticker(symbol)
                print(f"Results for {symbol}:")
                for key, value in analysis.items():
                    print(f"  {key}: {value}")
            except Exception as exc:
                print(f"Failed to analyze {symbol}: {exc}")
