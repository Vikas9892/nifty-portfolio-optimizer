import { LogOut, Moon, Sun } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useTheme } from '../../context/ThemeContext'
import { useAuth } from '../../hooks/useAuth'

export function Navbar() {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    toast.success('Signed out.')
    navigate('/login', { replace: true })
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6 dark:border-gray-800 dark:bg-gray-900">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Nifty 50 · Mean-Variance Portfolio Optimizer
      </p>

      <div className="flex items-center gap-3">
        {user && (
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
            {user.name}
          </span>
        )}

        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {user && (
          <button
            onClick={handleLogout}
            title="Sign out"
            className="rounded-lg p-2 text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-gray-400 dark:hover:bg-red-950 dark:hover:text-red-400"
          >
            <LogOut size={17} />
          </button>
        )}
      </div>
    </header>
  )
}
