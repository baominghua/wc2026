import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Activity, ArrowLeft, BarChart3, CalendarDays, Clock, MapPin, Shield, Star, Trophy, Users } from 'lucide-react'
import { getLocalTeamAnalysisProfile, matchAPI, teamAPI } from '../services/api'
import type { LocalTeamAnalysisProfile, TeamDetailData, TeamFeatureProfile } from '../services/api'
import { TEAMS, getStageNameCN, getEffectiveMatchStage } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'
import TeamFlag from '../components/TeamFlag'
import TeamFlagLink from '../components/TeamFlagLink'
import { getPredictMatchPath } from '../utils/navigation'

const formatMatchDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const getMatchLabel = (match: Match, teamName: string) => {
  if (match.status === 'completed' && match.home_score !== undefined && match.away_score !== undefined) {
    const isHome = match.home_team === teamName
    const teamScore = isHome ? match.home_score : match.away_score
    const opponentScore = isHome ? match.away_score : match.home_score
    const result = teamScore > opponentScore ? '胜' : teamScore < opponentScore ? '负' : '平'
    return `${result} ${match.home_score}-${match.away_score}`
  }

  if (match.status === 'live') return '进行中'
  return '未开赛'
}

const ROLE_LABELS_BY_COUNT: Record<number, string[]> = {
  1: ['ST'],
  2: ['LCM', 'RCM'],
  3: ['LW', 'AM', 'RW'],
  4: ['LB', 'LCB', 'RCB', 'RB'],
  5: ['LWB', 'LCB', 'CB', 'RCB', 'RWB'],
}

const getShortName = (name: string) => {
  const cleanName = name.replace(/[·.\s]/g, '')
  return cleanName.length > 4 ? cleanName.slice(0, 4) : cleanName
}

const formatProfileNumber = (value?: number | null, suffix = '') => (
  typeof value === 'number' && Number.isFinite(value) ? `${value.toFixed(2)}${suffix}` : '-'
)

const getFeatureTagLabel = (tag: string) => {
  const labels: Record<string, string> = {
    attack_hot: '进攻偏热',
    defense_leaky: '防线波动',
    momentum_up: '状态上行',
    form_dip: '状态下滑',
    draw_resilience: '平局韧性',
    discipline_watch: '纪律观察',
    red_card_distorted: '红牌噪声',
    pending_sample: '待补样本',
  }
  return labels[tag] || tag
}

function TeamFeatureLibraryCard({ featureProfile }: { featureProfile?: TeamFeatureProfile }) {
  if (!featureProfile) return null

  const form = featureProfile.form_state || {}
  const discipline = featureProfile.discipline_state || {}
  const tags = featureProfile.tactical_tags || []
  const notes = featureProfile.next_prediction_notes || featureProfile.review_lessons || []

  return (
    <section className="glass-card overflow-hidden">
      <div className="border-b bg-cyan-50/70 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
              <Activity className="h-5 w-5 text-cyan-600" />
              球队特征库 / 模型记忆
            </h2>
            <p className="mt-1 text-xs font-semibold text-gray-500">
              {featureProfile.source_label || '按正式赛样本生成'} · 样本 {featureProfile.sample_matches ?? 0} 场
            </p>
          </div>
          <span className="w-fit rounded-full bg-white/80 px-3 py-1 text-xs font-black text-cyan-700">
            状态分 {formatProfileNumber(form.score)}
          </span>
        </div>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-2">
          {[
            ['场均积分', formatProfileNumber(form.avg_points)],
            ['场均净胜', formatProfileNumber(form.avg_goal_diff)],
            ['场均进球', formatProfileNumber(form.avg_goals_for)],
            ['场均失球', formatProfileNumber(form.avg_goals_against)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-white/70 bg-white/70 p-3">
              <p className="text-xs font-bold text-gray-500">{label}</p>
              <p className="mt-1 text-2xl font-black text-cyan-700">{value}</p>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <div className="rounded-lg border border-white/70 bg-white/70 p-3">
            <p className="text-sm font-black text-gray-900">纪律与波动</p>
            <p className="mt-1 text-sm leading-6 text-gray-600">
              黄牌均值 {formatProfileNumber(discipline.yellow_cards_for)} · 红牌累计 {discipline.red_cards_for ?? '-'} · 风险 {discipline.risk || '-'}
            </p>
            {tags.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {tags.map(tag => (
                  <span key={tag} className="rounded-full bg-cyan-50 px-2.5 py-1 text-[11px] font-black text-cyan-700">
                    {getFeatureTagLabel(tag)}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-white/70 bg-white/70 p-3">
            <p className="text-sm font-black text-gray-900">下次预测注意事项</p>
            <div className="mt-2 space-y-1.5">
              {(notes.length ? notes : ['暂无额外注意事项，预测时按基础实力与战术画像处理。']).slice(0, 3).map(note => (
                <p key={note} className="text-sm leading-6 text-gray-600">· {note}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

const getTacticalRows = (profile: LocalTeamAnalysisProfile) => {
  const counts = profile.formation
    .split('-')
    .map(part => Number.parseInt(part, 10))
    .filter(count => Number.isFinite(count) && count > 0)
  let cursor = 1
  const outfieldLines = counts.map(count => {
    const labels = ROLE_LABELS_BY_COUNT[count] ?? Array.from({ length: count }, (_, index) => `P${index + 1}`)
    const players = profile.starters.slice(cursor, cursor + count)
    cursor += count
    return players.map((name, index) => ({ name, label: labels[index] ?? `P${index + 1}` }))
  })
  return [
    ...outfieldLines.slice().reverse(),
    [{ name: profile.starters[0] ?? '门将', label: 'GK' }],
  ]
}

function TacticalPitch({ profile }: { profile: LocalTeamAnalysisProfile }) {
  const rows = getTacticalRows(profile)

  return (
    <div className="tactical-pitch" aria-label={`${profile.formation} 战术阵型图`}>
      <div className="tactical-pitch-badge">{profile.formation}</div>
      <div className="tactical-pitch-lines">
        {rows.map((row, rowIndex) => (
          <div key={`${rowIndex}-${row.length}`} className="tactical-row" style={{ gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))` }}>
            {row.map(player => (
              <div key={`${player.label}-${player.name}`} className="tactical-player">
                <span>{player.label}</span>
                <strong>{getShortName(player.name)}</strong>
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="tactical-pitch-direction">进攻方向</div>
    </div>
  )
}

export default function TeamDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const teamId = parseInt(id || '0', 10)
  const team = TEAMS.find(t => t.id === teamId)
  const [liveMatches, setLiveMatches] = useState<Match[]>([])
  const [matchesError, setMatchesError] = useState<string | null>(null)
  const [teamDetail, setTeamDetail] = useState<TeamDetailData | null>(null)
  const [teamDetailError, setTeamDetailError] = useState<string | null>(null)

  const profile = useMemo(() => team ? getLocalTeamAnalysisProfile(team.name) : null, [team])

  useEffect(() => {
    let active = true
    const fetchData = async () => {
      try {
        const [matches, detail] = await Promise.all([
          matchAPI.getMatchesStrict(),
          teamAPI.getTeamDetail(teamId),
        ])
        if (!active) return
        setLiveMatches(matches)
        setTeamDetail(detail)
        setMatchesError(null)
        setTeamDetailError(null)
      } catch {
        if (active) {
          setMatchesError('实时赛程接口读取失败，请重新登录或稍后刷新。')
          setTeamDetailError('球队特征库读取失败，暂时只展示本地战术档案。')
        }
      }
    }

    void fetchData()
    const timer = window.setInterval(fetchData, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [teamId])

  const teamMatches = useMemo(() => {
    if (!team) return []
    return liveMatches
      .filter(match => match.home_team === team.name || match.away_team === team.name)
      .sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())
      .slice(0, 8)
  }, [liveMatches, team])

  if (!team || !profile) {
    return (
      <div className="py-20 text-center">
        <p className="text-lg text-gray-500">球队信息未找到</p>
        <Link to="/teams" className="mt-4 inline-block font-semibold text-blue-600 hover:underline">
          返回球队列表
        </Link>
      </div>
    )
  }

  const keyPlayers = profile.players.slice(0, 4)
  const squad = teamDetail?.squad || profile.squad
  const featureProfile = teamDetail?.feature_profile
  const squadCount = squad?.player_count ?? Array.from(new Set([...profile.starters, ...profile.benchOptions])).length
  const squadGroups = squad ? [
    { label: '门将', players: squad.positions.goalkeepers },
    { label: '后卫', players: squad.positions.defenders },
    { label: '中场', players: squad.positions.midfielders },
    { label: '前锋', players: squad.positions.forwards },
  ] : []

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
    <div className="space-y-5">
      <Link to="/teams" className="inline-flex items-center gap-1 text-sm font-bold text-blue-600 hover:underline">
        <ArrowLeft className="h-4 w-4" />
        返回球队列表
      </Link>

      <section className="glass-card overflow-hidden">
        <div className="grid gap-5 p-5 md:grid-cols-[1.4fr_1fr] md:p-7">
          <div className="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-center">
            <TeamFlag flagCode={team.flagCode} size="xl" />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-3xl font-black text-gray-900 font-display sm:text-4xl">{team.name}</h1>
                {team.is_host && <span className="rounded-full bg-yellow-100 px-2.5 py-1 text-xs font-bold text-yellow-700">东道主</span>}
                {team.is_defending && <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-bold text-green-700">卫冕冠军</span>}
                {team.is_debut && <span className="rounded-full bg-purple-100 px-2.5 py-1 text-xs font-bold text-purple-700">首次参赛</span>}
              </div>
              <p className="mt-2 text-sm text-gray-500">
                {team.code} · {team.group}组 · 常用阵型 {profile.formation}
              </p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">{profile.style}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-blue-50 p-3 text-center">
              <p className="text-2xl font-black text-blue-600">#{team.fifa_rank}</p>
              <p className="mt-1 text-xs font-semibold text-gray-500">FIFA排名</p>
            </div>
            <div className="rounded-lg bg-purple-50 p-3 text-center">
              <p className="text-2xl font-black text-purple-600">{team.elo_rating}</p>
              <p className="mt-1 text-xs font-semibold text-gray-500">Elo评分</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-2xl font-black text-green-600">{team.group}</p>
              <p className="mt-1 text-xs font-semibold text-gray-500">所在小组</p>
            </div>
            <div className="rounded-lg bg-orange-50 p-3 text-center">
              <p className="text-2xl font-black text-orange-600">{squadCount}</p>
              <p className="mt-1 text-xs font-semibold text-gray-500">{squad ? '官方名单' : '阵容候选'}</p>
            </div>
          </div>
        </div>
      </section>

      {teamDetailError && (
        <div className="rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-700">
          {teamDetailError}
        </div>
      )}

      <TeamFeatureLibraryCard featureProfile={featureProfile} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="glass-card overflow-hidden">
          <div className="border-b bg-gray-50/80 p-4">
            <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
              <Users className="h-5 w-5 text-blue-600" />
              阵容人员信息
            </h2>
            <p className="mt-1 text-xs text-gray-500">
              {squad
                ? `${squad.source_team_name} 官方26人名单；候选首发会在临场官方首发接入后自动覆盖`
                : '候选首发与替补变量，用于预测页首发模型'}
            </p>
          </div>

          <div className="grid gap-4 p-4 md:grid-cols-2">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-bold text-gray-900">预测常用首发</span>
                <span className="rounded-full bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{profile.formation}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {profile.starters.map((player, index) => (
                  <span key={`${player}-${index}`} className="rounded-lg bg-blue-50 px-2.5 py-2 text-xs font-bold leading-4 text-blue-800">
                    {player}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-2 text-sm font-bold text-gray-900">替补与轮换</div>
              <div className="flex flex-wrap gap-2">
                {profile.benchOptions.map(player => (
                  <span key={player} className="rounded-lg bg-gray-100 px-2.5 py-2 text-xs font-semibold text-gray-700">
                    {player}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {squad && (
            <div className="border-t border-white/70 p-4">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-black text-gray-900">完整26人名单</h3>
                  <p className="mt-1 text-xs text-gray-500">
                    主教练 {squad.coach || '待补'} · {squad.announcement || '官方名单已接入'}
                  </p>
                </div>
                <a
                  href={squad.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-bold text-blue-700 hover:bg-blue-100"
                >
                  名单来源
                </a>
              </div>
              <div className="grid gap-3 lg:grid-cols-4">
                {squadGroups.map(group => (
                  <div key={group.label} className="rounded-lg border border-white/70 bg-white/55 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-black text-gray-900">{group.label}</span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-500">{group.players.length}</span>
                    </div>
                    <div className="space-y-1.5">
                      {group.players.map(player => (
                        <div key={`${player.number}-${player.name}`} className="min-w-0 rounded-md bg-white/70 px-2 py-1.5">
                          <div className="flex min-w-0 items-center gap-2">
                            <span className="w-5 shrink-0 text-[11px] font-black text-blue-600">{player.number}</span>
                            <span className="truncate text-xs font-bold text-gray-900">{player.name}</span>
                          </div>
                          <p className="mt-0.5 truncate pl-7 text-[11px] font-semibold text-gray-400">
                            {player.club || 'Club N/A'} · {player.caps || 0}场/{player.goals || 0}球
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="glass-card overflow-hidden">
          <div className="border-b bg-gray-50/80 p-4">
            <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
              <Shield className="h-5 w-5 text-amber-500" />
              战术画像
            </h2>
          </div>
          <div className="grid gap-4 p-4 md:grid-cols-[0.95fr_1.05fr]">
            <TacticalPitch profile={profile} />
            <div className="space-y-3 text-sm">
              <div className="rounded-[20px] border border-white/50 bg-white/55 p-3">
                <span className="font-black text-gray-900">进攻路径：</span>
                <span className="text-gray-600">{profile.attackingPattern}</span>
              </div>
              <div className="rounded-[20px] border border-white/50 bg-white/55 p-3">
                <span className="font-black text-gray-900">防守结构：</span>
                <span className="text-gray-600">{profile.defensiveShape}</span>
              </div>
              <div className="rounded-[20px] border border-white/50 bg-white/55 p-3">
                <span className="font-black text-gray-900">定位球：</span>
                <span className="text-gray-600">{profile.setPiece}</span>
              </div>
              <div className="rounded-[20px] border border-white/50 bg-white/55 p-3">
                <span className="font-black text-gray-900">风险点：</span>
                <span className="text-gray-600">{profile.risk}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section className="glass-card overflow-hidden">
        <div className="border-b bg-gray-50/80 p-4">
          <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
            <Star className="h-5 w-5 text-yellow-500" />
            关键球员信息
          </h2>
          <p className="mt-1 text-xs text-gray-500">影响力、角色与进攻参与比例会进入进球球员预测</p>
        </div>
        <div className="grid grid-cols-1 gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
          {keyPlayers.map(player => (
            <div key={player.name} className="rounded-lg border border-gray-100 bg-white/80 p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-black text-gray-900">{player.name}</p>
                  <p className="mt-1 text-xs font-semibold text-gray-400">{player.position} · {player.role}</p>
                </div>
                <Activity className="h-5 w-5 shrink-0 text-blue-500" />
              </div>
              <p className="text-sm leading-6 text-gray-600">{player.keyMetric}</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-100">
                <div className="h-full rounded-full bg-blue-600" style={{ width: `${Math.round(player.attackShare * 100)}%` }} />
              </div>
              <p className="mt-2 text-xs font-bold text-blue-700">进攻参与约 {Math.round(player.attackShare * 100)}%</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <section className="glass-card overflow-hidden">
          <div className="border-b bg-gray-50/80 p-4">
            <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
              <CalendarDays className="h-5 w-5 text-green-600" />
              近期赛程与结果
            </h2>
          </div>
          <div className="divide-y divide-gray-100">
            {matchesError && teamMatches.length === 0 && (
              <div className="p-4 text-sm font-bold text-red-600">{matchesError}</div>
            )}
            {teamMatches.map(match => {
              const opponent = match.home_team === team.name ? match.away_team : match.home_team
              return (
                <article
                  key={match.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => openMatchPrediction(match.id)}
                  onKeyDown={(event) => handleMatchCardKeyDown(event, match.id)}
                  className="block cursor-pointer p-4 transition-colors hover:bg-blue-50/50 focus-visible:ring-4 focus-visible:ring-blue-500/20"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 items-center gap-3">
                      <TeamFlagLink teamName={opponent} size="sm" />
                      <div className="min-w-0">
                        <p className="truncate font-bold text-gray-900">
                          {match.home_team} vs {match.away_team}
                        </p>
                        <p className="mt-1 text-xs text-gray-400">{getEffectiveMatchStage(match) ? getStageNameCN(getEffectiveMatchStage(match) || '') : `${match.group}组第${match.round}轮`}</p>
                      </div>
                    </div>
                    <span className="w-fit rounded-full bg-gray-100 px-2.5 py-1 text-xs font-bold text-gray-700">{getMatchLabel(match, team.name)}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                    <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{formatMatchDate(match.match_date)}</span>
                    <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{match.venue}</span>
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <section className="glass-card overflow-hidden">
          <div className="border-b bg-gray-50/80 p-4">
            <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
              <Trophy className="h-5 w-5 text-yellow-600" />
              {team.group}组对手
            </h2>
          </div>
          <div className="divide-y divide-gray-100">
            {TEAMS.filter(t => t.group === team.group && t.id !== team.id).map(opponent => (
              <Link key={opponent.id} to={`/teams/${opponent.id}`} className="flex items-center gap-3 p-4 transition-colors hover:bg-blue-50/50">
                <TeamFlagLink teamName={opponent.name} flagCode={opponent.flagCode} size="sm" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-bold text-gray-900">{opponent.name}</p>
                  <p className="text-xs text-gray-400">FIFA #{opponent.fifa_rank} · Elo {opponent.elo_rating}</p>
                </div>
                <BarChart3 className="h-4 w-4 shrink-0 text-gray-300" />
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}
