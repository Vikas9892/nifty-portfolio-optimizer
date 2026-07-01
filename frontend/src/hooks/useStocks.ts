import { useEffect, useState } from 'react'
import { stockService } from '../services/stockService'
import type { StockUniverseResponse } from '../types/stocks'

export function useStocks() {
  const [data, setData] = useState<StockUniverseResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    stockService
      .getUniverse()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}
