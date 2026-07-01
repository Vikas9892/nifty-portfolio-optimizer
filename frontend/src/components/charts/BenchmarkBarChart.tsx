import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useTheme } from '../../context/ThemeContext'

interface BenchmarkBarChartProps {
  basketReturn: number
  niftyReturn: number
}

export function BenchmarkBarChart({ basketReturn, niftyReturn }: BenchmarkBarChartProps) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'
  const tickColor = isDark ? '#9ca3af' : '#6b7280'

  const data = [
    { name: 'Portfolio', value: basketReturn * 100 },
    { name: 'Nifty 50',  value: niftyReturn  * 100 },
  ]

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: tickColor, fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fill: tickColor, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [`${(v as number).toFixed(2)}%`, 'Annualized Return']}
          contentStyle={{
            backgroundColor: isDark ? '#111827' : '#ffffff',
            border: `1px solid ${isDark ? '#1f2937' : '#e5e7eb'}`,
            borderRadius: '8px',
            color: isDark ? '#f9fafb' : '#111827',
            fontSize: '12px',
            boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
          }}
          cursor={{ fill: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)' }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>
          <Cell fill="#3b82f6" />
          <Cell fill={isDark ? '#4b5563' : '#d1d5db'} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
