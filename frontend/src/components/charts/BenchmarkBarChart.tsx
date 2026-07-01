import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface BenchmarkBarChartProps {
  basketReturn: number
  niftyReturn: number
}

export function BenchmarkBarChart({ basketReturn, niftyReturn }: BenchmarkBarChartProps) {
  const data = [
    { name: 'Portfolio', value: basketReturn * 100 },
    { name: 'Nifty 50',  value: niftyReturn  * 100 },
  ]

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
        <XAxis
          dataKey="name"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fill: '#9ca3af', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v) => [`${(v as number).toFixed(2)}%`, 'Annualized Return']}
          contentStyle={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            color: '#f9fafb',
            fontSize: '12px',
          }}
          cursor={{ fill: 'rgba(255,255,255,0.03)' }}
        />
        <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={60}>
          <Cell fill="#3b82f6" />
          <Cell fill="#4b5563" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
