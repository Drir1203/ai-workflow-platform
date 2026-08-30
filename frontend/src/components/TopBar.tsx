import type { DataLayer } from '../lib/view'
import type { Mode, User } from '../types'
import { Brand } from './Logo'
import { NotificationBell } from './NotificationBell'
import { ThemeSwitcher } from './ThemeSwitcher'
import { Badge } from './ui/badge'
import { Button } from './ui/button'

interface TopBarProps {
  mode: Mode
  layer: DataLayer
  user?: User | null
  onLogout?: () => void
}

export function TopBar({ mode, layer, user, onLogout }: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-elev1 px-5">
      <Brand />
      <div className="flex items-center gap-3">
        <NotificationBell layer={layer} />
        <ThemeSwitcher />
        {mode === 'demo' && <Badge tone="gold">演示模式</Badge>}
        {mode === 'live' && user && (
          <>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-gold to-gold-deep text-[11px] font-semibold text-[#1A1406]">
                {user.name.slice(0, 1).toUpperCase()}
              </div>
              <span className="text-[12px] text-ink-2">{user.name}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={onLogout}>
              退出
            </Button>
          </>
        )}
      </div>
    </header>
  )
}
