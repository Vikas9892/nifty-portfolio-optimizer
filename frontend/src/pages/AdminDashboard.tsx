import { useEffect, useState } from 'react'
import api from '../services/api'

interface Metrics {
  'api:requests:total': number
  'api:errors:total': number
  'cache:hits': number
  'cache:misses': number
  'cache:hit_ratio': number
  'optimize:count': number
  'optimize:avg_ms': number
  'jobs:queued': number
  'jobs:completed': number
  'jobs:failed': number
  'queue:depth': number
}

function MetricTile({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  accent?: 'green' | 'red' | 'blue' | 'yellow'
}) {
  const colors = {
    green: 'border-green-400 bg-green-50 dark:bg-green-950',
    red: 'border-red-400 bg-red-50 dark:bg-red-950',
    blue: 'border-blue-400 bg-blue-50 dark:bg-blue-950',
    yellow: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-950',
  }
  return (
    <div
      className={`card border-l-4 p-5 ${accent ? colors[accent] : 'border-gray-200 dark:border-gray-700'}`}
    >
      <p className="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

export function AdminDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const fetchMetrics = async () => {
    try {
      const { data } = await api.get<Metrics>('/api/v1/admin/metrics')
      setMetrics(data)
      setLastRefresh(new Date())
    } catch {
      // silently ignore if no Redis
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
    const timer = setInterval(fetchMetrics, 30_000) // auto-refresh every 30s
    return () => clearInterval(timer)
  }, [])

  const hitRatio = metrics ? `${(metrics['cache:hit_ratio'] * 100).toFixed(1)}%` : '—'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Performance Dashboard</h1>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            Live metrics — auto-refreshes every 30 s
          </p>
        </div>
        <div className="text-right">
          <button
            onClick={fetchMetrics}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            Refresh
          </button>
          {lastRefresh && (
            <p className="mt-1 text-[10px] text-gray-400">
              Last: {lastRefresh.toLocaleTimeString()}
            </p>
          )}
        </div>
      </div>

      {loading ? (
        <div className="card flex h-32 items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        </div>
      ) : !metrics ? (
        <div className="card flex h-32 items-center justify-center">
          <p className="text-sm text-gray-400">
            Metrics unavailable — Redis is not configured in this environment.
          </p>
        </div>
      ) : (
        <>
          {/* API health */}
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              API
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricTile
                label="Total Requests"
                value={metrics['api:requests:total'].toLocaleString()}
                accent="blue"
              />
              <MetricTile
                label="Errors (5xx)"
                value={metrics['api:errors:total'].toLocaleString()}
                accent={metrics['api:errors:total'] > 0 ? 'red' : undefined}
              />
              <MetricTile
                label="Cache Hit Ratio"
                value={hitRatio}
                sub={`${metrics['cache:hits']} hits / ${metrics['cache:misses']} misses`}
                accent={metrics['cache:hit_ratio'] > 0.7 ? 'green' : 'yellow'}
              />
              <MetricTile
                label="Optimizations"
                value={metrics['optimize:count'].toLocaleString()}
                sub={`avg ${metrics['optimize:avg_ms'].toFixed(0)} ms`}
                accent="blue"
              />
            </div>
          </section>

          {/* Job queue */}
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
              Job Queue
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricTile
                label="Queue Depth"
                value={metrics['queue:depth'].toLocaleString()}
                accent={metrics['queue:depth'] > 10 ? 'yellow' : undefined}
              />
              <MetricTile
                label="Total Queued"
                value={metrics['jobs:queued'].toLocaleString()}
              />
              <MetricTile
                label="Completed"
                value={metrics['jobs:completed'].toLocaleString()}
                accent="green"
              />
              <MetricTile
                label="Failed"
                value={metrics['jobs:failed'].toLocaleString()}
                accent={metrics['jobs:failed'] > 0 ? 'red' : undefined}
              />
            </div>
          </section>

          {/* Quick reference */}
          <section className="card p-5">
            <h2 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
              Observability Links
            </h2>
            <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
              <li>
                <span className="font-mono text-xs text-blue-600 dark:text-blue-400">
                  GET /metrics
                </span>{' '}
                — Prometheus scrape endpoint
              </li>
              <li>
                <span className="font-mono text-xs text-blue-600 dark:text-blue-400">
                  localhost:9090
                </span>{' '}
                — Prometheus UI (docker-compose)
              </li>
              <li>
                <span className="font-mono text-xs text-blue-600 dark:text-blue-400">
                  localhost:3001
                </span>{' '}
                — Grafana (admin / admin)
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
