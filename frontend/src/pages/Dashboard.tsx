import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, TrendingUp } from 'lucide-react'
import { usePortfolioContext } from '../context/PortfolioContext'
import { MetricCard } from '../components/ui/MetricCard'
import { Loader } from '../components/ui/Loader'
import { Button } from '../components/ui/Button'
import { AllocationDonutChart } from '../components/charts/AllocationDonutChart'
import { BenchmarkBarChart } from '../components/charts/BenchmarkBarChart'
import { portfolioService } from '../services/portfolioService'
import type { PortfolioListItem } from '../types/portfolio'
import { fmt } from '../utils/formatters'

export function Dashboard() {
  const { currentPortfolio } = usePortfolioContext()
  const [recent, setRecent] = useState<PortfolioListItem[]>([])
  const [loadingRecent, setLoadingRecent] = useState(true)

  useEffect(() => {
    portfolioService
      .getHistory()
      .then((h) => setRecent(h.slice(0, 5)))
      .finally(() => setLoadingRecent(false))
  }, [])

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
          Nifty 50 mean-variance portfolio optimization
        </p>
      </div>

      {currentPortfolio ? (
        <>
          {/* Metric cards */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard
              label="Expected Return"
              value={fmt.pct(currentPortfolio.expected_return)}
              positive={currentPortfolio.expected_return > 0}
            />
            <MetricCard label="Volatility" value={fmt.pct(currentPortfolio.volatility)} />
            <MetricCard
              label="Sharpe Ratio"
              value={currentPortfolio.sharpe.toFixed(2)}
              positive={currentPortfolio.sharpe > 1}
            />
            <MetricCard
              label="Alpha vs Nifty"
              value={fmt.pct(currentPortfolio.alpha, true)}
              delta={
                currentPortfolio.alpha > 0
                  ? '↑ Outperforms Nifty 50'
                  : '↓ Underperforms Nifty 50'
              }
              positive={currentPortfolio.alpha > 0}
            />
          </div>

          {/* Charts row */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="card p-6">
              <h2 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
                Portfolio Allocation
              </h2>
              <AllocationDonutChart weights={currentPortfolio.weights} />
            </div>
            <div className="card p-6">
              <h2 className="mb-1 text-sm font-semibold text-gray-900 dark:text-white">
                vs Nifty 50 Benchmark
              </h2>
              <p className="mb-4 text-xs text-gray-400">Annualized return comparison</p>
              <BenchmarkBarChart
                basketReturn={currentPortfolio.basket_return}
                niftyReturn={currentPortfolio.nifty_return}
              />
              <p className="mt-3 text-center text-xs text-gray-400">
                {currentPortfolio.stocks_in_basket} stocks in basket ·{' '}
                {currentPortfolio.stocks_with_weight} with non-zero weight ·{' '}
                Portfolio #{currentPortfolio.portfolio_id}
              </p>
            </div>
          </div>
        </>
      ) : (
        /* Empty state CTA */
        <div className="card flex flex-col items-center p-10 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-blue-50 dark:bg-blue-950">
            <TrendingUp className="text-blue-600 dark:text-blue-400" size={24} />
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            No portfolio yet
          </h2>
          <p className="mt-1.5 max-w-sm text-sm text-gray-500 dark:text-gray-400">
            Run an optimization to see metrics, allocation charts, and benchmark comparison
            right here.
          </p>
          <Link to="/optimize" className="mt-6">
            <Button>
              Optimize Portfolio
              <ArrowRight size={15} />
            </Button>
          </Link>
        </div>
      )}

      {/* Recent history */}
      <div className="card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            Recent Optimizations
          </h2>
          <Link
            to="/history"
            className="flex items-center gap-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
          >
            View all <ArrowRight size={13} />
          </Link>
        </div>

        {loadingRecent ? (
          <Loader label="Loading history…" />
        ) : recent.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-400">No history yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs text-gray-500 dark:border-gray-800 dark:text-gray-400">
                <th className="pb-2 font-medium">ID</th>
                <th className="pb-2 font-medium">Date</th>
                <th className="pb-2 font-medium">Stocks</th>
                <th className="pb-2 font-medium">Sharpe</th>
                <th className="pb-2 font-medium">Return</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {recent.map((p) => (
                <tr key={p.id} className="text-gray-700 dark:text-gray-300">
                  <td className="py-2.5 font-mono text-xs text-gray-400">#{p.id}</td>
                  <td className="py-2.5">{fmt.date(p.created_at)}</td>
                  <td className="py-2.5">{p.tickers.length} stocks</td>
                  <td className="py-2.5 font-medium">{p.sharpe.toFixed(2)}</td>
                  <td
                    className={`py-2.5 font-medium ${
                      p.expected_return > 0 ? 'text-emerald-500' : 'text-red-500'
                    }`}
                  >
                    {fmt.pct(p.expected_return)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
