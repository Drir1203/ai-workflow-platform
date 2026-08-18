import { useEffect, useState } from 'react'
import { Button } from '../ui/button'
import { Input, Textarea } from '../ui/input'
import { summarizeParams, type FlowNode, type WorkflowNodeData } from '../../lib/workflowGraph'
import type { AgentInfo, ParamTemplate, Project } from '../../types'

/** onPatch 允许修改的节点数据字段（label/agent_key/params/paramsSummary） */
type NodePatch = Partial<Pick<WorkflowNodeData, 'label' | 'agent_key' | 'params' | 'paramsSummary'>>

interface StepConfigPanelProps {
  /** 当前选中节点；null 时展示占位提示 */
  node: FlowNode | null
  agents: AgentInfo[]
  projects: Project[]
  templates: ParamTemplate[]
  onPatch: (nodeId: string, patch: NodePatch) => void
  /** 保存为预置模板，由父级负责创建并刷新模板列表 */
  onSaveTemplate: (agentKey: string, name: string, params: Record<string, unknown>) => Promise<void>
}

/** 按 schema 默认值 + 已有 params 生成表单初始值（值一律字符串，提交时按类型转换） */
function initialForm(agent: AgentInfo, params: Record<string, unknown>): Record<string, string> {
  const form: Record<string, string> = {}
  for (const p of agent.param_schema) {
    const v = params[p.name]
    form[p.name] = v === undefined || v === null ? String(p.default ?? '') : String(v)
  }
  return form
}

/** 从表单收集参数值（数字转 number，空字符串跳过），与 AgentsPage.collectParams 同规则 */
function collectParams(agent: AgentInfo, form: Record<string, string>): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  for (const p of agent.param_schema) {
    const raw = form[p.name] ?? ''
    if (p.type === 'number') {
      if (raw !== '') params[p.name] = Number(raw)
    } else if (raw !== '') {
      params[p.name] = raw
    }
  }
  return params
}

const selectCls =
  'h-9 w-full rounded-lg border border-line-soft bg-elev1 px-3 text-[13px] text-ink focus:border-gold-primary/60 focus:outline-none focus:ring-2 focus:ring-gold-primary/25'

export function StepConfigPanel({ node, agents, projects, templates, onPatch, onSaveTemplate }: StepConfigPanelProps) {
  const agent = agents.find((a) => a.key === node?.data.agent_key)
  const [form, setForm] = useState<Record<string, string>>({})
  const [tplId, setTplId] = useState('')
  const [tplName, setTplName] = useState('')
  const [savingTpl, setSavingTpl] = useState(false)

  // 选中节点或切换 agent 时重置表单：以节点现有 params 优先，缺省用 schema 默认
  useEffect(() => {
    if (node && agent) setForm(initialForm(agent, node.data.params))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node?.id, node?.data.agent_key])

  if (!node) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-[12px] text-ink-4">
        点击画布中的步骤节点配置参数
      </div>
    )
  }

  const setField = (name: string, value: string) => {
    const next = { ...form, [name]: value }
    setForm(next)
    if (agent) {
      const params = collectParams(agent, next)
      onPatch(node.id, { params, paramsSummary: summarizeParams(params) })
    }
  }

  const changeAgent = (key: string) => {
    const a = agents.find((x) => x.key === key)
    if (!a) return
    const next = initialForm(a, {})
    setForm(next)
    setTplId('')
    const params = collectParams(a, next)
    onPatch(node.id, { agent_key: key, params, paramsSummary: summarizeParams(params) })
  }

  const changeLabel = (label: string) => onPatch(node.id, { label })

  // 选中预置模板 → 按参数名回填表单并同步节点
  const applyTemplate = (id: string) => {
    setTplId(id)
    const tpl = templates.find((t) => t.id === id)
    if (!tpl || !agent) return
    const next = initialForm(agent, tpl.params)
    setForm(next)
    onPatch(node.id, { params: tpl.params, paramsSummary: summarizeParams(tpl.params) })
  }

  async function saveTemplate() {
    if (!agent || !tplName.trim() || savingTpl) return
    setSavingTpl(true)
    try {
      await onSaveTemplate(agent.key, tplName.trim(), collectParams(agent, form))
      setTplName('')
    } finally {
      setSavingTpl(false)
    }
  }

  const agentTemplates = agent ? templates.filter((t) => t.agent_key === agent.key) : []

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] text-ink-3">步骤名</label>
        <Input value={node.data.label} onChange={(e) => changeLabel(e.target.value)} placeholder="步骤名（可选）" />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-[12px] text-ink-3">智能体</label>
        <select className={selectCls} value={node.data.agent_key} onChange={(e) => changeAgent(e.target.value)}>
          <option value="">选择智能体…</option>
          {agents.map((a) => (
            <option key={a.key} value={a.key}>
              {a.name}（{a.key}）
            </option>
          ))}
        </select>
      </div>

      {agent && (
        <>
          {agentTemplates.length > 0 && (
            <div className="flex flex-col gap-1.5">
              <label className="text-[12px] text-ink-3">预置模板回填</label>
              <select
                className={selectCls}
                value={tplId}
                onChange={(e) => applyTemplate(e.target.value)}
                disabled={!agent}
              >
                <option value="">选择模板…</option>
                {agentTemplates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] text-ink-3">参数</label>
            {agent.param_schema.map((p) => (
              <div key={p.name} className="flex flex-col gap-1.5">
                <label className="text-[12px] text-ink-3">
                  {p.label}
                  {p.required && <span className="ml-0.5 text-gold">*</span>}
                </label>
                {p.type === 'project_id' ? (
                  <select
                    className={selectCls}
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                  >
                    <option value="">{p.placeholder || '全部项目'}</option>
                    {projects.map((pr) => (
                      <option key={pr.id} value={pr.id}>
                        {pr.name}
                      </option>
                    ))}
                  </select>
                ) : p.type === 'select' ? (
                  <select
                    className={selectCls}
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                  >
                    {p.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : p.type === 'textarea' ? (
                  <Textarea
                    rows={3}
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                ) : p.type === 'number' ? (
                  <Input
                    type="number"
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                ) : (
                  <Input
                    value={form[p.name] ?? ''}
                    onChange={(e) => setField(p.name, e.target.value)}
                    placeholder={p.placeholder}
                  />
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-1.5 border-t border-line pt-3">
            <label className="text-[12px] text-ink-3">存为预置模板</label>
            <div className="flex items-center gap-2">
              <Input
                value={tplName}
                onChange={(e) => setTplName(e.target.value)}
                placeholder="模板名"
                className="h-8 flex-1"
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={saveTemplate}
                disabled={!tplName.trim()}
                loading={savingTpl}
              >
                保存
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
