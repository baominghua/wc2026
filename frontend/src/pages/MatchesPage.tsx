import { useEffect, useState, useMemo, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapPin, Clock, BarChart3 } from 'lucide-react'
import { matchAPI } from '../services/api'
import { TEAMS, calculateGroupStandingsFromMatches, isKnockoutPlaceholder, isPlaceholderFixture, getStageNameCN, getEffectiveMatchStage, isEffectiveKnockoutMatch } from '../services/wc2026-data'
import type { Match, StandingEntry } from '../services/wc2026-data'
import TeamFlagLink from '../components/TeamFlagLink'
import { getPredictMatchPath } from '../utils/navigation'

type ViewTab = 'group' | 'knockout' | 'standings'

export default function MatchesPage() {
  const navigate = useNavigate()
  const [selectedGroup, setSelectedGroup] = useState<string>('')
  const [selectedRound, setSelectedRound] = useState<number>(0)
  const [activeTab, setActiveTab] = useState<ViewTab>('group')
  const [selectedStage, setSelectedStage] = useState<string>('')
  const [liveMatches, setLiveMatches] = useState<Match[]>([])
  const [isLoadingMatches, setIsLoadingMatches] = useState(true)
  const [matchesError, setMatchesError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const fetchMatches = async () => {
      try {
        const matches = await matchAPI.getMatchesStrict()
        if (!active) return
        setLiveMatches(matches)
        setMatchesError(null)
      } catch (error) {
        console.error('Failed to load live matches:', error)
        if (active) setMatchesError('实时赛程接口读取失败，请重新登录或稍后刷新。')
      } finally {
        if (active) setIsLoadingMatches(false)
      }
    }
    fetchMatches()
    const timer = window.setInterval(fetchMatches, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const formatMatchDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return `${d.getMonth() + 1}月${d.getDate()}日 ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  const getTeamFlagCode = (name: string) => {
    return TEAMS.find(t => t.name === name)?.flagCode || ''
  }

  const openMatchPrediction = (matchId: number, disabled = false) => {
    if (disabled) return
    navigate(getPredictMatchPath(matchId))
  }

  const handleMatchCardKeyDown = (event: KeyboardEvent<HTMLElement>, matchId: number, disabled = false) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openMatchPrediction(matchId, disabled)
    }
  }

  const renderScore = (match: Match) => {
    if (match.status === 'completed') return <div className="text-lg font-black text-green-600">{match.home_score}-{match.away_score}</div>
    if (match.status === 'live') return <div className="text-sm font-black text-blue-600">进行中</div>
    if (match.status === 'awaiting_result') return <div className="text-xs font-black text-amber-600">待官方赛果</div>
    return <div className="text-lg font-black text-gray-400">VS</div>
  }

  // 小组赛数据
  const groupMatches = useMemo(() => liveMatches.filter(m => m.group && !isEffectiveKnockoutMatch(m)), [liveMatches])
  const filteredGroupMatches = useMemo(() => {
    let filtered = groupMatches
    if (selectedGroup) filtered = filtered.filter(m => m.group === selectedGroup)
    if (selectedRound) filtered = filtered.filter(m => m.round === selectedRound)
    return filtered
  }, [groupMatches, selectedGroup, selectedRound])

  // 淘汰赛数据
  const knockoutMatches = useMemo(() => liveMatches.filter(isEffectiveKnockoutMatch), [liveMatches])
  const filteredKnockoutMatches = useMemo(() => {
    if (!selectedStage) return knockoutMatches
    return knockoutMatches.filter(m => getEffectiveMatchStage(m) === selectedStage)
  }, [knockoutMatches, selectedStage])

  // 积分榜数据
  const groups = ['A','B','C','D','E','F','G','H','I','J','K','L']
  const [standingsGroup, setStandingsGroup] = useState('A')
  const standings: StandingEntry[] = useMemo(() => calculateGroupStandingsFromMatches(standingsGroup, liveMatches), [liveMatches, standingsGroup])

  const rounds = [
    { value: 0, label: '全部轮次' },
    { value: 1, label: '第1轮' },
    { value: 2, label: '第2轮' },
    { value: 3, label: '第3轮' },
  ]

  const stages = [
    { value: '', label: '全部阶段' },
    { value: 'Round of 32', label: '32强赛' },
    { value: 'Round of 16', label: '16强赛' },
    { value: 'Quarter-final', label: '四分之一决赛' },
    { value: 'Semi-final', label: '半决赛' },
    { value: 'Third place', label: '三四名决赛' },
    { value: 'Final', label: '决赛' },
  ]

  return (
    <div className="space-y-6">
      <div className="text-center mb-4">
        <h1 className="text-3xl font-black text-gray-900 font-display tracking-wide">赛程总览</h1>
        <p className="text-gray-500 mt-2">72场小组赛 + 32场淘汰赛 · 北京时间</p>
      </div>

      {/* 顶部Tab切换 */}
      <div className="flex justify-center gap-2">
        <button
          onClick={() => setActiveTab('group')}
          className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'group' ? 'bg-blue-600 text-white shadow-lg' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          ⚽ 小组赛
        </button>
        <button
          onClick={() => setActiveTab('knockout')}
          className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'knockout' ? 'bg-orange-600 text-white shadow-lg' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          🏆 淘汰赛
        </button>
        <button
          onClick={() => setActiveTab('standings')}
          className={`px-5 py-2.5 rounded-lg text-sm font-bold transition-all ${activeTab === 'standings' ? 'bg-green-600 text-white shadow-lg' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          📊 积分榜
        </button>
      </div>

      {matchesError && (
        <div className="glass-card border border-red-200 bg-red-50/70 p-4 text-sm font-semibold text-red-700">
          {matchesError}
        </div>
      )}

      {isLoadingMatches && liveMatches.length === 0 && (
        <div className="glass-card p-6 text-center text-sm font-semibold text-slate-600">
          正在同步实时赛程数据...
        </div>
      )}

      {/* ====== 小组赛视图 ====== */}
      {activeTab === 'group' && (
        <>
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={() => setSelectedGroup('')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${!selectedGroup ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
            >
              全部小组
            </button>
            {groups.map(g => (
              <button
                key={g}
                onClick={() => setSelectedGroup(g)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedGroup === g ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
              >
                {g}组
              </button>
            ))}
          </div>

          <div className="flex gap-2 justify-center">
            {rounds.map(r => (
              <button
                key={r.value}
                onClick={() => setSelectedRound(r.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${selectedRound === r.value ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                {r.label}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {filteredGroupMatches.map((match) => (
              <article
                key={match.id}
                role="button"
                tabIndex={0}
                onClick={() => openMatchPrediction(match.id)}
                onKeyDown={(event) => handleMatchCardKeyDown(event, match.id)}
                className={`glass-card cursor-pointer p-3 transition-all hover:shadow-lg focus-visible:ring-4 focus-visible:ring-blue-500/20 sm:p-4 md:flex md:items-center md:gap-4 ${match.status === 'completed' ? 'border-l-4 border-green-500 bg-green-50/30' : ''} ${match.status === 'awaiting_result' ? 'border-l-4 border-amber-400 bg-amber-50/30' : ''}`}
              >
                <div className="mb-3 flex items-center justify-between gap-2 md:mb-0 md:w-16 md:flex-shrink-0 md:flex-col md:justify-center md:text-center">
                  <div className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded">{match.group}组</div>
                  <div className="text-xs text-gray-400 mt-1">第{match.round}轮</div>
                </div>
                <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 md:flex md:flex-1 md:justify-between">
                  <div className="flex min-w-0 items-center justify-end gap-2">
                    <span className="truncate font-bold text-gray-900">{match.home_team}</span>
                    <TeamFlagLink teamName={match.home_team} flagCode={getTeamFlagCode(match.home_team)} size="md" />
                  </div>
                  <div className="px-1 text-center flex-shrink-0 sm:px-4">
                    <div className="flex items-center justify-center gap-1 text-[11px] text-gray-400 sm:text-xs">
                      <Clock className="w-3 h-3" />
                      {formatMatchDate(match.match_date)}
                    </div>
                    {renderScore(match)}
                  </div>
                  <div className="flex min-w-0 items-center gap-2">
                    <TeamFlagLink teamName={match.away_team} flagCode={getTeamFlagCode(match.away_team)} size="md" />
                    <span className="truncate font-bold text-gray-900">{match.away_team}</span>
                  </div>
                </div>
                <div className="text-xs text-gray-400 w-40 flex-shrink-0 text-right hidden md:block">
                  <div className="flex items-center gap-1 justify-end">
                    <MapPin className="w-3 h-3" />
                    {match.venue}
                  </div>
                </div>
              </article>
            ))}
          </div>
          <div className="text-center text-sm text-gray-400 pt-4">
            共 {filteredGroupMatches.length} 场小组赛
          </div>
        </>
      )}

      {/* ====== 淘汰赛视图 ====== */}
      {activeTab === 'knockout' && (
        <>
          <div className="flex flex-wrap gap-2 justify-center">
            {stages.map(s => (
              <button
                key={s.value}
                onClick={() => setSelectedStage(s.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${selectedStage === s.value ? 'bg-orange-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {filteredKnockoutMatches.map((match) => {
              const effectiveStage = getEffectiveMatchStage(match)
              const isPlaceholder = isPlaceholderFixture(match)
              const homeIsPlaceholder = isKnockoutPlaceholder(match.home_team)
              const awayIsPlaceholder = isKnockoutPlaceholder(match.away_team)
              const homeDisplay = match.home_team
              const awayDisplay = match.away_team
              const isResolved = !isPlaceholder

              return (
                <article
                  key={match.id}
                  role={isResolved ? 'button' : undefined}
                  tabIndex={isResolved ? 0 : -1}
                  onClick={() => openMatchPrediction(match.id, !isResolved)}
                  onKeyDown={(event) => handleMatchCardKeyDown(event, match.id, !isResolved)}
                  className={`glass-card p-3 transition-all sm:p-4 md:flex md:items-center md:gap-4 ${isResolved ? 'cursor-pointer hover:shadow-lg focus-visible:ring-4 focus-visible:ring-blue-500/20' : 'cursor-not-allowed'} ${match.status === 'completed' ? 'border-l-4 border-green-500 bg-green-50/30' : ''} ${match.status === 'awaiting_result' ? 'border-l-4 border-amber-400 bg-amber-50/30' : ''} ${!isResolved ? 'opacity-75' : ''}`}
                >
                  <div className="mb-3 flex items-center justify-between gap-2 md:mb-0 md:w-20 md:flex-shrink-0 md:flex-col md:justify-center md:text-center">
                    <div className="text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded">{getStageNameCN(effectiveStage ?? '')}</div>
                    {isPlaceholder && (
                      <div className="text-[10px] text-gray-400 mt-1">
                        {match.home_team.includes('W') ? '胜者' : match.home_team.includes('L') ? '败者' : match.home_team}
                      </div>
                    )}
                  </div>
                  <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 md:flex md:flex-1 md:justify-between">
                    <div className="flex min-w-0 items-center justify-end gap-2">
                      <span className={`font-bold ${homeIsPlaceholder ? 'text-gray-400 italic' : 'text-gray-900'}`}>
                        {homeDisplay}
                      </span>
                      {!homeIsPlaceholder && <TeamFlagLink teamName={match.home_team} flagCode={getTeamFlagCode(match.home_team)} size="md" />}
                    </div>
                    <div className="px-1 text-center flex-shrink-0 sm:px-4">
                      <div className="flex items-center justify-center gap-1 text-[11px] text-gray-400 sm:text-xs">
                        <Clock className="w-3 h-3" />
                        {formatMatchDate(match.match_date)}
                      </div>
                      {renderScore(match)}
                    </div>
                    <div className="flex min-w-0 items-center gap-2">
                      {!awayIsPlaceholder && <TeamFlagLink teamName={match.away_team} flagCode={getTeamFlagCode(match.away_team)} size="md" />}
                      <span className={`font-bold ${awayIsPlaceholder ? 'text-gray-400 italic' : 'text-gray-900'}`}>
                        {awayDisplay}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 w-40 flex-shrink-0 text-right hidden md:block">
                    <div className="flex items-center gap-1 justify-end">
                      <MapPin className="w-3 h-3" />
                      {match.venue}
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
          <div className="text-center text-sm text-gray-400 pt-4">
            共 {filteredKnockoutMatches.length} 场淘汰赛 · 小组赛结束后对阵自动更新
          </div>
        </>
      )}

      {/* ====== 积分榜视图 ====== */}
      {activeTab === 'standings' && (
        <>
          <div className="flex flex-wrap gap-2 justify-center mb-4">
            {groups.map(g => (
              <button
                key={g}
                onClick={() => setStandingsGroup(g)}
                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${standingsGroup === g ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
              >
                {g}组
              </button>
            ))}
          </div>

          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b bg-green-50">
              <h2 className="text-lg font-bold text-green-800 flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                {standingsGroup}组积分榜
              </h2>
              <p className="text-xs text-green-600 mt-1">基于已完成比赛实时计算</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-gray-500">
                    <th className="py-3 px-4 text-left font-medium">排名</th>
                    <th className="py-3 px-4 text-left font-medium">球队</th>
                    <th className="py-3 px-2 text-center font-medium">赛</th>
                    <th className="py-3 px-2 text-center font-medium">胜</th>
                    <th className="py-3 px-2 text-center font-medium">平</th>
                    <th className="py-3 px-2 text-center font-medium">负</th>
                    <th className="py-3 px-2 text-center font-medium">进球</th>
                    <th className="py-3 px-2 text-center font-medium">失球</th>
                    <th className="py-3 px-2 text-center font-medium">净胜球</th>
                    <th className="py-3 px-4 text-center font-bold text-green-700">积分</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.map((s: StandingEntry, idx: number) => (
                    <tr key={s.team} className={`border-b ${idx < 2 ? 'bg-green-50/40' : ''}`}>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${idx < 2 ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                          {idx + 1}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <TeamFlagLink teamName={s.team} flagCode={TEAMS.find(t => t.name === s.team)?.flagCode || ''} size="sm" />
                          <span className="font-bold text-gray-900">{s.team}</span>
                        </div>
                      </td>
                      <td className="py-3 px-2 text-center">{s.played}</td>
                      <td className="py-3 px-2 text-center text-green-600 font-medium">{s.won}</td>
                      <td className="py-3 px-2 text-center text-gray-500">{s.drawn}</td>
                      <td className="py-3 px-2 text-center text-red-500">{s.lost}</td>
                      <td className="py-3 px-2 text-center">{s.goalsFor}</td>
                      <td className="py-3 px-2 text-center">{s.goalsAgainst}</td>
                      <td className={`py-3 px-2 text-center font-medium ${s.goalDiff > 0 ? 'text-green-600' : s.goalDiff < 0 ? 'text-red-500' : 'text-gray-500'}`}>
                        {s.goalDiff > 0 ? '+' : ''}{s.goalDiff}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-lg font-black text-green-700">{s.points}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="p-3 bg-gray-50 text-xs text-gray-400 flex items-center gap-2">
              <span className="inline-block w-3 h-3 bg-green-600 rounded-full"></span>
              前2名晋级淘汰赛
              <span className="ml-4">· 数据基于已完成比赛实时计算</span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
