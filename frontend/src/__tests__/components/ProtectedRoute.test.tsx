import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from '../../components/auth/ProtectedRoute'

// We mock the hook so we control the auth state
vi.mock('../../hooks/useAuth', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../../hooks/useAuth'

const mockedUseAuth = vi.mocked(useAuth)

function renderRoute(authState: { user: object | null; loading: boolean }) {
  mockedUseAuth.mockReturnValue(authState as ReturnType<typeof useAuth>)
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  it('shows a loader while auth is being determined', () => {
    renderRoute({ user: null, loading: true })
    // Loader component renders — just check dashboard isn't shown yet
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })

  it('redirects to /login when user is null and not loading', () => {
    renderRoute({ user: null, loading: false })
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('renders outlet when user is authenticated', () => {
    renderRoute({ user: { id: 1, email: 'a@b.com' }, loading: false })
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument()
  })
})
