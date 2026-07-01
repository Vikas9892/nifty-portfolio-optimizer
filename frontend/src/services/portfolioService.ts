import api from './api'
import type {
  OptimizeRequest,
  OptimizeResponse,
  PortfolioListItem,
  PortfolioDetail,
} from '../types/portfolio'

export const portfolioService = {
  async optimize(req: OptimizeRequest): Promise<OptimizeResponse> {
    const { data } = await api.post<OptimizeResponse>('/api/v1/portfolio/optimize', req)
    return data
  },

  async getHistory(): Promise<PortfolioListItem[]> {
    const { data } = await api.get<PortfolioListItem[]>('/api/v1/portfolio/history')
    return data
  },

  async getById(id: number): Promise<PortfolioDetail> {
    const { data } = await api.get<PortfolioDetail>(`/api/v1/portfolio/${id}`)
    return data
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/api/v1/portfolio/${id}`)
  },
}
