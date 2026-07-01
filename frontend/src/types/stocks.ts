export interface StockUniverseResponse {
  sectors: Record<string, string[]>
  all_stocks: string[]
  total_count: number
}
