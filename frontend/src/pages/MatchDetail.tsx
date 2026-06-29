import { useEffect, useState, type KeyboardEvent } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, Calendar, Clock, Users, Target, BarChart3, Trophy, ListChecks, Flag } from 'lucide-react'
import { TEAMS, getEffectiveMatchStage, getStageNameCN } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'
import { matchAPI } from '../services/api'
import TeamFlag from '../components/TeamFlag'
import TeamFlagLink from '../components/TeamFlagLink'
import { getPredictMatchPath } from '../utils/navigation'

export default function MatchDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const matchId = parseInt(id || '0')
  const [match, setMatch] = useState<Match | undefined>()
  const [liveMatches, setLiveMatches] = useState<Match[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const fetchMatch = async () => {
      setIsLoading(true)
      const [detailResult, matchesResult] = await Promise.allSettled([
        matchAPI.getMatchDetail(matchId),
        matchAPI.getMatchesStrict(),
      ])
      if (!active) return

      if (matchesResult.status === 'fulfilled') {
        setLiveMatches(matchesResult.value)
      } else {
        setLiveMatches([])
      }

      if (detailResult.status === 'fulfilled') {
        setMatch(detailResult.value)
        setLoadError(null)
      } else if (matchesResult.status === 'fulfilled') {
        const fallbackMatch = matchesResult.value.find(item => item.id === matchId)
        setMatch(fallbackMatch)
        setLoadError(fallbackMatch ? null : '实时比赛详情未找到。')
      } else {
        setMatch(undefined)
        setLoadError('实时比赛详情读取失败，请重新登录或稍后刷新。')
      }
      setIsLoading(false)
    }
    void fetchMatch()
    return () => {
      active = false
    }
  }, [matchId])

  const openMatchPrediction = (targetMatchId: number) => {
    navigate(getPredictMatchPath(targetMatchId))
  }

  const handleMatchCardKeyDown = (event: KeyboardEvent<HTMLElement>, targetMatchId: number) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openMatchPrediction(targetMatchId)
    }
  }

  if (isLoading && !match) {
    return (
      <div className="glass-card py-20 text-center">
        <p className="text-lg font-bold text-gray-600">正在同步实时比赛详情...</p>
      </div>
    )
  }

  if (!match) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-500 text-lg">{loadError || '比赛信息未找到'}</p>
        <Link to="/matches" className="text-blue-600 hover:underline mt-4 inline-block">返回赛程列表</Link>
      </div>
    )
  }

  const homeTeam = TEAMS.find(t => t.name === match.home_team)
  const awayTeam = TEAMS.find(t => t.name === match.away_team)
  const effectiveStage = getEffectiveMatchStage(match)
  const report = match.report
  const relatedMatches = liveMatches.filter(m => m.group === match.group && m.round === match.round && m.id !== match.id)

  const formatMatchDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')} 北京时间`
  }

  const stats = report?.stats as Record<string, unknown> | undefined
  const getStat = (key: string) => typeof stats?.[key] === 'number' ? stats[key] as number : null
  const statRows = report ? [
    { label: '控球率', home: getStat('possession_home'), away: getStat('possession_away'), suffix: '%' },
    { label: '射门', home: getStat('shots_home'), away: getStat('shots_away') },
    { label: '射正', home: getStat('shots_on_target_home'), away: getStat('shots_on_target_away') },
    { label: '预期进球', home: getStat('xg_home'), away: getStat('xg_away') },
    { label: '角球', home: getStat('corners_home'), away: getStat('corners_away') },
    { label: '犯规', home: getStat('fouls_home'), away: getStat('fouls_away') },
    { label: '黄牌', home: getStat('yellow_cards_home'), away: getStat('yellow_cards_away') },
    { label: '传球', home: getStat('passes_home'), away: getStat('passes_away') },
  ].filter((row): row is { label: string; home: number; away: number; suffix?: string } => row.home !== null && row.away !== null) : []

  const renderStatRow = (row: { label: string; home: number; away: number; suffix?: string }) => {
    const total = Math.max(row.home + row.away, 1)
    const homeWidth = `${(row.home / total) * 100}%`
    const awayWidth = `${(row.away / total) * 100}%`
    return (
      <div key={row.label} className="space-y-2">
        <div className="grid grid-cols-[70px_1fr_70px] items-center gap-3 text-sm">
          <span className="text-left font-bold text-gray-900">{row.home}{row.suffix || ''}</span>
          <span className="text-center text-gray-500">{row.label}</span>
          <span className="text-right font-bold text-gray-900">{row.away}{row.suffix || ''}</span>
        </div>
        <div className="grid grid-cols-2 gap-1 overflow-hidden rounded-full bg-slate-100">
          <div className="flex justify-end bg-transparent">
            <div className="h-2 rounded-l-full bg-blue-600" style={{ width: homeWidth }} />
          </div>
          <div className="bg-transparent">
            <div className="h-2 rounded-r-full bg-emerald-500" style={{ width: awayWidth }} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link to="/matches" className="flex items-center text-blue-600 hover:underline">
        <ArrowLeft className="w-4 h-4 mr-1" /> 返回赛程列表
      </Link>

      <div className="glass-card p-5 sm:p-8">
        <div className="text-center mb-6">
          <div className="flex flex-wrap items-center justify-center gap-2 mb-2">
            {match.group && <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full font-semibold">{match.group}组</span>}
            {match.round && <span className="px-3 py-1 bg-green-100 text-green-700 text-sm rounded-full font-semibold">第{match.round}轮</span>}
            {effectiveStage && <span className="px-3 py-1 bg-purple-100 text-purple-700 text-sm rounded-full font-semibold">{getStageNameCN(effectiveStage)}</span>}
            {match.status === 'completed' && <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-sm rounded-full font-semibold">已完赛</span>}
            {match.status === 'live' && <span className="px-3 py-1 bg-blue-100 text-blue-700 text-sm rounded-full font-semibold">进行中</span>}
            {match.status === 'awaiting_result' && <span className="px-3 py-1 bg-amber-100 text-amber-700 text-sm rounded-full font-semibold">等待官方赛果</span>}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] items-center gap-5">
          <div className="text-center">
            <div className="mb-3">
              <TeamFlagLink teamName={match.home_team} flagCode={homeTeam?.flagCode} size="xl" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{match.home_team}</p>
            <p className="text-sm text-gray-500 mt-1">FIFA #{homeTeam?.fifa_rank} · Elo {homeTeam?.elo_rating}</p>
            {homeTeam?.is_host && <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded mt-1 inline-block">东道主</span>}
          </div>

          <div className="text-center rounded-2xl bg-white/70 px-6 py-4 shadow-sm">
            {match.status === 'completed' ? (
              <>
                <div className="text-4xl font-black text-green-600">{match.home_score}-{match.away_score}</div>
                <p className="mt-1 text-xs font-semibold text-gray-500">全场比分</p>
              </>
            ) : match.status === 'awaiting_result' ? (
              <>
                <p className="text-2xl font-black text-amber-600">待赛果</p>
                <p className="mt-1 text-xs font-semibold text-gray-500">等待实时源写入</p>
              </>
            ) : (
              <p className="text-4xl font-black text-gray-300">VS</p>
            )}
          </div>

          <div className="text-center">
            <div className="mb-3">
              <TeamFlagLink teamName={match.away_team} flagCode={awayTeam?.flagCode} size="xl" />
            </div>
            <p className="text-2xl font-bold text-gray-900">{match.away_team}</p>
            <p className="text-sm text-gray-500 mt-1">FIFA #{awayTeam?.fifa_rank} · Elo {awayTeam?.elo_rating}</p>
            {awayTeam?.is_host && <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded mt-1 inline-block">东道主</span>}
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-center gap-2 text-sm text-gray-500 sm:flex-row sm:flex-wrap sm:gap-x-6">
          <span className="flex items-center"><Calendar className="w-4 h-4 mr-1" />{formatMatchDate(match.match_date)}</span>
          <span className="flex items-center text-center"><MapPin className="w-4 h-4 mr-1" />{match.venue}</span>
        </div>
      </div>

      {match.status === 'completed' && report && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="glass-card p-5">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="text-sm text-gray-500">现场观众</p>
                  <p className="text-2xl font-black text-gray-900">{report.attendance.toLocaleString()}</p>
                </div>
              </div>
            </div>
            <div className="glass-card p-5">
              <div className="flex items-center gap-3">
                <Trophy className="h-5 w-5 text-amber-500" />
                <div>
                  <p className="text-sm text-gray-500">全场最佳</p>
                  <p className="text-xl font-black text-gray-900">{report.player_of_match}</p>
                </div>
              </div>
            </div>
            <div className="glass-card p-5">
              <div className="flex items-center gap-3">
                <Flag className="h-5 w-5 text-emerald-600" />
                <div>
                  <p className="text-sm text-gray-500">主裁判</p>
                  <p className="text-xl font-black text-gray-900">{report.referee}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="glass-card p-5 sm:p-6">
              <h2 className="mb-5 flex items-center gap-2 text-xl font-bold text-gray-900">
                <Target className="h-5 w-5 text-red-500" />
                进球时间线
              </h2>
              <div className="space-y-3">
                {report.goals.map(goal => {
                  const scoringTeam = TEAMS.find(t => t.name === goal.team)
                  return (
                    <div key={`${goal.minute}-${goal.player}`} className="flex items-start gap-4 rounded-xl bg-white/70 p-4 shadow-sm">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-black text-white">
                        {goal.minute}'
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <TeamFlag flagCode={scoringTeam?.flagCode} size="sm" />
                          <p className="font-bold text-gray-900">{goal.player}</p>
                          <span className="text-sm text-gray-500">{goal.team}</span>
                        </div>
                        {goal.assist && <p className="mt-1 text-sm text-gray-500">助攻：{goal.assist}</p>}
                        {goal.note && <p className="mt-1 text-xs text-gray-400">{goal.note}</p>}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="glass-card p-5 sm:p-6">
              <h2 className="mb-5 flex items-center gap-2 text-xl font-bold text-gray-900">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                数据统计
              </h2>
              <div className="mb-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3 text-sm font-semibold text-gray-700">
                <span className="text-left">{match.home_team}</span>
                <span className="text-gray-400">对比</span>
                <span className="text-right">{match.away_team}</span>
              </div>
              <div className="space-y-4">
                {statRows.length > 0 ? statRows.map(renderStatRow) : (
                  <p className="rounded-xl bg-white/70 px-4 py-6 text-center text-sm text-gray-500">
                    官方技术统计暂未接入，当前仅展示赛果、进球与赛后基础信息。
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="glass-card p-5 sm:p-6">
            <h2 className="mb-5 flex items-center gap-2 text-xl font-bold text-gray-900">
              <ListChecks className="h-5 w-5 text-blue-600" />
              首发阵容
            </h2>
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {report.lineups.map(lineup => {
                const team = TEAMS.find(t => t.name === lineup.team)
                return (
                  <div key={lineup.team} className="rounded-2xl bg-white/70 p-5 shadow-sm">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <TeamFlag flagCode={team?.flagCode} size="md" />
                        <div>
                          <p className="font-black text-gray-900">{lineup.team}</p>
                          <p className="text-xs text-gray-500">{lineup.coach ? `主教练：${lineup.coach}` : '主教练待确认'}</p>
                        </div>
                      </div>
                      <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-bold text-blue-700">{lineup.formation}</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {lineup.starters.map((player, index) => (
                        <div key={`${lineup.team}-${player}-${index}`} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-gray-700">
                          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-bold text-blue-600">{index + 1}</span>
                          <span className="truncate">{player}</span>
                        </div>
                      ))}
                    </div>
                    {lineup.substitutes && lineup.substitutes.length > 0 && (
                      <p className="mt-4 text-sm text-gray-500">主要替补：{lineup.substitutes.join('、')}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="glass-card p-5 sm:p-6">
            <h2 className="mb-3 text-xl font-bold text-gray-900">赛后备注</h2>
            <div className="space-y-2">
              {report.notes.map(note => (
                <p key={note} className="rounded-xl bg-white/70 px-4 py-3 text-sm leading-6 text-gray-600">{note}</p>
              ))}
            </div>
          </div>
        </>
      )}

      {match.status === 'completed' && !report && (
        <div className="glass-card p-6 text-center text-gray-500">
          这场比赛已有比分，详细赛后报告暂未接入。
        </div>
      )}

      {match.status === 'awaiting_result' && (
        <div className="glass-card p-6 text-center text-amber-700">
          {match.data_message || '这场比赛已过预计完场时间，但官方赛果、观众、进球和技术统计尚未进入实时数据源。'}
        </div>
      )}

      <div className="glass-card p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-blue-600" />
          {match.group}组 · 第{match.round}轮其他比赛
        </h2>
        <div className="space-y-3">
          {relatedMatches.map(m => {
            const mHome = TEAMS.find(t => t.name === m.home_team)
            const mAway = TEAMS.find(t => t.name === m.away_team)
            return (
              <article
                key={m.id}
                role="button"
                tabIndex={0}
                onClick={() => openMatchPrediction(m.id)}
                onKeyDown={(event) => handleMatchCardKeyDown(event, m.id)}
                className="flex cursor-pointer items-center justify-between gap-3 rounded-xl bg-gray-50 p-4 transition-colors hover:bg-blue-50 focus-visible:ring-4 focus-visible:ring-blue-500/20"
              >
                <div className="flex min-w-0 items-center gap-2">
                  <TeamFlagLink teamName={m.home_team} flagCode={mHome?.flagCode} size="sm" />
                  <span className="truncate font-medium text-gray-900">{m.home_team}</span>
                </div>
                <span className={`shrink-0 font-bold ${m.status === 'completed' ? 'text-green-600' : 'text-gray-400'}`}>
                  {m.status === 'completed' ? `${m.home_score}-${m.away_score}` : m.status === 'awaiting_result' ? '待赛果' : 'VS'}
                </span>
                <div className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-medium text-gray-900">{m.away_team}</span>
                  <TeamFlagLink teamName={m.away_team} flagCode={mAway?.flagCode} size="sm" />
                </div>
              </article>
            )
          })}
        </div>
        {relatedMatches.length === 0 && (
          <p className="text-gray-400 text-sm text-center py-4">暂无同轮其他比赛</p>
        )}
      </div>
    </div>
  )
}
