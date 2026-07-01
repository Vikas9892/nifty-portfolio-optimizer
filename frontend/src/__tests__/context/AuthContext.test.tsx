import { act, render, renderHook, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import type { ReactNode } from 'react'
import { AuthProvider, useAuthContext } from '../../context/AuthContext'

// ── Mock the authService module ───────────────────────────────────────────────
vi.mock('../../services/authService', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    me: vi.fn(),
  },
}))

import { authService } from '../../services/authService'

const mockAuthService = vi.mocked(authService)

const MOCK_USER = { id: 1, name: 'Alice', email: 'alice@test.com', is_active: true, created_at: '' }
const MOCK_AUTH = {
  user: MOCK_USER,
  tokens: { access_token: 'at123', refresh_token: 'rt456', token_type: 'bearer', expires_in: 900 },
}

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}

// ── Setup / Teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  // Default: /me fails (no token) → fast path in the hook
  mockAuthService.me.mockRejectedValue(new Error('Not authenticated'))
})

afterEach(() => {
  localStorage.clear()
})

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AuthContext', () => {
  it('resolves to null user and loading=false when no token stored', async () => {
    // RTL's renderHook wraps in act() which flushes effects before returning,
    // so the no-token path (synchronous setLoading(false)) completes immediately.
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user).toBeNull()
  })

  it('sets user in localStorage on login', async () => {
    mockAuthService.login.mockResolvedValue(MOCK_AUTH)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.login({ email: 'alice@test.com', password: 'pass' })
    })

    expect(result.current.user?.email).toBe('alice@test.com')
    expect(localStorage.getItem('access_token')).toBe('at123')
    expect(localStorage.getItem('refresh_token')).toBe('rt456')
  })

  it('sets user in localStorage on register', async () => {
    mockAuthService.register.mockResolvedValue(MOCK_AUTH)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.register({ name: 'Alice', email: 'alice@test.com', password: 'pass' })
    })

    expect(result.current.user?.name).toBe('Alice')
    expect(localStorage.getItem('access_token')).toBe('at123')
  })

  it('clears session on logout', async () => {
    mockAuthService.login.mockResolvedValue(MOCK_AUTH)
    mockAuthService.logout.mockResolvedValue(undefined)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.login({ email: 'alice@test.com', password: 'pass' })
    })
    expect(result.current.user).not.toBeNull()

    await act(async () => {
      await result.current.logout()
    })

    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('restores user from localStorage on mount when token present', async () => {
    localStorage.setItem('user', JSON.stringify(MOCK_USER))
    localStorage.setItem('access_token', 'at123')
    mockAuthService.me.mockResolvedValue(MOCK_USER)

    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user?.email).toBe('alice@test.com')
  })

  it('clears session when /me fails on mount', async () => {
    localStorage.setItem('user', JSON.stringify(MOCK_USER))
    localStorage.setItem('access_token', 'stale-token')
    mockAuthService.me.mockRejectedValue(new Error('401'))

    const { result } = renderHook(() => useAuthContext(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('throws when useAuthContext is used outside AuthProvider', () => {
    // Suppress the React error boundary console.error noise
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => renderHook(() => useAuthContext())).toThrow(
      'useAuthContext must be used inside <AuthProvider>',
    )
    spy.mockRestore()
  })
})
