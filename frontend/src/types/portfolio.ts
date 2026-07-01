export interface OptimizeRequest {
  stocks: string[]
  start: string
  end: string
  max_weight: number
}

export interface OptimizeResponse {
  portfolio_id: number
  expected_return: number
  volatility: number
  sharpe: number
  basket_return: number
  nifty_return: number
  alpha: number
  weights: Record<string, number>
  stocks_in_basket: number
  stocks_with_weight: number
}

export interface PortfolioListItem {
  id: number
  created_at: string
  tickers: string[]
  start_date: string
  end_date: string
  expected_return: number
  volatility: number
  sharpe: number
  basket_return: number | null
  nifty_return: number | null
  max_weight: number
  num_portfolios: number
}

export interface PortfolioDetail extends PortfolioListItem {
  weights: Record<string, number>
}
