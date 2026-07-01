import api from './api'
import type { BenchmarkRequest, BenchmarkResponse } from '../types/benchmark'

export const benchmarkService = {
  async compare(req: BenchmarkRequest): Promise<BenchmarkResponse> {
    const { data } = await api.post<BenchmarkResponse>('/benchmark/', req)
    return data
  },
}
