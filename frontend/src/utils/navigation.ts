import { TEAMS } from '../services/wc2026-data'

const teamNameAliases: Record<string, string> = {
  USA: '美国',
  'United States': '美国',
  Mexico: '墨西哥',
  Canada: '加拿大',
  Argentina: '阿根廷',
  France: '法国',
  Brazil: '巴西',
  England: '英格兰',
  'South Africa': '南非',
  'South Korea': '韩国',
  Czechia: '捷克',
  'Czech Republic': '捷克',
}

export function getPredictMatchPath(matchId: number | string) {
  return `/predict?matchId=${matchId}`
}

export function getTeamByName(teamName?: string) {
  if (!teamName) return undefined
  const normalizedName = teamNameAliases[teamName] || teamName
  return TEAMS.find(team => team.name === normalizedName || team.code === teamName)
}

export function getTeamDetailPath(teamName?: string) {
  const team = getTeamByName(teamName)
  return team ? `/teams/${team.id}` : '/teams'
}
