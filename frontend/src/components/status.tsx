import type { BadgeTone } from './ui/badge'
import { Badge } from './ui/badge'

export const STATUS_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  active: { label: '进行中', tone: 'success' },
  planning: { label: '规划中', tone: 'warning' },
  paused: { label: '已暂停', tone: 'info' },
  archived: { label: '已归档', tone: 'neutral' },
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_MAP[status] ?? { label: status, tone: 'neutral' as BadgeTone }
  return <Badge tone={s.tone}>{s.label}</Badge>
}

const PRIORITY_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  high: { label: '高', tone: 'error' },
  medium: { label: '中', tone: 'warning' },
  low: { label: '低', tone: 'info' },
}

export function priorityTone(p: string): BadgeTone {
  return PRIORITY_MAP[p]?.tone ?? 'neutral'
}

export function priorityLabel(p: string): string {
  return PRIORITY_MAP[p]?.label ?? p
}
