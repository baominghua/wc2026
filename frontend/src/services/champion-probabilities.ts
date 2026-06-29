import { CONFEDERATION_MAP, TEAMS } from './wc2026-data'

export interface ChampionProbability {
  teamName: string
  group: string
  flagCode: string
  fifaRank: number
  eloRating: number
  probability: number
  tier: string
  factors: string[]
}

export interface ChampionPathStep {
  stage: string
  opponent: string
  probability: number
  venueNote: string
}

const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value))
const round1 = (value: number) => Math.round((value + Number.EPSILON) * 10) / 10

const getTier = (probability: number) => {
  if (probability >= 8) return '争冠第一梯队'
  if (probability >= 5) return '强争冠候选'
  if (probability >= 2.5) return '黑马/八强区间'
  return '晋级路径偏难'
}

const getHostBoost = (teamName: string) => {
  if (teamName === '美国') return 0.32
  if (teamName === '墨西哥' || teamName === '加拿大') return 0.22
  return 0
}

export const getChampionProbabilities = (): ChampionProbability[] => {
  const weightedTeams = TEAMS.map(team => {
    const eloScore = (team.elo_rating - 1500) / 120
    const rankScore = (52 - team.fifa_rank) / 18
    const hostBoost = getHostBoost(team.name)
    const defendingBoost = team.is_defending ? 0.16 : 0
    const debutPenalty = team.is_debut ? -0.18 : 0
    const confedBoost = CONFEDERATION_MAP[team.name] === 'UEFA' || CONFEDERATION_MAP[team.name] === 'CONMEBOL' ? 0.08 : 0
    const strength = eloScore + rankScore + hostBoost + defendingBoost + debutPenalty + confedBoost
    return {
      team,
      weight: Math.exp(strength / 2.15),
      factors: [
        `Elo ${team.elo_rating}`,
        `FIFA #${team.fifa_rank}`,
        hostBoost > 0 ? '东道主赛区加成' : '',
        team.is_defending ? '卫冕冠军经验' : '',
        team.is_debut ? '首次参赛不确定性' : '',
      ].filter(Boolean),
    }
  })

  const totalWeight = weightedTeams.reduce((sum, item) => sum + item.weight, 0) || 1
  return weightedTeams
    .map(({ team, weight, factors }) => {
      const probability = round1((weight / totalWeight) * 100)
      return {
        teamName: team.name,
        group: team.group,
        flagCode: team.flagCode,
        fifaRank: team.fifa_rank,
        eloRating: team.elo_rating,
        probability,
        tier: getTier(probability),
        factors,
      }
    })
    .sort((a, b) => b.probability - a.probability || a.fifaRank - b.fifaRank)
}

export const getChampionProbability = (teamName: string) =>
  getChampionProbabilities().find(item => item.teamName === teamName)

export const buildChampionPath = (teamName: string): ChampionPathStep[] => {
  const ranking = getChampionProbabilities()
  const selected = ranking.find(team => team.teamName === teamName) ?? ranking[0]
  const opponents = ranking.filter(team => team.teamName !== selected.teamName)
  const groupRivals = opponents.filter(team => team.group === selected.group)
  const sameBracket = opponents.filter(team => team.group !== selected.group)
  const getOpponent = (index: number, fallbackIndex: number) =>
    (index === 0 ? groupRivals[0] : sameBracket[index + fallbackIndex])?.teamName ?? opponents[index + fallbackIndex]?.teamName ?? '待定对手'

  const base = clamp(selected.probability, 0.6, 14)
  return [
    {
      stage: '32强入口',
      opponent: `${selected.group}组出线路径 / ${getOpponent(0, 7)}`,
      probability: round1(clamp(78 - selected.fifaRank * 0.35 + selected.probability * 1.4, 28, 92)),
      venueNote: selected.teamName === '美国' ? '美国淘汰赛完整主场权重' : '小组排序决定落位',
    },
    {
      stage: '16强',
      opponent: getOpponent(1, 6),
      probability: round1(clamp(58 + base * 1.1 - selected.fifaRank * 0.18, 18, 82)),
      venueNote: '按同半区强队热度预估',
    },
    {
      stage: '8强',
      opponent: getOpponent(2, 3),
      probability: round1(clamp(36 + base * 0.95 - selected.fifaRank * 0.11, 8, 64)),
      venueNote: '强强对话概率显著上升',
    },
    {
      stage: '半决赛',
      opponent: getOpponent(3, 1),
      probability: round1(clamp(21 + base * 0.78 - selected.fifaRank * 0.07, 4, 44)),
      venueNote: '赛程消耗与牌面风险进入高权重',
    },
    {
      stage: '冠军',
      opponent: getOpponent(4, 0),
      probability: selected.probability,
      venueNote: '冠军概率由实力、赛程、地域和经验综合归一化',
    },
  ]
}
