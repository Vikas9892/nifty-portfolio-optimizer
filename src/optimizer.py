from pypfopt import EfficientFrontier, expected_returns, risk_models


def optimize_portfolio(price_data, max_weight: float = 0.30):
    """Optimize the basket for maximum Sharpe ratio using Ledoit-Wolf covariance."""
    mu = expected_returns.mean_historical_return(price_data)
    # Ledoit-Wolf shrinkage stabilizes the covariance matrix for larger asset sets
    covariance = risk_models.CovarianceShrinkage(price_data).ledoit_wolf()
    frontier = EfficientFrontier(mu, covariance)
    frontier.add_constraint(lambda w: w <= max_weight)
    frontier.max_sharpe()
    ret, vol, sharpe = frontier.portfolio_performance()
    cleaned_weights = frontier.clean_weights()
    return mu, covariance, cleaned_weights, ret, vol, sharpe
