import { createContext, useContext, useState } from 'react'
import type { OptimizeResponse } from '../types/portfolio'

interface PortfolioContextValue {
  currentPortfolio: OptimizeResponse | null
  setCurrentPortfolio: (p: OptimizeResponse | null) => void
}

const PortfolioContext = createContext<PortfolioContextValue | null>(null)

export function PortfolioProvider({ children }: { children: React.ReactNode }) {
  const [currentPortfolio, setCurrentPortfolio] = useState<OptimizeResponse | null>(null)

  return (
    <PortfolioContext.Provider value={{ currentPortfolio, setCurrentPortfolio }}>
      {children}
    </PortfolioContext.Provider>
  )
}

export function usePortfolioContext() {
  const ctx = useContext(PortfolioContext)
  if (!ctx) throw new Error('usePortfolioContext must be used inside PortfolioProvider')
  return ctx
}
