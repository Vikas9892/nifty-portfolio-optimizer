interface WeightsTableProps {
  weights: Record<string, number>
}

export function WeightsTable({ weights }: WeightsTableProps) {
  const sorted = Object.entries(weights)
    .filter(([, v]) => v > 0.001)
    .sort(([, a], [, b]) => b - a)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500 dark:border-gray-800 dark:text-gray-400">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium">Weight</th>
            <th className="w-full pb-2 font-medium">Allocation bar</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {sorted.map(([ticker, weight]) => (
            <tr key={ticker}>
              <td className="py-2.5 pr-6 font-mono text-xs font-medium text-gray-700 dark:text-gray-300">
                {ticker.replace('.NS', '')}
              </td>
              <td className="py-2.5 pr-6 text-right font-semibold text-gray-900 dark:text-white">
                {(weight * 100).toFixed(1)}%
              </td>
              <td className="py-2.5">
                <div className="h-1.5 overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                  <div
                    className="h-full rounded-full bg-blue-500 transition-all"
                    style={{ width: `${(weight * 100).toFixed(1)}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
