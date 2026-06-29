import { TEAMS, calculateGroupStandingsFromMatches } from './wc2026-data'
import type { Match } from './wc2026-data'
import type { TeamHistoricalStats } from './wc-history-data'

export function build2026TeamStatsFromMatches(matches: Match[]): TeamHistoricalStats[] {
  const rankByTeam = new Map<string, number>()
  const standingByTeam = new Map<string, ReturnType<typeof calculateGroupStandingsFromMatches>[number]>()

  Array.from(new Set(TEAMS.map(team => team.group))).forEach(group => {
    calculateGroupStandingsFromMatches(group, matches).forEach((standing, index) => {
      rankByTeam.set(standing.team, index + 1)
      standingByTeam.set(standing.team, standing)
    })
  })

  return TEAMS.map(team => {
    const standing = standingByTeam.get(team.name)
    const played = standing?.played ?? 0
    const won = standing?.won ?? 0
    const drawn = standing?.drawn ?? 0
    const lost = standing?.lost ?? 0
    const goalsFor = standing?.goalsFor ?? 0
    const goalsAgainst = standing?.goalsAgainst ?? 0
    const groupRank = rankByTeam.get(team.name) ?? 4
    const position = played > 0 ? `${team.group}组第${groupRank}` : '未开赛'

    return {
      name: team.name,
      flagCode: team.flagCode,
      tournaments: [2026],
      titles: 0,
      finals: 0,
      semiFinals: 0,
      quarterFinals: 0,
      totalWins: won,
      totalDraws: drawn,
      totalLosses: lost,
      totalGoalsFor: goalsFor,
      totalGoalsAgainst: goalsAgainst,
      biggestWin: '2026赛事进行中',
      biggestLoss: '2026赛事进行中',
      yearlyStats: {
        2026: {
          position,
          played,
          won,
          drawn,
          lost,
          goalsFor,
          goalsAgainst,
          finalRank: played > 0 ? groupRank : 99,
        },
      },
    }
  })
}
