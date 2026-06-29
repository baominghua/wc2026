import { useMemo, useState } from 'react'
import { AlertCircle, CalendarDays, Download, Loader2, Sparkles } from 'lucide-react'
import { injuryAPI, predictionAPI, type PredictionResult, type TotalGoalsPrediction } from '../services/api'
import { HOST_COUNTRY_MAP, TEAMS, getStageNameCN, getEffectiveMatchStage, isEffectiveKnockoutMatch } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'

interface DailyPredictionsExportProps {
  matches: Match[]
  loading?: boolean
  targetDayKey?: string
  maxMatches?: number
}

interface DailyPredictionItem {
  match: Match
  prediction: PredictionResult
}

type AdvantageLevel = 'full' | 'half' | 'none'
type WeatherCode = 'normal' | 'rain' | 'storm' | 'hot' | 'wind'
type VenueFactor = 'normal' | 'indoor' | 'high_altitude'
type ScorePoolItem = { score: string; probability?: number }

interface BatchVenueAdvantage {
  side: 'home' | 'away' | 'none'
  level: AdvantageLevel
}

interface BatchWeatherContext {
  weather: WeatherCode
  venue_factor: VenueFactor
}

const BATCH_VENUE_PROFILES: Array<{ patterns: string[]; weather: WeatherCode; venue_factor: VenueFactor }> = [
  { patterns: ['azteca', '阿兹特克'], weather: 'normal', venue_factor: 'high_altitude' },
  { patterns: ['akron', '阿克伦'], weather: 'hot', venue_factor: 'normal' },
  { patterns: ['bbva'], weather: 'hot', venue_factor: 'normal' },
  { patterns: ['bc place', 'bc广场'], weather: 'normal', venue_factor: 'indoor' },
  { patterns: ['sofi'], weather: 'normal', venue_factor: 'indoor' },
  { patterns: ['at&t', 'att stadium', 'at＆t'], weather: 'hot', venue_factor: 'indoor' },
  { patterns: ['mercedes-benz', 'mercedes benz', '梅赛德斯'], weather: 'normal', venue_factor: 'indoor' },
  { patterns: ['nrg'], weather: 'hot', venue_factor: 'indoor' },
  { patterns: ['hard rock', '硬石'], weather: 'hot', venue_factor: 'normal' },
  { patterns: ['arrowhead', '箭头'], weather: 'hot', venue_factor: 'normal' },
  { patterns: ['lumen', '流明'], weather: 'rain', venue_factor: 'normal' },
]

const BEIJING_TIME_ZONE = 'Asia/Shanghai'
const POSTER_WIDTH = 1080
const POSTER_MIN_HEIGHT = 1920
const CARD_TOP = 258
const CARD_STEP = 392
const FOOTER_HEIGHT = 130

function getBeijingDayKey(dateInput: string | Date) {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const year = parts.find(part => part.type === 'year')?.value ?? '2026'
  const month = parts.find(part => part.type === 'month')?.value ?? '01'
  const day = parts.find(part => part.type === 'day')?.value ?? '01'
  return `${year}-${month}-${day}`
}

function formatBeijingDateTime(dateInput: string | Date) {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

function dayLabel(dayKey: string) {
  const [, month, day] = dayKey.split('-')
  return `${Number(month)}月${Number(day)}日`
}

function isConcreteTeam(teamName: string) {
  return Boolean(TEAMS.find(team => team.name === teamName || team.code === teamName))
}

function isDownloadCandidate(match: Match) {
  const status = match.status || 'upcoming'
  return status !== 'completed'
    && status !== 'cancelled'
    && isConcreteTeam(match.home_team)
    && isConcreteTeam(match.away_team)
}

function isHostTeam(teamName: string): boolean {
  return Boolean(HOST_COUNTRY_MAP[teamName])
}

function detectBatchVenueAdvantage(match: Match): BatchVenueAdvantage {
  const isKnockout = isEffectiveKnockoutMatch(match)

  if (!isKnockout) {
    if (isHostTeam(match.home_team)) return { side: 'home', level: 'full' }
    if (isHostTeam(match.away_team)) return { side: 'away', level: 'full' }
  }

  if (isKnockout) {
    if (match.home_team === '美国') return { side: 'home', level: 'full' }
    if (match.away_team === '美国') return { side: 'away', level: 'full' }
  }

  return { side: 'none', level: 'none' }
}

function detectBatchWeatherContext(match: Match): BatchWeatherContext {
  const venueText = (match.venue || '').toLowerCase()
  const profile = BATCH_VENUE_PROFILES.find(item =>
    item.patterns.some(pattern => venueText.includes(pattern.toLowerCase())),
  )

  if (!profile) return { weather: 'normal', venue_factor: 'normal' }
  return {
    weather: profile.venue_factor === 'indoor' ? 'normal' : profile.weather,
    venue_factor: profile.venue_factor,
  }
}

function selectExportMatches(matches: Match[], now = new Date(), targetDayKey?: string, maxMatches?: number) {
  const todayKey = getBeijingDayKey(now)
  const nowMs = now.getTime()
  const candidates = matches
    .filter(isDownloadCandidate)
    .filter(match => new Date(match.match_date).getTime() >= nowMs - 30 * 60 * 1000)
    .sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())
  const dayKeys = Array.from(new Set(candidates.map(match => getBeijingDayKey(match.match_date)))).sort()
  const selectedDayKey = targetDayKey && dayKeys.includes(targetDayKey)
    ? targetDayKey
    : dayKeys.find(key => key >= todayKey) ?? dayKeys[0] ?? todayKey
  const dayMatches = candidates.filter(match => getBeijingDayKey(match.match_date) === selectedDayKey)
  const limit = typeof maxMatches === 'number' ? Math.max(1, maxMatches) : dayMatches.length
  return {
    dayKey: selectedDayKey,
    matches: dayMatches.slice(0, limit),
  }
}

function probabilityValue(value?: number) {
  if (value === undefined || value === null || Number.isNaN(value)) return 0
  return value <= 1 ? value * 100 : value
}

function pct(value?: number, digits = 0) {
  if (value === undefined || value === null || Number.isNaN(value)) return '-'
  return `${probabilityValue(value).toFixed(digits)}%`
}

function numberText(value?: number, digits = 2) {
  if (value === undefined || value === null || Number.isNaN(value)) return '-'
  return value.toFixed(digits)
}

function truncateText(value: string, maxLength: number) {
  if (value.length <= maxLength) return value
  return `${value.slice(0, maxLength - 1)}…`
}

function getTeamCode(teamName: string) {
  return TEAMS.find(team => team.name === teamName || team.code === teamName)?.code ?? teamName.slice(0, 2).toUpperCase()
}

function getStageLabel(match: Match) {
  if (match.group) return `${match.group}组`
  const effectiveStage = getEffectiveMatchStage(match)
  return getStageNameCN(effectiveStage || '') || '淘汰赛'
}

function isKnockoutPrediction(match: Match, prediction: PredictionResult) {
  return Boolean(isEffectiveKnockoutMatch(match) || prediction.is_knockout || prediction.knockout_decision)
}

function getMainPick(match: Match, prediction: PredictionResult) {
  const choices = [
    { label: match.home_team, value: prediction.home_win_probability },
    { label: '平局', value: prediction.draw_probability },
    { label: match.away_team, value: prediction.away_win_probability },
  ]
  return choices.sort((a, b) => b.value - a.value)[0]?.label ?? '-'
}

function getInsight(prediction: PredictionResult) {
  const candidates = [
    prediction.skill_audit?.match_type?.label,
    prediction.skill_audit?.risk_flags?.[0],
    prediction.skill_audit?.score_adjustment?.reasons?.[0],
    prediction.factors?.[0],
  ].filter(Boolean).map(item => String(item))
  return truncateText(
    (candidates[0] || '模型综合胜平负、xG、进球线与赛程状态生成。')
      .replace(/赔率/g, '外部数据')
      .replace(/盘口/g, '数据线')
      .replace(new RegExp(['投' + '注', '竞' + '彩', '彩' + '票'].join('|'), 'g'), '模拟参考'),
    50,
  )
}

function scoreProbability(prediction: PredictionResult) {
  return prediction.predicted_score_probability
    ?? prediction.possible_scores?.find(score => score.score === prediction.predicted_score)?.probability
}

function getScorePoolItems(prediction: PredictionResult): ScorePoolItem[] {
  const pool = prediction.possible_scores?.length
    ? prediction.possible_scores.slice(0, 3)
    : [{ score: prediction.predicted_score, probability: scoreProbability(prediction) ?? 0 }]
  return pool.slice(0, 3)
}

function formatScorePool(prediction: PredictionResult) {
  const pool = getScorePoolItems(prediction)
  return pool
    .map(item => `${item.score} ${pct(item.probability, 1)}`)
    .join(' / ')
}

function formatTotalGoalsShort(totalGoals?: TotalGoalsPrediction) {
  if (!totalGoals) return '-'
  const over = probabilityValue(totalGoals.over_probability)
  const under = probabilityValue(totalGoals.under_probability)
  const recommendation = totalGoals.recommendation || ''
  const side = recommendation.includes('小') && !recommendation.includes('大')
    ? '小'
    : recommendation.includes('大') && !recommendation.includes('小')
      ? '大'
      : over >= under ? '大' : '小'
  const sideProbability = totalGoals.side_probability
    ?? (side === '大' ? totalGoals.over_probability : totalGoals.under_probability)
  return `${side}${numberText(totalGoals.main_line, 1)} ${pct(sideProbability, 0)}`
}

function formatUpsetScore(prediction: PredictionResult) {
  const upset = prediction.upset_prediction
  if (!upset?.score) return '暂无'
  return `${upset.score} ${pct(upset.score_probability ?? upset.probability, 1)}`
}

function getKnockoutDrawProbability(prediction: PredictionResult) {
  return prediction.extra_time_probability
    ?? prediction.knockout_decision?.regular_time_draw_probability
    ?? prediction.regular_time_probabilities?.draw
    ?? prediction.knockout_decision?.extra_time_probability
    ?? 0
}

function getKnockoutExtraTimeDecisiveProbability(prediction: PredictionResult) {
  const drawProbability = getKnockoutDrawProbability(prediction)
  const penaltyProbability = prediction.penalty_probability
    ?? prediction.knockout_decision?.penalty_probability
    ?? 0
  return prediction.extra_time_decisive_probability
    ?? prediction.knockout_decision?.extra_time_decisive_probability
    ?? Math.max(0, drawProbability - penaltyProbability)
}

function getKnockoutPenaltyProbability(prediction: PredictionResult) {
  return prediction.penalty_probability
    ?? prediction.knockout_decision?.penalty_probability
    ?? 0
}

function getKnockoutDecisionText(prediction: PredictionResult) {
  return [
    `90分钟平局 ${pct(getKnockoutDrawProbability(prediction), 0)}`,
    `加时决胜 ${pct(getKnockoutExtraTimeDecisiveProbability(prediction), 0)}`,
    `点球决胜 ${pct(getKnockoutPenaltyProbability(prediction), 0)}`,
  ].join(' · ')
}

function downloadDataUrl(dataUrl: string, fileName: string) {
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const radius = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.arcTo(x + w, y, x + w, y + h, radius)
  ctx.arcTo(x + w, y + h, x, y + h, radius)
  ctx.arcTo(x, y + h, x, y, radius)
  ctx.arcTo(x, y, x + w, y, radius)
  ctx.closePath()
}

function fillRoundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number, fill: string, stroke?: string) {
  roundRect(ctx, x, y, w, h, r)
  ctx.fillStyle = fill
  ctx.fill()
  if (stroke) {
    ctx.strokeStyle = stroke
    ctx.lineWidth = 2
    ctx.stroke()
  }
}

function drawText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, color: string, font: string, align: CanvasTextAlign = 'left') {
  ctx.fillStyle = color
  ctx.font = font
  ctx.textAlign = align
  ctx.textBaseline = 'alphabetic'
  ctx.fillText(text, x, y)
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth: number, lineHeight: number, maxLines: number) {
  const chars = Array.from(text)
  const lines: string[] = []
  let line = ''
  chars.forEach(char => {
    const next = `${line}${char}`
    if (ctx.measureText(next).width > maxWidth && line) {
      lines.push(line)
      line = char
    } else {
      line = next
    }
  })
  if (line) lines.push(line)
  lines.slice(0, maxLines).forEach((lineText, index) => {
    const suffix = index === maxLines - 1 && lines.length > maxLines ? '…' : ''
    ctx.fillText(`${lineText}${suffix}`, x, y + index * lineHeight)
  })
}

function drawPill(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, fill: string, color: string, width = 148) {
  fillRoundRect(ctx, x, y, width, 42, 21, fill)
  drawText(ctx, text, x + width / 2, y + 28, color, '900 21px "Microsoft YaHei", Arial, sans-serif', 'center')
}

function drawMetricBox(ctx: CanvasRenderingContext2D, label: string, value: string, x: number, y: number, w: number, color: string) {
  fillRoundRect(ctx, x, y, w, 58, 18, 'rgba(255,255,255,0.08)')
  drawText(ctx, label, x + 14, y + 22, '#94a3b8', '800 15px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, value, x + 14, y + 48, color, '950 23px "Microsoft YaHei", Arial, sans-serif')
}

function drawInfoStrip(ctx: CanvasRenderingContext2D, label: string, value: string, x: number, y: number, w: number, color: string) {
  fillRoundRect(ctx, x, y, w, 32, 16, 'rgba(255,255,255,0.09)', 'rgba(255,255,255,0.08)')
  drawText(ctx, label, x + 14, y + 22, color, '900 15px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, truncateText(value, w > 430 ? 34 : 16), x + 92, y + 22, '#ffffff', '900 18px "Microsoft YaHei", Arial, sans-serif')
}

function drawKnockoutDecisionStrip(ctx: CanvasRenderingContext2D, prediction: PredictionResult, x: number, y: number, w: number) {
  fillRoundRect(ctx, x, y, w, 32, 16, 'rgba(250,204,21,0.10)', 'rgba(250,204,21,0.18)')
  drawText(ctx, '淘汰赛决胜', x + 14, y + 22, '#fde68a', '900 15px "Microsoft YaHei", Arial, sans-serif')
  const metrics = getKnockoutDecisionText(prediction).split(' · ').map(item => {
    const [label, value] = item.split(' ')
    return [label, value || '-'] as const
  })
  metrics.forEach(([label, value], index) => {
    const metricX = x + 126 + index * 98
    drawText(ctx, label, metricX, y + 14, '#94a3b8', '800 10px "Microsoft YaHei", Arial, sans-serif')
    drawText(ctx, value, metricX, y + 28, '#ffffff', '900 15px "Microsoft YaHei", Arial, sans-serif')
  })
}

function drawProbabilityBar(ctx: CanvasRenderingContext2D, label: string, value: number, x: number, y: number, w: number, color: string) {
  drawText(ctx, label, x, y, '#cbd5e1', '900 20px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, pct(value, 1), x + w, y, color, '900 20px "Microsoft YaHei", Arial, sans-serif', 'right')
  fillRoundRect(ctx, x, y + 13, w, 15, 8, 'rgba(255,255,255,0.14)')
  fillRoundRect(ctx, x, y + 13, Math.max(10, w * probabilityValue(value) / 100), 15, 8, color)
}

function drawTeamPanel(ctx: CanvasRenderingContext2D, team: string, code: string, x: number, y: number, w: number, align: CanvasTextAlign) {
  fillRoundRect(ctx, x, y, w, 96, 24, 'rgba(255,255,255,0.075)')
  const textX = align === 'right' ? x + w - 20 : x + 20
  drawText(ctx, code, textX, y + 35, align === 'right' ? '#f9a8d4' : '#67e8f9', '950 20px "Microsoft YaHei", Arial, sans-serif', align)
  drawText(ctx, truncateText(team, 8), textX, y + 75, '#ffffff', '950 35px "Microsoft YaHei", Arial, sans-serif', align)
}

function drawScorePick(ctx: CanvasRenderingContext2D, item: ScorePoolItem, label: string, x: number, y: number, w: number, active: boolean) {
  fillRoundRect(
    ctx,
    x,
    y,
    w,
    90,
    20,
    active ? 'rgba(103,232,249,0.17)' : 'rgba(255,255,255,0.08)',
    active ? 'rgba(103,232,249,0.36)' : 'rgba(255,255,255,0.12)',
  )
  drawText(ctx, label, x + w / 2, y + 24, active ? '#fde68a' : '#bae6fd', '900 16px "Microsoft YaHei", Arial, sans-serif', 'center')
  drawText(ctx, item.score, x + w / 2, y + 62, '#67e8f9', '950 38px "Microsoft YaHei", Arial, sans-serif', 'center')
  drawText(ctx, pct(item.probability, 1), x + w / 2, y + 82, '#fef3c7', '900 15px "Microsoft YaHei", Arial, sans-serif', 'center')
}

function drawMatchCard(ctx: CanvasRenderingContext2D, item: DailyPredictionItem, index: number, y: number) {
  const { match, prediction } = item
  const totalGoals = prediction.total_goals_prediction
  const knockout = isKnockoutPrediction(match, prediction)
  const x = 54
  const w = 972
  const h = 374
  fillRoundRect(ctx, x, y, w, h, 32, 'rgba(8,18,38,0.82)', 'rgba(255,255,255,0.17)')

  fillRoundRect(ctx, x + 26, y + 24, 50, 50, 18, '#67e8f9')
  drawText(ctx, String(index + 1), x + 51, y + 59, '#07111f', '950 25px "Microsoft YaHei", Arial, sans-serif', 'center')
  drawText(ctx, `${formatBeijingDateTime(match.match_date)} · ${getStageLabel(match)}`, x + 92, y + 50, '#bae6fd', '900 20px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, truncateText(match.venue, 42), x + 92, y + 77, '#94a3b8', '800 18px "Microsoft YaHei", Arial, sans-serif')
  drawPill(ctx, `${knockout ? '晋级' : '首选'} ${truncateText(getMainPick(match, prediction), 5)}`, x + w - 214, y + 28, 'rgba(250,204,21,0.17)', '#fde68a', 182)

  drawTeamPanel(ctx, match.home_team, getTeamCode(match.home_team), x + 28, y + 104, 280, 'left')
  drawTeamPanel(ctx, match.away_team, getTeamCode(match.away_team), x + w - 308, y + 104, 280, 'right')
  getScorePoolItems(prediction).forEach((scorePick, scoreIndex) => {
    const labels = ['首选', '次选', '三选']
    drawScorePick(ctx, scorePick, labels[scoreIndex] || `${scoreIndex + 1}选`, x + w / 2 - 171 + scoreIndex * 116, y + 107, 108, scoreIndex === 0)
  })

  drawProbabilityBar(ctx, `${truncateText(match.home_team, 5)}${knockout ? '晋级' : '胜'}`, prediction.home_win_probability, x + 30, y + 244, 300, '#67e8f9')
  drawProbabilityBar(ctx, knockout ? '90分钟平局' : '平局', knockout ? getKnockoutDrawProbability(prediction) : prediction.draw_probability, x + 30, y + 293, 300, '#fde047')
  drawProbabilityBar(ctx, `${truncateText(match.away_team, 5)}${knockout ? '晋级' : '胜'}`, prediction.away_win_probability, x + 372, y + 244, 300, '#fb7185')

  drawMetricBox(ctx, 'xG', `${numberText(prediction.xg_home, 1)}-${numberText(prediction.xg_away, 1)}`, x + 710, y + 220, 118, '#67e8f9')
  drawMetricBox(ctx, '总进球', numberText(totalGoals?.expected_total ?? prediction.xg_home + prediction.xg_away), x + 842, y + 220, 106, '#fde68a')
  drawMetricBox(ctx, '主线大小', formatTotalGoalsShort(totalGoals), x + 710, y + 286, 118, '#86efac')
  drawMetricBox(ctx, '置信度', pct(prediction.confidence, 0), x + 842, y + 286, 106, '#f9a8d4')

  fillRoundRect(ctx, x + 372, y + 293, 300, 42, 21, 'rgba(255,255,255,0.08)')
  ctx.fillStyle = '#cbd5e1'
  ctx.font = '800 19px "Microsoft YaHei", Arial, sans-serif'
  wrapText(ctx, getInsight(prediction), x + 392, y + 321, 260, 23, 1)

  drawInfoStrip(ctx, '比分池', formatScorePool(prediction), x + 30, y + 346, 476, '#67e8f9')
  if (knockout) {
    drawKnockoutDecisionStrip(ctx, prediction, x + 522, y + 346, 426)
  } else {
    drawInfoStrip(ctx, '冷门比分', formatUpsetScore(prediction), x + 522, y + 346, 426, '#f9a8d4')
  }
}

function buildDailyPosterDataUrl(items: DailyPredictionItem[], dayKey: string, generatedAt: string) {
  const pixelRatio = 2
  const posterHeight = Math.max(POSTER_MIN_HEIGHT, CARD_TOP + items.length * CARD_STEP + FOOTER_HEIGHT)
  const canvas = document.createElement('canvas')
  canvas.width = POSTER_WIDTH * pixelRatio
  canvas.height = posterHeight * pixelRatio
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('浏览器不支持 Canvas 导出')
  ctx.scale(pixelRatio, pixelRatio)

  const bg = ctx.createLinearGradient(0, 0, POSTER_WIDTH, posterHeight)
  bg.addColorStop(0, '#07111f')
  bg.addColorStop(0.55, '#0b1b2f')
  bg.addColorStop(1, '#020617')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, POSTER_WIDTH, posterHeight)

  const glow = ctx.createRadialGradient(810, 140, 80, 810, 140, 640)
  glow.addColorStop(0, 'rgba(103,232,249,0.25)')
  glow.addColorStop(0.48, 'rgba(250,204,21,0.11)')
  glow.addColorStop(1, 'rgba(2,6,23,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, POSTER_WIDTH, posterHeight)

  const topLine = ctx.createLinearGradient(0, 0, POSTER_WIDTH, 0)
  topLine.addColorStop(0, '#67e8f9')
  topLine.addColorStop(0.5, '#fde047')
  topLine.addColorStop(1, '#fb7185')
  ctx.fillStyle = topLine
  ctx.fillRect(0, 0, POSTER_WIDTH, 10)

  drawPill(ctx, 'WORLD CUP LENS', 58, 56, 'rgba(103,232,249,0.13)', '#bae6fd', 250)
  drawText(ctx, `${dayLabel(dayKey)} ${items.length}场预测`, 58, 160, '#ffffff', '950 68px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, '胜平负/晋级概率 · 前三比分池 · 淘汰赛决胜层 · xG · 大小球主线', 62, 206, '#fde68a', '900 28px "Microsoft YaHei", Arial, sans-serif')
  fillRoundRect(ctx, 730, 62, 292, 106, 28, 'rgba(255,255,255,0.1)', 'rgba(255,255,255,0.16)')
  drawText(ctx, '生成时间', 760, 102, '#94a3b8', '900 19px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, generatedAt, 760, 141, '#ffffff', '950 28px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, '赛前模型分析摘要', 760, 171, '#bae6fd', '800 18px "Microsoft YaHei", Arial, sans-serif')

  items.forEach((item, index) => drawMatchCard(ctx, item, index, CARD_TOP + index * CARD_STEP))

  ctx.strokeStyle = 'rgba(255,255,255,0.16)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(58, posterHeight - 92)
  ctx.lineTo(1022, posterHeight - 92)
  ctx.stroke()
  drawText(ctx, 'Elo + xG + 状态权重 + 观点复核', 58, posterHeight - 48, '#cbd5e1', '800 22px "Microsoft YaHei", Arial, sans-serif')
  drawText(ctx, '赛前模型分析摘要', 1022, posterHeight - 48, '#94a3b8', '800 20px "Microsoft YaHei", Arial, sans-serif', 'right')

  return canvas.toDataURL('image/png')
}

export default function DailyPredictionsExport({ matches, loading, targetDayKey, maxMatches }: DailyPredictionsExportProps) {
  const [exporting, setExporting] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const exportTarget = useMemo(() => selectExportMatches(matches, new Date(), targetDayKey, maxMatches), [matches, targetDayKey, maxMatches])

  const handleExport = async () => {
    if (!exportTarget.matches.length || exporting) return
    setExporting(true)
    setError(null)
    setStatus(`正在预测 ${dayLabel(exportTarget.dayKey)} ${exportTarget.matches.length} 场比赛...`)

    try {
      const results = await Promise.all(exportTarget.matches.map(async match => {
        const venueAdvantage = detectBatchVenueAdvantage(match)
        const weatherContext = detectBatchWeatherContext(match)
        const injuryFeed = await injuryAPI
          .getMatchInjuries(match.home_team, match.away_team, match.match_date)
          .catch(() => null)
        const response = await predictionAPI.predictMatch({
          stage: getEffectiveMatchStage(match) ?? match.stage,
          match_id: match.id,
          home_team: match.home_team,
          away_team: match.away_team,
          venue: match.venue,
          advantage_team: venueAdvantage.side,
          advantage_level: venueAdvantage.level,
          force_neutral: false,
          weather: weatherContext.weather,
          venue_factor: weatherContext.venue_factor,
          model_type: 'form_weighted',
          high_press: false,
          home_key_absence: Boolean(injuryFeed?.auto_apply.home_key_absence),
          away_key_absence: Boolean(injuryFeed?.auto_apply.away_key_absence),
          home_fatigue: false,
          away_fatigue: false,
          match_round: match.round,
          is_knockout: isEffectiveKnockoutMatch(match),
        })
        return { match, prediction: response.data }
      }))

      setStatus(`正在生成${exportTarget.matches.length}场预测图片...`)
      const generatedAt = formatBeijingDateTime(new Date())
      const dataUrl = buildDailyPosterDataUrl(results, exportTarget.dayKey, generatedAt)
      downloadDataUrl(dataUrl, `wc2026-daily-predictions-${exportTarget.dayKey}.png`)
      setStatus(`已下载 ${dayLabel(exportTarget.dayKey)} ${exportTarget.matches.length}场预测`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '4合一预测下载失败')
      setStatus(null)
    } finally {
      setExporting(false)
    }
  }

  const disabled = loading || exporting || exportTarget.matches.length === 0
  const buttonLabel = exportTarget.matches.length
    ? `下载${dayLabel(exportTarget.dayKey)}${exportTarget.matches.length}场预测`
    : '暂无可预测比赛'

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={handleExport}
        disabled={disabled}
        className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-3.5 py-2 text-sm font-black text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-55 active:scale-95"
      >
        {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
        {exporting ? '生成中...' : buttonLabel}
      </button>
      <span className="hidden items-center gap-1 rounded-full bg-white/70 px-3 py-1.5 text-xs font-black text-slate-600 ring-1 ring-white/60 sm:inline-flex">
        <CalendarDays className="h-3.5 w-3.5 text-blue-600" />
        {exportTarget.matches.length ? `${dayLabel(exportTarget.dayKey)} · ${exportTarget.matches.length}场` : '暂无可预测比赛'}
      </span>
      {status && (
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-black text-emerald-700 ring-1 ring-emerald-100">
          <Sparkles className="h-3.5 w-3.5" />
          {status}
        </span>
      )}
      {error && (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-3 py-1.5 text-xs font-black text-red-700 ring-1 ring-red-100">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </span>
      )}
    </div>
  )
}
