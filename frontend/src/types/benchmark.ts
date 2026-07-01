export interface BenchmarkRequest {
  stocks: string[]
  weights: Record<string, number>
  start: string
  end: string
}

export interface BenchmarkResponse {
  basket_return: number
  nifty_return: number
  alpha: number
  outperforms: boolean
}
