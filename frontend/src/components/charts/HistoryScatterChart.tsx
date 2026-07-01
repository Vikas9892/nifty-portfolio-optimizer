import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import type { PortfolioListItem } from '../../types/portfolio'

interface HistoryScatterChartProps {
  portfolios: PortfolioListItem[]
}

interface TooltipPayload {
  payload: { x: number; y: number; z: number; name: string }
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null
  const { x, y, z, name } = payload[0].payload
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-3 text-xs text-gray-200 shadow-lg">
      <p className="mb-1 font-semibold">{name}</p>
      <p>Return: <span className="text-emerald-400">{y.toFixed(2)}%</span></p>
      <p>Volatility: <span className="text-yellow-400">{x.toFixed(2)}%</span></p>
      <p>Sharpe: <span className="text-blue-400">{z.toFixed(2)}</span></p>
    </div>
  )
}

export function HistoryScatterChart({ portfolios }: HistoryScatterChartProps) {
  const data = portfolios.map((p) => ({
    x: p.volatility * 100,
    y: p.expected_return * 100,
    z: Math.max(p.sharpe, 0.1),
    name: `Portfolio #${p.id}`,
  }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
        <XAxis
          dataKey="x"
          name="Volatility"
          label={{ value: 'Volatility (%)', position: 'insideBottom', offset: -15, fill: '#6b7280', fontSize: 11 }}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          dataKey="y"
          name="Return"
          label={{ value: 'Return (%)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <ZAxis dataKey="z" range={[60, 220]} name="Sharpe" />
        <Tooltip content={<CustomTooltip />} />
        <Scatter data={data} fill="#3b82f6" fillOpacity={0.75} />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
