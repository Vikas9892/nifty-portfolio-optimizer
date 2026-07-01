import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { AllocationDonutChart } from '../components/charts/AllocationDonutChart'
import { HistoryScatterChart } from '../components/charts/HistoryScatterChart'
import { ErrorCard } from '../components/ui/ErrorCard'
import { Loader } from '../components/ui/Loader'
import { useHistory } from '../hooks/useHistory'
import { portfolioService } from '../services/portfolioService'
import type { PortfolioDetail } from '../types/portfolio'
import { fmt } from '../utils/formatters'

export function History() {
  const { history, loading, error, refetch, remove } = useHistory()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [detailCache, setDetailCache] = useState<Record<number, PortfolioDetail>>({})
  const [loadingDetail, setLoadingDetail] = useState<number | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)

  const toggleExpand = async (id: number) => {
    if (expanded === id) { setExpanded(null); return }
    setExpanded(id)
    if (!detailCache[id]) {
      setLoadingDetail(id)
      try {
        const d = await portfolioService.getById(id)
        setDetailCache((prev) => ({ ...prev, [id]: d }))
      } finally {
        setLoadingDetail(null)
      }
    }
  }

  const handleDelete = async (id: number) => {
    setDeleting(id)
    try {
      await portfolioService.delete(id)
      remove(id)
      if (expanded === id) setExpanded(null)
      toast.success(`Portfolio #${id} deleted.`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Delete failed')
    } finally {
      setDeleting(null)
    }
  }

  if (loading) return <Loader label="Loading history…" />
  if (error) return <ErrorCard message={error} onRetry={refetch} />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">History</h1>
        <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
          {history.length} optimization run{history.length !== 1 ? 's' : ''} saved
        </p>
      </div>

      {history.length === 0 ? (
        <div className="card py-20 text-center text-gray-400">
          <p>No past optimizations yet.</p>
          <p className="mt-1 text-sm">Run the optimizer to save your first result.</p>
        </div>
      ) : (
        <>
          {/* Risk / return landscape */}
          {history.length > 1 && (
            <div className="card p-6">
              <h2 className="mb-1 text-sm font-semibold text-gray-900 dark:text-white">
                Risk / Return Landscape
              </h2>
              <p className="mb-4 text-xs text-gray-400">
                Each bubble is a saved portfolio · bubble size = Sharpe ratio
              </p>
              <HistoryScatterChart portfolios={history} />
            </div>
          )}

          {/* Portfolio list */}
          <div className="card overflow-hidden">
            {history.map((p) => (
              <div key={p.id} className="border-b border-gray-100 last:border-0 dark:border-gray-800">
                {/* Row header */}
                <div
                  className="flex cursor-pointer items-center gap-4 px-6 py-4 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/40"
                  onClick={() => toggleExpand(p.id)}
                >
                  <span className="w-10 shrink-0 font-mono text-xs text-gray-400">
                    #{p.id}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-gray-900 dark:text-white">
                      {p.tickers.length} stocks · {p.start_date} → {p.end_date}
                    </p>
                    <p className="mt-0.5 text-xs text-gray-400">{fmt.datetime(p.created_at)}</p>
                  </div>

                  <div className="hidden shrink-0 items-center gap-6 text-sm sm:flex">
                    <span className="text-gray-500 dark:text-gray-400">
                      Sharpe{' '}
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {p.sharpe.toFixed(2)}
                      </span>
                    </span>
                    <span className="text-gray-500 dark:text-gray-400">
                      Return{' '}
                      <span
                        className={`font-semibold ${
                          p.expected_return > 0 ? 'text-emerald-500' : 'text-red-500'
                        }`}
                      >
                        {fmt.pct(p.expected_return)}
                      </span>
                    </span>
                    <span className="text-gray-500 dark:text-gray-400">
                      Vol{' '}
                      <span className="font-semibold text-gray-900 dark:text-white">
                        {fmt.pct(p.volatility)}
                      </span>
                    </span>
                  </div>

                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(p.id) }}
                    disabled={deleting === p.id}
                    className="shrink-0 rounded-md p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500 disabled:opacity-40 dark:hover:bg-red-950"
                    title="Delete"
                  >
                    <Trash2 size={15} />
                  </button>

                  {expanded === p.id ? (
                    <ChevronUp size={15} className="shrink-0 text-gray-400" />
                  ) : (
                    <ChevronDown size={15} className="shrink-0 text-gray-400" />
                  )}
                </div>

                {/* Expanded detail */}
                {expanded === p.id && (
                  <div className="border-t border-gray-100 bg-gray-50 px-6 pb-6 dark:border-gray-800 dark:bg-gray-800/20">
                    {loadingDetail === p.id ? (
                      <Loader label="Loading weights…" />
                    ) : detailCache[p.id] ? (
                      <div className="grid grid-cols-1 gap-6 pt-5 lg:grid-cols-2">
                        {/* Weight bars */}
                        <div>
                          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
                            Weights
                          </h4>
                          <div className="space-y-2">
                            {Object.entries(detailCache[p.id].weights)
                              .sort(([, a], [, b]) => b - a)
                              .map(([ticker, w]) => (
                                <div key={ticker} className="flex items-center gap-3">
                                  <span className="w-20 shrink-0 font-mono text-xs text-gray-500 dark:text-gray-400">
                                    {ticker.replace('.NS', '')}
                                  </span>
                                  <div className="flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700" style={{ height: 6 }}>
                                    <div
                                      className="h-full rounded-full bg-blue-500"
                                      style={{ width: `${(w * 100).toFixed(1)}%` }}
                                    />
                                  </div>
                                  <span className="w-12 text-right text-xs font-semibold text-gray-700 dark:text-gray-300">
                                    {(w * 100).toFixed(1)}%
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>

                        {/* Donut chart */}
                        <AllocationDonutChart weights={detailCache[p.id].weights} />
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
