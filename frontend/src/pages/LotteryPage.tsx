import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CalendarDays,
  Check,
  Clock,
  Copy,
  MapPin,
  Minus,
  Plus,
  Save,
  Sparkles,
  Target,
  Ticket,
  Trash2,
  Wand2,
} from 'lucide-react'
import TeamFlag from '../components/TeamFlag'
import { TEAMS, getStageNameCN, getEffectiveMatchStage, isEffectiveKnockoutMatch } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'
import { matchAPI, predictionAPI } from '../services/api'
import type { PredictionResult } from '../services/api'

type PlayType = 'wdl' | 'score'
type MatchWindow = '3d' | '7d' | 'all'

interface ModelView {
  homeP: number
  drawP: number
  awayP: number
  xgHome: number
  xgAway: number
  score: string
  confidence: number
  source: string
  possibleScores: { score: string; probability: number }[]
}

interface BetOption {
  id: string
  playType: PlayType
  label: string
  shortLabel: string
  odds: number
  probability: number
  hint: string
}

interface BetSelection extends BetOption {
  matchId: number
  matchLabel: string
  matchDate: string
  groupLabel: string
}

interface TicketLine {
  selections: BetSelection[]
  oddsProduct: number
  probabilityProduct: number
  bonus: number
}

interface SavedScheme {
  id: string
  createdAt: string
  selections: BetSelection[]
  passSize: number
  multiple: number
  lineCount: number
  totalStake: number
  maxBonus: number
  expectedBonus: number
}

const STORAGE_KEY = 'wc2026_lottery_schemes'
const BASE_STAKE = 2

const playTabs: { key: PlayType; label: string; detail: string }[] = [
  { key: 'wdl', label: '胜平负', detail: '主胜 / 平 / 主负' },
  { key: 'score', label: '比分', detail: '常用比分模拟固定奖金' },
]

function getTeamInfo(teamName: string) {
  return TEAMS.find(team => team.name === teamName)
}

function formatMatchDate(dateStr: string) {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

function formatMoney(value: number) {
  if (!Number.isFinite(value)) return '0.00'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function round2(value: number) {
  return Math.round(value * 100) / 100
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function factorial(n: number): number {
  if (n <= 1) return 1
  let result = 1
  for (let i = 2; i <= n; i += 1) result *= i
  return result
}

function poisson(k: number, lambda: number) {
  return (Math.exp(-lambda) * Math.pow(lambda, k)) / factorial(k)
}

function estimateModel(match: Match): ModelView {
  const home = getTeamInfo(match.home_team)
  const away = getTeamInfo(match.away_team)
  const homeRating = home?.elo_rating ?? 1500
  const awayRating = away?.elo_rating ?? 1500
  const hostBoost = home?.is_host ? 70 : away?.is_host ? -70 : 0
  const ratingDiff = homeRating + hostBoost - awayRating
  const strengthShare = 1 / (1 + Math.pow(10, -ratingDiff / 420))
  const drawP = clamp(0.27 - Math.abs(ratingDiff) / 2600, 0.14, 0.3)
  const homeP = clamp((1 - drawP) * strengthShare, 0.08, 0.82)
  const awayP = clamp(1 - drawP - homeP, 0.06, 0.8)
  const total = homeP + drawP + awayP
  const normalizedHome = homeP / total
  const normalizedDraw = drawP / total
  const normalizedAway = awayP / total
  const xgHome = clamp(1.32 + ratingDiff / 460, 0.45, 3.35)
  const xgAway = clamp(1.25 - ratingDiff / 520, 0.35, 3.1)
  const scoreHome = Math.max(0, Math.round(xgHome))
  const scoreAway = Math.max(0, Math.round(xgAway))

  return {
    homeP: normalizedHome,
    drawP: normalizedDraw,
    awayP: normalizedAway,
    xgHome: round2(xgHome),
    xgAway: round2(xgAway),
    score: `${scoreHome}-${scoreAway}`,
    confidence: Math.max(normalizedHome, normalizedDraw, normalizedAway),
    source: 'Elo/xG 快速估算',
    possibleScores: buildPoissonScores(xgHome, xgAway).slice(0, 5),
  }
}

function modelFromPrediction(match: Match, prediction?: PredictionResult): ModelView {
  if (!prediction) return estimateModel(match)
  return {
    homeP: prediction.home_win_probability,
    drawP: prediction.draw_probability,
    awayP: prediction.away_win_probability,
    xgHome: prediction.xg_home,
    xgAway: prediction.xg_away,
    score: prediction.predicted_score,
    confidence: prediction.confidence,
    source: prediction.model_version || '美加墨世界杯AI预测模型',
    possibleScores: prediction.possible_scores?.map(item => ({
      score: item.score,
      probability: item.probability / 100,
    })) ?? [],
  }
}

function buildPoissonScores(xgHome: number, xgAway: number) {
  const scores: { score: string; probability: number }[] = []
  for (let h = 0; h <= 5; h += 1) {
    for (let a = 0; a <= 5; a += 1) {
      scores.push({ score: `${h}-${a}`, probability: poisson(h, xgHome) * poisson(a, xgAway) })
    }
  }
  const total = scores.reduce((sum, item) => sum + item.probability, 0) || 1
  return scores
    .map(item => ({ ...item, probability: item.probability / total }))
    .sort((a, b) => b.probability - a.probability)
}

function oddsFromProbability(probability: number, playType: PlayType) {
  const margin = playType === 'score' ? 0.82 : 0.88
  const min = playType === 'score' ? 4.2 : 1.08
  const max = playType === 'score' ? 90 : 9.5
  return round2(clamp(margin / Math.max(probability, 0.01), min, max))
}

function optionHint(probability: number, odds: number) {
  const valueIndex = probability * odds
  if (valueIndex >= 1.05) return '模型价值偏高'
  if (probability >= 0.5) return '命中倾向较强'
  if (odds >= 8) return '高奖高风险'
  return '均衡参考'
}

function buildWdlOptions(match: Match, model: ModelView): BetOption[] {
  const rows = [
    { id: 'home', label: `${match.home_team}胜`, shortLabel: '胜', probability: model.homeP },
    { id: 'draw', label: '平局', shortLabel: '平', probability: model.drawP },
    { id: 'away', label: `${match.away_team}胜`, shortLabel: '负', probability: model.awayP },
  ]

  return rows.map(row => {
    const odds = oddsFromProbability(row.probability, 'wdl')
    return {
      ...row,
      playType: 'wdl' as const,
      odds,
      hint: optionHint(row.probability, odds),
    }
  })
}

function buildScoreOptions(model: ModelView): BetOption[] {
  const baseScores = model.possibleScores.length > 0
    ? model.possibleScores
    : buildPoissonScores(model.xgHome, model.xgAway)
  const merged = new Map<string, number>()

  baseScores.forEach(item => merged.set(item.score, Math.max(merged.get(item.score) || 0, item.probability)))
  buildPoissonScores(model.xgHome, model.xgAway).slice(0, 8).forEach(item => {
    merged.set(item.score, Math.max(merged.get(item.score) || 0, item.probability))
  })

  return [...merged.entries()]
    .map(([score, probability]) => {
      const odds = oddsFromProbability(probability, 'score')
      return {
        id: score,
        playType: 'score' as const,
        label: score,
        shortLabel: score,
        odds,
        probability,
        hint: optionHint(probability, odds),
      }
    })
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 9)
}

function getGroupLabel(match: Match) {
  const effectiveStage = getEffectiveMatchStage(match)
  if (effectiveStage) return getStageNameCN(effectiveStage)
  return `${match.group}组 · 第${match.round}轮`
}

function combine<T>(items: T[], size: number): T[][] {
  if (size <= 0) return [[]]
  if (size > items.length) return []
  if (size === items.length) return [items]
  const result: T[][] = []
  const walk = (start: number, picked: T[]) => {
    if (picked.length === size) {
      result.push([...picked])
      return
    }
    for (let i = start; i <= items.length - (size - picked.length); i += 1) {
      picked.push(items[i])
      walk(i + 1, picked)
      picked.pop()
    }
  }
  walk(0, [])
  return result
}

function cartesian<T>(groups: T[][]): T[][] {
  return groups.reduce<T[][]>(
    (acc, group) => acc.flatMap(prefix => group.map(item => [...prefix, item])),
    [[]]
  )
}

function buildTicketLines(groupedSelections: BetSelection[][], passSize: number, multiple: number): TicketLine[] {
  if (groupedSelections.length === 0 || passSize <= 0) return []
  return combine(groupedSelections, passSize).flatMap(matchGroups =>
    cartesian(matchGroups).map(selections => {
      const oddsProduct = selections.reduce((product, item) => product * item.odds, 1)
      const probabilityProduct = selections.reduce((product, item) => product * item.probability, 1)
      return {
        selections,
        oddsProduct,
        probabilityProduct,
        bonus: BASE_STAKE * multiple * oddsProduct,
      }
    })
  )
}

function loadSavedSchemes(): SavedScheme[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) as SavedScheme[] : []
  } catch {
    return []
  }
}

export default function LotteryPage() {
  const [matches, setMatches] = useState<Match[]>([])
  const [matchesLoading, setMatchesLoading] = useState(true)
  const [matchesError, setMatchesError] = useState<string | null>(null)
  const upcomingMatches = useMemo(() => matches.filter(match => match.status !== 'completed'), [matches])
  const [matchWindow, setMatchWindow] = useState<MatchWindow>('7d')
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null)
  const [playType, setPlayType] = useState<PlayType>('wdl')
  const [selections, setSelections] = useState<BetSelection[]>([])
  const [multiple, setMultiple] = useState(1)
  const [passSize, setPassSize] = useState(2)
  const [savedSchemes, setSavedSchemes] = useState<SavedScheme[]>(loadSavedSchemes)
  const [modelCache, setModelCache] = useState<Record<number, PredictionResult>>({})

  useEffect(() => {
    let active = true
    const fetchMatches = async () => {
      try {
        const liveMatches = await matchAPI.getMatchesStrict()
        if (!active) return
        setMatches(liveMatches)
        setMatchesError(null)
      } catch {
        if (active) setMatchesError('实时赛程接口读取失败，请重新登录或稍后刷新。')
      } finally {
        if (active) setMatchesLoading(false)
      }
    }

    void fetchMatches()
    const timer = window.setInterval(fetchMatches, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const filteredMatches = useMemo(() => {
    if (matchWindow === 'all') return upcomingMatches
    const now = new Date()
    const days = matchWindow === '3d' ? 3 : 7
    const end = new Date(now)
    end.setDate(end.getDate() + days)
    return upcomingMatches.filter(match => {
      const date = new Date(match.match_date)
      return date >= now && date <= end
    })
  }, [matchWindow, upcomingMatches])

  const visibleMatches = filteredMatches.length > 0 ? filteredMatches : upcomingMatches.slice(0, 12)
  const selectedMatch = visibleMatches.find(match => match.id === selectedMatchId) ?? visibleMatches[0]
  const selectedModel = selectedMatch ? modelFromPrediction(selectedMatch, modelCache[selectedMatch.id]) : null

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (visibleMatches.length === 0) {
        setSelectedMatchId(null)
        return
      }
      if (!selectedMatchId || !visibleMatches.some(match => match.id === selectedMatchId)) {
        setSelectedMatchId(visibleMatches[0].id)
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [selectedMatchId, visibleMatches])

  useEffect(() => {
    if (!selectedMatch || modelCache[selectedMatch.id]) return
    let active = true
    const effectiveStage = getEffectiveMatchStage(selectedMatch)
    void predictionAPI.predictMatch({
      home_team: selectedMatch.home_team,
      away_team: selectedMatch.away_team,
      venue: selectedMatch.venue,
      model_type: 'form_weighted',
      is_knockout: isEffectiveKnockoutMatch(selectedMatch),
      match_round: selectedMatch.round,
      stage: effectiveStage ?? selectedMatch.stage,
    }).then(result => {
      if (active) {
        setModelCache(prev => ({ ...prev, [selectedMatch.id]: result.data }))
      }
    }).catch(() => undefined)

    return () => {
      active = false
    }
  }, [modelCache, selectedMatch])

  const selectedOptions = useMemo(() => {
    if (!selectedMatch || !selectedModel) return []
    return playType === 'wdl'
      ? buildWdlOptions(selectedMatch, selectedModel)
      : buildScoreOptions(selectedModel)
  }, [playType, selectedMatch, selectedModel])

  const selectionsByMatch = useMemo(() => {
    const groups = new Map<number, BetSelection[]>()
    selections.forEach(selection => {
      const current = groups.get(selection.matchId) || []
      current.push(selection)
      groups.set(selection.matchId, current)
    })
    return [...groups.values()]
  }, [selections])

  const selectedMatchCount = selectionsByMatch.length
  const hasScoreSelection = selections.some(selection => selection.playType === 'score')
  const maxPassSize = Math.min(selectedMatchCount, hasScoreSelection ? 4 : 8)
  const effectivePassSize = Math.min(passSize, Math.max(maxPassSize, 1))
  const passOptions = Array.from({ length: Math.max(maxPassSize, 1) }, (_, index) => index + 1)
  const ticketLines = useMemo(
    () => buildTicketLines(selectionsByMatch, effectivePassSize, multiple),
    [effectivePassSize, multiple, selectionsByMatch]
  )
  const totalStake = ticketLines.length * BASE_STAKE * multiple
  const maxBonus = ticketLines.reduce((sum, line) => sum + line.bonus, 0)
  const expectedBonus = ticketLines.reduce((sum, line) => sum + line.bonus * line.probabilityProduct, 0)
  const minSingleBonus = ticketLines.length > 0 ? Math.min(...ticketLines.map(line => line.bonus)) : 0

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(savedSchemes))
  }, [savedSchemes])

  const isSelected = (matchId: number, optionId: string, optionPlayType: PlayType) =>
    selections.some(selection => selection.matchId === matchId && selection.id === optionId && selection.playType === optionPlayType)

  const toggleSelection = (match: Match, option: BetOption) => {
    const exists = isSelected(match.id, option.id, option.playType)
    if (exists) {
      setSelections(prev => prev.filter(selection => !(selection.matchId === match.id && selection.id === option.id && selection.playType === option.playType)))
      return
    }
    setSelections(prev => [
      ...prev,
      {
        ...option,
        matchId: match.id,
        matchLabel: `${match.home_team} vs ${match.away_team}`,
        matchDate: match.match_date,
        groupLabel: getGroupLabel(match),
      },
    ])
  }

  const addModelMainPick = () => {
    if (!selectedMatch || !selectedModel) return
    const bestOption = buildWdlOptions(selectedMatch, selectedModel).sort((a, b) => b.probability - a.probability)[0]
    if (bestOption) toggleSelection(selectedMatch, bestOption)
  }

  const addModelScorePick = () => {
    if (!selectedMatch || !selectedModel) return
    const bestScore = buildScoreOptions(selectedModel)[0]
    if (bestScore) toggleSelection(selectedMatch, bestScore)
  }

  const generateAiScheme = () => {
    const candidates = visibleMatches
      .slice(0, 24)
      .map(match => {
        const model = modelFromPrediction(match, modelCache[match.id])
        const option = buildWdlOptions(match, model).sort((a, b) => b.probability - a.probability)[0]
        return { match, model, option, score: option.probability * option.odds }
      })
      .sort((a, b) => (b.option.probability - a.option.probability) || (b.score - a.score))
      .slice(0, 3)

    setSelections(candidates.map(({ match, option }) => ({
      ...option,
      matchId: match.id,
      matchLabel: `${match.home_team} vs ${match.away_team}`,
      matchDate: match.match_date,
      groupLabel: getGroupLabel(match),
    })))
    setPassSize(Math.min(3, candidates.length || 1))
    setPlayType('wdl')
  }

  const saveCurrentScheme = () => {
    if (ticketLines.length === 0) return
    const createdAt = new Date().toISOString()
    const scheme: SavedScheme = {
      id: `${createdAt}-${savedSchemes.length}`,
      createdAt,
      selections,
      passSize: effectivePassSize,
      multiple,
      lineCount: ticketLines.length,
      totalStake,
      maxBonus,
      expectedBonus,
    }
    setSavedSchemes(prev => [scheme, ...prev].slice(0, 12))
  }

  const copyScheme = async () => {
    if (ticketLines.length === 0) return
    const text = [
      '世界杯模拟竞猜方案',
      `过关: ${effectivePassSize === 1 ? '单关' : `${effectivePassSize}串1`}，倍数: ${multiple}倍`,
      `注数: ${ticketLines.length}，方案金额: ${formatMoney(totalStake)}元`,
      `理论最高奖金: ${formatMoney(maxBonus)}元，模型期望奖金: ${formatMoney(expectedBonus)}元`,
      ...selections.map(selection => `- ${formatMatchDate(selection.matchDate)} ${selection.matchLabel}｜${selection.playType === 'wdl' ? '胜平负' : '比分'} ${selection.label} @ ${selection.odds}`),
      '提示: 模拟测算非官方凭证，最终奖金参考系数和可售赛事以体彩店终端为准。',
    ].join('\n')
    await navigator.clipboard?.writeText(text)
  }

  const removeSelection = (selection: BetSelection) => {
    setSelections(prev => prev.filter(item => !(item.matchId === selection.matchId && item.playType === selection.playType && item.id === selection.id)))
  }

  return (
    <div className="space-y-4">
      <section className="glass-card overflow-hidden p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">
              <Ticket className="h-4 w-4" />
              中国体育彩票 · 世界杯竞猜模拟
            </div>
            <h1 className="mt-3 text-2xl font-black text-gray-900 sm:text-3xl">模拟竞猜</h1>
            <p className="mt-1 max-w-3xl text-sm font-semibold leading-6 text-gray-500">
              胜平负、比分、过关方案和奖金模拟。模型预测只做参考，最终可售赛事、固定奖金和出票金额以体彩店终端为准。
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center sm:min-w-[28rem]">
            <div className="rounded-2xl bg-white/80 p-3">
              <div className="text-xs font-bold text-gray-500">注数</div>
              <div className="text-xl font-black text-blue-600">{ticketLines.length}</div>
            </div>
            <div className="rounded-2xl bg-white/80 p-3">
              <div className="text-xs font-bold text-gray-500">方案金额</div>
              <div className="text-xl font-black text-gray-900">¥{formatMoney(totalStake)}</div>
            </div>
            <div className="rounded-2xl bg-white/80 p-3">
              <div className="text-xs font-bold text-gray-500">最高奖金</div>
              <div className="text-xl font-black text-emerald-600">¥{formatMoney(maxBonus)}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[0.82fr_1.08fr_0.9fr]">
        <div className="glass-card overflow-hidden p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
                <CalendarDays className="h-5 w-5 text-blue-600" />
                赛事池
              </h2>
              <p className="text-xs font-semibold text-gray-500">选择比赛后添加玩法选项</p>
            </div>
            <div className="flex rounded-xl bg-white/80 p-1">
              {[
                { key: '3d' as MatchWindow, label: '3日' },
                { key: '7d' as MatchWindow, label: '7日' },
                { key: 'all' as MatchWindow, label: '全部' },
              ].map(item => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setMatchWindow(item.key)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-black transition ${matchWindow === item.key ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 hover:bg-white'}`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 'min(34rem, 58vh)' }}>
            {matchesLoading && visibleMatches.length === 0 && (
              <div className="rounded-2xl bg-white/75 p-5 text-center text-sm font-bold text-gray-500">
                正在同步实时赛程...
              </div>
            )}
            {matchesError && visibleMatches.length === 0 && (
              <div className="rounded-2xl bg-red-50 p-5 text-center text-sm font-bold text-red-600">
                {matchesError}
              </div>
            )}
            {visibleMatches.map(match => {
              const home = getTeamInfo(match.home_team)
              const away = getTeamInfo(match.away_team)
              const active = match.id === selectedMatch?.id
              const matchSelectionCount = selections.filter(selection => selection.matchId === match.id).length
              return (
                <button
                  key={match.id}
                  type="button"
                  onClick={() => setSelectedMatchId(match.id)}
                  className={`w-full rounded-2xl border p-3 text-left transition ${active ? 'border-blue-300 bg-blue-50/90 shadow-md shadow-blue-500/10' : 'border-white/70 bg-white/78 hover:bg-white'}`}
                >
                  <div className="mb-2 flex items-center justify-between gap-2 text-xs font-bold text-gray-500">
                    <span>{getGroupLabel(match)}</span>
                    <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{formatMatchDate(match.match_date)}</span>
                  </div>
                  <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 text-center">
                    <div className="min-w-0">
                      <TeamFlag flagCode={home?.flagCode} size="sm" />
                      <div className="mt-1 truncate text-sm font-black text-gray-900">{match.home_team}</div>
                    </div>
                    <span className="text-xs font-black text-gray-400">VS</span>
                    <div className="min-w-0">
                      <TeamFlag flagCode={away?.flagCode} size="sm" />
                      <div className="mt-1 truncate text-sm font-black text-gray-900">{match.away_team}</div>
                    </div>
                  </div>
                  {matchSelectionCount > 0 && (
                    <div className="mt-2 inline-flex rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-black text-emerald-700">
                      已选 {matchSelectionCount} 项
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="space-y-4">
          <div className="glass-card overflow-hidden p-4">
            {selectedMatch && selectedModel && (
              <>
                <div className="flex flex-col gap-3 border-b border-white/70 pb-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-lg font-black text-gray-900">{selectedMatch.home_team} vs {selectedMatch.away_team}</h2>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-semibold text-gray-500">
                      <span>{getGroupLabel(selectedMatch)}</span>
                      <span className="inline-flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{selectedMatch.venue}</span>
                    </div>
                  </div>
                  <div className="rounded-2xl bg-white/80 px-4 py-2 text-center">
                    <div className="text-xs font-bold text-gray-500">模型预测比分</div>
                    <div className="text-2xl font-black text-blue-600">{selectedModel.score}</div>
                  </div>
                </div>

                <div className="mt-3 grid grid-cols-3 gap-2">
                  {[
                    { label: `${selectedMatch.home_team}胜`, value: selectedModel.homeP, color: 'text-blue-600' },
                    { label: '平局', value: selectedModel.drawP, color: 'text-slate-700' },
                    { label: `${selectedMatch.away_team}胜`, value: selectedModel.awayP, color: 'text-red-600' },
                  ].map(item => (
                    <div key={item.label} className="rounded-2xl bg-white/78 p-3 text-center">
                      <div className="truncate text-xs font-bold text-gray-500">{item.label}</div>
                      <div className={`mt-1 text-xl font-black ${item.color}`}>{(item.value * 100).toFixed(1)}%</div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {playTabs.map(tab => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => setPlayType(tab.key)}
                      className={`rounded-2xl border px-4 py-2 text-left transition ${playType === tab.key ? 'border-blue-300 bg-blue-600 text-white shadow-md shadow-blue-500/20' : 'border-white/70 bg-white/80 text-gray-600 hover:bg-white'}`}
                    >
                      <div className="text-sm font-black">{tab.label}</div>
                      <div className={`text-[11px] font-semibold ${playType === tab.key ? 'text-blue-100' : 'text-gray-500'}`}>{tab.detail}</div>
                    </button>
                  ))}
                </div>

                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {selectedOptions.map(option => {
                    const selected = isSelected(selectedMatch.id, option.id, option.playType)
                    return (
                      <button
                        key={`${option.playType}-${option.id}`}
                        type="button"
                        onClick={() => toggleSelection(selectedMatch, option)}
                        className={`rounded-2xl border p-3 text-left transition ${selected ? 'border-emerald-300 bg-emerald-50 shadow-md shadow-emerald-500/10' : 'border-white/70 bg-white/80 hover:border-blue-200 hover:bg-white'}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-base font-black text-gray-900">{option.label}</div>
                            <div className="mt-1 text-xs font-semibold text-gray-500">模型概率 {(option.probability * 100).toFixed(1)}%</div>
                          </div>
                          <span className={`flex h-6 w-6 items-center justify-center rounded-full ${selected ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-400'}`}>
                            {selected && <Check className="h-4 w-4" />}
                          </span>
                        </div>
                        <div className="mt-3 flex items-end justify-between gap-2">
                          <div>
                            <div className="text-xs font-bold text-gray-500">模拟倍率</div>
                            <div className="text-2xl font-black text-blue-600">{option.odds.toFixed(2)}</div>
                          </div>
                          <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] font-black text-blue-700">{option.hint}</span>
                        </div>
                      </button>
                    )
                  })}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button type="button" onClick={addModelMainPick} className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-black text-white shadow-md shadow-blue-500/20">
                    添加模型胜平负
                  </button>
                  <button type="button" onClick={addModelScorePick} className="rounded-2xl bg-white/85 px-4 py-3 text-sm font-black text-blue-700 shadow-sm">
                    添加模型比分
                  </button>
                </div>
              </>
            )}
          </div>

          <div className="glass-card p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
                  <Sparkles className="h-5 w-5 text-amber-500" />
                  AI一键方案
                </h2>
                <p className="text-xs font-semibold text-gray-500">自动挑选模型倾向更明确的 3 场胜平负</p>
              </div>
              <button type="button" onClick={generateAiScheme} className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-black text-white shadow-md shadow-blue-500/20">
                <Wand2 className="h-4 w-4" />
                生成
              </button>
            </div>
            <div className="rounded-2xl border border-amber-100 bg-amber-50/80 p-3 text-xs font-semibold leading-5 text-amber-800">
              倾向方案会优先控制风险，不代表操作建议。若用于线下核对，请再次确认场次编号、开赛时间、玩法和固定奖金。
            </div>
          </div>
        </div>

        <aside className="glass-card h-fit p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-black text-gray-900">
                <Target className="h-5 w-5 text-blue-600" />
                方案篮
              </h2>
              <p className="text-xs font-semibold text-gray-500">选择项、过关和奖金测算</p>
            </div>
            <button type="button" onClick={() => setSelections([])} className="rounded-xl bg-white/80 p-2 text-gray-500 hover:text-red-600" aria-label="清空方案">
              <Trash2 className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-2">
            {selections.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-white/60 p-5 text-center text-sm font-semibold text-gray-500">
                还没有选择项。先从左侧选比赛，再添加胜平负或比分。
              </div>
            ) : selections.map(selection => (
              <div key={`${selection.matchId}-${selection.playType}-${selection.id}`} className="rounded-2xl bg-white/80 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-black text-gray-900">{selection.matchLabel}</div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">{selection.playType === 'wdl' ? '胜平负' : '比分'} · {selection.label} · {selection.odds.toFixed(2)}</div>
                  </div>
                  <button type="button" onClick={() => removeSelection(selection)} className="rounded-lg p-1 text-gray-400 hover:bg-red-50 hover:text-red-600" aria-label="移除选项">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-2xl bg-white/78 p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-sm font-black text-gray-900">倍数</span>
              <div className="flex items-center rounded-xl bg-slate-100 p-1">
                <button type="button" onClick={() => setMultiple(value => Math.max(1, value - 1))} className="rounded-lg bg-white p-2 text-gray-700">
                  <Minus className="h-4 w-4" />
                </button>
                <span className="w-14 text-center text-sm font-black text-gray-900">{multiple}倍</span>
                <button type="button" onClick={() => setMultiple(value => Math.min(99, value + 1))} className="rounded-lg bg-white p-2 text-gray-700">
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="mb-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-black text-gray-900">过关方式</span>
                <span className="text-xs font-semibold text-gray-500">{hasScoreSelection ? '含比分最多4关' : '胜平负最多8关'}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {passOptions.map(size => (
                  <button
                    key={size}
                    type="button"
                    disabled={size > maxPassSize}
                    onClick={() => setPassSize(size)}
                    className={`rounded-xl px-3 py-1.5 text-xs font-black transition disabled:cursor-not-allowed disabled:opacity-35 ${effectivePassSize === size ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-blue-50'}`}
                  >
                    {size === 1 ? '单关' : `${size}串1`}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl bg-blue-50 p-3">
                <div className="text-xs font-bold text-blue-700">方案金额</div>
                <div className="text-lg font-black text-blue-700">¥{formatMoney(totalStake)}</div>
              </div>
              <div className="rounded-xl bg-emerald-50 p-3">
                <div className="text-xs font-bold text-emerald-700">最高奖金</div>
                <div className="text-lg font-black text-emerald-700">¥{formatMoney(maxBonus)}</div>
              </div>
              <div className="rounded-xl bg-purple-50 p-3">
                <div className="text-xs font-bold text-purple-700">期望奖金</div>
                <div className="text-lg font-black text-purple-700">¥{formatMoney(expectedBonus)}</div>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <div className="text-xs font-bold text-slate-600">单组最低</div>
                <div className="text-lg font-black text-slate-800">¥{formatMoney(minSingleBonus)}</div>
              </div>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <button type="button" onClick={saveCurrentScheme} disabled={ticketLines.length === 0} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-blue-600 px-4 py-3 text-sm font-black text-white shadow-md shadow-blue-500/20 disabled:cursor-not-allowed disabled:opacity-40">
              <Save className="h-4 w-4" />
              保存方案
            </button>
            <button type="button" onClick={copyScheme} disabled={ticketLines.length === 0} className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white/85 px-4 py-3 text-sm font-black text-gray-700 shadow-sm disabled:cursor-not-allowed disabled:opacity-40">
              <Copy className="h-4 w-4" />
              复制清单
            </button>
          </div>

          <div className="mt-3 rounded-2xl border border-orange-100 bg-orange-50/80 p-3 text-xs font-semibold leading-5 text-orange-800">
            <AlertTriangle className="mr-1 inline h-4 w-4" />
            仅用于模拟测算和记录思路，不保证中奖，不构成购彩建议。请理性参与，未成年人不得购彩。
          </div>
        </aside>
      </section>

      <section className="glass-card p-4">
        <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-lg font-black text-gray-900">已保存方案</h2>
            <p className="text-xs font-semibold text-gray-500">保存在当前浏览器，可作为去体彩店核对的模拟清单</p>
          </div>
          {savedSchemes.length > 0 && (
            <button type="button" onClick={() => setSavedSchemes([])} className="text-xs font-black text-red-600">清空保存</button>
          )}
        </div>

        {savedSchemes.length === 0 ? (
          <div className="rounded-2xl bg-white/70 p-6 text-center text-sm font-semibold text-gray-500">暂无保存方案</div>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {savedSchemes.map(scheme => (
              <div key={scheme.id} className="rounded-2xl bg-white/80 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-black text-gray-900">{new Date(scheme.createdAt).toLocaleString('zh-CN')}</div>
                    <div className="mt-1 text-xs font-semibold text-gray-500">
                      {scheme.passSize === 1 ? '单关' : `${scheme.passSize}串1`} · {scheme.multiple}倍 · {scheme.lineCount}注
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-bold text-gray-500">最高奖金</div>
                    <div className="text-lg font-black text-emerald-600">¥{formatMoney(scheme.maxBonus)}</div>
                  </div>
                </div>
                <div className="mt-3 space-y-1.5">
                  {scheme.selections.slice(0, 5).map(selection => (
                    <div key={`${scheme.id}-${selection.matchId}-${selection.playType}-${selection.id}`} className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-semibold text-gray-600">
                      {selection.matchLabel} · {selection.playType === 'wdl' ? '胜平负' : '比分'} {selection.label} @ {selection.odds.toFixed(2)}
                    </div>
                  ))}
                  {scheme.selections.length > 5 && <div className="text-xs font-bold text-gray-400">还有 {scheme.selections.length - 5} 项</div>}
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                  <div className="rounded-xl bg-blue-50 p-2">
                    <div className="text-[11px] font-bold text-blue-700">方案金额</div>
                    <div className="text-sm font-black text-blue-700">¥{formatMoney(scheme.totalStake)}</div>
                  </div>
                  <div className="rounded-xl bg-purple-50 p-2">
                    <div className="text-[11px] font-bold text-purple-700">期望</div>
                    <div className="text-sm font-black text-purple-700">¥{formatMoney(scheme.expectedBonus)}</div>
                  </div>
                  <div className="rounded-xl bg-slate-50 p-2">
                    <div className="text-[11px] font-bold text-slate-600">选项</div>
                    <div className="text-sm font-black text-slate-800">{scheme.selections.length}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
