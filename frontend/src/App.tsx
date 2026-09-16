import { useCallback, useEffect, useState } from 'react'
import { Shell } from './components/Shell'
import { Logo } from './components/Logo'
import { clearSession, getToken } from './lib/api'
import { detectMode, redetectMode } from './lib/mode'
import { LoginPage } from './pages/LoginPage'
import type { Mode } from './types'

export default function App() {
  const [mode, setMode] = useState<Mode | null>(null)
  const [authed, setAuthed] = useState(() => !!getToken())
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    detectMode().then(setMode)
  }, [])

  // 演示模式横幅上的「重试连接」：清掉探测缓存重来一次，
  // 后端恢复即刻切回真实数据（旧实现失败会永久缓存 demo，只能刷新页面）
  const retryConnect = useCallback(async () => {
    setRetrying(true)
    try {
      setMode(await redetectMode())
    } finally {
      setRetrying(false)
    }
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

  if (mode === 'demo')
    return <Shell mode="demo" onRetryConnect={retryConnect} retrying={retrying} />
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
