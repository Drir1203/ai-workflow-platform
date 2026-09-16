import type { Mode } from '../types'

export const BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://127.0.0.1:8000'

// 探测超时。线上实测 TTFB 约 0.7s（跨境反代 + 容器），但冷启动、容器重启、
// 现场网络抖动都会吃掉余量 —— 原值 1.5s 只有 2 倍冗余，一次抖动就够把整个
// 前端钉死在演示模式（且旧实现会把失败结果永久缓存，再也切不回来）。
const PROBE_TIMEOUT_MS = 5000

let mode: Mode | null = null

export async function detectMode(): Promise<Mode> {
  if (mode) return mode
  try {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), PROBE_TIMEOUT_MS)
    const res = await fetch(`${BASE}/health`, { signal: ctrl.signal })
    clearTimeout(timer)
    mode = res.ok ? 'live' : 'demo'
  } catch {
    // 关键：失败结果**不写入缓存**。演示现场后端只是抖一下，
    // 不该因此永久降级；调用方可随时重试（见 redetectMode）。
    return 'demo'
  }
  return mode
}

/** 清掉探测缓存并重跑，供演示模式横幅上的「重试连接」调用。 */
export async function redetectMode(): Promise<Mode> {
  mode = null
  return detectMode()
}

export function getMode(): Mode {
  return mode ?? 'demo'
}
