import type { Edge, Node } from '@xyflow/react'
import type { WorkflowStep } from '../types'

/** 自定义节点尺寸与间距（与画布渲染保持一致） */
export const NODE_W = 220
export const NODE_H = 96
export const X_GAP = 56

/** 画布节点数据：label/agent_key/params 为持久化核心，其余为渲染/交互辅助 */
export type WorkflowNodeData = {
  label: string
  agent_key: string
  params: Record<string, unknown>
  /** agent 展示名（agent_key 未匹配到注册表时的兜底） */
  agentName: string
  /** 参数摘要（截断后），避免每次渲染重算 */
  paramsSummary: string
  onDelete?: (nodeId: string) => void
  onSelect?: (nodeId: string) => void
}

export type FlowNode = Node<WorkflowNodeData, 'agentStep'>
export type FlowEdge = Edge

/** 参数摘要：键值对连接，超长截断，防撑破节点卡片 */
export function summarizeParams(params: Record<string, unknown>, max = 40): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
  const joined = parts.join(', ')
  return joined.length > max ? joined.slice(0, max) + '…' : joined
}

/** 会话内稳定新节点 id（勿用 random，避免 StrictMode 双跑抖动） */
export function newNodeId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // 非 secure context 兜底：时间戳 + 随机后缀
  return `n-${Date.now()}-${Math.floor(Math.random() * 1e6)}`
}

/**
 * steps[]（线性）→ 画布图结构。
 * 无 node_id 用下标派生（n-${i}），无 position 自动水平排布；相邻下标连边。
 */
export function stepsToGraph(steps: WorkflowStep[]): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const nodes: FlowNode[] = steps.map((s, i) => {
    const id = s.node_id ?? `n-${i}`
    return {
      id,
      type: 'agentStep',
      position: s.position ?? { x: i * (NODE_W + X_GAP), y: 0 },
      data: {
        label: s.label,
        agent_key: s.agent_key,
        params: s.params ?? {},
        agentName: s.agent_key,
        paramsSummary: summarizeParams(s.params ?? {}),
      },
    }
  })
  const edges: FlowEdge[] = nodes.slice(0, -1).map((n, i) => ({
    id: `e-${n.id}-${nodes[i + 1].id}`,
    source: n.id,
    target: nodes[i + 1].id,
  }))
  return { nodes, edges }
}

/**
 * 画布图结构 → steps[]（线性化），含单链校验。
 * 失败返回 { error }，成功返回按链序排列的 steps。
 */
export function graphToSteps(
  nodes: FlowNode[],
  edges: FlowEdge[],
): { steps: WorkflowStep[] } | { error: string } {
  if (nodes.length === 0) return { steps: [] }

  // 建 out / indeg，出度 > 1 报错
  const out = new Map<string, string>()
  const indeg = new Map<string, number>()
  for (const n of nodes) {
    out.set(n.id, '')
    indeg.set(n.id, 0)
  }
  for (const e of edges) {
    if (!out.has(e.source) || !out.has(e.target)) continue
    if (out.get(e.source) !== '') return { error: '每节点最多一个出边：当前为分支结构，后续版本支持' }
    out.set(e.source, e.target)
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1)
  }

  // 多起点报错
  const heads = nodes.filter((n) => (indeg.get(n.id) ?? 0) === 0)
  if (heads.length > 1) return { error: '存在多个起点：请连接成单一链条' }

  // 沿 out 遍历，遇环或断链报错
  const order: string[] = []
  const seen = new Set<string>()
  let cur = heads[0]?.id
  while (cur) {
    if (seen.has(cur)) return { error: '存在循环连线：请断开形成环的边' }
    seen.add(cur)
    order.push(cur)
    cur = out.get(cur) ?? ''
  }
  if (seen.size !== nodes.length) {
    return { error: '存在断链/孤立节点：请连接所有步骤或删除孤立节点' }
  }

  const byId = new Map(nodes.map((n) => [n.id, n]))
  const steps: WorkflowStep[] = order.map((id) => {
    const n = byId.get(id)!
    return {
      label: n.data.label || n.data.agentName || n.data.agent_key,
      agent_key: n.data.agent_key,
      params: n.data.params,
      node_id: n.id,
      position: { x: n.position.x, y: n.position.y },
    }
  })
  return { steps }
}

/** 从 target 出发沿出边能否绕回 source（含自环）→ 新建此边会产生环 */
export function wouldCreateCycle(edges: FlowEdge[], source: string, target: string): boolean {
  if (source === target) return true
  const out = new Map<string, string>()
  for (const e of edges) {
    if (!out.has(e.source)) out.set(e.source, e.target)
  }
  const seen = new Set<string>()
  let cur = target
  while (cur) {
    if (cur === source) return true
    if (seen.has(cur)) return true
    seen.add(cur)
    const next = out.get(cur)
    if (!next) break
    cur = next
  }
  return false
}

/** 链头：唯一入度为 0 的节点（多起点时取第一个，供连接新节点定位） */
export function chainHead(nodes: FlowNode[], edges: FlowEdge[]): FlowNode | null {
  const indeg = new Set(edges.map((e) => e.target))
  return nodes.find((n) => !indeg.has(n.id)) ?? null
}

/** 链尾：唯一出度为 0 的节点（供追加新节点定位） */
export function chainTail(nodes: FlowNode[], edges: FlowEdge[]): FlowNode | null {
  const hasOut = new Set(edges.map((e) => e.source))
  return nodes.find((n) => !hasOut.has(n.id)) ?? null
}
