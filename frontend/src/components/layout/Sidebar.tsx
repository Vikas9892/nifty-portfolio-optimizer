import { LogOut, LayoutDashboard, TrendingUp, History, Settings } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/',         label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/optimize', label: 'Optimize',  icon: TrendingUp,      exact: false },
  { to: '/history',  label: 'History',   icon: History,         exact: false },
]

const DISABLED = [
  { label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    toast.success('Signed out.')
    navigate('/login', { replace: true })
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      {/* Logo */}
      <div className="border-b border-gray-200 px-6 py-5 dark:border-gray-800">
        <p className="text-base font-bold text-gray-900 dark:text-white">Nifty Optimizer</p>
        <p className="mt-0.5 text-xs text-gray-400">Portfolio Intelligence</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3 py-4">
        {NAV.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-white'
              }`
            }
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}

        {/* Disabled / coming-soon items */}
        <div className="mt-4 border-t border-gray-100 pt-4 dark:border-gray-800">
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
            Coming Soon
          </p>
          {DISABLED.map(({ label, icon: Icon }) => (
            <span
              key={label}
              className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-300 dark:text-gray-600"
            >
              <Icon size={17} />
              {label}
            </span>
          ))}
        </div>
      </nav>

      {/* User footer */}
      <div className="border-t border-gray-200 px-4 py-4 dark:border-gray-800">
        {user ? (
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-gray-700 dark:text-gray-200">
                {user.name}
              </p>
              <p className="truncate text-[10px] text-gray-400">{user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <p className="text-xs text-gray-400">Nifty 50 · 50 stocks · 14 sectors</p>
        )}
      </div>
    </aside>
  )
}
