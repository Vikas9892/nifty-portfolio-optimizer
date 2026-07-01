import { AllocationDonutChart } from '../components/charts/AllocationDonutChart'
import { BenchmarkBarChart } from '../components/charts/BenchmarkBarChart'
import { OptimizeForm } from '../components/portfolio/OptimizeForm'
import { WeightsTable } from '../components/portfolio/WeightsTable'
import { MetricCard } from '../components/ui/MetricCard'
import { usePortfolioContext } from '../context/PortfolioContext'
import { useOptimize } from '../hooks/useOptimize'
import type { OptimizeRequest } from '../types/portfolio'
import { fmt } from '../utils/formatters'

const STATUS_LABEL: Record<string, string> = {
  queued: 'Queued — waiting for worker…',
  running: 'Running optimization…',
  completed: 'Done',
  failed: 'Failed',
}

export function Optimize() {
  const { optimize, loading, error, job } = useOptimize()
  const { currentPortfolio: p } = usePortfolioContext()

  const handleSubmit = async (req: OptimizeRequest) => {
    await optimize(req)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Optimize Portfolio</h1>
        <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
          Select stocks, set a date range, and run mean-variance optimization.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Left panel — form */}
        <div className="card p-6 xl:col-span-1">
          <h2 className="mb-5 text-sm font-semibold text-gray-900 dark:text-white">Parameters</h2>
          <OptimizeForm onSubmit={handleSubmit} loading={loading} />
        </div>

        {/* Right panel — results / status */}
        <div className="space-y-6 xl:col-span-2">
          {/* Job status banner */}
          {loading && job && (
            <div className="card flex items-center gap-4 p-4">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {STATUS_LABEL[job.status] ?? 'Processing…'}
                </p>
                <p className="text-xs text-gray-400">
                  Job {job.job_id.slice(0, 8)}
                  {job.status === 'queued' && ' · polling every 2s'}
                  {job.status === 'running' && ' · fetching prices & computing weights'}
                </p>
              </div>
            </div>
          )}

          {/* Simple spinner when loading but no job yet (queuing in-flight) */}
          {loading && !job && (
            <div className="card flex h-32 items-center justify-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
              <p className="text-sm text-gray-500 dark:text-gray-400">Queuing job…</p>
            </div>
          )}

          {/* Error state */}
          {!loading && error && (
            <div className="card border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950">
              <p className="text-sm font-medium text-red-700 dark:text-red-400">
                Optimization failed
              </p>
              <p className="mt-0.5 text-xs text-red-600 dark:text-red-500">{error}</p>
            </div>
          )}

          {/* Empty state */}
          {!loading && !p && !error && (
            <div className="card flex h-64 items-center justify-center border-dashed">
              <p className="text-sm text-gray-400">Results will appear here after optimization.</p>
            </div>
          )}

          {/* Results */}
          {!loading && p && (
            <>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <MetricCard
                  label="Expected Return"
                  value={fmt.pct(p.expected_return)}
                  positive={p.expected_return > 0}
                />
                <MetricCard label="Volatility" value={fmt.pct(p.volatility)} />
                <MetricCard
                  label="Sharpe Ratio"
                  value={p.sharpe.toFixed(2)}
                  positive={p.sharpe > 1}
                />
                <MetricCard
                  label="Alpha"
                  value={fmt.pct(p.alpha, true)}
                  positive={p.alpha > 0}
                />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="card p-6">
                  <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
                    Portfolio Allocation
                  </h3>
                  <AllocationDonutChart weights={p.weights} />
                </div>
                <div className="card p-6">
                  <h3 className="mb-1 text-sm font-semibold text-gray-900 dark:text-white">
                    vs Nifty 50
                  </h3>
                  <p className="mb-4 text-xs text-gray-400">Annualized return comparison</p>
                  <BenchmarkBarChart
                    basketReturn={p.basket_return}
                    niftyReturn={p.nifty_return}
                  />
                </div>
              </div>

              <div className="card p-6">
                <h3 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
                  Optimal Weights
                </h3>
                <WeightsTable weights={p.weights} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
