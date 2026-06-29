import type { PlayerHistoricalStats } from '../services/wc-history-data'

export function selectPlayerStatsForYear(
  selectedYear: number,
  livePlayers: PlayerHistoricalStats[],
  historicalPlayers: PlayerHistoricalStats[],
): PlayerHistoricalStats[] {
  if (selectedYear === 2026) {
    return [...livePlayers]
  }

  if (selectedYear === 0) {
    return [...livePlayers, ...historicalPlayers]
  }

  return historicalPlayers.filter(player => player.tournaments.includes(selectedYear))
}
