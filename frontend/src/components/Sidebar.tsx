import type { ReactNode } from 'react'
import { cn } from '../lib/cn'
import type { View } from '../lib/view'
import type { Project } from '../types'

function SideItem({
  active,
  disabled,
  onClick,
  children,
}: {
  active?: boolean
  disabled?: boolean
  onClick?: () => void
  children: ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'flex items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-primary/60',
        active ? 'bg-active text-gold shadow-inner-light' : 'text-ink-2 hover:bg-active/60 hover:text-ink',
        disabled && 'cursor-not-allowed opacity-40',
      )}
    >
      {children}
    </button>
  )
}

function DashboardIcon({ className }: { className?: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function AgentIcon({ className }: { className?: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <rect x="9" y="9" width="6" height="6" rx="1.5" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4M5 5l2.5 2.5M16.5 16.5 19 19M19 5l-2.5 2.5M7.5 16.5 5 19" strokeLinecap="round" />
    </svg>
  )
}

function WorkflowIcon({ className }: { className?: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <circle cx="5" cy="6" r="2" />
      <circle cx="5" cy="18" r="2" />
      <circle cx="19" cy="12" r="2" />
      <path d="M5 8v8M7 6h7a2 2 0 0 1 2 2v2M17 14v-2" strokeLinecap="round" />
    </svg>
  )
}

function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function Sidebar({
  projects,
  view,
  onSelect,
}: {
  projects: Project[]
  view: View
  onSelect: (v: View) => void
}) {
  return (
    <aside className="hidden w-[184px] shrink-0 flex-col gap-6 border-r border-line bg-elev1 p-3 md:flex">
      <nav className="flex flex-col gap-1">
        <SideItem active={view.name === 'dashboard'} onClick={() => onSelect({ name: 'dashboard' })}>
          <DashboardIcon /> 工作台
        </SideItem>
        <SideItem active={view.name === 'agents'} onClick={() => onSelect({ name: 'agents' })}>
          <AgentIcon /> 智能体
        </SideItem>
        <SideItem active={view.name === 'workflows'} onClick={() => onSelect({ name: 'workflows' })}>
          <WorkflowIcon /> 工作流
        </SideItem>
      </nav>
      <div className="flex flex-col gap-1">
        <div className="px-2 pb-1 text-[10px] font-medium uppercase tracking-[.08em] text-ink-5">项目</div>
        {projects.map((p) => (
          <SideItem
            key={p.id}
            active={view.name === 'project' && view.id === p.id}
            onClick={() => onSelect({ name: 'project', id: p.id })}
          >
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full bg-current"
              style={{ boxShadow: '0 0 5px currentColor' }}
            />
            <span className="truncate">{p.name}</span>
          </SideItem>
        ))}
      </div>
      <div className="mt-auto flex flex-col gap-1">
        <SideItem disabled>
          <SettingsIcon /> 设置
        </SideItem>
      </div>
    </aside>
  )
}
