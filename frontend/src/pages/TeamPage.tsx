import { useEffect, useState, type FormEvent } from 'react'
import type { BadgeTone } from '../components/ui/badge'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card } from '../components/ui/card'
import { Empty } from '../components/ui/empty'
import { Input } from '../components/ui/input'
import type { DataLayer } from '../lib/view'
import type { TeamMember, User } from '../types'

const ROLE_MAP: Record<string, { label: string; tone: BadgeTone }> = {
  owner: { label: 'Owner', tone: 'gold' },
  member: { label: 'Member', tone: 'info' },
  readonly: { label: '只读', tone: 'neutral' },
}

const ROLE_OPTIONS = ['owner', 'member', 'readonly'] as const

/** 团队管理：成员列表 + owner 专属的邀请/改角色/移除。团队 = 共享 tenant_id 的一组用户。 */
export function TeamPage({ layer, currentUser }: { layer: DataLayer; currentUser: User | null }) {
  const [members, setMembers] = useState<TeamMember[]>([])
  const [email, setEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'member' | 'readonly'>('member')
  const [invite, setInvite] = useState<{ code: string; invite_url: string } | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layer])

  async function refresh() {
    try {
      setMembers(await layer.listTeamMembers())
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载成员失败')
    }
  }

  // 当前用户在成员中；demo 模式 currentUser 为 null 时退化为第一个成员（owner），保证演示可管理
  const me = members.find((m) => m.id === currentUser?.id) ?? members[0]
  const isOwner = me?.role === 'owner'

  async function submitInvite(e: FormEvent) {
    e.preventDefault()
    if (!email.trim()) return
    try {
      const r = await layer.createInvite(email.trim(), inviteRole)
      setInvite(r)
      setEmail('')
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成邀请失败')
    }
  }

  async function changeRole(id: string, role: string) {
    try {
      await layer.updateMemberRole(id, role)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '修改角色失败')
    }
  }

  async function remove(m: TeamMember) {
    if (window.confirm(`确定移除「${m.name}」？该成员将退出团队，其在团队中的数据将不可见。`)) {
      try {
        await layer.removeMember(m.id)
        setInvite(null)
        await refresh()
      } catch (err) {
        setError(err instanceof Error ? err.message : '移除失败')
      }
    }
  }

  async function copyLink() {
    if (!invite) return
    const url = `${window.location.origin}${invite.invite_url}`
    try {
      await navigator.clipboard.writeText(url)
      setError('')
    } catch {
      setError('复制失败，请手动复制链接')
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <header>
        <h1 className="text-[20px] font-[650] tracking-tight text-ink">团队</h1>
        <p className="mt-1 text-[12.5px] text-ink-3">共享工作区的成员与角色权限。Owner 可邀请、改角色、移除成员。</p>
      </header>

      {error && <div className="rounded-lg border border-error/20 bg-error/10 px-3 py-2 text-[12px] text-error">{error}</div>}

      {isOwner ? (
        <Card className="p-4">
          <h2 className="mb-3 text-[13px] font-semibold text-ink-2">邀请成员</h2>
          <form onSubmit={submitInvite} className="flex flex-wrap items-center gap-2">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="对方邮箱"
              className="min-w-[220px] flex-1"
              required
            />
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as 'member' | 'readonly')}
              className="h-9 rounded-lg border border-line-soft bg-elev1 px-2 text-[12px] text-ink-2 focus:border-gold-primary/60 focus:outline-none"
            >
              <option value="member">可编辑</option>
              <option value="readonly">只读</option>
            </select>
            <Button size="sm" type="submit" disabled={!email.trim()}>
              生成邀请链接
            </Button>
          </form>
          {invite && (
            <div className="mt-3 rounded-lg border border-gold/20 bg-gold-tint/30 p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] font-medium text-gold">邀请链接（7 天内有效）</span>
                <Button size="sm" variant="ghost" onClick={copyLink}>
                  复制
                </Button>
              </div>
              <code className="mt-1 block break-all font-mono text-[11px] text-ink-2">
                {`${window.location.origin}${invite.invite_url}`}
              </code>
              <div className="mt-2 text-[11px] text-ink-4">
                或复制邀请码：<code className="font-mono text-ink-3">{invite.code}</code>
              </div>
            </div>
          )}
        </Card>
      ) : (
        <Card>
          <Empty title="只读查看" hint="联系管理员（Owner）邀请你加入团队，或调整你的角色。" />
        </Card>
      )}

      <Card className="p-4">
        <div className="flex items-center justify-between border-b border-line pb-2">
          <h2 className="text-[13px] font-semibold text-ink-2">成员</h2>
          <span className="rounded-full bg-elev2 px-2 py-0.5 font-mono text-[10.5px] tabular-nums text-ink-4">
            {members.length}
          </span>
        </div>
        {members.length === 0 ? (
          <Empty title="还没有成员" hint="通过邀请链接邀请他人加入团队。" />
        ) : (
          <div className="divide-y divide-line">
            {members.map((m) => {
              const ro = ROLE_MAP[m.role] ?? { label: m.role, tone: 'neutral' as BadgeTone }
              const self = m.id === me?.id
              return (
                <div key={m.id} className="flex items-center gap-3 py-2.5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gold-primary/15 font-[600] text-gold">
                    {m.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-[13px] text-ink">
                      {m.name}
                      {self && <span className="ml-1.5 text-[11px] text-ink-4">（我）</span>}
                    </div>
                    <div className="truncate text-[11px] text-ink-4">{m.email}</div>
                  </div>
                  <div className="ml-auto flex shrink-0 items-center gap-2">
                    {isOwner && !self ? (
                      <>
                        <select
                          value={m.role}
                          onChange={(e) => void changeRole(m.id, e.target.value)}
                          className="h-8 rounded-lg border border-line-soft bg-elev1 px-2 text-[12px] text-ink-2 focus:border-gold-primary/60 focus:outline-none"
                        >
                          {ROLE_OPTIONS.map((r) => (
                            <option key={r} value={r}>
                              {ROLE_MAP[r].label}
                            </option>
                          ))}
                        </select>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-error hover:bg-error/10"
                          onClick={() => void remove(m)}
                        >
                          移除
                        </Button>
                      </>
                    ) : (
                      <Badge tone={ro.tone}>{ro.label}</Badge>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
