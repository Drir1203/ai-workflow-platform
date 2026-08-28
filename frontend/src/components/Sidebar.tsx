import type { ReactNode } from 'react'
import { cn } from '../lib/cn'
import type { View } from '../lib/view'
import type { Project } from '../types'
import { AgentIcon, DashboardIcon, SettingsIcon, WorkflowIcon } from './icons'

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
        <SideItem active={view.name === 'team'} onClick={() => onSelect({ name: 'team' })}>
          <SettingsIcon /> 团队
        </SideItem>
      </div>
    </aside>
  )
}
