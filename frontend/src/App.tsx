import { useEffect, useState } from 'react'
import { Shell } from './components/Shell'
import { Logo } from './components/Logo'
import { clearSession, getToken } from './lib/api'
import { detectMode } from './lib/mode'
import { LoginPage } from './pages/LoginPage'
import type { Mode } from './types'

export default function App() {
  const [mode, setMode] = useState<Mode | null>(null)
  const [authed, setAuthed] = useState(() => !!getToken())

  useEffect(() => {
    detectMode().then(setMode)
  }, [])

  if (!mode) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-bg">
        <div className="flex flex-col items-center gap-4">
          <Logo size={40} />
          <div className="flex gap-1.5">
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-gold" />
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-gold" style={{ animationDelay: '150ms' }} />
            <span className="h-2 w-2 animate-pulseDot rounded-full bg-gold" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    )
  }

  if (mode === 'demo') return <Shell mode="demo" />
  if (!authed) return <LoginPage onLogin={() => setAuthed(true)} />
  return (
    <Shell
      mode="live"
      onLogout={() => {
        clearSession()
        setAuthed(false)
      }}
    />
  )
}
