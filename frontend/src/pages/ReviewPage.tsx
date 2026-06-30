import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, BarChart3, CheckCircle2, Download, FileText, RefreshCw, Target, Trophy } from 'lucide-react'
import { reviewAPI, type ReviewAuditPayload, type ReviewRow, type TeamFeatureProfile } from '../services/api'

function pct(value?: number) {
  return `${(((value || 0) * 100)).toFixed(1)}%`
}

function signedPct(value?: number) {
  const percent = (value || 0) * 100
  return `${percent > 0 ? '+' : ''}${percent.toFixed(1)}%`
}

function formatDate(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function outcomeText(value?: string) {
  if (value === 'home') return '主胜'
  if (value === 'away') return '客胜'
  if (value === 'draw') return '平局'
  return '-'
}

function boolText(value: boolean) {
  return value ? '命中' : '未中'
}

function varianceNoteClass(type: string) {
  if (type === 'red_card_turning_point') return 'border border-red-100 bg-red-50/90 text-red-900'
  if (type === 'finishing_variance') return 'border border-amber-100 bg-amber-50/90 text-amber-900'
  if (type === 'match_control') return 'border border-blue-100 bg-blue-50/90 text-blue-900'
  return 'bg-white/72 text-slate-900'
}

function varianceNoteBadge(type: string) {
  if (type === 'red_card_turning_point') return '核心变量'
  if (type === 'finishing_variance') return '效率偏差'
  if (type === 'match_control') return '场面偏差'
  if (type === 'set_piece_pressure') return '定位球'
  if (type === 'card_discipline') return '纪律'
  return '复盘'
}

function scoreSlotLabel(slot: string) {
  if (slot === 'score_pick1') return '1选比分'
  if (slot === 'score_pick2') return '2选比分'
  if (slot === 'score_pick3') return '3选比分'
  if (slot === 'upset_score_hit') return '冷门比分'
  return slot
}

function csvEscape(value: unknown) {
  return `"${String(value ?? '').replace(/"/g, '""')}"`
}

function buildAuditCsv(audit: ReviewAuditPayload) {
  const header = [
    'match_id',
    'home_team',
    'away_team',
    'actual_score',
    'predicted_score',
    'wdl_hit',
    'score_pick1',
    'score_pick2',
    'score_pick3',
    'upset_score_hit',
    'score_total_hit',
    'total_goals_range',
    'total_goals_range_hit',
    'btts_view',
    'btts_hit',
    'evaluation_mode',
  ]
  const rows = audit.rows.map(row => [
    row.match_id,
    row.home_team,
    row.away_team,
    row.actual.score,
    row.prediction.score,
    row.accuracy.wdl_hit,
    row.accuracy.score_pick1,
    row.accuracy.score_pick2,
    row.accuracy.score_pick3,
    row.accuracy.upset_score_hit,
    row.accuracy.score_pool_hit,
    row.prediction.total_goals_range,
    row.accuracy.total_goals_range_hit,
    row.prediction.btts_view,
    row.accuracy.btts_hit,
    audit.evaluation_mode || 'pre_match_snapshot',
  ])
  return [header, ...rows].map(row => row.map(csvEscape).join(',')).join('\n')
}

function buildReportMarkdown(row: ReviewRow) {
  const notes = row.variance_notes.map(note => `- ${note.title}: ${note.detail}`).join('\n') || '- 暂无偏差说明'
  const lessons = row.lessons.map(item => `- ${item}`).join('\n') || '- 暂无复盘建议'
  const candidates = row.prediction.score_candidates.join(' / ') || '-'
  const scoreSlots = row.prediction.score_slots?.map(item => `${scoreSlotLabel(item.slot)}: ${item.score}`).join(' / ') || '-'
  return `# ${row.home_team} vs ${row.away_team} 复盘报告

- 比赛时间: ${formatDate(row.match_date)}
- 场地: ${row.venue || '-'}
- 实际比分: ${row.actual.score}
- 预测比分: ${row.prediction.score}
- 其他预测比分: ${candidates}
- 四项比分: ${scoreSlots}
- 胜平负命中: ${boolText(Boolean(row.accuracy.wdl_hit))}
- 1选命中: ${boolText(Boolean(row.accuracy.score_pick1))}
- 2选命中: ${boolText(Boolean(row.accuracy.score_pick2))}
- 3选命中: ${boolText(Boolean(row.accuracy.score_pick3))}
- 冷门命中: ${boolText(Boolean(row.accuracy.upset_score_hit))}
- 总命中率: ${boolText(Boolean(row.accuracy.score_pool_hit))}
- 总进球区间: ${row.prediction.total_goals_range || '-'}，${boolText(Boolean(row.accuracy.total_goals_range_hit))}
- 双方进球: ${row.prediction.btts_view || '-'}，${boolText(Boolean(row.accuracy.btts_hit))}

## 偏差原因

${notes}

## 下次预测注意

${lessons}

## 数据来源

- 来源: ${row.data_source.match}
- 状态: ${row.data_source.status}
- 更新时间: ${row.data_source.last_updated || '-'}
`
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 30000)
}

function TeamProfileCard({ profile }: { profile: TeamFeatureProfile }) {
  const tags = profile.tactical_tags || []
  const notes = profile.next_prediction_notes || profile.review_lessons || []
  return (
    <div className="rounded-2xl border border-white/60 bg-white/72 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-base font-black text-slate-950">{profile.team}</p>
          <p className="mt-1 text-xs font-bold text-slate-500">{profile.source_label || `${profile.sample_matches} 场样本`}</p>
        </div>
        <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-black text-cyan-700">
          {profile.form_state?.score?.toFixed?.(1) || profile.form_state?.score || '-'}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl bg-slate-50 p-2">
          <p className="text-[10px] font-bold text-slate-500">场均积分</p>
          <p className="text-sm font-black text-slate-900">{profile.form_state?.avg_points ?? '-'}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-2">
          <p className="text-[10px] font-bold text-slate-500">场均净胜</p>
          <p className="text-sm font-black text-slate-900">{profile.form_state?.avg_goal_diff ?? '-'}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-2">
          <p className="text-[10px] font-bold text-slate-500">纪律</p>
          <p className="text-sm font-black text-slate-900">{profile.discipline_state?.risk || '-'}</p>
        </div>
      </div>
      {tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tags.slice(0, 4).map(tag => (
            <span key={tag} className="rounded-full bg-blue-50 px-2 py-1 text-[10px] font-black text-blue-700">{tag}</span>
          ))}
        </div>
      )}
      {notes[0] && <p className="mt-3 text-xs font-semibold leading-relaxed text-slate-600">{notes[0]}</p>}
    </div>
  )
}

export default function ReviewPage() {
  const [audit, setAudit] = useState<ReviewAuditPayload | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const selectedRow = useMemo(() => {
    if (!audit?.rows.length) return null
    return audit.rows.find(row => row.match_id === selectedId) || audit.rows[0]
  }, [audit, selectedId])

  const isCurrentModelBacktest = audit?.evaluation_mode === 'current_model_backtest'
  const teamProfiles = audit?.team_profiles?.profiles
  const profileEntries = useMemo(
    () => Object.values(teamProfiles || {})
      .sort((a, b) => (b.form_state?.score || 0) - (a.form_state?.score || 0)),
    [teamProfiles],
  )
  const selectedTeamProfiles = useMemo(() => {
    if (!selectedRow || !teamProfiles) return []
    return [selectedRow.home_team, selectedRow.away_team]
      .map(team => teamProfiles[team])
      .filter((profile): profile is TeamFeatureProfile => Boolean(profile))
  }, [teamProfiles, selectedRow])
  const profileComparison = audit?.profile_comparison
  const totalTournamentMatches = audit
    ? audit.summary.total_matches || audit.team_profiles?.fixture_match_count || audit.team_profiles?.match_count || 104
    : 104

  const loadAudit = async (mode: 'snapshot' | 'backtest' = 'snapshot') => {
    setLoading(true)
    setError(null)
    try {
      const payload = mode === 'backtest'
        ? await reviewAPI.runCurrentModelBacktest()
        : await reviewAPI.getAudit()
      setAudit(payload)
      setSelectedId(payload.rows[0]?.match_id ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void reviewAPI.getAudit()
      .then(payload => {
        if (!active) return
        setAudit(payload)
        setSelectedId(payload.rows[0]?.match_id ?? null)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const handleDownloadCsv = async () => {
    if (audit?.evaluation_mode === 'current_model_backtest') {
      downloadBlob(
        new Blob([buildAuditCsv(audit)], { type: 'text/csv;charset=utf-8' }),
        'wc2026-current-model-backtest.csv',
      )
      return
    }
    const blob = await reviewAPI.downloadAuditCsv()
    downloadBlob(blob, 'wc2026-prediction-review.csv')
  }

  const handleDownloadReport = () => {
    if (!selectedRow) return
    const markdown = buildReportMarkdown(selectedRow)
    downloadBlob(new Blob([markdown], { type: 'text/markdown;charset=utf-8' }), `复盘报告-${selectedRow.home_team}-vs-${selectedRow.away_team}.md`)
  }

  return (
    <div className="space-y-6">
      <section className="glass-card p-5 sm:p-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-blue-600">
              <FileText className="h-4 w-4" />
              赛后复盘
            </p>
            <h1 className="mt-2 text-3xl font-black text-slate-950 sm:text-4xl">预测复盘</h1>
            <p className="mt-2 max-w-3xl text-sm font-semibold leading-relaxed text-slate-600">
              每场完赛后对照预测和真实结果，记录偏差原因，并把公开数据源里的真实表现转成下一轮的小幅校准权重。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => loadAudit()} className="btn-secondary inline-flex items-center gap-2" disabled={loading}>
              <RefreshCw className="h-4 w-4" />
              刷新复盘
            </button>
            <button type="button" onClick={() => loadAudit('backtest')} className="btn-secondary inline-flex items-center gap-2" disabled={loading}>
              <BarChart3 className="h-4 w-4" />
              现有模型一键回测
            </button>
            <button type="button" onClick={handleDownloadCsv} className="btn-secondary inline-flex items-center gap-2" disabled={!audit}>
              <Download className="h-4 w-4" />
              下载统计表
            </button>
            <button type="button" onClick={handleDownloadReport} className="btn-primary inline-flex items-center gap-2" disabled={!selectedRow}>
              <Download className="h-4 w-4" />
              下载单场报告
            </button>
          </div>
        </div>
      </section>

      {loading && (
        <div className="glass-card p-10 text-center text-sm font-black text-slate-700">
          正在同步公开数据源并生成复盘...
        </div>
      )}

      {error && (
        <div className="glass-card flex items-center gap-3 p-5 text-sm font-bold text-red-700">
          <AlertCircle className="h-5 w-5" />
          复盘数据加载失败：{error}
        </div>
      )}

      {audit && (
        <>
          <section className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 2xl:grid-cols-10">
            {[
              ['统计口径', isCurrentModelBacktest ? '模型回测' : '赛前快照', isCurrentModelBacktest ? '当前模型重跑' : '真实赛前样本', BarChart3],
              ['已复盘', `${audit.summary.reviewed_matches}/${totalTournamentMatches}`, '场总赛程', Trophy],
              ['胜平负命中', pct(audit.summary.wdl_accuracy), `${audit.summary.wdl_hits || 0}场命中`, CheckCircle2],
              ['1选命中', pct(audit.summary.score_pick1_accuracy), `${audit.summary.score_pick1_hits || 0}场命中`, Target],
              ['2选命中', pct(audit.summary.score_pick2_accuracy), `${audit.summary.score_pick2_hits || 0}场命中`, FileText],
              ['3选命中', pct(audit.summary.score_pick3_accuracy), `${audit.summary.score_pick3_hits || 0}场命中`, FileText],
              ['冷门命中', pct(audit.summary.upset_score_accuracy), `${audit.summary.upset_score_hits || 0}场命中`, AlertCircle],
              ['总命中率', pct(audit.summary.score_total_accuracy ?? audit.summary.score_pool_accuracy), `${audit.summary.score_total_hits ?? audit.summary.score_pool_hits ?? 0}场命中`, CheckCircle2],
              ['总进球区间', pct(audit.summary.total_goals_range_accuracy), `${audit.summary.total_goals_range_hits || 0}场命中`, BarChart3],
              ['BTTS', pct(audit.summary.btts_accuracy), `${audit.summary.btts_hits || 0}场命中`, CheckCircle2],
            ].map(([label, value, sub, Icon]) => (
              <div key={String(label)} className="glass-card p-5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-slate-500">{label as string}</span>
                  <Icon className="h-5 w-5 text-blue-600" />
                </div>
                <p className="mt-3 text-3xl font-black text-slate-950">{value as string}</p>
                <p className="mt-1 text-xs font-semibold text-slate-500">{sub as string}</p>
              </div>
            ))}
          </section>

          {isCurrentModelBacktest && profileComparison && (
            <section className="glass-card p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-black uppercase tracking-wide text-cyan-700">Profile A/B</p>
                  <h2 className="mt-1 text-xl font-black text-slate-950">球队特征库前后对比</h2>
                  <p className="mt-1 text-xs font-semibold text-slate-500">同一批已完赛样本，其他模型层保持一致，仅对比是否启用球队 profile。</p>
                </div>
                <span className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-black text-cyan-700">
                  {profileComparison.with_profile.reviewed_matches || audit.summary.reviewed_matches} 场样本
                </span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  ['胜平负', 'wdl_accuracy'],
                  ['首选比分', 'score_pick1_accuracy'],
                  ['总命中率', 'score_total_accuracy'],
                  ['总进球区间', 'total_goals_range_accuracy'],
                  ['BTTS', 'btts_accuracy'],
                ].map(([label, key]) => (
                  <div key={key} className="rounded-2xl bg-white/75 p-4">
                    <p className="text-xs font-bold text-slate-500">{label}</p>
                    <p className="mt-2 text-2xl font-black text-slate-950">
                      {pct(profileComparison.with_profile[key as keyof typeof profileComparison.with_profile] as number)}
                    </p>
                    <p className={`mt-1 text-xs font-black ${(profileComparison.delta[key as keyof typeof profileComparison.delta] || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {signedPct(profileComparison.delta[key as keyof typeof profileComparison.delta] as number)}
                    </p>
                    <p className="mt-1 text-[11px] font-semibold text-slate-500">
                      关闭库 {pct(profileComparison.without_profile[key as keyof typeof profileComparison.without_profile] as number)}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {profileEntries.length > 0 && (
            <section className="glass-card p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-black uppercase tracking-wide text-blue-600">Team Memory</p>
                  <h2 className="mt-1 text-xl font-black text-slate-950">球队模型记忆</h2>
                  <p className="mt-1 text-xs font-semibold text-slate-500">
                    赛程共 {audit.team_profiles?.fixture_match_count || audit.team_profiles?.match_count || 104} 场；
                    已生成 {audit.team_profiles?.profile_count || profileEntries.length} 支球队档案，
                    参考 {audit.team_profiles?.feature_source_match_count || audit.team_profiles?.match_count || 0} 条赛前/赛后特征样本。
                  </p>
                </div>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">
                  {profileEntries.length} 队
                </span>
              </div>
              <div className="mt-4 grid max-h-[430px] gap-3 overflow-auto pr-1 sm:grid-cols-2 xl:grid-cols-3">
                {profileEntries.map(profile => (
                  <TeamProfileCard key={profile.team} profile={profile} />
                ))}
              </div>
            </section>
          )}

          <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/60 p-5">
                <h2 className="text-xl font-black text-slate-950">预测与真实结果对照</h2>
                <p className="mt-1 text-xs font-semibold text-slate-500">{audit.source_policy}</p>
                {audit.metric_definitions && (
                  <div className="mt-3 grid gap-2 text-xs font-semibold leading-relaxed text-slate-600 sm:grid-cols-2">
                    {['wdl_hit', 'score_pick1', 'score_pick2', 'score_pick3', 'upset_score_hit', 'score_pool_hit', 'total_goals_range_hit', 'btts_hit'].map(key => (
                      <p key={key} className="rounded-2xl bg-white/65 px-3 py-2">
                        {audit.metric_definitions?.[key]}
                      </p>
                    ))}
                  </div>
                )}
              </div>
              <div className="max-h-[560px] overflow-auto">
                <table className="w-full min-w-[1220px] text-left text-sm">
                  <thead className="sticky top-0 bg-white/90 text-xs font-black uppercase text-slate-500 backdrop-blur">
                    <tr>
                      <th className="px-5 py-3">比赛</th>
                      <th className="px-5 py-3">时间</th>
                      <th className="px-5 py-3">预测</th>
                      <th className="px-5 py-3">实际</th>
                      <th className="px-5 py-3">胜平负</th>
                      <th className="px-5 py-3">1选命中</th>
                      <th className="px-5 py-3">2选命中</th>
                      <th className="px-5 py-3">3选命中</th>
                      <th className="px-5 py-3">冷门命中</th>
                      <th className="px-5 py-3">总命中</th>
                      <th className="px-5 py-3">总进球区间</th>
                      <th className="px-5 py-3">BTTS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.rows.length === 0 && (
                      <tr>
                        <td className="px-5 py-10 text-center text-sm font-bold text-slate-500" colSpan={12}>
                          暂无可计算真实准确率的赛前预测快照；完赛但无快照的比赛已列为缺失样本，不纳入命中率。
                        </td>
                      </tr>
                    )}
                    {audit.rows.map(row => (
                      <tr
                        key={row.match_id}
                        className={`cursor-pointer border-t border-white/60 transition-colors hover:bg-white/70 ${selectedRow?.match_id === row.match_id ? 'bg-blue-50/70' : ''}`}
                        onClick={() => setSelectedId(row.match_id)}
                      >
                        <td className="px-5 py-4 font-black text-slate-900">{row.home_team} vs {row.away_team}</td>
                        <td className="px-5 py-4 font-semibold text-slate-500">{formatDate(row.match_date)}</td>
                        <td className="px-5 py-4 font-black text-blue-700">{row.prediction.score}</td>
                        <td className="px-5 py-4 font-black text-emerald-700">{row.actual.score}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.wdl_hit))}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.score_pick1))}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.score_pick2))}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.score_pick3))}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.upset_score_hit))}</td>
                        <td className="px-5 py-4">{boolText(Boolean(row.accuracy.score_pool_hit))}</td>
                        <td className="px-5 py-4">
                          <span className="font-bold text-slate-700">{row.prediction.total_goals_range || '-'}</span>
                          <span className="ml-2 text-xs font-bold text-slate-500">{boolText(Boolean(row.accuracy.total_goals_range_hit))}</span>
                        </td>
                        <td className="px-5 py-4">
                          <span className="font-bold text-slate-700">{row.prediction.btts_view || '-'}</span>
                          <span className="ml-2 text-xs font-bold text-slate-500">{boolText(Boolean(row.accuracy.btts_hit))}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <aside className="glass-card p-5">
              {selectedRow ? (
                <div className="space-y-5">
                  <div>
                    <p className="text-xs font-black uppercase text-blue-600">已选复盘</p>
                    <h2 className="mt-1 text-2xl font-black text-slate-950">{selectedRow.home_team} vs {selectedRow.away_team}</h2>
                    <p className="mt-1 text-sm font-semibold text-slate-500">{formatDate(selectedRow.match_date)} · {selectedRow.venue}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
	                    <div className="rounded-2xl bg-white/72 p-4">
	                      <p className="text-xs font-bold text-slate-500">预测比分</p>
	                      <p className="mt-1 text-3xl font-black text-blue-700">{selectedRow.prediction.score}</p>
	                      <p className="mt-1 text-xs font-semibold text-slate-500">{selectedRow.prediction.score_candidates.join(' / ')}</p>
	                      {selectedRow.prediction.score_slots && (
	                        <p className="mt-1 text-[11px] font-semibold text-slate-500">
	                          四项比分：{selectedRow.prediction.score_slots.map(item => item.score).join(' / ')}
	                        </p>
	                      )}
	                    </div>
                    <div className="rounded-2xl bg-white/72 p-4">
                      <p className="text-xs font-bold text-slate-500">实际比分</p>
                      <p className="mt-1 text-3xl font-black text-emerald-700">{selectedRow.actual.score}</p>
                      <p className="mt-1 text-xs font-semibold text-slate-500">{outcomeText(selectedRow.actual.outcome)}</p>
                    </div>
                  </div>
                  {selectedTeamProfiles.length > 0 && (
                    <div>
                      <h3 className="text-sm font-black text-slate-900">两队最新模型记忆</h3>
                      <div className="mt-2 grid gap-3">
                        {selectedTeamProfiles.map(profile => (
                          <TeamProfileCard key={profile.team} profile={profile} />
                        ))}
                      </div>
                    </div>
                  )}
                  <div>
                    <h3 className="text-sm font-black text-slate-900">偏差原因</h3>
                    <div className="mt-2 space-y-2">
                      {selectedRow.variance_notes.map(note => (
                        <div key={`${note.type}-${note.title}`} className={`rounded-2xl p-3 ${varianceNoteClass(note.type)}`}>
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-black">{note.title}</p>
                            <span className="rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-black">
                              {varianceNoteBadge(note.type)}
                            </span>
                          </div>
                          <p className="mt-1 text-xs font-semibold leading-relaxed opacity-85">{note.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-slate-900">下次预测注意</h3>
                    <ul className="mt-2 space-y-2 text-xs font-semibold leading-relaxed text-slate-600">
                      {selectedRow.lessons.map(item => <li key={item} className="rounded-2xl bg-white/72 p-3">{item}</li>)}
                    </ul>
                  </div>
                </div>
              ) : (
                <p className="text-sm font-bold text-slate-500">暂无已完成比赛可复盘。</p>
              )}
            </aside>
          </section>
        </>
      )}
    </div>
  )
}
