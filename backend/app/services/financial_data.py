"""
Financial Data Service — fetches real company financials from Yahoo Finance via yfinance.
No API key required. Supports NSE (.NS), BSE (.BO), and global tickers.
"""
import yfinance as yf
from datetime import datetime
from app.models.schemas import (
    YearlyFinancial, StockDataPoint, KeyRatios,
)

# ── Curated ticker map for common Indian + global companies ───────────────────
KNOWN_TICKERS: dict[str, str | None] = {
    # Indian tech / startup
    "zomato": "ETERNAL.NS",          # Zomato rebranded to Eternal Ltd in 2025
    "eternal": "ETERNAL.NS",
    "swiggy": "SWIGGY.NS",
    "paytm": "PAYTM.NS",
    "nykaa": "NYKAA.NS",
    "policybazaar": "POLICYBZR.NS",
    "delhivery": "DELHIVERY.NS",
    "freshworks": "FRSH",
    "ola electric": "OLAELEC.NS",
    "ola": "OLAELEC.NS",
    # Indian blue chip
    "infosys": "INFY.NS",
    "tcs": "TCS.NS",
    "wipro": "WIPRO.NS",
    "hcl": "HCLTECH.NS",
    "reliance": "RELIANCE.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "sbi": "SBIN.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "asian paints": "ASIANPAINT.NS",
    "bajaj finance": "BAJFINANCE.NS",
    "bajaj": "BAJFINANCE.NS",
    "titan": "TITAN.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "maruti": "MARUTI.NS",
    "tata motors": "TATAMOTORS.NS",
    "tata": "TCS.NS",
    # Global tech
    "apple": "AAPL",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "nvidia": "NVDA",
    # Private (no public ticker)
    "openai": None,
    "anthropic": None,
    "razorpay": None,
    "zepto": None,
}


def resolve_ticker(company_name: str) -> str | None:
    """Maps a company name → ticker. Returns None if company is private/unlisted."""
    name_lower = company_name.lower().strip()

    # Direct match
    if name_lower in KNOWN_TICKERS:
        return KNOWN_TICKERS[name_lower]

    # Partial match (e.g. "Zomato limited" → "zomato")
    for key, ticker in KNOWN_TICKERS.items():
        if key in name_lower or name_lower in key:
            return ticker

    # yfinance search fallback
    try:
        results = yf.Search(company_name, max_results=3).quotes
        for r in results:
            if r.get("quoteType") in ("EQUITY", "ETF"):
                return r.get("symbol")
    except Exception:
        pass

    return None


def _safe_float(val) -> float | None:
    """Convert pandas/numpy scalar to float safely."""
    try:
        f = float(val)
        return None if (f != f) else round(f, 2)  # NaN check
    except Exception:
        return None


def fetch_financials(ticker_symbol: str) -> dict:
    """
    Fetches and structures financial data for a given ticker.
    Returns a dict ready for FinancialIntelligence schema.
    """
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info or {}

    # ── Yearly Financials ────────────────────────────────────────────────────
    yearly: list[YearlyFinancial] = []
    try:
        fin = ticker.financials          # Income statement (annual)
        bs  = ticker.balance_sheet       # Balance sheet (annual)

        # yfinance returns columns as Timestamps, most recent first
        years = list(fin.columns)[:4] if fin is not None and not fin.empty else []

        for col in years:
            year_str = str(col.year) if hasattr(col, "year") else str(col)[:4]

            revenue = _safe_float(fin.loc["Total Revenue", col]) if "Total Revenue" in fin.index else None
            net_profit = _safe_float(fin.loc["Net Income", col]) if "Net Income" in fin.index else None
            ebit = _safe_float(fin.loc["EBIT", col]) if "EBIT" in fin.index else None
            gross = _safe_float(fin.loc["Gross Profit", col]) if "Gross Profit" in fin.index else None

            # Gross margin %
            gross_margin = None
            if gross and revenue and revenue != 0:
                gross_margin = round((gross / revenue) * 100, 1)

            # EPS
            eps = _safe_float(fin.loc["Diluted EPS", col]) if "Diluted EPS" in fin.index else None
            if eps is None:
                eps = _safe_float(fin.loc["Basic EPS", col]) if "Basic EPS" in fin.index else None

            # Balance sheet
            total_debt = None
            total_equity = None
            if bs is not None and not bs.empty and col in bs.columns:
                total_debt = _safe_float(bs.loc["Total Debt", col]) if "Total Debt" in bs.index else None
                total_equity = _safe_float(bs.loc["Stockholders Equity", col]) if "Stockholders Equity" in bs.index else (
                    _safe_float(bs.loc["Total Equity Gross Minority Interest", col]) if "Total Equity Gross Minority Interest" in bs.index else None
                )

            # Convert from raw units to Crores (for Indian stocks) or Millions (for US)
            divisor = 1_00_00_000 if ticker_symbol.endswith(".NS") or ticker_symbol.endswith(".BO") else 1_000_000
            def to_display(v):
                return round(v / divisor, 2) if v is not None else None

            yearly.append(YearlyFinancial(
                year=year_str,
                revenue=to_display(revenue),
                net_profit=to_display(net_profit),
                gross_margin=gross_margin,
                eps=eps,
                total_debt=to_display(total_debt),
                total_equity=to_display(total_equity),
            ))
    except Exception as e:
        print(f"[FinancialData] Financials error for {ticker_symbol}: {e}")

    # ── Stock Price History (1 year) ─────────────────────────────────────────
    stock_history: list[StockDataPoint] = []
    try:
        hist = ticker.history(period="1y")
        for date, row in hist.iterrows():
            stock_history.append(StockDataPoint(
                date=date.strftime("%Y-%m-%d"),
                close=round(float(row["Close"]), 2),
                volume=int(row["Volume"]) if "Volume" in row else None,
            ))
    except Exception as e:
        print(f"[FinancialData] Stock history error for {ticker_symbol}: {e}")

    # ── Key Ratios ───────────────────────────────────────────────────────────
    rev_growth = None
    if len(yearly) >= 2 and yearly[0].revenue and yearly[1].revenue and yearly[1].revenue != 0:
        rev_growth = round(((yearly[0].revenue - yearly[1].revenue) / abs(yearly[1].revenue)) * 100, 1)

    key_ratios = KeyRatios(
        pe_ratio=_safe_float(info.get("trailingPE") or info.get("forwardPE")),
        market_cap_cr=round(info.get("marketCap", 0) / 1_00_00_000, 0) if info.get("marketCap") else None,
        week_52_high=_safe_float(info.get("fiftyTwoWeekHigh")),
        week_52_low=_safe_float(info.get("fiftyTwoWeekLow")),
        revenue_growth_yoy=rev_growth,
        profit_margin=_safe_float(info.get("profitMargins", 0) * 100) if info.get("profitMargins") else None,
    )

    company_name = info.get("longName") or info.get("shortName") or ticker_symbol
    currency = info.get("currency", "INR" if ".NS" in ticker_symbol else "USD")

    return {
        "ticker": ticker_symbol,
        "company": company_name,
        "currency": currency,
        "yearly_financials": yearly,
        "stock_price_history": stock_history,
        "key_ratios": key_ratios,
    }
