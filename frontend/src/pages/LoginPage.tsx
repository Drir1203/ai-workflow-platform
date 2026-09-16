import { useState, type FormEvent } from 'react'
import { ApiError, api, setSession } from '../lib/api'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Logo } from '../components/Logo'
import { cn } from '../lib/cn'

/** 能力概览：登录页给陌生访客的第一眼上下文（不单独做介绍页） */
const CAPABILITIES = [
  'AI 副驾 · 流式对话',
  '多智能体编排',
  '定时工作流',
  '知识库 RAG 问答',
]

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [guestBusy, setGuestBusy] = useState(false)

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

  // 访客入口：后端会保证演示账号与样例数据存在，这里只负责换 token。
  // 与登录/注册分开计 busy，避免互相把按钮置灰。
  async function enterAsGuest() {
    setError('')
    setGuestBusy(true)
    try {
      setSession(await api.guestLogin())
      onLogin()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '网络错误，请确认后端已启动')
    } finally {
      setGuestBusy(false)
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
            <p className="mt-2.5 text-[11.5px] leading-relaxed text-ink-4">
              把项目、任务、笔记收进同一个工作台，让 AI 副驾与定时工作流接手重复动作 ——
              你只负责决定做什么。
            </p>
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

          {/* 访客入口：给没有账号的访客（面试官 / 简历链接点进来的人）一条不用注册的路 */}
          <div className="my-4 flex items-center gap-3">
            <span className="h-px flex-1 bg-line" />
            <span className="text-[10.5px] text-ink-5">或</span>
            <span className="h-px flex-1 bg-line" />
          </div>
          <Button
            type="button"
            variant="secondary"
            loading={guestBusy}
            onClick={enterAsGuest}
            className="w-full"
          >
            无需注册，直接体验
          </Button>
          <p className="mt-2 text-center text-[10.5px] leading-relaxed text-ink-5">
            进入共享的演示租户（内置样例数据，改动对所有访客可见）
          </p>
        </Card>

        <ul className="mt-5 grid grid-cols-2 gap-x-3 gap-y-1.5">
          {CAPABILITIES.map((c) => (
            <li key={c} className="flex items-center gap-1.5 text-[11px] text-ink-4">
              <span className="h-1 w-1 shrink-0 rounded-full bg-gold/70" />
              {c}
            </li>
          ))}
        </ul>

        <p className="mt-5 text-center text-[11px] leading-relaxed text-ink-5">
          连不上后端时页面会退回演示模式，届时展示的是内存样例数据与预设回复，
          并非真实数据；登录后所见才是平台真实内容。
        </p>
      </div>
    </div>
  )
}
