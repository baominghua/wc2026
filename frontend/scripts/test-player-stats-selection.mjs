import assert from 'node:assert/strict'
import { selectPlayerStatsForYear } from '../src/utils/playerStatsSelection.ts'

const livePlayers = [
  {
    name: 'Live Player',
    tournaments: [2026],
    goals: 1,
    assists: 0,
    appearances: 1,
    yellowCards: 0,
    redCards: 0,
    yearlyStats: { 2026: { goals: 1, assists: 0, appearances: 1, yellowCards: 0, redCards: 0 } },
  },
]

const historicalPlayers = [
  {
    name: 'Historical 2026 Placeholder',
    tournaments: [2026],
    goals: 99,
    assists: 99,
    appearances: 1,
    yellowCards: 0,
    redCards: 0,
    yearlyStats: { 2026: { goals: 99, assists: 99, appearances: 1, yellowCards: 0, redCards: 0 } },
  },
  {
    name: 'Historic Legend',
    tournaments: [2022],
    goals: 8,
    assists: 2,
    appearances: 7,
    yellowCards: 0,
    redCards: 0,
    yearlyStats: { 2022: { goals: 8, assists: 2, appearances: 7, yellowCards: 0, redCards: 0 } },
  },
]

assert.deepEqual(
  selectPlayerStatsForYear(2026, livePlayers, historicalPlayers).map(player => player.name),
  ['Live Player'],
)

assert.deepEqual(
  selectPlayerStatsForYear(0, livePlayers, historicalPlayers).map(player => player.name),
  ['Live Player', 'Historical 2026 Placeholder', 'Historic Legend'],
)

assert.deepEqual(
  selectPlayerStatsForYear(2022, livePlayers, historicalPlayers).map(player => player.name),
  ['Historic Legend'],
)

console.log('player stats selection ok')
