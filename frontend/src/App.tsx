import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import { PortfolioProvider } from './context/PortfolioContext'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Layout } from './components/layout/Layout'
import { AdminDashboard } from './pages/AdminDashboard'
import { Dashboard } from './pages/Dashboard'
import { Optimize } from './pages/Optimize'
import { History } from './pages/History'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { NotFound } from './pages/NotFound'

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <PortfolioProvider>
            <Toaster
              position="top-right"
              toastOptions={{
                style: {
                  background: '#111827',
                  color: '#f9fafb',
                  border: '1px solid #1f2937',
                  fontSize: '13px',
                },
              }}
            />
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Protected routes — redirect to /login if not authenticated */}
              <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="optimize" element={<Optimize />} />
                  <Route path="history" element={<History />} />
                  <Route path="admin" element={<AdminDashboard />} />
                </Route>
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </PortfolioProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
