import api from './api'
import type {
  OptimizeRequest,
  OptimizeResponse,
  PortfolioListItem,
  PortfolioDetail,
} from '../types/portfolio'

export const portfolioService = {
  async optimize(req: OptimizeRequest): Promise<OptimizeResponse> {
    const { data } = await api.post<OptimizeResponse>('/optimize', req)
    return data
  },

  async getHistory(): Promise<PortfolioListItem[]> {
    const { data } = await api.get<PortfolioListItem[]>('/history')
    return data
  },

  async getById(id: number): Promise<PortfolioDetail> {
    const { data } = await api.get<PortfolioDetail>(`/portfolio/${id}`)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/portfolio/${id}`)
  },
}
