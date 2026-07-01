import api from './api'
import type { OptimizeRequest } from '../types/portfolio'
import type { Job, QueuedJob } from '../types/job'

export const jobService = {
  async queueOptimize(req: OptimizeRequest, idempotencyKey?: string): Promise<QueuedJob> {
    const headers: Record<string, string> = {}
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
    const { data } = await api.post<QueuedJob>('/api/v1/jobs/optimize', req, { headers })
    return data
  },

  async getJob(jobId: string): Promise<Job> {
    const { data } = await api.get<Job>(`/api/v1/jobs/${jobId}`)
    return data
  },
}
