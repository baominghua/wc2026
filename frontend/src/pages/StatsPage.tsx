import { useEffect, useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BarChart3, Trophy, Target, Users, TrendingUp, Medal, ChevronDown, ChevronUp, Filter, Clock, RefreshCw } from 'lucide-react'
import {
  TOURNAMENTS,
  PLAYER_STATS,
  TEAM_HISTORICAL_STATS,
  AVAILABLE_YEARS,
} from '../services/wc-history-data'
import type {
  PlayerSortField,
  TeamSortField,
  PlayerHistoricalStats,
  TeamHistoricalStats,
} from '../services/wc-history-data'
import { matchAPI, playerStatsAPI } from '../services/api'
import type { LiveSyncStatus, PlayerLeaderboardPayload } from '../services/api'
import { TEAMS, calculateGroupStandingsFromMatches } from '../services/wc2026-data'
import type { Match, StandingEntry } from '../services/wc2026-data'
import {
  build2026TeamStatsFromMatches,
} from '../services/live-stats'
import TeamFlag from '../components/TeamFlag'
import { selectPlayerStatsForYear } from '../utils/playerStatsSelection'

type TabType = 'overview' | 'players' | 'teams' | 'live2026'

const GROUPS_2026 = ['A','B','C','D','E','F','G','H','I','J','K','L']

function mergeTeamStatsWith2026(liveMatches: Match[]): TeamHistoricalStats[] {
  const byName = new Map<string, TeamHistoricalStats>()

  TEAM_HISTORICAL_STATS.forEach(team => {
    byName.set(team.name, {
      ...team,
      tournaments: [...team.tournaments],
      yearlyStats: { ...team.yearlyStats },
    })
  })

  build2026TeamStatsFromMatches(liveMatches).forEach(team2026 => {
    const existing = byName.get(team2026.name)
    if (!existing) {
      byName.set(team2026.name, team2026)
      return
    }

    const y2026 = team2026.yearlyStats[2026]
    existing.tournaments = Array.from(new Set([2026, ...existing.tournaments]))
    existing.yearlyStats = { ...existing.yearlyStats, 2026: y2026 }
    existing.totalWins += team2026.totalWins
    existing.totalDraws += team2026.totalDraws
    existing.totalLosses += team2026.totalLosses
    existing.totalGoalsFor += team2026.totalGoalsFor
    existing.totalGoalsAgainst += team2026.totalGoalsAgainst
  })

  return Array.from(byName.values())
}

// ============ 赛事概况卡片 ============
function TournamentOverview() {
  return (
    <div className="w-full max-w-full min-w-0 overflow-x-hidden space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {TOURNAMENTS.map(t => (
          <div key={t.year} className="glass-card overflow-hidden p-4 transition-all hover:shadow-xl sm:p-6">
            <div className="flex flex-col gap-3 mb-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-xl flex items-center justify-center text-lg font-black font-display">
                  {String(t.year).slice(2)}
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg font-bold text-gray-900 font-display tracking-wide">{t.year} 世界杯</h3>
                  <p className="text-sm text-gray-500 flex items-center gap-1">
                    <TeamFlag flagCode={t.hostCode} size="sm" /> {t.host}
                  </p>
                </div>
              </div>
              <div className="text-left text-xs text-gray-400 sm:text-right">
                <div>{t.totalTeams}支球队</div>
                <div>{t.totalMatches}场比赛</div>
              </div>
            </div>

            {/* 领奖台 */}
            <div className="grid grid-cols-1 items-end gap-2 mb-4 min-[480px]:grid-cols-3 sm:gap-3">
              {/* 亚军 */}
              <div className="mx-auto w-full max-w-[18rem] min-w-0 text-center min-[480px]:max-w-none">
                <TeamFlag flagCode={t.runnerUpCode} size="md" />
                <p className="text-xs font-semibold text-gray-600 mt-1 truncate">{t.runnerUp}</p>
                <div className="bg-gray-300 text-gray-600 text-xs font-bold py-1 rounded mt-1">🥈 亚军</div>
              </div>
              {/* 冠军 */}
              <div className="mx-auto w-full max-w-[18rem] min-w-0 text-center min-[480px]:-mt-3 min-[480px]:max-w-none">
                <TeamFlag flagCode={t.championCode} size="lg" />
                <p className="text-sm font-bold text-gray-900 mt-1 truncate">{t.champion}</p>
                <div className="bg-gradient-to-r from-yellow-400 to-yellow-600 text-white text-xs font-bold py-1 rounded mt-1">🏆 冠军</div>
              </div>
              {/* 季军 */}
              <div className="mx-auto w-full max-w-[18rem] min-w-0 text-center min-[480px]:max-w-none">
                <TeamFlag flagCode={t.thirdPlaceCode} size="md" />
                <p className="text-xs font-semibold text-gray-600 mt-1 truncate">{t.thirdPlace}</p>
                <div className="bg-amber-600 text-white text-xs font-bold py-1 rounded mt-1">🥉 季军</div>
              </div>
            </div>

            {/* 数据条 */}
            <div className="grid grid-cols-1 gap-3 text-center min-[480px]:grid-cols-3">
              <div className="bg-blue-50 rounded-lg py-2">
                <p className="text-lg font-bold text-blue-700">{t.totalGoals}</p>
                <p className="text-xs text-gray-500">总进球</p>
              </div>
              <div className="bg-green-50 rounded-lg py-2">
                <p className="text-lg font-bold text-green-700">{t.avgGoalsPerMatch}</p>
                <p className="text-xs text-gray-500">场均进球</p>
              </div>
              <div className="bg-purple-50 rounded-lg py-2">
                <p className="text-sm font-bold text-purple-700">{t.topScorer}</p>
                <p className="text-xs text-gray-500">金靴({t.topScorerGoals}球)</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ============ 球员统计排行 ============
function PlayerStatsPanel({
  initialYear = 0,
  playerLeaderboards,
}: {
  initialYear?: number
  playerLeaderboards: PlayerLeaderboardPayload | null
}) {
  const [selectedYear, setSelectedYear] = useState<number>(initialYear) // 0 = 全部
  const [sortField, setSortField] = useState<PlayerSortField>('goals')
  const [sortAsc, setSortAsc] = useState(false)
  const [expandedPlayer, setExpandedPlayer] = useState<string | null>(null)
  const playerData = useMemo(
    () => selectPlayerStatsForYear(selectedYear, playerLeaderboards?.players ?? [], PLAYER_STATS),
    [playerLeaderboards, selectedYear],
  )

  const filteredPlayers = useMemo(() => {
    const players = selectedYear
      ? playerData.filter(p => {
        const yearly = p.yearlyStats[selectedYear]
        if (!yearly) return false
        if (selectedYear === 2026) {
          return yearly.appearances > 0 || yearly.goals > 0 || yearly.assists > 0 || yearly.yellowCards > 0 || yearly.redCards > 0
        }
        return selectedYear === 2026 || p.tournaments.includes(selectedYear)
      })
      : [...playerData]

    return players.sort((a, b) => {
      let va: number, vb: number
      if (selectedYear) {
        // 按年份筛选时，排序用该年数据，不能拿历史累计黄牌/红牌混排。
        const ya = a.yearlyStats[selectedYear]
        const yb = b.yearlyStats[selectedYear]
        if (!ya) return 1
        if (!yb) return -1
        va = ya[sortField as keyof typeof ya] as number
        vb = yb[sortField as keyof typeof yb] as number
      } else {
        va = a[sortField] as number
        vb = b[sortField] as number
      }
      return sortAsc ? va - vb : vb - va
    })
  }, [playerData, selectedYear, sortField, sortAsc])

  const getPlayerValue = (p: PlayerHistoricalStats, field: PlayerSortField): number => {
    if (selectedYear) {
      return p.yearlyStats[selectedYear]?.[field as keyof typeof p.yearlyStats[number]] ?? 0
    }
    return p[field] as number
  }

  const sortOptions: { key: PlayerSortField; label: string; icon: typeof Target }[] = [
    { key: 'goals', label: '进球', icon: Target },
    { key: 'assists', label: '助攻', icon: TrendingUp },
    { key: 'appearances', label: '出场', icon: Users },
    { key: 'yellowCards', label: '黄牌', icon: Medal },
  ]

  return (
    <div className="space-y-4">
      {/* 筛选器 */}
      <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:gap-3">
        <div className="flex w-full items-center gap-2 text-sm text-gray-600 sm:w-auto">
          <Filter className="w-4 h-4" />
          <span className="font-medium">年份：</span>
        </div>
        <button
          onClick={() => setSelectedYear(0)}
          className={`shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${!selectedYear ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          全部
        </button>
        {AVAILABLE_YEARS.map(y => (
          <button
            key={y}
            onClick={() => setSelectedYear(y)}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${selectedYear === y ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
          >
            {y}
          </button>
        ))}
      </div>

      <div className="flex w-full min-w-0 flex-wrap items-center gap-2">
        <span className="w-full text-sm font-medium text-gray-600 sm:w-auto">排序：</span>
        {sortOptions.map(opt => (
          <button
            key={opt.key}
            onClick={() => {
              if (sortField === opt.key) setSortAsc(!sortAsc)
              else { setSortField(opt.key); setSortAsc(false) }
            }}
            className={`basis-[calc(50%-0.25rem)] shrink-0 justify-center px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1 transition-all sm:basis-auto ${
              sortField === opt.key ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            <opt.icon className="w-3.5 h-3.5" />
            {opt.label}
            {sortField === opt.key && (
              sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
            )}
          </button>
        ))}
      </div>

      {/* 球员列表 */}
      <div className="space-y-2">
        {filteredPlayers.map((p, idx) => (
          <div key={p.name} className="glass-card overflow-hidden">
            <div
              className="flex flex-col gap-4 p-4 cursor-pointer hover:bg-blue-50/50 transition-colors sm:flex-row sm:items-center"
              onClick={() => setExpandedPlayer(expandedPlayer === p.name ? null : p.name)}
            >
              <div className="flex w-full items-center gap-3 sm:w-auto">
                <div className={`w-8 h-8 rounded-full flex flex-shrink-0 items-center justify-center text-sm font-bold ${
                  idx < 3 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {idx + 1}
                </div>
                <TeamFlag flagCode={p.flagCode} size="md" />
                <div className="min-w-0 flex-1 sm:hidden">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-gray-900">{p.name}</span>
                    <span className="text-xs text-gray-400">{p.position}</span>
                  </div>
                  <p className="text-xs text-gray-500">{p.country}</p>
                </div>
              </div>
              <div className="hidden flex-1 min-w-0 sm:block">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-gray-900">{p.name}</span>
                  <span className="text-xs text-gray-400">{p.position}</span>
                </div>
                <p className="text-xs text-gray-500">{p.country}</p>
              </div>
              <div className="grid w-full grid-cols-3 gap-3 text-center sm:w-auto sm:min-w-[220px]">
                <div>
                  <p className="text-lg font-black text-green-600">{getPlayerValue(p, 'goals')}</p>
                  <p className="text-xs text-gray-400">进球</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-blue-600">{getPlayerValue(p, 'assists')}</p>
                  <p className="text-xs text-gray-400">助攻</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-gray-600">{getPlayerValue(p, 'appearances')}</p>
                  <p className="text-xs text-gray-400">出场</p>
                </div>
              </div>
              <ChevronDown className={`hidden w-5 h-5 text-gray-400 transition-transform sm:block ${expandedPlayer === p.name ? 'rotate-180' : ''}`} />
            </div>

            {/* 展开的年份详细数据 */}
            {expandedPlayer === p.name && (
              <div className="px-4 pb-4 border-t border-gray-100">
                <div className="pt-3">
                  <h4 className="text-sm font-semibold text-gray-600 mb-2">按年份表现</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                    {p.tournaments.map(year => {
                      const ys = p.yearlyStats[year]
                      if (!ys) return null
                      return (
                        <div key={year} className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3">
                          <p className="text-sm font-bold text-blue-700 mb-1">{year} 世界杯</p>
                          <div className="grid grid-cols-2 gap-1 text-xs">
                            <div><span className="text-gray-500">进球:</span> <span className="font-semibold text-green-600">{ys.goals}</span></div>
                            <div><span className="text-gray-500">助攻:</span> <span className="font-semibold text-blue-600">{ys.assists}</span></div>
                            <div><span className="text-gray-500">出场:</span> <span className="font-semibold">{ys.appearances}</span></div>
                            <div><span className="text-gray-500">黄牌:</span> <span className="font-semibold text-yellow-600">{ys.yellowCards}</span></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                  {!selectedYear && (
                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-gray-400">
                      <span>累计出场: {p.appearances}场</span>
                      <span>累计进球: {p.goals}个</span>
                      <span>累计助攻: {p.assists}次</span>
                      <span>参赛届数: {p.tournaments.length}届</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ============ 球队统计排行 ============
function TeamStatsPanel({ initialYear = 0, liveMatches }: { initialYear?: number; liveMatches: Match[] }) {
  const [selectedYear, setSelectedYear] = useState<number>(initialYear)
  const [sortField, setSortField] = useState<TeamSortField>('totalWins')
  const [sortAsc, setSortAsc] = useState(false)
  const [expandedTeam, setExpandedTeam] = useState<string | null>(null)
  const teamData = useMemo(() => mergeTeamStatsWith2026(liveMatches), [liveMatches])

  const sortedTeams = useMemo(() => {
    const teams = selectedYear
      ? teamData.filter(t => t.tournaments.includes(selectedYear))
      : [...teamData]

    return teams.sort((a, b) => {
      let va: number, vb: number
      if (selectedYear) {
        const ya = a.yearlyStats[selectedYear]
        const yb = b.yearlyStats[selectedYear]
        if (!ya) return 1
        if (!yb) return -1
        switch (sortField) {
          case 'totalWins': va = ya.won; vb = yb.won; break
          case 'totalGoalsFor': va = ya.goalsFor; vb = yb.goalsFor; break
          case 'totalGoalsAgainst': va = ya.goalsAgainst; vb = yb.goalsAgainst; break
          case 'winRate': va = ya.won / Math.max(ya.played, 1); vb = yb.won / Math.max(yb.played, 1); break
          default: va = ya.won; vb = yb.won
        }
      } else {
        switch (sortField) {
          case 'winRate':
            va = a.totalWins / Math.max(a.totalWins + a.totalDraws + a.totalLosses, 1)
            vb = b.totalWins / Math.max(b.totalWins + b.totalDraws + b.totalLosses, 1)
            break
          default:
            va = a[sortField] as number
            vb = b[sortField] as number
        }
      }
      return sortAsc ? va - vb : vb - va
    })
  }, [teamData, selectedYear, sortField, sortAsc])

  const getTeamDisplayValue = (t: TeamHistoricalStats, field: TeamSortField): string => {
    if (selectedYear) {
      const ys = t.yearlyStats[selectedYear]
      if (!ys) return '-'
      switch (field) {
        case 'totalWins': return String(ys.won)
        case 'totalGoalsFor': return String(ys.goalsFor)
        case 'totalGoalsAgainst': return String(ys.goalsAgainst)
        case 'winRate': return `${(ys.won / Math.max(ys.played, 1) * 100).toFixed(0)}%`
        case 'titles': return ys.finalRank === 1 ? '1' : '0'
        default: return '-'
      }
    }
    switch (field) {
      case 'winRate': return `${(t.totalWins / Math.max(t.totalWins + t.totalDraws + t.totalLosses, 1) * 100).toFixed(0)}%`
      case 'titles': return String(t.titles)
      default: return String(t[field as keyof TeamHistoricalStats])
    }
  }

  const sortOptions: { key: TeamSortField; label: string; icon: typeof Trophy }[] = [
    { key: 'totalWins', label: '胜场', icon: Trophy },
    { key: 'winRate', label: '胜率', icon: TrendingUp },
    { key: 'totalGoalsFor', label: '进球', icon: Target },
    { key: 'totalGoalsAgainst', label: '失球', icon: BarChart3 },
    { key: 'titles', label: '冠军', icon: Medal },
  ]

  return (
    <div className="space-y-4">
      {/* 筛选器 */}
      <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:gap-3">
        <div className="flex w-full items-center gap-2 text-sm text-gray-600 sm:w-auto">
          <Filter className="w-4 h-4" />
          <span className="font-medium">年份：</span>
        </div>
        <button
          onClick={() => setSelectedYear(0)}
          className={`shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${!selectedYear ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          全部
        </button>
        {AVAILABLE_YEARS.map(y => (
          <button
            key={y}
            onClick={() => setSelectedYear(y)}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${selectedYear === y ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
          >
            {y}
          </button>
        ))}
      </div>

      <div className="flex w-full min-w-0 flex-wrap items-center gap-2">
        <span className="w-full text-sm font-medium text-gray-600 sm:w-auto">排序：</span>
        {sortOptions.map(opt => (
          <button
            key={opt.key}
            onClick={() => {
              if (sortField === opt.key) setSortAsc(!sortAsc)
              else { setSortField(opt.key); setSortAsc(false) }
            }}
            className={`basis-[calc(50%-0.25rem)] shrink-0 justify-center px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1 transition-all sm:basis-auto ${
              sortField === opt.key ? 'bg-green-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            <opt.icon className="w-3.5 h-3.5" />
            {opt.label}
            {sortField === opt.key && (
              sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
            )}
          </button>
        ))}
      </div>

      {/* 球队列表 */}
      <div className="space-y-2">
        {sortedTeams.map((t, idx) => {
          const totalMatches = selectedYear
            ? t.yearlyStats[selectedYear]?.played ?? 0
            : t.totalWins + t.totalDraws + t.totalLosses
          const wins = selectedYear ? t.yearlyStats[selectedYear]?.won ?? 0 : t.totalWins
          const draws = selectedYear ? t.yearlyStats[selectedYear]?.drawn ?? 0 : t.totalDraws
          const losses = selectedYear ? t.yearlyStats[selectedYear]?.lost ?? 0 : t.totalLosses
          const winPct = totalMatches > 0 ? (wins / totalMatches * 100) : 0
          const drawPct = totalMatches > 0 ? (draws / totalMatches * 100) : 0

          return (
            <div key={t.name} className="glass-card overflow-hidden">
            <div
              className="flex flex-col gap-4 p-4 cursor-pointer hover:bg-blue-50/50 transition-colors sm:flex-row sm:items-center"
              onClick={() => setExpandedTeam(expandedTeam === t.name ? null : t.name)}
            >
              <div className="flex w-full items-center gap-3 sm:w-auto">
                <div className={`w-8 h-8 rounded-full flex flex-shrink-0 items-center justify-center text-sm font-bold ${
                  idx < 3 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {idx + 1}
                </div>
                <TeamFlag flagCode={t.flagCode} size="lg" />
                <div className="min-w-0 flex-1 sm:hidden">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-gray-900 text-lg">{t.name}</span>
                    {t.titles > 0 && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-semibold">
                        x{t.titles}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">参赛 {t.tournaments.length} 届</p>
                </div>
              </div>
              <div className="hidden flex-1 min-w-0 sm:block">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 text-lg">{t.name}</span>
                    {t.titles > 0 && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-semibold">
                        🏆 x{t.titles}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">参赛 {t.tournaments.length} 届</p>
                </div>
                <div className="grid w-full grid-cols-3 gap-3 text-center sm:w-auto sm:min-w-[220px]">
                  <div>
                    <p className="text-lg font-black text-green-600">{getTeamDisplayValue(t, 'totalWins')}</p>
                    <p className="text-xs text-gray-400">胜场</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-blue-600">{getTeamDisplayValue(t, 'totalGoalsFor')}</p>
                    <p className="text-xs text-gray-400">进球</p>
                  </div>
                  <div>
                    <p className="text-lg font-bold text-purple-600">{getTeamDisplayValue(t, 'winRate')}</p>
                    <p className="text-xs text-gray-400">胜率</p>
                  </div>
                </div>
                <ChevronDown className={`hidden w-5 h-5 text-gray-400 transition-transform sm:block ${expandedTeam === t.name ? 'rotate-180' : ''}`} />
              </div>

              {/* 展开的年份详细数据 + 胜负条 */}
              {expandedTeam === t.name && (
                <div className="px-4 pb-4 border-t border-gray-100">
                  {/* 胜负比例条 */}
                  <div className="mt-3 mb-3">
                    <div className="flex h-4 rounded-full overflow-hidden text-xs font-semibold">
                      <div className="bg-green-500 text-white flex items-center justify-center" style={{ width: `${winPct}%` }}>
                        {winPct > 15 && `${winPct.toFixed(0)}%`}
                      </div>
                      <div className="bg-gray-400 text-white flex items-center justify-center" style={{ width: `${drawPct}%` }}>
                        {drawPct > 15 && `${drawPct.toFixed(0)}%`}
                      </div>
                      <div className="bg-red-400 text-white flex items-center justify-center" style={{ width: `${100 - winPct - drawPct}%` }}>
                        {100 - winPct - drawPct > 15 && `${(100 - winPct - drawPct).toFixed(0)}%`}
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span className="text-green-600">胜 {wins}</span>
                      <span className="text-gray-500">平 {draws}</span>
                      <span className="text-red-500">负 {losses}</span>
                    </div>
                  </div>

                  {/* 年份卡片 */}
                  <h4 className="text-sm font-semibold text-gray-600 mb-2">历届战绩</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                    {t.tournaments.map(year => {
                      const ys = t.yearlyStats[year]
                      if (!ys) return null
                      return (
                        <div key={year} className={`rounded-lg p-3 ${
                          ys.finalRank === 1 ? 'bg-gradient-to-br from-yellow-50 to-yellow-100 border border-yellow-200' :
                          ys.finalRank <= 4 ? 'bg-gradient-to-br from-blue-50 to-indigo-50' :
                          'bg-gray-50'
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-sm font-bold text-blue-700">{year}</p>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                              ys.finalRank === 1 ? 'bg-yellow-200 text-yellow-800' :
                              ys.finalRank <= 3 ? 'bg-blue-200 text-blue-800' :
                              ys.finalRank <= 8 ? 'bg-green-100 text-green-800' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {ys.position}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-1 text-xs">
                            <div><span className="text-gray-500">胜:</span> <span className="font-semibold text-green-600">{ys.won}</span></div>
                            <div><span className="text-gray-500">平:</span> <span className="font-semibold">{ys.drawn}</span></div>
                            <div><span className="text-gray-500">负:</span> <span className="font-semibold text-red-600">{ys.lost}</span></div>
                            <div><span className="text-gray-500">进:</span> <span className="font-semibold text-blue-600">{ys.goalsFor}</span></div>
                            <div><span className="text-gray-500">失:</span> <span className="font-semibold text-orange-600">{ys.goalsAgainst}</span></div>
                            <div><span className="text-gray-500">排名:</span> <span className="font-semibold">#{ys.finalRank}</span></div>
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {!selectedYear && (
                    <div className="mt-3 text-xs text-gray-400">
                      累计 {t.totalWins}胜 {t.totalDraws}平 {t.totalLosses}负 | 进{t.totalGoalsFor}球 失{t.totalGoalsAgainst}球
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LiveLeaderboardCard({
  title,
  entries,
  valueField,
  valueLabel,
  icon: Icon,
  accentClass,
  barClass,
  isLoading = false,
  errorMessage = null,
}: {
  title: string
  entries: PlayerHistoricalStats[]
  valueField: 'goals' | 'assists'
  valueLabel: string
  icon: typeof Target
  accentClass: string
  barClass: string
  isLoading?: boolean
  errorMessage?: string | null
}) {
  const topValue = Math.max(...entries.map(entry => entry.yearlyStats[2026]?.[valueField] ?? 0), 1)

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex flex-col gap-2 border-b bg-gray-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="flex items-center gap-2 text-lg font-bold text-gray-900">
          <Icon className={`h-5 w-5 ${accentClass}`} />
          {title}
        </h2>
        <span className="flex items-center gap-1 text-xs text-gray-400">
          <Clock className="h-3 w-3" />
          随比赛事件更新
        </span>
      </div>

      {errorMessage ? (
        <div className="py-8 text-center text-red-600">
          <RefreshCw className="mx-auto mb-2 h-10 w-10 opacity-40" />
          <p className="text-sm font-semibold">{errorMessage}</p>
        </div>
      ) : isLoading ? (
        <div className="py-8 text-center text-gray-500">
          <RefreshCw className="mx-auto mb-2 h-10 w-10 animate-spin opacity-40" />
          <p className="text-sm font-medium">正在同步官方实时榜单...</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="py-8 text-center text-gray-400">
          <Icon className="mx-auto mb-2 h-10 w-10 opacity-30" />
          <p className="text-sm">暂无可统计的 2026 比赛事件</p>
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {entries.map((player, idx) => {
            const yearStats = player.yearlyStats[2026]
            const value = yearStats?.[valueField] ?? 0
            const width = `${Math.max(18, value / topValue * 100)}%`

            return (
              <div key={`${title}-${player.name}`} className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                    idx < 3 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 text-white' : 'bg-gray-200 text-gray-600'
                  }`}>
                    {idx + 1}
                  </div>
                  <TeamFlag flagCode={player.flagCode} size="md" />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-gray-900">{player.name}</span>
                      <span className="text-xs text-gray-400">{player.position}</span>
                    </div>
                    <p className="text-xs text-gray-500">{player.country} · 出场 {yearStats?.appearances ?? 0}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-2xl font-black ${accentClass}`}>{value}</p>
                    <p className="text-xs text-gray-400">{valueLabel}</p>
                  </div>
                </div>
                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-gray-100">
                  <div className={`h-full rounded-full ${barClass}`} style={{ width }} />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ============ 2026实时数据面板 ============
function Live2026Panel({
  liveMatches,
  liveStatus,
  playerLeaderboards,
  playerLeaderboardsLoading,
  playerLeaderboardsError,
}: {
  liveMatches: Match[]
  liveStatus: LiveSyncStatus | null
  playerLeaderboards: PlayerLeaderboardPayload | null
  playerLeaderboardsLoading: boolean
  playerLeaderboardsError: string | null
}) {
  const [selectedGroup, setSelectedGroup] = useState('A')
  const [now, setNow] = useState(() => new Date())
  const standings: StandingEntry[] = useMemo(
    () => calculateGroupStandingsFromMatches(selectedGroup, liveMatches),
    [liveMatches, selectedGroup],
  )
  const scorerBoard = useMemo(
    () => playerLeaderboards?.scorers ?? [],
    [playerLeaderboards],
  )
  const assistBoard = useMemo(
    () => playerLeaderboards?.assists ?? [],
    [playerLeaderboards],
  )

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30000)
    return () => window.clearInterval(timer)
  }, [])

  // 统计数据
  const completedMatches = liveMatches.filter(m => m.status === 'completed')
  const totalGoals = completedMatches.reduce((sum, m) => sum + (m.home_score || 0) + (m.away_score || 0), 0)

  return (
    <div className="w-full max-w-full min-w-0 overflow-x-hidden space-y-6">
      {/* 实时统计概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">已完成比赛</p>
          <p className="text-3xl font-black text-green-600">{completedMatches.length}</p>
          <p className="text-xs text-gray-400">/ {liveMatches.length}场</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">总进球</p>
          <p className="text-3xl font-black text-blue-600">{totalGoals}</p>
          <p className="text-xs text-gray-400">场均 {(totalGoals / Math.max(completedMatches.length, 1)).toFixed(1)} 球</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">参赛球队</p>
          <p className="text-3xl font-black text-purple-600">{TEAMS.length}</p>
          <p className="text-xs text-gray-400">12个小组</p>
        </div>
        <div className="glass-card p-4 text-center">
          <p className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1">
            <RefreshCw className="w-3 h-3" />
            数据更新
          </p>
          <p className="text-lg font-bold text-orange-600">{liveStatus?.status === 'connected' ? '已连接' : liveStatus?.status === 'stale' ? '延迟' : '待配置'}</p>
          <p className="text-xs text-gray-400">{now.getHours()}:{now.getMinutes().toString().padStart(2, '0')}</p>
        </div>
      </div>

      {Boolean(liveStatus?.pending_result_count) && (
        <div className="glass-card p-4 text-sm font-semibold text-amber-800">
          有 {liveStatus?.pending_result_count} 场比赛已过预计完场时间，但实时数据源尚未写入官方赛果。
        </div>
      )}

      {/* 小组积分榜 */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b bg-blue-50 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-bold text-blue-800 flex items-center gap-2">
            <Trophy className="w-5 h-5" />
            小组积分榜
          </h2>
          <div className="grid w-full max-w-72 grid-cols-6 gap-1 sm:flex sm:w-auto sm:max-w-none sm:flex-wrap">
            {GROUPS_2026.map(g => (
              <button
                key={g}
                onClick={() => setSelectedGroup(g)}
                className={`shrink-0 px-2.5 py-1 rounded text-xs font-bold transition-all ${selectedGroup === g ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-500">
                <th className="py-3 px-4 text-left font-medium">#</th>
                <th className="py-3 px-4 text-left font-medium">球队</th>
                <th className="py-3 px-2 text-center font-medium">赛</th>
                <th className="py-3 px-2 text-center font-medium">胜</th>
                <th className="py-3 px-2 text-center font-medium">平</th>
                <th className="py-3 px-2 text-center font-medium">负</th>
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
                      <TeamFlag flagCode={TEAMS.find(t => t.name === s.team)?.flagCode || ''} size="sm" />
                      <span className="font-bold text-gray-900">{s.team}</span>
                      {TEAMS.find(t => t.name === s.team)?.is_host && <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">东道主</span>}
                    </div>
                  </td>
                  <td className="py-3 px-2 text-center">{s.played}</td>
                  <td className="py-3 px-2 text-center text-green-600 font-medium">{s.won}</td>
                  <td className="py-3 px-2 text-center text-gray-500">{s.drawn}</td>
                  <td className="py-3 px-2 text-center text-red-500">{s.lost}</td>
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
        <div className="p-3 bg-gray-50 text-xs text-gray-400 flex flex-wrap items-center gap-2">
          <span className="inline-block w-3 h-3 bg-green-600 rounded-full"></span>
          前2名晋级淘汰赛
          <span className="ml-4">· 基于 {completedMatches.length} 场已完成比赛实时计算</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <LiveLeaderboardCard
          title="2026实时射手榜"
          entries={scorerBoard}
          valueField="goals"
          valueLabel="进球"
          icon={Target}
          accentClass="text-red-500"
          barClass="bg-red-500"
          isLoading={playerLeaderboardsLoading}
          errorMessage={playerLeaderboardsError}
        />
        <LiveLeaderboardCard
          title="2026实时助攻榜"
          entries={assistBoard}
          valueField="assists"
          valueLabel="助攻"
          icon={TrendingUp}
          accentClass="text-blue-600"
          barClass="bg-blue-600"
          isLoading={playerLeaderboardsLoading}
          errorMessage={playerLeaderboardsError}
        />
      </div>
    </div>
  )
}

// ============ 主页面 ============
export default function StatsPage() {
  const [searchParams] = useSearchParams()
  const requestedTab = searchParams.get('tab') as TabType | null
  const initialTab: TabType = requestedTab && ['overview', 'players', 'teams', 'live2026'].includes(requestedTab)
    ? requestedTab
    : 'live2026'
  const requestedYear = Number(searchParams.get('year'))
  const initialYear = Number.isFinite(requestedYear) && AVAILABLE_YEARS.includes(requestedYear) ? requestedYear : 0
  const [activeTab, setActiveTab] = useState<TabType>(initialTab)
  const [liveMatches, setLiveMatches] = useState<Match[]>([])
  const [liveStatus, setLiveStatus] = useState<LiveSyncStatus | null>(null)
  const [playerLeaderboards, setPlayerLeaderboards] = useState<PlayerLeaderboardPayload | null>(null)
  const [playerLeaderboardsLoading, setPlayerLeaderboardsLoading] = useState(true)
  const [playerLeaderboardsError, setPlayerLeaderboardsError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const fetchLiveData = async () => {
      const [matchesResult, statusResult, leaderboardsResult] = await Promise.allSettled([
        matchAPI.getMatchesStrict(),
        matchAPI.getLiveStatusStrict(),
        playerStatsAPI.get2026Leaderboards(),
      ])
      if (!active) return

      if (matchesResult.status === 'fulfilled') {
        setLiveMatches(matchesResult.value)
      } else {
        console.error('Failed to load live matches for stats page:', matchesResult.reason)
      }

      if (statusResult.status === 'fulfilled') {
        setLiveStatus(statusResult.value)
      } else {
        console.error('Failed to load live sync status:', statusResult.reason)
        setLiveStatus({
          status: 'error',
          source: 'api_error',
          last_updated: null,
          last_sync_attempt: new Date().toISOString(),
          message: '实时数据接口读取失败，请重新登录或稍后刷新',
          match_count: 0,
          pending_result_count: 0,
          pending_results: [],
        })
      }

      if (leaderboardsResult.status === 'fulfilled') {
        setPlayerLeaderboards(leaderboardsResult.value)
        setPlayerLeaderboardsError(null)
      } else {
        console.error('Failed to load 2026 player leaderboards:', leaderboardsResult.reason)
        setPlayerLeaderboardsError('实时射手/助攻榜读取失败，请重新登录或稍后刷新。')
      }
      setPlayerLeaderboardsLoading(false)
    }

    fetchLiveData()
    const timer = window.setInterval(fetchLiveData, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const tabs: { key: TabType; label: string; icon: typeof BarChart3 }[] = [
    { key: 'live2026', label: '2026实时', icon: Clock },
    { key: 'players', label: '球员数据', icon: Users },
    { key: 'teams', label: '球队数据', icon: Trophy },
    { key: 'overview', label: '赛事概况', icon: BarChart3 },
  ]

  return (
    <div className="space-y-6">
      <div className="text-center mb-4">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-900 font-display tracking-wide">数据统计</h1>
        <p className="mx-auto mt-2 max-w-2xl px-2 text-sm leading-6 text-gray-500 sm:text-base">
          <span className="block sm:inline">1994-2022历史数据 · 2026实时/赛前数据</span>
          <span className="hidden sm:inline"> · </span>
          <span className="block sm:inline">球员与球队统计排行</span>
        </p>
      </div>

      {/* Tab 切换 */}
      <div className="grid grid-cols-1 gap-2 min-[520px]:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:flex sm:flex-wrap sm:justify-center">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`min-w-0 px-3 py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all sm:px-5 ${
              activeTab === tab.key
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      {activeTab === 'live2026' && (
        <Live2026Panel
          liveMatches={liveMatches}
          liveStatus={liveStatus}
          playerLeaderboards={playerLeaderboards}
          playerLeaderboardsLoading={playerLeaderboardsLoading}
          playerLeaderboardsError={playerLeaderboardsError}
        />
      )}
      {activeTab === 'overview' && <TournamentOverview />}
      {activeTab === 'players' && (
        <PlayerStatsPanel
          initialYear={initialYear}
          playerLeaderboards={playerLeaderboards}
        />
      )}
      {activeTab === 'teams' && <TeamStatsPanel initialYear={initialYear} liveMatches={liveMatches} />}
    </div>
  )
}
