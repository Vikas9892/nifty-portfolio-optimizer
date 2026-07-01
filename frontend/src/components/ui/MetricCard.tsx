interface MetricCardProps {
  label: string
  value: string
  delta?: string
  /** When provided, colors both the value and the delta text green (true) or red (false). */
  positive?: boolean
}

export function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  const valueColor =
    positive === true
      ? 'text-emerald-500'
      : positive === false
        ? 'text-red-500'
        : 'text-gray-900 dark:text-white'

  return (
    <div className="card p-5">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        {label}
      </p>
      <p className={`mt-1.5 text-2xl font-bold ${valueColor}`}>{value}</p>
      {delta && (
        <p
          className={`mt-1 text-xs font-medium ${
            positive ? 'text-emerald-500' : 'text-red-500'
          }`}
        >
          {delta}
        </p>
      )}
    </div>
  )
}
