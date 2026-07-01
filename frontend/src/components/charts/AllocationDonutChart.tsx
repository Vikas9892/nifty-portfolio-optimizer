import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useTheme } from '../../context/ThemeContext'
import { CHART_COLORS } from '../../utils/constants'

interface AllocationDonutChartProps {
  weights: Record<string, number>
}

export function AllocationDonutChart({ weights }: AllocationDonutChartProps) {
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const data = Object.entries(weights)
    .filter(([, v]) => v > 0.001)
    .sort(([, a], [, b]) => b - a)
    .map(([name, value]) => ({ name: name.replace('.NS', ''), value }))

  const tooltipStyle = {
    backgroundColor: isDark ? '#111827' : '#ffffff',
    border: `1px solid ${isDark ? '#1f2937' : '#e5e7eb'}`,
    borderRadius: '8px',
    color: isDark ? '#f9fafb' : '#111827',
    fontSize: '12px',
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
  }

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
          contentStyle={tooltipStyle}
        />
        <Legend
          iconSize={10}
          iconType="circle"
          formatter={(value) => (
            <span style={{ fontSize: '11px', color: isDark ? '#9ca3af' : '#4b5563' }}>
              {value}
            </span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
