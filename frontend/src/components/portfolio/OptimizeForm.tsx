import { useState } from 'react'
import { Button } from '../ui/Button'
import { ErrorCard } from '../ui/ErrorCard'
import { Loader } from '../ui/Loader'
import { useStocks } from '../../hooks/useStocks'
import { DEFAULT_STOCKS } from '../../utils/constants'
import type { OptimizeRequest } from '../../types/portfolio'

interface OptimizeFormProps {
  onSubmit: (req: OptimizeRequest) => void
  loading: boolean
}

/** Yesterday's date as YYYY-MM-DD — avoids using today when the market may not have closed yet. */
function defaultEndDate(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().split('T')[0]
}

export function OptimizeForm({ onSubmit, loading }: OptimizeFormProps) {
  const { data: universe, loading: loadingStocks, error: stocksError } = useStocks()
  const [selected, setSelected] = useState<Set<string>>(new Set(DEFAULT_STOCKS))
  const [start, setStart] = useState('2020-01-01')
  const [end, setEnd] = useState(defaultEndDate)
  const [maxWeight, setMaxWeight] = useState(0.30)

  const toggle = (ticker: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(ticker) ? next.delete(ticker) : next.add(ticker)
      return next
    })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selected.size < 2 || loading) return
    onSubmit({ stocks: Array.from(selected), start, end, max_weight: maxWeight })
  }

  if (loadingStocks) return <Loader label="Loading stock universe..." />
  if (stocksError) return <ErrorCard message={stocksError} />

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Stock picker */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Stocks
          </label>
          <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-600 dark:bg-blue-950 dark:text-blue-400">
            {selected.size} selected
          </span>
        </div>

        <div className="max-h-72 space-y-3 overflow-y-auto rounded-lg border border-gray-200 p-3 dark:border-gray-700">
          {universe &&
            Object.entries(universe.sectors).map(([sector, tickers]) => (
              <div key={sector}>
                <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-gray-400 dark:text-gray-500">
                  {sector}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {tickers.map((ticker) => {
                    const on = selected.has(ticker)
                    return (
                      <button
                        key={ticker}
                        type="button"
                        onClick={() => toggle(ticker)}
                        className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                          on
                            ? 'border-blue-600 bg-blue-600 text-white'
                            : 'border-gray-300 bg-transparent text-gray-600 hover:border-blue-400 hover:text-blue-500 dark:border-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {ticker.replace('.NS', '')}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
        </div>

        {selected.size < 2 && (
          <p className="mt-1.5 text-xs text-red-500">Select at least 2 stocks.</p>
        )}
      </div>

      {/* Date range */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Start date', value: start, onChange: setStart },
          { label: 'End date',   value: end,   onChange: setEnd   },
        ].map(({ label, value, onChange }) => (
          <div key={label}>
            <label className="mb-1.5 block text-xs font-medium text-gray-600 dark:text-gray-400">
              {label}
            </label>
            <input
              type="date"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
            />
          </div>
        ))}
      </div>

      {/* Max weight slider */}
      <div>
        <div className="mb-1.5 flex justify-between">
          <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Max weight per stock
          </label>
          <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
            {(maxWeight * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min="0.10"
          max="0.50"
          step="0.01"
          value={maxWeight}
          onChange={(e) => setMaxWeight(parseFloat(e.target.value))}
          className="w-full accent-blue-600"
        />
        <div className="mt-0.5 flex justify-between text-[10px] text-gray-400">
          <span>10%</span><span>50%</span>
        </div>
      </div>

      <Button
        type="submit"
        disabled={selected.size < 2 || loading}
        loading={loading}
        className="w-full py-2.5"
      >
        {loading ? 'Optimizing…' : 'Optimize Portfolio'}
      </Button>
    </form>
  )
}
