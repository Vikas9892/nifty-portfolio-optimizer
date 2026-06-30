from pathlib import Path

NIFTY_50 = {
    "IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "Financial Services": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS", "M&M.NS"],
    "Metals & Mining": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
    "Cement": ["ULTRACEMCO.NS", "SHREECEM.NS", "GRASIM.NS"],
    "Conglomerate / Infra": ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS"],
    "Telecom": ["BHARTIARTL.NS"],
    "Consumer": ["ASIANPAINT.NS", "TITAN.NS"],
    "Healthcare": ["APOLLOHOSP.NS"],
    "Agro / Chemicals": ["UPL.NS"],
}

NIFTY_50_STOCKS: list[str] = [ticker for tickers in NIFTY_50.values() for ticker in tickers]

DEFAULT_STOCKS = [
    "TCS.NS", "INFY.NS", "HCLTECH.NS",
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",
    "RELIANCE.NS", "ONGC.NS",
    "HINDUNILVR.NS", "ITC.NS",
    "SUNPHARMA.NS",
    "MARUTI.NS", "TATAMOTORS.NS",
    "BHARTIARTL.NS",
    "LT.NS",
]

PLOTS_DIR = Path("plots")
