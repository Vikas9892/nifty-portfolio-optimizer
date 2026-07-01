import { useCallback, useEffect, useState } from 'react'
import { portfolioService } from '../services/portfolioService'
import type { PortfolioListItem } from '../types/portfolio'

export function useHistory() {
  const [history, setHistory] = useState<PortfolioListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(() => {
    setLoading(true)
    setError(null)
    portfolioService
      .getHistory()
      .then(setHistory)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    refetch()
  }, [refetch])

  /** Optimistically remove a portfolio from local state after a successful delete. */
  const remove = useCallback((id: number) => {
    setHistory((prev) => prev.filter((p) => p.id !== id))
  }, [])

  return { history, loading, error, refetch, remove }
}
