import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { usePortfolioContext } from '../context/PortfolioContext'
import { jobService } from '../services/jobService'
import type { Job } from '../types/job'
import type { OptimizeRequest, OptimizeResponse } from '../types/portfolio'

const POLL_MS = 2_000 // poll every 2 seconds

export function useOptimize() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const { setCurrentPortfolio } = usePortfolioContext()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  // React to job state changes
  useEffect(() => {
    if (!job) return

    if (job.status === 'completed' && job.result) {
      const result = job.result as OptimizeResponse
      setCurrentPortfolio(result)
      toast.success(
        `Portfolio #${result.portfolio_id} optimized — Sharpe ${result.sharpe.toFixed(2)}`,
      )
      setLoading(false)
      stopPolling()
    } else if (job.status === 'failed') {
      const msg = job.error ?? 'Optimization failed'
      setError(msg)
      toast.error(msg)
      setLoading(false)
      stopPolling()
    }
  }, [job, setCurrentPortfolio, stopPolling])

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [stopPolling])

  const optimize = useCallback(
    async (req: OptimizeRequest) => {
      setLoading(true)
      setError(null)
      setJob(null)
      stopPolling()

      try {
        const queued = await jobService.queueOptimize(req)
        // Seed local state so the UI shows "queued" immediately
        setJob({
          job_id: queued.job_id,
          status: queued.status,
          user_id: 0,
          created_at: new Date().toISOString(),
          started_at: null,
          completed_at: null,
          result: null,
          error: null,
          request: req as unknown as Record<string, unknown>,
        })
        toast('Optimization queued', { icon: '⏳', duration: 2000 })

        // Start polling until terminal state
        pollRef.current = setInterval(async () => {
          try {
            const updated = await jobService.getJob(queued.job_id)
            setJob(updated)
          } catch (fetchErr) {
            stopPolling()
            setLoading(false)
            setError('Lost connection to job — please check History.')
          }
        }, POLL_MS)
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Failed to queue optimization'
        setError(msg)
        toast.error(msg)
        setLoading(false)
      }
    },
    [setCurrentPortfolio, stopPolling],
  )

  return { optimize, loading, error, job }
}
