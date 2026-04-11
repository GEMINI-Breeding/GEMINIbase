import { Moon, Sun } from 'lucide-react'
import { useEffect, useState } from 'react'

export function Topbar() {
  const [dark, setDark] = useState(() =>
    typeof window !== 'undefined' && document.documentElement.classList.contains('dark')
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  return (
    <header className="h-12 border-b border-border bg-background flex items-center justify-between px-4 shrink-0">
      <div />
      <button
        onClick={() => setDark(!dark)}
        className="p-2 rounded-md hover:bg-muted transition-colors"
        aria-label="Toggle dark mode"
      >
        {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </header>
  )
}
