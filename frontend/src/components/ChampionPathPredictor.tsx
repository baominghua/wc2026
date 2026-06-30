import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, ArrowRight, ChevronsRight, RefreshCw, ShieldCheck, Sparkles, Trophy } from 'lucide-react'
import { tournamentAPI, type TournamentProjectedMatch, type TournamentProjection } from '../services/api'
import TeamFlag from './TeamFlag'

function buildMatchMap(projection: TournamentProjection) {
  const matches = [
    ...(projection.knockout?.rounds['Round of 32'] || projection.round_of_32 || []),
    ...(projection.knockout?.rounds['Round of 16'] || []),
    ...(projection.knockout?.rounds['Quarter-final'] || []),
    ...(projection.knockout?.rounds['Semi-final'] || []),
    ...(projection.knockout?.rounds.Final || []),
    ...(projection.knockout?.rounds['Third place'] || []),
  ]
  return new Map(matches.map(match => [match.id, match]))
}

function scoreText(match?: TournamentProjectedMatch | null) {
  if (!match) return '-'
  if (match.home_score !== null && match.home_score !== undefined && match.away_score !== null && match.away_score !== undefined) {
    return `${match.home_score}-${match.away_score}`
  }
  return match.prediction?.predicted_score || '-'
}

function decisionLabel(match?: TournamentProjectedMatch | null) {
  if (!match) return '待生成'
  if (match.decided_by === 'penalties' || match.resolution === 'penalties') return '点球'
  if (match.decided_by === 'extra_time' || match.resolution === 'extra_time_or_penalties') return '加时/点球'
  return match.score_source === 'actual' ? '真实比分' : '模型预测'
}

function formatDate(value?: string) {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  } catch {
    return value
  }
}

function TeamPill({ team, winner, align = 'left' }: { team: string; winner?: boolean; align?: 'left' | 'right' }) {
  return (
    <div className={`flex min-w-0 items-center gap-2 rounded-2xl px-3 py-2 ${
      winner ? 'bg-cyan-300/18 text-slate-950 ring-1 ring-cyan-300/30' : 'bg-white/55 text-slate-800'
    } ${align === 'right' ? 'justify-end' : ''}`}>
      {align === 'left' && <TeamFlag teamName={team} size="sm" />}
      <span className="truncate text-sm font-black">{team || '待定'}</span>
      {align === 'right' && <TeamFlag teamName={team} size="sm" />}
    </div>
  )
}

function MatchSnapshot({ label, match }: { label: string; match?: TournamentProjectedMatch | null }) {
  const homeWinner = Boolean(match && match.winner === match.home_team)
  const awayWinner = Boolean(match && match.winner === match.away_team)

  return (
    <article className="rounded-[22px] border border-white/55 bg-white/55 p-3 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-black uppercase text-blue-600">{label}</p>
        <span className="rounded-full bg-slate-900/7 px-2 py-0.5 text-[11px] font-black text-slate-500">
          {decisionLabel(match)}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
        <TeamPill team={match?.home_team || '待定'} winner={homeWinner} />
        <span className="rounded-2xl bg-cyan-300 px-3 py-1 text-lg font-black text-slate-950 shadow-sm">
          {scoreText(match)}
        </span>
        <TeamPill team={match?.away_team || '待定'} winner={awayWinner} align="right" />
      </div>
    </article>
  )
}

function SummaryTile({
  label,
  value,
  hint,
  tone = 'blue',
}: {
  label: string
  value: string | number
  hint: string
  tone?: 'blue' | 'green' | 'amber' | 'slate'
}) {
  const toneClass = {
    blue: 'from-blue-500 to-cyan-400',
    green: 'from-emerald-500 to-teal-400',
    amber: 'from-amber-400 to-yellow-300',
    slate: 'from-slate-500 to-blue-400',
  }[tone]

  return (
    <div className="rounded-[22px] border border-white/55 bg-white/58 p-3 shadow-sm">
      <p className="text-xs font-black text-blue-600">{label}</p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200/75">
        <div className={`h-full rounded-full bg-gradient-to-r ${toneClass}`} style={{ width: '78%' }} />
      </div>
      <p className="mt-3 text-2xl font-black leading-none text-slate-950">{value}</p>
      <p className="mt-2 text-[11px] font-bold leading-4 text-slate-500">{hint}</p>
    </div>
  )
}

function RouteTile({
  label,
  value,
  hint,
  isLast,
}: {
  label: string
  value: string
  hint: string
  isLast?: boolean
}) {
  return (
    <div className="relative rounded-[22px] border border-white/55 bg-white/58 p-3 shadow-sm">
      {!isLast && (
        <ChevronsRight className="absolute right-[-0.85rem] top-1/2 z-10 hidden h-5 w-5 -translate-y-1/2 text-blue-500 sm:block" />
      )}
      <p className="text-xs font-black text-blue-600">{label}</p>
      <p className="mt-2 min-h-[2.5rem] text-base font-black leading-5 text-slate-950">{value}</p>
      <p className="mt-2 text-[11px] font-bold leading-4 text-slate-500">{hint}</p>
    </div>
  )
}

export default function ChampionPathPredictor() {
  const [projection, setProjection] = useState<TournamentProjection | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProjection = async () => {
    if (!projection) setLoading(true)
    setRefreshing(true)
    setError(null)
    try {
      const data = await tournamentAPI.getProjection(true)
      setProjection(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '出线预测加载失败')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    let active = true
    void tournamentAPI.getProjection(true)
      .then(data => {
        if (active) setProjection(data)
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : '鍑虹嚎棰勬祴鍔犺浇澶辫触')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const matchMap = useMemo(() => (projection ? buildMatchMap(projection) : new Map<number, TournamentProjectedMatch>()), [projection])
  const finalMatch = matchMap.get(104)
  const thirdMatch = matchMap.get(103)
  const champion = projection?.knockout?.champion || finalMatch?.winner || '-'
  const runnerUp = projection?.knockout?.runner_up || finalMatch?.loser || '-'
  const thirdPlace = projection?.knockout?.third_place || thirdMatch?.winner || '-'
  const qualifiedThirdGroups = useMemo(() => (
    projection?.best_thirds.filter(row => row.qualified).map(row => row.group).join(' / ') || '-'
  ), [projection])
  const qualifierPreview = useMemo(() => projection?.qualifiers.slice(0, 8) || [], [projection])

  const routeTiles = projection ? [
    {
      label: '小组出线',
      value: `${projection.summary.qualified_count} 队`,
      hint: `真实 ${projection.summary.actual_group_match_count} 场，模型补齐 ${projection.summary.model_group_match_count} 场`,
    },
    {
      label: '32强入口',
      value: `${projection.round_of_32.length || projection.knockout?.rounds['Round of 32']?.length || 0} 场`,
      hint: `最佳第三：${qualifiedThirdGroups}`,
    },
    {
      label: '半决赛',
      value: `${projection.knockout?.rounds['Semi-final']?.length || 0} 场`,
      hint: `按 Annex C #${projection.summary.third_place_option} 落位`,
    },
    {
      label: '决赛',
      value: finalMatch ? `${finalMatch.home_team} vs ${finalMatch.away_team}` : '待生成',
      hint: `预测比分 ${scoreText(finalMatch)}`,
    },
    {
      label: '冠军',
      value: champion,
      hint: `亚军 ${runnerUp}，季军 ${thirdPlace}`,
    },
  ] : []

  return (
    <section className="glass-card overflow-hidden">
      <div className="grid gap-4 p-4 lg:grid-cols-[0.86fr_1.14fr] lg:p-5">
        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-xl font-black text-slate-900">
                <ShieldCheck className="h-5 w-5 text-blue-600" />
                小组出线与淘汰赛快照
              </h2>
              <p className="mt-1 text-sm font-medium text-slate-500">
                首页简版与出线预测页共用同一套模拟数据
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void loadProjection()}
                disabled={refreshing}
                className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-3 py-2 text-sm font-black text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 active:scale-95"
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                刷新模拟
              </button>
              <Link
                to="/tournament"
                className="inline-flex items-center gap-2 rounded-2xl bg-white/75 px-3 py-2 text-sm font-black text-blue-700 ring-1 ring-white/70 transition hover:bg-white"
              >
                完整预测
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-[22px] border border-red-200 bg-red-50/80 p-3 text-sm font-bold text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>出线预测加载失败：{error}</span>
            </div>
          )}

          {loading ? (
            <div className="rounded-[24px] border border-white/50 bg-white/58 p-4">
              <div className="h-4 w-32 animate-pulse rounded-full bg-slate-200" />
              <div className="mt-4 h-12 animate-pulse rounded-2xl bg-slate-200/80" />
              <div className="mt-3 h-20 animate-pulse rounded-3xl bg-slate-200/65" />
            </div>
          ) : (
            <div className="rounded-[24px] border border-amber-200/60 bg-amber-50/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-yellow-300/30 ring-1 ring-yellow-300/45">
                    <Trophy className="h-6 w-6 text-amber-600" />
                  </span>
                  <div>
                    <p className="text-xs font-black uppercase text-amber-700">当前冠军模拟</p>
                    <div className="mt-1 flex items-center gap-2">
                      <TeamFlag teamName={champion} size="md" />
                      <p className="text-xl font-black text-slate-950">{champion}</p>
                    </div>
                  </div>
                </div>
                <span className="rounded-full bg-white/75 px-3 py-1 text-xs font-black text-slate-500">
                  {formatDate(projection?.generated_at)}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs font-black">
                <span className="rounded-2xl bg-white/65 px-3 py-2 text-slate-600">亚军：{runnerUp}</span>
                <span className="rounded-2xl bg-white/65 px-3 py-2 text-slate-600">季军：{thirdPlace}</span>
                <span className="rounded-2xl bg-white/65 px-3 py-2 text-slate-600">规则：C #{projection?.summary.third_place_option || '-'}</span>
              </div>
            </div>
          )}

          {!loading && projection && (
            <div className="rounded-[24px] border border-white/50 bg-white/58 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-black uppercase text-blue-600">32强名单预览</p>
                <Link to="/tournament" className="text-xs font-black text-blue-600 hover:text-blue-700">
                  查看全部
                </Link>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {qualifierPreview.map(row => (
                  <div key={`${row.group}-${row.rank}-${row.team}`} className="flex min-w-0 items-center gap-2 rounded-2xl bg-white/65 px-3 py-2">
                    <TeamFlag teamName={row.team} size="sm" />
                    <span className="min-w-0 flex-1 truncate text-sm font-black text-slate-800">{row.team}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-black ${
                      row.rank <= 2 ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                    }`}>
                      {row.group}{row.rank}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="grid gap-2 sm:grid-cols-4">
            <SummaryTile
              label="真实比分"
              value={projection?.summary.actual_group_match_count ?? '-'}
              hint="完赛优先读取真实赛果"
              tone="green"
            />
            <SummaryTile
              label="模型补齐"
              value={projection?.summary.model_group_match_count ?? '-'}
              hint="未赛由当前模型补齐"
              tone="blue"
            />
            <SummaryTile
              label="32强名额"
              value={projection?.summary.qualified_count ?? '-'}
              hint={`最佳第三：${qualifiedThirdGroups}`}
              tone="slate"
            />
            <SummaryTile
              label="冠军模拟"
              value={champion}
              hint="同源生成淘汰赛路径"
              tone="amber"
            />
          </div>

          <div className="grid gap-2 sm:grid-cols-5">
            {routeTiles.map((step, index) => (
              <RouteTile
                key={step.label}
                label={step.label}
                value={step.value}
                hint={step.hint}
                isLast={index === routeTiles.length - 1}
              />
            ))}
          </div>

          <div className="grid gap-2 xl:grid-cols-2">
            <MatchSnapshot label="M104 决赛" match={finalMatch} />
            <MatchSnapshot label="M103 季军战" match={thirdMatch} />
          </div>

          <div className="flex items-center gap-2 rounded-[22px] border border-white/55 bg-white/50 px-3 py-2 text-xs font-bold text-slate-500">
            <Sparkles className="h-4 w-4 text-blue-600" />
            <span>首页只保留关键信息；完整小组排名、32强路径和导出海报请进入出线预测页。</span>
          </div>
        </div>
      </div>
    </section>
  )
}
