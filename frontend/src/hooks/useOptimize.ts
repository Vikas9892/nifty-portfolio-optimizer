import { useCallback, useState } from 'react'
import toast from 'react-hot-toast'
import { usePortfolioContext } from '../context/PortfolioContext'
import { portfolioService } from '../services/portfolioService'
import type { OptimizeRequest, OptimizeResponse } from '../types/portfolio'

export function useOptimize() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { setCurrentPortfolio } = usePortfolioContext()

  const optimize = useCallback(
    async (req: OptimizeRequest): Promise<OptimizeResponse | null> => {
      setLoading(true)
      setError(null)
      try {
        const result = await portfolioService.optimize(req)
        setCurrentPortfolio(result)
        toast.success(`Portfolio #${result.portfolio_id} optimized — Sharpe ${result.sharpe.toFixed(2)}`)
        return result
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Optimization failed'
        setError(msg)
        toast.error(msg)
        return null
      } finally {
        setLoading(false)
      }
    },
    [setCurrentPortfolio],
  )

  return { optimize, loading, error }
}
