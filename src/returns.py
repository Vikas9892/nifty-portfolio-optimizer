def calculate_returns(price_data):
    """Convert close prices into daily returns."""
    return price_data.pct_change().dropna()
