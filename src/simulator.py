import numpy as np
import pandas as pd


def simulate_portfolios(returns, num_portfolios: int = 5000):
    """Generate random portfolios for a Monte Carlo frontier."""
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    portfolio_rows = []
    asset_count = len(mean_returns)

    for _ in range(num_portfolios):
        weights = np.random.random(asset_count)
        weights /= np.sum(weights)
        portfolio_return = np.sum(mean_returns.values * weights) * 252
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix.values * 252, weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility else 0
        portfolio_rows.append({
            "return": portfolio_return,
            "volatility": portfolio_volatility,
            "sharpe": sharpe_ratio,
        })

    return pd.DataFrame(portfolio_rows)
