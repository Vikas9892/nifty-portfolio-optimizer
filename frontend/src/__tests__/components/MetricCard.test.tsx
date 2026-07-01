import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MetricCard } from '../../components/ui/MetricCard'

describe('MetricCard', () => {
  it('renders label and value', () => {
    render(<MetricCard label="Sharpe Ratio" value="1.42" />)
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument()
    expect(screen.getByText('1.42')).toBeInTheDocument()
  })

  it('renders delta when provided', () => {
    render(<MetricCard label="Return" value="18%" delta="+3% vs Nifty" positive />)
    expect(screen.getByText('+3% vs Nifty')).toBeInTheDocument()
  })

  it('does not render delta element when not provided', () => {
    render(<MetricCard label="Return" value="18%" />)
    expect(screen.queryByText(/vs/i)).not.toBeInTheDocument()
  })

  it('shows green value color when positive=true', () => {
    render(<MetricCard label="X" value="10%" positive={true} />)
    const valueEl = screen.getByText('10%')
    expect(valueEl).toHaveClass('text-emerald-500')
  })

  it('shows red value color when positive=false', () => {
    render(<MetricCard label="X" value="-5%" positive={false} />)
    const valueEl = screen.getByText('-5%')
    expect(valueEl).toHaveClass('text-red-500')
  })

  it('shows neutral value color when positive not provided', () => {
    render(<MetricCard label="X" value="N/A" />)
    const valueEl = screen.getByText('N/A')
    expect(valueEl).toHaveClass('text-gray-900')
  })
})
