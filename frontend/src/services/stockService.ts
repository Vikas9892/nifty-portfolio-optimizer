import api from './api'
import type { StockUniverseResponse } from '../types/stocks'

export const stockService = {
  async getUniverse(): Promise<StockUniverseResponse> {
    const { data } = await api.get<StockUniverseResponse>('/api/v1/stocks/')
    return data
  },
}
