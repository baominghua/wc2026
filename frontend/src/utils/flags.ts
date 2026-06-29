import { TEAMS } from '../services/wc2026-data'

export function getFlagUrl(flagCode: string, width: number = 40): string {
  return `https://flagcdn.com/w${width}/${flagCode}.png`
}

export function getTeamFlagUrl(teamName: string, width: number = 40): string {
  const team = TEAMS.find(t => t.name === teamName)
  return team?.flagCode ? getFlagUrl(team.flagCode, width) : ''
}
