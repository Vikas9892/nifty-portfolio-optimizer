import type { OptimizeResponse } from './portfolio'

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'

export interface Job {
  job_id: string
  user_id: number
  status: JobStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  result: OptimizeResponse | null
  error: string | null
  request: Record<string, unknown>
}

export interface QueuedJob {
  job_id: string
  status: JobStatus
}
