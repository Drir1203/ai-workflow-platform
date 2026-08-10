import type { Mode } from '../types'

export const BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

let mode: Mode | null = null

export async function detectMode(): Promise<Mode> {
  if (mode) return mode
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 1500)
    const res = await fetch(`${BASE}/health`, { signal: ctrl.signal })
    clearTimeout(timer)
    mode = res.ok ? 'live' : 'demo'
  } catch {
    mode = 'demo'
  }
  return mode
}

export function getMode(): Mode {
  return mode ?? 'demo'
}
