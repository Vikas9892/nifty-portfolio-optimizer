interface MetricCardProps {
  label: string
  value: string
  delta?: string
  positive?: boolean
}

export function MetricCard({ label, value, delta, positive }: MetricCardProps) {
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
        {label}
      </p>
      <p className="mt-1.5 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
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
