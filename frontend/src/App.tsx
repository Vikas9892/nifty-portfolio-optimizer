import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import { PortfolioProvider } from './context/PortfolioContext'
import { Layout } from './components/layout/Layout'
import { Dashboard } from './pages/Dashboard'
import { Optimize } from './pages/Optimize'
import { History } from './pages/History'
import { NotFound } from './pages/NotFound'

export default function App() {
  return (
    <ThemeProvider>
      <PortfolioProvider>
        <BrowserRouter>
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
            <Route element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="optimize" element={<Optimize />} />
              <Route path="history" element={<History />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </PortfolioProvider>
    </ThemeProvider>
  )
}
