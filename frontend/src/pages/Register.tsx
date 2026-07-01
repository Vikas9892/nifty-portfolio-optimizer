import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Moon, Sun, TrendingUp } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../context/ThemeContext'
import { Button } from '../components/ui/Button'

export function Register() {
  const { register } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()

  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      toast.error('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await register({ name: form.name, email: form.email, password: form.password })
      toast.success('Account created! Welcome aboard.')
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const field = (
    id: keyof typeof form,
    label: string,
    type: string,
    placeholder: string,
    autoComplete?: string,
  ) => (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <input
        type={type}
        autoComplete={autoComplete}
        required
        value={form[id]}
        onChange={(e) => setForm((f) => ({ ...f, [id]: e.target.value }))}
        className="w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:placeholder:text-gray-500 dark:focus:border-blue-500"
        placeholder={placeholder}
      />
    </div>
  )

  return (
    <div className="flex min-h-screen flex-col bg-gray-50 dark:bg-gray-950">
      {/* Top bar */}
      <div className="flex h-14 items-center justify-between px-6 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2">
          <TrendingUp size={18} className="text-blue-600" />
          <span className="text-sm font-bold text-gray-900 dark:text-white">Nifty Optimizer</span>
        </div>
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
      </div>

      {/* Card */}
      <div className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-6 text-center">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">Create account</h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Start optimizing your Nifty 50 portfolio
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {field('name', 'Full name', 'text', 'Jane Doe', 'name')}
              {field('email', 'Email', 'email', 'you@example.com', 'email')}
              {field('password', 'Password', 'password', '••••••••', 'new-password')}
              {field('confirm', 'Confirm password', 'password', '••••••••', 'new-password')}

              <p className="text-xs text-gray-400 dark:text-gray-500">
                Min 8 characters, must include a letter and a digit.
              </p>

              <Button type="submit" variant="primary" className="w-full" loading={loading}>
                Create account
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-gray-500 dark:text-gray-400">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-blue-600 hover:underline dark:text-blue-400"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
