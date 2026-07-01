import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from './Button'

interface ErrorCardProps {
  message: string
  onRetry?: () => void
}

export function ErrorCard({ message, onRetry }: ErrorCardProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-950">
        <AlertCircle className="text-red-500" size={22} />
      </div>
      <div>
        <p className="text-sm font-semibold text-gray-900 dark:text-white">
          Something went wrong
        </p>
        <p className="mt-1 max-w-xs text-sm text-gray-500 dark:text-gray-400">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          <RefreshCw size={14} />
          Retry
        </Button>
      )}
    </div>
  )
}
