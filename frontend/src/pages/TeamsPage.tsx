import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trophy, TrendingUp } from 'lucide-react'
import { TEAMS } from '../services/wc2026-data'
import { getChampionProbabilities } from '../services/champion-probabilities'
import TeamFlag from '../components/TeamFlag'

export default function TeamsPage() {
  const [selectedGroup, setSelectedGroup] = useState<string>('')
  const [sortBy, setSortBy] = useState<'fifa_rank' | 'elo_rating'>('fifa_rank')
  const championRanking = useMemo(() => getChampionProbabilities(), [])
  const championMap = useMemo(() => new Map(championRanking.map(team => [team.teamName, team])), [championRanking])
  const topChampionTeams = championRanking.slice(0, 8)

  const groups = ['A','B','C','D','E','F','G','H','I','J','K','L']
  const filteredTeams = selectedGroup
    ? TEAMS.filter(t => t.group === selectedGroup)
    : TEAMS
  const sortedTeams = [...filteredTeams].sort((a, b) =>
    sortBy === 'fifa_rank' ? a.fifa_rank - b.fifa_rank : b.elo_rating - a.elo_rating
  )

  return (
    <div className="space-y-6">
      <div className="text-center mb-4">
        <h1 className="text-3xl font-black text-gray-900 font-display tracking-wide">48支参赛球队</h1>
        <p className="text-gray-500 mt-2">12个小组 · FIFA排名 + Elo评分 · 4支首次参赛</p>
      </div>

      <section className="glass-card p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-black text-slate-900">
              <Trophy className="h-5 w-5 text-amber-500" />
              冠军几率排名
            </h2>
            <p className="mt-1 text-sm font-medium text-slate-500">按 Elo、FIFA 排名、地域优势和赛程经验做本地归一化估算</p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">
            <TrendingUp className="h-3.5 w-3.5" />
            Top 8
          </span>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {topChampionTeams.map((team, index) => (
            <Link key={team.teamName} to={`/teams/${TEAMS.find(item => item.name === team.teamName)?.id ?? ''}`} className="rounded-[22px] border border-white/50 bg-white/58 p-3 transition hover:bg-white/75">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-black text-white">#{index + 1}</span>
                <TeamFlag flagCode={team.flagCode} size="md" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-black text-slate-900">{team.teamName}</p>
                  <p className="text-xs font-semibold text-slate-500">{team.tier}</p>
                </div>
                <span className="text-lg font-black text-blue-700">{team.probability.toFixed(1)}%</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200/70">
                <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500" style={{ width: `${Math.min(team.probability * 8, 100)}%` }} />
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 筛选 */}
      <div className="flex flex-wrap gap-2 justify-center">
        <button
          onClick={() => setSelectedGroup('')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${!selectedGroup ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}
        >
          全部
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

      <div className="flex justify-center gap-2">
        <button
          onClick={() => setSortBy('fifa_rank')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${sortBy === 'fifa_rank' ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600'}`}
        >
          按FIFA排名
        </button>
        <button
          onClick={() => setSortBy('elo_rating')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium ${sortBy === 'elo_rating' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600'}`}
        >
          按Elo评分
        </button>
      </div>

      {/* 球队卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedTeams.map((team, idx) => (
          <Link
            key={team.id}
            to={`/teams/${team.id}`}
            className="glass-card p-5 hover:shadow-lg transition-all hover:-translate-y-0.5"
          >
            <div className="flex items-center gap-4">
              <TeamFlag flagCode={team.flagCode} size="lg" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-gray-900 text-lg">{team.name}</h3>
                  {team.is_host && <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full">东道主</span>}
                  {team.is_defending && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">卫冕</span>}
                  {team.is_debut && <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">首次参赛</span>}
                </div>
                <div className="flex items-center gap-4 mt-1">
                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">{team.group}组</span>
                  <span className="text-xs text-gray-500">FIFA #{team.fifa_rank}</span>
                  <span className="text-xs text-gray-500">Elo {team.elo_rating}</span>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-black text-amber-700">
                    夺冠 {championMap.get(team.name)?.probability.toFixed(1) ?? '0.0'}%
                  </span>
                  <span className="truncate text-xs font-semibold text-gray-400">{championMap.get(team.name)?.tier}</span>
                </div>
              </div>
              <div className="text-2xl font-black text-gray-300">#{idx + 1}</div>
            </div>
          </Link>
        ))}
      </div>

      <div className="text-center text-sm text-gray-400 pt-4">
        共 {sortedTeams.length} 支球队 · FIFA排名数据截至2026年4月
      </div>
    </div>
  )
}
