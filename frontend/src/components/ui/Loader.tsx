interface LoaderProps {
  label?: string
}

export function Loader({ label = 'Loading...' }: LoaderProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3">
      <div className="h-7 w-7 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  )
}
