import type { ComponentType } from 'react'
import { cn } from '../lib/cn'
import type { View } from '../lib/view'
import { AgentIcon, DashboardIcon, WorkflowIcon, type IconProps } from './icons'

// 移动端底部标签栏：桌面侧边栏在 <768px 被隐藏，需要这条入口到达智能体/工作流。
// 工作台/项目仍可从工作台卡片进入；项目在侧边栏单独列出，故此处只放三个顶层视图。
const ITEMS: { key: 'dashboard' | 'agents' | 'workflows'; label: string; Icon: ComponentType<IconProps> }[] = [
  { key: 'dashboard', label: '工作台', Icon: DashboardIcon },
  { key: 'agents', label: '智能体', Icon: AgentIcon },
  { key: 'workflows', label: '工作流', Icon: WorkflowIcon },
]

export function MobileNav({ view, onSelect }: { view: View; onSelect: (v: View) => void }) {
  return (
    <nav className="flex shrink-0 items-stretch border-t border-line bg-elev1 pb-[env(safe-area-inset-bottom)] md:hidden">
      {ITEMS.map(({ key, label, Icon }) => {
        const active = view.name === key
        return (
          <button
            key={key}
            onClick={() => onSelect({ name: key })}
            className={cn(
              'flex flex-1 flex-col items-center gap-1 py-2.5 text-[10.5px] transition-colors duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-primary/60',
              active ? 'text-gold' : 'text-ink-4 hover:text-ink-2',
            )}
          >
            <Icon />
            <span>{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
