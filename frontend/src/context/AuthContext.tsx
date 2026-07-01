import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { authService } from '../services/authService'
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '../types/auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (req: LoginRequest) => Promise<void>
  register: (req: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function persistSession(auth: AuthResponse) {
  localStorage.setItem('access_token', auth.tokens.access_token)
  localStorage.setItem('refresh_token', auth.tokens.refresh_token)
  localStorage.setItem('user', JSON.stringify(auth.user))
}

function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const verified = useRef(false)

  // On mount: restore user from localStorage, then silently verify with /me
  useEffect(() => {
    if (verified.current) return
    verified.current = true

    const raw = localStorage.getItem('user')
    if (raw) {
      try {
        setUser(JSON.parse(raw))
      } catch {
        clearSession()
      }
    }

    const token = localStorage.getItem('access_token')
    if (token) {
      authService
        .me()
        .then((freshUser) => {
          setUser(freshUser)
          localStorage.setItem('user', JSON.stringify(freshUser))
        })
        .catch(() => {
          // /me failed even after auto-refresh — clear everything
          clearSession()
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = useCallback(async (req: LoginRequest) => {
    const auth = await authService.login(req)
    persistSession(auth)
    setUser(auth.user)
  }, [])

  const register = useCallback(async (req: RegisterRequest) => {
    const auth = await authService.register(req)
    persistSession(auth)
    setUser(auth.user)
  }, [])

  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try {
        await authService.logout(refreshToken)
      } catch {
        // Server revocation failure is non-critical — clear client side anyway
      }
    }
    clearSession()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuthContext must be used inside <AuthProvider>')
  return ctx
}
