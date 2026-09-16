import { useState, type FormEvent } from 'react'
import { ApiError, api, setSession } from '../lib/api'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Logo } from '../components/Logo'
import { cn } from '../lib/cn'

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const res = isRegister
        ? await api.register(email, password, name)
        : await api.login(email, password)
      setSession(res)
      onLogin()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '网络错误，请确认后端已启动')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-bg p-4">
      <div className="pointer-events-none absolute -top-48 left-1/2 h-96 w-[720px] -translate-x-1/2 rounded-full bg-gold/5 blur-[120px]" />
      <div className="w-full max-w-[380px] animate-fadeUp">
        <div className="mb-8 flex flex-col items-center gap-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-[14px] border border-gold/25 bg-gold-tint shadow-gold">
            <Logo size={40} />
          </div>
          <div>
            <div className="text-[20px] font-[650] tracking-tight text-ink">
              Veya<span className="text-gold">Work</span> 雅秩
            </div>
            <p className="mt-1.5 text-[12.5px] text-ink-3">你的 AI 工作流指挥中心</p>
          </div>
        </div>

        <Card className="p-6">
          <div className="mb-5 flex rounded-lg border border-line-strong bg-elev1 p-1">
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setIsRegister(m === 'register')}
                className={cn(
                  'flex-1 rounded-md py-1.5 text-[13px] transition-colors duration-150',
                  (m === 'register') === isRegister
                    ? 'bg-active text-gold shadow-inner-light'
                    : 'text-ink-3 hover:text-ink',
                )}
              >
                {m === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="flex flex-col gap-4">
            {isRegister && (
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="昵称" required />
            )}
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="邮箱"
              required
            />
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="密码（至少 8 位）"
              required
            />
            {error && (
              <div className="rounded-lg border border-error/25 bg-error/10 px-3 py-2 text-[12px] text-error">
                {error}
              </div>
            )}
            <Button type="submit" loading={busy} className="w-full">
              {isRegister ? '创建账号' : '登录'}
            </Button>
          </form>
        </Card>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-ink-5">
          后端未启动时，页面会自动进入演示模式展示结构样例，无需登录。
        </p>
      </div>
    </div>
  )
}
