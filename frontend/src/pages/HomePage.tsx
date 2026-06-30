import { useState, useEffect, useMemo, type KeyboardEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Calendar, BarChart3, Users, MapPin, Clock, Flame, Radio, Star, Trophy, ClipboardCheck, Brain } from 'lucide-react'
import { predictionAPI, matchAPI } from '../services/api'
import type { LiveSyncStatus, ModelPerformance } from '../services/api'
import { TEAMS, getStageNameCN, getEffectiveMatchStage, isEffectiveKnockoutMatch, isPlaceholderFixture } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'
import TeamFlagLink from '../components/TeamFlagLink'
import ChampionPathPredictor from '../components/ChampionPathPredictor'
import DailyPredictionsExport from '../components/DailyPredictionsExport'
import { getPredictMatchPath } from '../utils/navigation'

const TEAM_HEAT: Record<string, number> = {
  阿根廷: 99,
  法国: 98,
  巴西: 98,
  英格兰: 97,
  葡萄牙: 96,
  西班牙: 95,
  德国: 94,
  墨西哥: 94,
  美国: 93,
  荷兰: 92,
  克罗地亚: 89,
  乌拉圭: 88,
  比利时: 87,
  日本: 86,
  韩国: 86,
  加拿大: 85,
  摩洛哥: 85,
  瑞士: 82,
  土耳其: 81,
  哥伦比亚: 81,
  澳大利亚: 79,
  苏格兰: 78,
  南非: 78,
  捷克: 76,
  巴拉圭: 75,
  卡塔尔: 75,
  波黑: 73,
  海地: 70,
}

const STAR_HEAT: Record<string, number> = {
  阿根廷: 100,
  法国: 99,
  英格兰: 98,
  葡萄牙: 97,
  巴西: 96,
  西班牙: 93,
  德国: 91,
  荷兰: 89,
  韩国: 88,
  比利时: 87,
  克罗地亚: 85,
  日本: 85,
  乌拉圭: 84,
  美国: 83,
  墨西哥: 83,
  加拿大: 82,
  摩洛哥: 82,
  哥伦比亚: 81,
  土耳其: 80,
  瑞士: 79,
  澳大利亚: 76,
  捷克: 74,
  苏格兰: 73,
  南非: 70,
  巴拉圭: 70,
  波黑: 69,
  卡塔尔: 68,
  海地: 64,
}

const MATCH_MEDIA_HEAT: Record<number, number> = {
  1: 98,
  2: 82,
  3: 79,
  4: 93,
  5: 76,
  6: 92,
  7: 73,
  8: 75,
  10: 90,
  13: 91,
  17: 94,
  19: 96,
  21: 95,
  22: 96,
  28: 92,
  29: 91,
  31: 94,
  41: 95,
  42: 94,
  45: 94,
  46: 95,
  64: 93,
  69: 94,
  72: 95,
}

const clampHeat = (value: number) => Math.max(45, Math.min(100, Math.round(value)))

const getBeijingDayKey = (dateInput: string | Date) => {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const year = parts.find(part => part.type === 'year')?.value ?? '2026'
  const month = parts.find(part => part.type === 'month')?.value ?? '01'
  const day = parts.find(part => part.type === 'day')?.value ?? '01'
  return `${year}-${month}-${day}`
}

const getTeamProfile = (teamName: string) => TEAMS.find(team => team.name === teamName)

const getTeamHeat = (teamName: string) => {
  const team = getTeamProfile(teamName)
  if (TEAM_HEAT[teamName]) return TEAM_HEAT[teamName]
  if (!team) return 60
  const rankHeat = 104 - team.fifa_rank * 0.62
  return clampHeat(rankHeat + (team.is_host ? 6 : 0))
}

const getStarHeat = (teamName: string) => {
  const team = getTeamProfile(teamName)
  if (STAR_HEAT[teamName]) return STAR_HEAT[teamName]
  if (!team) return 58
  return clampHeat(91 - team.fifa_rank * 0.44)
}

const getMediaHeat = (match: Match) => {
  if (MATCH_MEDIA_HEAT[match.id]) return MATCH_MEDIA_HEAT[match.id]
  const teamHeat = (getTeamHeat(match.home_team) + getTeamHeat(match.away_team)) / 2
  const hostBoost = [match.home_team, match.away_team].some(teamName => getTeamProfile(teamName)?.is_host) ? 5 : 0
  const roundBoost = match.round === 3 ? 8 : match.round === 1 ? 6 : 4
  return clampHeat(teamHeat * 0.86 + hostBoost + roundBoost)
}

const getFocusMetrics = (match: Match) => {
  const teamHeat = clampHeat((getTeamHeat(match.home_team) + getTeamHeat(match.away_team)) / 2)
  const starHeat = clampHeat((getStarHeat(match.home_team) + getStarHeat(match.away_team)) / 2)
  const mediaHeat = getMediaHeat(match)
  const total = clampHeat(teamHeat * 0.35 + starHeat * 0.35 + mediaHeat * 0.3)
  return { teamHeat, starHeat, mediaHeat, total }
}

const isGroupStageMatch = (match: Match) => Boolean(match.group && !isEffectiveKnockoutMatch(match) && getTeamProfile(match.home_team) && getTeamProfile(match.away_team))

function selectDailyFocusMatch(matches: Match[], now = new Date()) {
  const focusCandidates = matches.filter(isGroupStageMatch)
  const todayKey = getBeijingDayKey(now)
  const dayKeys = Array.from(new Set(focusCandidates.map(match => getBeijingDayKey(match.match_date)))).sort()
  const targetDayKey = dayKeys.find(dayKey => dayKey >= todayKey) ?? dayKeys[dayKeys.length - 1]
  const matchesForDay = focusCandidates.filter(match => getBeijingDayKey(match.match_date) === targetDayKey)

  return [...matchesForDay].sort((a, b) => {
    const heatDiff = getFocusMetrics(b).total - getFocusMetrics(a).total
    if (heatDiff !== 0) return heatDiff
    return new Date(a.match_date).getTime() - new Date(b.match_date).getTime()
  })[0]
}

const getMatchStatusLabel = (match: Match) => {
  if (match.status === 'completed') return '已完赛'
  if (match.status === 'live') return '进行中'
  if (match.status === 'awaiting_result') return '待官方赛果'
  return '待开赛'
}

const getFocusScoreText = (match: Match) => {
  if (match.status === 'completed' && match.home_score !== undefined && match.away_score !== undefined) {
    return `${match.home_score} - ${match.away_score}`
  }
  return 'VS'
}

export default function HomePage() {
  const navigate = useNavigate()
  const [allMatches, setAllMatches] = useState<Match[]>([])
  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([])
  const [modelPerformance, setModelPerformance] = useState<ModelPerformance | null>(null)
  const [liveStatus, setLiveStatus] = useState<LiveSyncStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const todayFocusMatch = useMemo(() => selectDailyFocusMatch(allMatches), [allMatches])
  const focusMetrics = useMemo(() => todayFocusMatch ? getFocusMetrics(todayFocusMatch) : null, [todayFocusMatch])

  useEffect(() => {
    let active = true
    const fetchData = async () => {
      try {
        const [matchesResult, perfResult, statusResult] = await Promise.allSettled([
          matchAPI.getMatchesStrict(),
          predictionAPI.getModelPerformance(),
          matchAPI.getLiveStatusStrict(),
        ])
        if (!active) return

        if (matchesResult.status === 'fulfilled' && Array.isArray(matchesResult.value)) {
          const matches = matchesResult.value
          const now = Date.now()
          setAllMatches(matches)
          setUpcomingMatches(
            matches
              .filter(match => (!match.status || match.status === 'upcoming') && new Date(match.match_date).getTime() > now && !isPlaceholderFixture(match))
              .slice(0, 6)
          )
        } else {
          console.error('Failed to fetch live matches:', matchesResult.status === 'rejected' ? matchesResult.reason : matchesResult.value)
        }

        if (perfResult.status === 'fulfilled') {
          setModelPerformance(perfResult.value)
        } else {
          console.error('Failed to fetch model performance:', perfResult.reason)
        }

        if (statusResult.status === 'fulfilled') {
          setLiveStatus(statusResult.value)
        } else {
          console.error('Failed to fetch live sync status:', statusResult.reason)
          setLiveStatus({
            status: 'error',
            source: 'api_error',
            last_updated: null,
            last_sync_attempt: new Date().toISOString(),
            message: '实时数据同步失败',
            match_count: 0,
            pending_result_count: 0,
            pending_results: [],
          })
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    fetchData()
    const timer = window.setInterval(fetchData, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const formatMatchDate = (dateStr: string) => {
    const d = new Date(dateStr)
    const month = d.getMonth() + 1
    const day = d.getDate()
    const hour = d.getHours().toString().padStart(2, '0')
    const min = d.getMinutes().toString().padStart(2, '0')
    return `${month}月${day}日 ${hour}:${min}`
  }

  const activeModelMetrics = modelPerformance ? {
    accuracy: modelPerformance.accuracy ?? modelPerformance.models?.form_weighted?.accuracy ?? 0,
    precision: modelPerformance.precision ?? modelPerformance.models?.form_weighted?.precision ?? 0,
    recall: modelPerformance.recall ?? modelPerformance.models?.form_weighted?.recall ?? 0,
  } : null
  const compactUpcomingMatches = useMemo(() => {
    const localUpcoming = allMatches
      .filter(match => (!match.status || match.status === 'upcoming') && new Date(match.match_date) > new Date())
      .slice(0, 3)
    return (upcomingMatches.length ? upcomingMatches : localUpcoming).slice(0, 3)
  }, [allMatches, upcomingMatches])

  const openMatchPrediction = (matchId: number) => {
    navigate(getPredictMatchPath(matchId))
  }

  const handleMatchCardKeyDown = (event: KeyboardEvent<HTMLElement>, matchId: number) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openMatchPrediction(matchId)
    }
  }

  return (
    <div className="space-y-7">
      {/* Hero区域 */}
      <section className="wc-hero wc-hero-compact text-left">
        <div className="wc-hero-atlas" aria-hidden="true">
          <img
            src="/wc2026-hero-north-america-stadium.png"
            alt=""
            className="wc-hero-atlas-image"
            loading="eager"
          />
          <div className="wc-hero-atlas-vignette" />
        </div>

        <div className="wc-hero-content relative mx-auto max-w-6xl px-2">
          <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div className="space-y-4">
              <div className="wc-hero-brand justify-start">
                <TeamFlagLink teamName="美国" flagCode="us" size="md" />
                <TeamFlagLink teamName="加拿大" flagCode="ca" size="md" />
                <TeamFlagLink teamName="墨西哥" flagCode="mx" size="md" />
                <span>美加墨世界杯AI预测模型</span>
              </div>

              <div className="flex items-center gap-4">
                <img src="/wc2026-logo.png" alt="FIFA World Cup 2026" className="wc-hero-logo h-20 w-20 shrink-0 object-contain md:h-24 md:w-24" />
                <div className="min-w-0">
                  <h1 className="wc-hero-title font-display">2026 世界杯</h1>
                  <p className="wc-hero-subtitle mt-2">
                    三个国家 · 48支球队 · 104场比赛 · 一个冠军
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-lg bg-white/75 p-3 text-center shadow-sm backdrop-blur">
                  <p className="text-xl font-black text-blue-700">72</p>
                  <p className="text-[11px] font-semibold text-slate-500">小组赛</p>
                </div>
                <div className="rounded-lg bg-white/75 p-3 text-center shadow-sm backdrop-blur">
                  <p className="text-xl font-black text-green-700">32</p>
                  <p className="text-[11px] font-semibold text-slate-500">淘汰赛</p>
                </div>
                <div className="rounded-lg bg-white/75 p-3 text-center shadow-sm backdrop-blur">
                  <p className="text-xl font-black text-amber-700">48</p>
                  <p className="text-[11px] font-semibold text-slate-500">球队</p>
                </div>
              </div>

              {liveStatus && (
                <div className="rounded-full bg-white/75 px-3 py-2 text-xs font-semibold text-slate-600 shadow-sm backdrop-blur">
                  实时数据：{liveStatus.status === 'connected' ? '已连接' : liveStatus.status === 'stale' ? '数据可能延迟' : '待配置'}
                  {Boolean(liveStatus.pending_result_count) && (
                    <span className="ml-2 text-amber-700">· {liveStatus.pending_result_count} 场待官方赛果</span>
                  )}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <Link to="/predict" className="wc-button-primary">
                  开始预测
                </Link>
                <Link to="/matches" className="wc-button-gold">
                  查看赛程
                </Link>
              </div>
            </div>

            <div className="grid gap-3 xl:grid-cols-[1.08fr_0.92fr]">
              {todayFocusMatch && focusMetrics && (
                <article
                  role="button"
                  tabIndex={0}
                  onClick={() => openMatchPrediction(todayFocusMatch.id)}
                  onKeyDown={(event) => handleMatchCardKeyDown(event, todayFocusMatch.id)}
                  className="glass-card block cursor-pointer p-4 text-left transition-all duration-300 hover:-translate-y-0.5 focus-visible:ring-4 focus-visible:ring-blue-500/20"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm font-black text-slate-800">
                      <Flame className="h-4 w-4 text-red-500" />
                      今日焦点战
                    </div>
                    <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-bold text-red-600">
                      综合热度 {focusMetrics.total}
                    </span>
                  </div>

                  <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2">
                    <div className="min-w-0 text-center">
                      <TeamFlagLink teamName={todayFocusMatch.home_team} size="md" />
                      <p className="mt-1 truncate text-sm font-black text-slate-900 md:text-base">{todayFocusMatch.home_team}</p>
                    </div>
                    <div className="min-w-[4.5rem] text-center">
                      <div className="text-2xl font-black text-slate-900">{getFocusScoreText(todayFocusMatch)}</div>
                      <div className="mt-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-700">{getMatchStatusLabel(todayFocusMatch)}</div>
                    </div>
                    <div className="min-w-0 text-center">
                      <TeamFlagLink teamName={todayFocusMatch.away_team} size="md" />
                      <p className="mt-1 truncate text-sm font-black text-slate-900 md:text-base">{todayFocusMatch.away_team}</p>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1.5 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {formatMatchDate(todayFocusMatch.match_date)}
                    </span>
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {todayFocusMatch.venue}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <div className="rounded-lg bg-blue-50 px-2 py-2 text-center">
                      <BarChart3 className="mx-auto mb-1 h-4 w-4 text-blue-600" />
                      <p className="text-base font-black text-blue-700">{focusMetrics.teamHeat}</p>
                      <p className="text-[10px] font-semibold text-slate-500">球队</p>
                    </div>
                    <div className="rounded-lg bg-yellow-50 px-2 py-2 text-center">
                      <Star className="mx-auto mb-1 h-4 w-4 text-yellow-600" />
                      <p className="text-base font-black text-yellow-700">{focusMetrics.starHeat}</p>
                      <p className="text-[10px] font-semibold text-slate-500">球星</p>
                    </div>
                    <div className="rounded-lg bg-red-50 px-2 py-2 text-center">
                      <Radio className="mx-auto mb-1 h-4 w-4 text-red-500" />
                      <p className="text-base font-black text-red-600">{focusMetrics.mediaHeat}</p>
                      <p className="text-[10px] font-semibold text-slate-500">媒体</p>
                    </div>
                  </div>
                </article>
              )}

              <div className="glass-card p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="flex items-center gap-2 text-sm font-black text-slate-900">
                    <Calendar className="h-4 w-4 text-blue-600" />
                    即将开赛
                  </h2>
                  <Link to="/matches" className="text-xs font-bold text-blue-600 hover:text-blue-800">全部赛程</Link>
                </div>
                <div className="space-y-2">
                  {compactUpcomingMatches.map(match => (
                    <article
                      key={match.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => openMatchPrediction(match.id)}
                      onKeyDown={(event) => handleMatchCardKeyDown(event, match.id)}
                      className="block cursor-pointer rounded-lg border border-slate-100 bg-white/75 p-3 transition-colors hover:bg-blue-50 focus-visible:ring-4 focus-visible:ring-blue-500/20"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="shrink-0 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-black text-blue-700">{match.group ? `${match.group}组` : getStageNameCN(getEffectiveMatchStage(match) || '')}</span>
                        <span className="truncate text-xs font-semibold text-slate-500">{formatMatchDate(match.match_date)}</span>
                      </div>
                      <div className="mt-2 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-center">
                        <span className="truncate text-sm font-black text-slate-900">{match.home_team}</span>
                        <span className="text-xs font-black text-slate-300">VS</span>
                        <span className="truncate text-sm font-black text-slate-900">{match.away_team}</span>
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <ChampionPathPredictor />

      {/* 即将进行的比赛 */}
      <section>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="section-heading mb-0">
            <Calendar className="w-5 h-5 text-blue-600" />
            即将开赛
          </h2>
          <DailyPredictionsExport matches={allMatches} loading={loading} />
        </div>
        {loading ? (
          <div className="text-center py-12 text-gray-400">加载中...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingMatches.map((match) => (
              <article
                key={match.id}
                role="button"
                tabIndex={0}
                onClick={() => openMatchPrediction(match.id)}
                onKeyDown={(event) => handleMatchCardKeyDown(event, match.id)}
                className="glass-card cursor-pointer p-5 transition-all duration-300 hover:-translate-y-1 focus-visible:ring-4 focus-visible:ring-blue-500/20"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold px-2 py-1 bg-blue-50 text-blue-700 rounded-lg border border-blue-100">
                    {match.group}组
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatMatchDate(match.match_date)}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <div className="text-center flex-1">
                    <div className="mb-1"><TeamFlagLink teamName={match.home_team} size="md" /></div>
                    <p className="font-bold text-gray-900">{match.home_team}</p>
                  </div>
                  <div className="px-4">
                    <span className="text-xl font-black text-gray-300">VS</span>
                  </div>
                  <div className="text-center flex-1">
                    <div className="mb-1"><TeamFlagLink teamName={match.away_team} size="md" /></div>
                    <p className="font-bold text-gray-900">{match.away_team}</p>
                  </div>
                </div>
                <div className="text-xs text-gray-400 mt-2 flex items-center justify-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {match.venue}
                </div>
              </article>
            ))}
          </div>
        )}
        <div className="text-center mt-4">
          <Link to="/matches" className="text-blue-600 hover:text-blue-800 text-sm font-semibold">
            查看完整104场赛程 →
          </Link>
        </div>
      </section>

      {/* 12组一览 */}
      <section>
        <h2 className="section-heading">
          <Users className="w-5 h-5 text-green-600" />
          12组分组一览
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {['A','B','C','D','E','F','G','H','I','J','K','L'].map(group => {
            const groupTeams = TEAMS.filter(t => t.group === group).sort((a, b) => a.fifa_rank - b.fifa_rank)
            return (
              <div key={group} className="glass-card p-4 transition-all hover:-translate-y-0.5">
                <Link to={`/teams?group=${group}`} className="mb-2 inline-flex text-sm font-bold text-blue-600 hover:text-blue-800">{group}组</Link>
                <div className="space-y-1">
                  {groupTeams.map((t) => (
                    <div key={t.id} className="flex items-center gap-2 text-sm">
                      <TeamFlagLink teamName={t.name} flagCode={t.flagCode} size="sm" />
                      <Link to={`/teams/${t.id}`} className="min-w-0 truncate text-gray-700 font-medium hover:text-blue-700">{t.name}</Link>
                      {t.is_host && <span className="text-xs bg-yellow-100 text-yellow-700 px-1 rounded">东道主</span>}
                      {t.is_defending && <span className="text-xs bg-green-100 text-green-700 px-1 rounded">卫冕</span>}
                      {t.is_debut && <span className="text-xs bg-purple-100 text-purple-700 px-1 rounded">首秀</span>}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* AI模型性能 */}
      {modelPerformance && activeModelMetrics && (
        <section className="glass-card p-8">
          <h2 className="section-heading">
            <BarChart3 className="w-5 h-5 text-green-600" />
            美加墨世界杯AI预测模型性能
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { label: '预测准确率', value: `${(activeModelMetrics.accuracy * 100).toFixed(1)}%`, color: 'text-green-600' },
              { label: '精确率', value: `${(activeModelMetrics.precision * 100).toFixed(1)}%`, color: 'text-blue-600' },
              { label: '召回率', value: `${(activeModelMetrics.recall * 100).toFixed(1)}%`, color: 'text-purple-600' },
              { label: '预测总数', value: modelPerformance.total_predictions, color: 'text-orange-600' },
            ].map(m => (
              <div key={m.label} className="metric-tile text-center">
                <p className={`text-3xl font-bold ${m.color}`}>{m.value}</p>
                <p className="text-sm text-gray-500 mt-1">{m.label}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 text-center text-sm text-gray-400">
            模型版本: 美加墨世界杯AI预测模型 26.4 · 三层架构: Baseline Elo → Form Weighted → Monte Carlo
          </div>
        </section>
      )}

      {/* 功能入口 */}
      <section>
        <h2 className="section-heading">探索更多</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {[
            { icon: BarChart3, title: '赛前预测', desc: '单场概率、比分池、大小、冷门、角球黄牌与赛前简报导出', link: '/predict', color: 'bg-blue-600' },
            { icon: Trophy, title: '出线与淘汰赛', desc: '小组出线路径、32强入口、左右半区对称晋级路径模拟', link: '/tournament', color: 'bg-amber-500' },
            { icon: ClipboardCheck, title: '赛果复盘', desc: '胜平负命中、比分池命中、偏差原因和下次预测修正', link: '/reviews', color: 'bg-emerald-600' },
            { icon: Brain, title: '球队档案 / 模型记忆', desc: '48队阵容、战术画像、球队特征库和下次预测注意事项', link: '/teams', color: 'bg-purple-600' },
            { icon: Calendar, title: '完整赛程', desc: '104场完整赛程、北京时间、场馆与赛果状态同步', link: '/matches', color: 'bg-green-600' },
            { icon: Users, title: '数据榜单', desc: '射手、助攻、球队统计与公开数据源状态汇总', link: '/stats', color: 'bg-slate-700' },
          ].map(feature => (
            <Link key={feature.title} to={feature.link} className="glass-card p-6 transition-all duration-300 hover:-translate-y-1">
              <div className={`w-12 h-12 ${feature.color} text-white rounded-lg flex items-center justify-center mb-4`}>
                <feature.icon className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-gray-500">{feature.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
