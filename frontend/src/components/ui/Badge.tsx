type Tone = 'blue' | 'green' | 'yellow' | 'red' | 'gray'

const TONES: Record<Tone, string> = {
  blue:   'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  green:  'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  yellow: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300',
  red:    'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  gray:   'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
}

export function Badge({
  children,
  tone = 'gray',
}: {
  children: React.ReactNode
  tone?: Tone
}) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  )
}
