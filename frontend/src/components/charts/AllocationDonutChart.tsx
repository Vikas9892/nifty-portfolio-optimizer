import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { CHART_COLORS } from '../../utils/constants'

interface AllocationDonutChartProps {
  weights: Record<string, number>
}

export function AllocationDonutChart({ weights }: AllocationDonutChartProps) {
  const data = Object.entries(weights)
    .filter(([, v]) => v > 0.001)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value]) => ({ name: name.replace('.NS', ''), value }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="45%"
          innerRadius={65}
          outerRadius={105}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v) => [`${((v as number) * 100).toFixed(1)}%`, 'Weight']}
          contentStyle={{
            backgroundColor: '#111827',
            border: '1px solid #1f2937',
            borderRadius: '8px',
            color: '#f9fafb',
            fontSize: '12px',
          }}
        />
        <Legend
          iconSize={10}
          iconType="circle"
          formatter={(value) => (
            <span style={{ fontSize: '11px', color: '#9ca3af' }}>{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
