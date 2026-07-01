import { Link } from 'react-router-dom'
import { Home } from 'lucide-react'
import { Button } from '../components/ui/Button'

export function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <p className="text-8xl font-black text-gray-100 dark:text-gray-800">404</p>
      <div>
        <p className="text-lg font-semibold text-gray-900 dark:text-white">Page not found</p>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          The page you're looking for doesn't exist.
        </p>
      </div>
      <Link to="/">
        <Button>
          <Home size={15} />
          Back to Dashboard
        </Button>
      </Link>
    </div>
  )
}
