export const fmt = {
  /** Format a decimal as a percentage string. Pass signed=true for +/- prefix. */
  pct(value: number, signed = false): string {
    const abs = (Math.abs(value) * 100).toFixed(2) + '%'
    if (!signed) return abs
    return value >= 0 ? `+${abs}` : `-${abs}`
  },

  /** Format a date-time ISO string to a human-readable local string. */
  datetime(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  },

  /** Format a date ISO string to a short date. */
  date(iso: string): string {
    return new Date(iso).toLocaleDateString()
  },
}
