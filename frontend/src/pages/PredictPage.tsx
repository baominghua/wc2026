import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Zap, Target, TrendingUp, BarChart3, Calendar, Clock, MapPin, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Home, CloudRain, Thermometer, Wind, ShieldAlert, Activity, Download, FileText, X } from 'lucide-react'
import { injuryAPI, matchAPI, predictionAPI } from '../services/api'
import type { InjuryMatchFeed, InjuryTeamStatus, PredictionResult } from '../services/api'
import { TEAMS, VENUES, HOST_COUNTRY_MAP, isPlaceholderFixture, getStageNameCN, getEffectiveMatchStage, isEffectiveKnockoutMatch } from '../services/wc2026-data'
import type { Match } from '../services/wc2026-data'
import TeamFlag from '../components/TeamFlag'
import TeamFlagLink from '../components/TeamFlagLink'
import DailyPredictionsExport from '../components/DailyPredictionsExport'

// ============ 类型定义 ============
type AdvantageLevel = 'full' | 'half' | 'none'
type TimeFilter = '3d' | '7d' | 'all'
type ModelType = 'baseline' | 'form_weighted' | 'monte_carlo'
type WeatherCode = 'normal' | 'rain' | 'storm' | 'hot' | 'wind'
type VenueFactor = 'normal' | 'indoor' | 'high_altitude'

const MATCH_LIST_REFRESH_MS = 60000
const SELECTED_MATCH_REFRESH_MS = 180000

interface VenueAdvantage {
  team: string | null
  side: 'home' | 'away' | 'none'
  level: AdvantageLevel
  reason: string
  detail: string
}

interface ScenarioSettings {
  forceNeutral: boolean
  weatherOverride: WeatherCode | 'auto'
  highPress: boolean
  homeKeyAbsence: boolean
  awayKeyAbsence: boolean
  homeFatigue: boolean
  awayFatigue: boolean
}

type BooleanScenarioKey = Exclude<keyof ScenarioSettings, 'weatherOverride'>

interface VenueWeatherProfile {
  lat: number
  lon: number
  climate: WeatherCode
  venueFactor: VenueFactor
  detail: string
}

interface WeatherInsight {
  code: WeatherCode
  label: string
  detail: string
  source: string
  venueFactor: VenueFactor
}

function getPrimaryScoreProbability(prediction?: PredictionResult | null): number | undefined {
  if (!prediction) return undefined
  if (typeof prediction.predicted_score_probability === 'number') {
    return prediction.predicted_score_probability
  }
  const exact = prediction.possible_scores?.find(score => score.score === prediction.predicted_score)
  return exact?.probability ?? prediction.possible_scores?.[0]?.probability
}

function formatScoreProbability(value?: number): string {
  return typeof value === 'number' ? `${value.toFixed(2)}%` : '-'
}

function formatAdjustmentPercent(value?: number): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0.0%'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

interface ScorePickDisplay {
  label: string
  score: string
  probability?: number
}

function parseScoreValue(score?: string): [number, number] | null {
  const match = String(score || '').match(/^(\d+)\s*-\s*(\d+)$/)
  if (!match) return null
  return [Number(match[1]), Number(match[2])]
}

function estimateHalfTimeScore(prediction?: PredictionResult | null): string | null {
  if (!prediction) return null
  if (prediction.half_time_score) return prediction.half_time_score
  const parsed = parseScoreValue(prediction.predicted_score)
  if (!parsed) return null
  const [homeFull, awayFull] = parsed
  const homeXg = Number(prediction.xg_home || 0)
  const awayXg = Number(prediction.xg_away || 0)
  const projectHalf = (full: number, xg: number) => {
    if (full <= 0) return 0
    const singleGoalDrag = full === 1 ? 0.16 : 0
    const highTempoLift = xg >= 1.65 ? 0.18 : 0
    return Math.min(full, Math.max(0, Math.floor(full * 0.45 + highTempoLift - singleGoalDrag + 0.25)))
  }
  let homeHalf = projectHalf(homeFull, homeXg)
  let awayHalf = projectHalf(awayFull, awayXg)
  if (homeFull + awayFull >= 3 && homeHalf + awayHalf === 0) {
    if (homeFull > awayFull || homeXg >= awayXg) homeHalf = 1
    else awayHalf = 1
  }
  return `${homeHalf}-${awayHalf}`
}

function getScorePickRows(
  prediction?: PredictionResult | null,
  preferredScores: string[] = []
): ScorePickDisplay[] {
  if (!prediction) return []
  const probabilities = new Map((prediction.possible_scores || []).map(item => [item.score, item.probability]))
  const orderedScores = [
    prediction.predicted_score,
    ...preferredScores,
    ...(prediction.possible_scores || []).map(item => item.score),
  ].filter(Boolean)
  const uniqueScores = Array.from(new Set(orderedScores)).slice(0, 3)
  const labels = ['首选', '次选', '三选']
  return uniqueScores.map((score, index) => ({
    label: labels[index] || `${index + 1}选`,
    score,
    probability: index === 0 ? getPrimaryScoreProbability(prediction) : probabilities.get(score),
  }))
}

function compactPosterInsight(value: string, maxLength = 86): string {
  const text = String(value || '')
    .replace(/\s+/g, ' ')
    .replace(/^风险校验[:：]\s*/, '波动校验: ')
    .replace(/赔率/g, '外部数据')
    .replace(/盘口/g, '数据线')
    .replace(new RegExp(['投' + '注', '竞' + '彩', '彩' + '票'].join('|'), 'g'), '模拟参考')
    .trim()
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength - 1)}…`
}

function getPosterTeamInfo(teamName?: string | null) {
  if (!teamName) return undefined
  return TEAMS.find(team => team.name === teamName || team.code === teamName)
}

function buildEloInsight(prediction: PredictionResult, match?: Match | null): string {
  const homeName = match?.home_team || prediction.ranking_snapshot?.teams?.home?.team || '主队'
  const awayName = match?.away_team || prediction.ranking_snapshot?.teams?.away?.team || '客队'
  const homeInfo = getPosterTeamInfo(homeName)
  const awayInfo = getPosterTeamInfo(awayName)
  if (!homeInfo?.elo_rating && !awayInfo?.elo_rating) return ''
  return `Elo评分: ${homeName} ${homeInfo?.elo_rating ?? '?'} vs ${awayName} ${awayInfo?.elo_rating ?? '?'}，基础实力差已进入 xG 与胜平负矩阵。`
}

function buildRankingInsight(prediction: PredictionResult, match?: Match | null): string {
  const homeName = match?.home_team || prediction.ranking_snapshot?.teams?.home?.team || '主队'
  const awayName = match?.away_team || prediction.ranking_snapshot?.teams?.away?.team || '客队'
  const homeInfo = getPosterTeamInfo(homeName)
  const awayInfo = getPosterTeamInfo(awayName)
  const homeRank = prediction.ranking_snapshot?.teams?.home?.rank ?? homeInfo?.fifa_rank
  const awayRank = prediction.ranking_snapshot?.teams?.away?.rank ?? awayInfo?.fifa_rank
  if (!homeRank && !awayRank) return ''
  return `世界排名: ${homeName} #${homeRank ?? '?'} vs ${awayName} #${awayRank ?? '?'}，用于校准同洲/跨洲强弱基线。`
}

function formatPosterPlayerList(players?: string[], maxCount = 3): string {
  const names = (players || []).filter(Boolean)
  if (!names.length) return ''
  const visible = names.slice(0, maxCount).join('、')
  return names.length > maxCount ? `${visible}等${names.length}人` : visible
}

function buildInjurySideInsight(status?: InjuryTeamStatus): string {
  if (!status) return ''
  const parts = [
    status.unavailable_players.length ? `缺阵${formatPosterPlayerList(status.unavailable_players)}` : '',
    status.doubtful_players.length ? `成疑${formatPosterPlayerList(status.doubtful_players)}` : '',
    (status.card_risk_players?.length || 0) ? `停赛风险${formatPosterPlayerList(status.card_risk_players)}` : '',
  ].filter(Boolean)
  return parts.length ? `${status.team}: ${parts.join('、')}` : ''
}

function buildInjuryInsight(injuryFeed?: InjuryMatchFeed | null): string {
  const homeLine = buildInjurySideInsight(injuryFeed?.teams?.home)
  const awayLine = buildInjurySideInsight(injuryFeed?.teams?.away)
  const lines = [homeLine, awayLine].filter(Boolean)
  if (!lines.length) return ''
  const statusLabel = injuryFeed?.status === 'connected' ? '公开源同步' : '赛前复核'
  return `关键伤停: ${lines.join('；')}（${statusLabel}，临场名单变化需再刷新）。`
}

function buildInjuryFactorInsight(prediction: PredictionResult): string {
  return prediction.factors?.find(item => /伤停|缺阵|成疑|停赛风险/.test(item)) || ''
}

function buildPosterInsights(
  prediction: PredictionResult,
  match?: Match | null,
  injuryFeed?: InjuryMatchFeed | null
): string[] {
  const audit = prediction.skill_audit
  const setPieces = prediction.set_piece_card_prediction
  const teamFeature = prediction.team_feature_adjustment || prediction.profile_adjustment
  const teamFeatureProfiles = teamFeature?.team_profiles
  const homeProfile = teamFeatureProfiles?.home
  const awayProfile = teamFeatureProfiles?.away
  const teamFeatureHeadline = teamFeature?.applied
    ? `球队特征库: ${homeProfile?.team || match?.home_team || '主队'} ${homeProfile?.form_state?.score ?? '-'}分 / ${awayProfile?.team || match?.away_team || '客队'} ${awayProfile?.form_state?.score ?? '-'}分，按赛前样本低权重修正 xG 与平局倾向。`
    : ''
  const featureNotes = [
    ...(teamFeature?.reasons || []),
    ...(homeProfile?.next_prediction_notes || []),
    ...(awayProfile?.next_prediction_notes || []),
  ]
  const market = prediction.market_calibration
  const marketLine = market?.applied
    ? `外部数据校准: 胜平负分歧触发 ${(market.weight * 100).toFixed(0)}% 权重修正，差异 ${(market.difference * 100).toFixed(1)}%。`
    : ''
  const knockoutDecision = prediction.knockout_decision
  const knockoutDecisionLine = knockoutDecision || prediction.is_knockout
    ? `淘汰赛决胜层: 90分钟平局 ${formatScoreProbability(prediction.extra_time_probability ?? knockoutDecision?.regular_time_draw_probability ?? prediction.regular_time_probabilities?.draw)}，加时决胜 ${formatScoreProbability(prediction.extra_time_decisive_probability ?? knockoutDecision?.extra_time_decisive_probability)}，点球决胜 ${formatScoreProbability(prediction.penalty_probability ?? knockoutDecision?.penalty_probability)}。`
    : ''
  const totalGoals = prediction.total_goals_prediction
  const requiredTail = [
    buildInjuryInsight(injuryFeed || prediction.injury_feed) || buildInjuryFactorInsight(prediction),
    buildEloInsight(prediction, match),
    buildRankingInsight(prediction, match),
  ].filter(Boolean)
  const featureCandidates = [
    teamFeatureHeadline,
    ...featureNotes.slice(0, 2).map(item => `特征库提示: ${item}`),
  ].filter(Boolean)
  const analysisCandidates = [
    audit?.single_match_brief?.paragraphs?.[0],
    audit?.match_type?.reasoning ? `比赛类型: ${audit.match_type.reasoning}` : '',
    match?.round && match.round > 1 && audit?.group_motivation?.notes?.[0]
      ? `小组形势: ${audit.group_motivation.notes[0]}`
      : '',
    totalGoals?.risk_note ? `大小球: ${totalGoals.recommendation}，${totalGoals.risk_note}` : '',
    marketLine,
    knockoutDecisionLine,
    audit?.review_layer?.red_card_notes?.[0] ? `红牌复盘: ${audit.review_layer.red_card_notes[0]}` : '',
    audit?.score_adjustment?.reasons?.[0] ? `比分修正: ${audit.score_adjustment.reasons[0]}` : '',
    audit?.risk_flags?.[0] ? `波动: ${audit.risk_flags[0]}` : '',
    prediction.upset_prediction?.reasons?.[0] ? `冷门观察: ${prediction.upset_prediction.reasons[0]}` : '',
    setPieces
      ? `角球预估 ${setPieces.corners.total}、黄牌预估 ${setPieces.yellow_cards.total}；节奏和对抗强度已计入。`
      : '',
    ...(prediction.factors || []).filter(item => !/(Elo|FIFA|排名|球队特征库)/i.test(item)).slice(0, 2),
  ]
  const reservedSlots = featureCandidates.length + requiredTail.length
  const candidates = [
    ...featureCandidates,
    ...analysisCandidates.slice(0, Math.max(0, 8 - reservedSlots)),
    ...requiredTail,
  ]
    .map(item => compactPosterInsight(String(item || '')))
    .filter(Boolean)

  return Array.from(new Set(candidates)).slice(0, 8)
}

function evidenceStatusLabel(value?: string): string {
  if (value === 'partial-high') return '证据较完整'
  if (value === 'partial') return '证据不完整'
  if (value === 'complete') return '证据完整'
  if (value === 'blocked') return '等待关键数据'
  if (value === 'missing') return '缺少数据'
  return value || '未标记'
}

function scoreAdjustmentLabel(value?: string): string {
  if (!value || value === 'keep') return '保留首选'
  if (value.includes('draw_protection') && value.includes('overflow_watch')) return '防平 + 大胜溢出'
  if (value.includes('draw_protection')) return '加入防平'
  if (value.includes('overflow_watch')) return '大胜溢出观察'
  return value
}

function bttsViewLabel(value?: string): string {
  if (value === 'yes') return '双方进球倾向'
  if (value === 'lean-no') return '双方进球偏否'
  return value || '未标记'
}

const VENUE_WEATHER_PROFILES: Record<string, VenueWeatherProfile> = {
  '阿兹特克体育场': { lat: 19.3029, lon: -99.1505, climate: 'normal', venueFactor: 'high_altitude', detail: '墨西哥城高海拔，体能消耗权重上调' },
  '阿克伦体育场': { lat: 20.6817, lon: -103.4626, climate: 'hot', venueFactor: 'normal', detail: '萨波潘六月偏热，节奏略受影响' },
  'BBVA体育场': { lat: 25.668, lon: -100.244, climate: 'hot', venueFactor: 'normal', detail: '蒙特雷夏季高温风险较高' },
  'BC广场': { lat: 49.2767, lon: -123.1119, climate: 'normal', venueFactor: 'indoor', detail: '温哥华顶棚场地，天气扰动较低' },
  'BMO球场': { lat: 43.6327, lon: -79.4186, climate: 'normal', venueFactor: 'normal', detail: '多伦多六月常温，常规天气权重' },
  'SoFi体育场': { lat: 33.9535, lon: -118.3392, climate: 'normal', venueFactor: 'indoor', detail: '洛杉矶顶棚场地，天气扰动较低' },
  'AT&T体育场': { lat: 32.7473, lon: -97.0945, climate: 'hot', venueFactor: 'indoor', detail: '达拉斯顶棚场地，高温影响较低' },
  '大都会人寿体育场': { lat: 40.8135, lon: -74.0745, climate: 'normal', venueFactor: 'normal', detail: '纽约六月常规天气权重' },
  '梅赛德斯-奔驰体育场': { lat: 33.7554, lon: -84.4008, climate: 'normal', venueFactor: 'indoor', detail: '亚特兰大顶棚场地，天气扰动较低' },
  'NRG体育场': { lat: 29.6847, lon: -95.4107, climate: 'hot', venueFactor: 'indoor', detail: '休斯顿可闭合顶棚，高温影响较低' },
  '硬石体育场': { lat: 25.958, lon: -80.2389, climate: 'hot', venueFactor: 'normal', detail: '迈阿密高温高湿风险较高' },
  '吉列体育场': { lat: 42.0909, lon: -71.2643, climate: 'normal', venueFactor: 'normal', detail: '波士顿六月常规天气权重' },
  '箭头体育场': { lat: 39.049, lon: -94.4839, climate: 'hot', venueFactor: 'normal', detail: '堪萨斯城夏季偏热，节奏略受影响' },
  '林肯金融球场': { lat: 39.9008, lon: -75.1675, climate: 'normal', venueFactor: 'normal', detail: '费城六月常规天气权重' },
  '李维斯体育场': { lat: 37.403, lon: -121.9702, climate: 'normal', venueFactor: 'normal', detail: '旧金山湾区常规天气权重' },
  '流明球场': { lat: 47.5952, lon: -122.3316, climate: 'rain', venueFactor: 'normal', detail: '西雅图存在降雨/湿滑场地风险' },
}

function getVenueName(venueStr: string): string {
  return VENUES.find(v => venueStr.startsWith(v.name))?.name || venueStr.split('，')[0] || venueStr
}

function getWeatherLabel(code: WeatherCode): string {
  const labels: Record<WeatherCode, string> = {
    normal: '常规天气',
    rain: '雨天/湿滑',
    storm: '暴雨强扰动',
    hot: '高温闷热',
    wind: '大风',
  }
  return labels[code]
}

function mapForecastToWeather(temp: number, precipitation: number, windSpeed: number, weatherCode: number): WeatherCode {
  if (weatherCode >= 95) return 'storm'
  if (precipitation >= 60 || (weatherCode >= 61 && weatherCode <= 82)) return 'rain'
  if (windSpeed >= 32) return 'wind'
  if (temp >= 30) return 'hot'
  return 'normal'
}

async function fetchLiveWeatherInsight(match: Match): Promise<WeatherInsight | null> {
  const venueName = getVenueName(match.venue)
  const profile = VENUE_WEATHER_PROFILES[venueName]
  if (!profile) return null

  const matchTime = new Date(match.match_date)
  const diffDays = (matchTime.getTime() - Date.now()) / (24 * 60 * 60 * 1000)
  if (diffDays < -1 || diffDays > 16) return null

  const params = new URLSearchParams({
    latitude: String(profile.lat),
    longitude: String(profile.lon),
    hourly: 'temperature_2m,precipitation_probability,weather_code,wind_speed_10m',
    forecast_days: '16',
    timezone: 'auto',
  })
  const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`, {
    signal: AbortSignal.timeout(3500),
  })
  if (!response.ok) return null

  const data = await response.json()
  const times: string[] = data.hourly?.time || []
  if (times.length === 0) return null

  let bestIndex = 0
  let bestDistance = Number.POSITIVE_INFINITY
  times.forEach((time, index) => {
    const distance = Math.abs(new Date(time).getTime() - matchTime.getTime())
    if (distance < bestDistance) {
      bestDistance = distance
      bestIndex = index
    }
  })

  const temp = Number(data.hourly.temperature_2m?.[bestIndex] ?? 22)
  const precipitation = Number(data.hourly.precipitation_probability?.[bestIndex] ?? 0)
  const windSpeed = Number(data.hourly.wind_speed_10m?.[bestIndex] ?? 0)
  const forecastCode = Number(data.hourly.weather_code?.[bestIndex] ?? 0)
  const rawCode = mapForecastToWeather(temp, precipitation, windSpeed, forecastCode)
  const code = profile.venueFactor === 'indoor' ? 'normal' : rawCode
  const roofNote = profile.venueFactor === 'indoor' ? '；场馆顶棚/室内属性会降低天气权重' : ''

  return {
    code,
    label: getWeatherLabel(code),
    source: 'Open-Meteo 实时预报',
    venueFactor: profile.venueFactor,
    detail: `${venueName} 近似开球时段：${Math.round(temp)}°C，降雨${precipitation}%，风速${Math.round(windSpeed)}km/h${roofNote}`,
  }
}

function detectAutoWeather(match: Match, liveWeather: WeatherInsight | null): WeatherInsight {
  const venueName = getVenueName(match.venue)
  const profile = VENUE_WEATHER_PROFILES[venueName]
  if (!profile) {
    return {
      code: 'normal',
      label: '常规天气',
      source: '赛程场馆默认',
      venueFactor: 'normal',
      detail: '暂无该场馆天气画像，按常规条件处理',
    }
  }

  if (liveWeather) return liveWeather

  const code = profile.venueFactor === 'indoor' ? 'normal' : profile.climate
  return {
    code,
    label: getWeatherLabel(code),
    source: '场馆气候画像',
    venueFactor: profile.venueFactor,
    detail: profile.detail,
  }
}

function formatInjuryUpdatedAt(value: string | null | undefined) {
  if (!value) return '未同步'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function getInjuryStatusLabel(feed: InjuryMatchFeed | null) {
  if (!feed) return '读取中'
  if (feed.status === 'connected') return '公开源已同步'
  if (feed.status === 'stale') return '数据可能过期'
  if (feed.status === 'error') return '读取失败'
  return '公开源待同步'
}

function getInjuryStatusStyle(feed: InjuryMatchFeed | null) {
  if (!feed) return 'bg-blue-50 text-blue-700 border-blue-100'
  if (feed.status === 'connected') return 'bg-emerald-50 text-emerald-700 border-emerald-100'
  if (feed.status === 'stale') return 'bg-amber-50 text-amber-700 border-amber-100'
  if (feed.status === 'error') return 'bg-red-50 text-red-700 border-red-100'
  return 'bg-gray-50 text-gray-600 border-gray-100'
}

function formatInjuryTeamSummary(status?: InjuryTeamStatus) {
  if (!status) return '等待伤停数据'
  const parts = [
    status.unavailable_players.length ? `缺阵/停赛 ${formatPosterPlayerList(status.unavailable_players, 4)}` : '',
    status.doubtful_players.length ? `成疑 ${formatPosterPlayerList(status.doubtful_players, 4)}` : '',
    (status.card_risk_players?.length || 0) ? `停赛风险 ${formatPosterPlayerList(status.card_risk_players, 4)}` : '',
  ].filter(Boolean)
  if (parts.length) return parts.join('；')
  return status.note || '公开源暂无具体伤停'
}

function isHostTeam(teamName: string): boolean {
  return Boolean(HOST_COUNTRY_MAP[teamName])
}

function detectVenueAdvantage(match: Match): VenueAdvantage {
  const isKnockout = isEffectiveKnockoutMatch(match)

  if (!isKnockout) {
    if (isHostTeam(match.home_team)) {
      return {
        team: match.home_team,
        side: 'home',
        level: 'full',
        reason: `${match.home_team}小组赛主场`,
        detail: '小组赛阶段三支东道主按完整主场优势处理',
      }
    }
    if (isHostTeam(match.away_team)) {
      return {
        team: match.away_team,
        side: 'away',
        level: 'full',
        reason: `${match.away_team}小组赛主场`,
        detail: '小组赛阶段三支东道主按完整主场优势处理',
      }
    }
  }

  if (isKnockout) {
    if (match.home_team === '美国') {
      return {
        team: match.home_team,
        side: 'home',
        level: 'full',
        reason: '美国淘汰赛主场',
        detail: '淘汰赛阶段美国按完整主场优势处理',
      }
    }
    if (match.away_team === '美国') {
      return {
        team: match.away_team,
        side: 'away',
        level: 'full',
        reason: '美国淘汰赛主场',
        detail: '淘汰赛阶段美国按完整主场优势处理',
      }
    }
  }

  return {
    team: null,
    side: 'none',
    level: 'none',
    reason: '中立场地',
    detail: '比赛在第三方场地进行，无主场优势',
  }
}

// ============ 日期格式化 ============
function formatMatchDate(dateStr: string) {
  const d = new Date(dateStr)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const dayAfter = new Date(today)
  dayAfter.setDate(dayAfter.getDate() + 2)

  const isSameDay = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()

  const prefix = isSameDay(d, today) ? '今天' : isSameDay(d, tomorrow) ? '明天' : isSameDay(d, dayAfter) ? '后天' : ''
  const time = `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`

  if (prefix) return `${prefix} ${time}`
  return `${d.getMonth() + 1}月${d.getDate()}日 ${time}`
}

function getScheduleDateLabel(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function getScheduleDayKey(dateStr: string) {
  const d = new Date(dateStr)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

function getMatchTimeLabel(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

// ============ 主组件 ============
export default function PredictPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const handledUrlMatchIdRef = useRef<number | null>(null)
  const predictionRequestIdRef = useRef(0)
  const [timeFilter, setTimeFilter] = useState<TimeFilter>('3d')
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null)
  const [matches, setMatches] = useState<Match[]>([])
  const [modelType, setModelType] = useState<ModelType>('form_weighted')
  const [prediction, setPrediction] = useState<PredictionResult | null>(null)
  const [predictionMatchId, setPredictionMatchId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [matchesLoading, setMatchesLoading] = useState(true)
  const [matchesError, setMatchesError] = useState<string | null>(null)
  const [showModelGuide, setShowModelGuide] = useState(false)
  const [showScheduleTools, setShowScheduleTools] = useState(false)
  const [showLineupSection, setShowLineupSection] = useState(false)
  const [showKeyPlayersSection, setShowKeyPlayersSection] = useState(false)
  const [downloadStatus, setDownloadStatus] = useState<string | null>(null)
  const [scenarioSettings, setScenarioSettings] = useState<ScenarioSettings>({
    forceNeutral: false,
    weatherOverride: 'auto',
    highPress: false,
    homeKeyAbsence: false,
    awayKeyAbsence: false,
    homeFatigue: false,
    awayFatigue: false,
  })
  const [liveWeather, setLiveWeather] = useState<{ matchId: number; insight: WeatherInsight | null } | null>(null)
  const [injuryFeed, setInjuryFeed] = useState<{ matchId: number; feed: InjuryMatchFeed } | null>(null)
  const [filterGroup, setFilterGroup] = useState<string>('')
  const [filterRound, setFilterRound] = useState<number>(0)

  const selectMatch = useCallback((matchId: number) => {
    handledUrlMatchIdRef.current = matchId
    setSelectedMatchId(matchId)
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      next.set('matchId', String(matchId))
      return next
    }, { replace: true })
  }, [setSearchParams])

  useEffect(() => {
    let active = true

    const fetchMatches = async () => {
      try {
        const nextMatches = await matchAPI.getMatchesStrict()
        if (active && Array.isArray(nextMatches) && nextMatches.length > 0) {
          setMatches(nextMatches)
          setMatchesError(null)
        }
      } catch (error) {
        console.warn('Failed to refresh live matches for prediction page', error)
        if (active) setMatchesError('实时赛程同步失败，请重新登录或稍后刷新。')
      } finally {
        if (active) setMatchesLoading(false)
      }
    }

    void fetchMatches()
    const refreshMs = selectedMatchId ? SELECTED_MATCH_REFRESH_MS : MATCH_LIST_REFRESH_MS
    const timer = window.setInterval(fetchMatches, refreshMs)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [selectedMatchId])

  useEffect(() => {
    const rawMatchId = searchParams.get('matchId')
    const urlMatchId = rawMatchId ? Number(rawMatchId) : null
    if (!urlMatchId || Number.isNaN(urlMatchId) || handledUrlMatchIdRef.current === urlMatchId) return
    if (!matches.some(match => match.id === urlMatchId)) return

    handledUrlMatchIdRef.current = urlMatchId
    setSelectedMatchId(urlMatchId)
    setTimeFilter('all')
    setFilterGroup('')
    setFilterRound(0)
  }, [matches, searchParams])

  // 时间窗口计算
  const startOfToday = useMemo(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), now.getDate())
  }, [])

  // 按时间筛选比赛
  const timeFilteredMatches = useMemo(() => {
    const sorted = [...matches].sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())

    if (timeFilter === '3d') {
      const endDate = new Date(startOfToday.getTime() + 4 * 24 * 60 * 60 * 1000)
      return sorted.filter(m => {
        const d = new Date(m.match_date)
        return d >= startOfToday && d < endDate
      })
    } else if (timeFilter === '7d') {
      const endDate = new Date(startOfToday.getTime() + 8 * 24 * 60 * 60 * 1000)
      return sorted.filter(m => {
        const d = new Date(m.match_date)
        return d >= startOfToday && d < endDate
      })
    }
    return sorted
  }, [matches, timeFilter, startOfToday])

  // 按小组/轮次筛选
  const filteredMatches = useMemo(() => timeFilteredMatches.filter(m => {
    if (filterGroup && m.group !== filterGroup) return false
    if (filterRound && m.round !== filterRound) return false
    return true
  }), [timeFilteredMatches, filterGroup, filterRound])

  const defaultMatchId = useMemo(() => {
    if (filteredMatches.length === 0) return null
    const upcoming = filteredMatches.filter(m => new Date(m.match_date) > new Date())
    return upcoming.length > 0 ? upcoming[0].id : filteredMatches[0].id
  }, [filteredMatches])

  const effectiveSelectedMatchId = filteredMatches.some(m => m.id === selectedMatchId)
    ? selectedMatchId
    : defaultMatchId

  // 当前选中的比赛
  const selectedMatch = useMemo(
    () => matches.find(m => m.id === effectiveSelectedMatchId) || null,
    [matches, effectiveSelectedMatchId]
  )
  const selectedFixturePending = isPlaceholderFixture(selectedMatch)
  const selectedEffectiveStage = selectedMatch ? getEffectiveMatchStage(selectedMatch) : null

  useEffect(() => {
    predictionRequestIdRef.current += 1
    setPrediction(null)
    setPredictionMatchId(null)
    setDownloadStatus(null)
    setLoading(false)
  }, [selectedMatch?.id])

  // 检测主场优势
  const venueAdvantage = useMemo(
    () => selectedMatch ? detectVenueAdvantage(selectedMatch) : null,
    [selectedMatch]
  )

  useEffect(() => {
    let active = true

    if (!selectedMatch) return

    void fetchLiveWeatherInsight(selectedMatch)
      .then(insight => {
        if (active) setLiveWeather({ matchId: selectedMatch.id, insight })
      })
      .catch(() => {
        if (active) setLiveWeather({ matchId: selectedMatch.id, insight: null })
      })

    return () => {
      active = false
    }
  }, [selectedMatch])

  useEffect(() => {
    let active = true

    if (!selectedMatch) return

    void injuryAPI.getMatchInjuries(selectedMatch.home_team, selectedMatch.away_team, selectedMatch.match_date)
      .then(feed => {
        if (!active) return
        setInjuryFeed({ matchId: selectedMatch.id, feed })
        if (feed.status !== 'not_configured' && feed.status !== 'error') {
          setScenarioSettings(prev => ({
            ...prev,
            homeKeyAbsence: feed.auto_apply.home_key_absence,
            awayKeyAbsence: feed.auto_apply.away_key_absence,
          }))
        }
      })
      .catch(() => {
        if (!active) return
        setInjuryFeed({
          matchId: selectedMatch.id,
          feed: {
            status: 'not_configured',
            source: 'manual_only',
            last_updated: null,
            match_date: selectedMatch.match_date,
      message: '公开伤停源暂未同步，当前保留手动伤停勾选',
      teams: {
        home: { team: selectedMatch.home_team, unavailable_players: [], doubtful_players: [], card_risk_players: [], note: '暂无可信伤停数据', source: 'manual_only' },
        away: { team: selectedMatch.away_team, unavailable_players: [], doubtful_players: [], card_risk_players: [], note: '暂无可信伤停数据', source: 'manual_only' },
      },
            auto_apply: { home_key_absence: false, away_key_absence: false },
          },
        })
      })

    return () => {
      active = false
    }
  }, [selectedMatch])

  const selectedLiveWeather = liveWeather && liveWeather.matchId === selectedMatch?.id ? liveWeather.insight : null
  const selectedInjuryFeed = injuryFeed && injuryFeed.matchId === selectedMatch?.id ? injuryFeed.feed : null
  const autoWeather = useMemo(
    () => selectedMatch ? detectAutoWeather(selectedMatch, selectedLiveWeather) : null,
    [selectedMatch, selectedLiveWeather]
  )

  const effectiveWeather = scenarioSettings.weatherOverride === 'auto'
    ? autoWeather?.code || 'normal'
    : scenarioSettings.weatherOverride

  const getTeamInfo = useCallback((name: string) => TEAMS.find(t => t.name === name), [])

  const runPrediction = useCallback(async () => {
    if (!selectedMatch) return
    if (selectedFixturePending) {
      setDownloadStatus('淘汰赛对阵尚未官方确认，等双方确定后再生成预测')
      return
    }
    if (!autoWeather || !selectedInjuryFeed) return
    const requestId = ++predictionRequestIdRef.current
    const requestMatchId = selectedMatch.id
    setLoading(true)
    setPrediction(null)
    setPredictionMatchId(null)
    setDownloadStatus(null)
    try {
      const adv = scenarioSettings.forceNeutral
        ? { side: 'none' as const, level: 'none' as const }
        : { side: venueAdvantage?.side || 'none', level: venueAdvantage?.level || 'none' }
      const effectiveStage = getEffectiveMatchStage(selectedMatch)

      const result = await predictionAPI.predictMatch({
        match_id: selectedMatch.id,
        home_team: selectedMatch.home_team,
        away_team: selectedMatch.away_team,
        venue: selectedMatch.venue,
        advantage_team: adv.side,
        advantage_level: adv.level,
        force_neutral: scenarioSettings.forceNeutral,
        weather: effectiveWeather,
        venue_factor: autoWeather?.venueFactor || 'normal',
        model_type: modelType,
        is_knockout: Boolean(effectiveStage),
        high_press: scenarioSettings.highPress,
        home_key_absence: scenarioSettings.homeKeyAbsence,
        away_key_absence: scenarioSettings.awayKeyAbsence,
        home_fatigue: scenarioSettings.homeFatigue,
        away_fatigue: scenarioSettings.awayFatigue,
        match_round: selectedMatch.round,
        stage: effectiveStage ?? selectedMatch.stage,
      })
      if (predictionRequestIdRef.current === requestId) {
        setPrediction(result.data)
        setPredictionMatchId(requestMatchId)
      }
    } catch (e) {
      console.error(e)
    } finally {
      if (predictionRequestIdRef.current === requestId) {
        setLoading(false)
      }
    }
  }, [autoWeather, effectiveWeather, modelType, scenarioSettings, selectedFixturePending, selectedInjuryFeed, selectedMatch, venueAdvantage])

  const downloadPredictionImage = useCallback(async () => {
    if (!selectedMatch || !prediction || predictionMatchId !== selectedMatch.id || loading || !selectedInjuryFeed) {
      setDownloadStatus('请先完成当前比赛预测，再下载图片')
      return
    }
    setDownloadStatus('正在生成高清预测海报...')
    const isMobileLike =
      typeof navigator !== 'undefined' &&
      /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent)
    const fallbackWindow = isMobileLike ? window.open('', '_blank') : null
    if (fallbackWindow) {
      try {
        fallbackWindow.opener = null
      } catch {
        // Some mobile browsers block assigning opener; the save page can still render.
      }
      fallbackWindow.document.write(
        '<!doctype html><html><head><meta charset="utf-8"><title>正在生成预测海报</title><style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:24px;background:#07111f;color:#e2e8f0;text-align:center}p{color:#94a3b8}</style></head><body><h2>正在生成高清预测海报...</h2><p>生成完成后可长按图片保存。</p></body></html>'
      )
    }

    const canvas = document.createElement('canvas')
    const width = 1600
    let height = 2200
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const drawRoundRect = (x: number, y: number, w: number, h: number, r: number, fill: string) => {
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.lineTo(x + w - r, y)
      ctx.quadraticCurveTo(x + w, y, x + w, y + r)
      ctx.lineTo(x + w, y + h - r)
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
      ctx.lineTo(x + r, y + h)
      ctx.quadraticCurveTo(x, y + h, x, y + h - r)
      ctx.lineTo(x, y + r)
      ctx.quadraticCurveTo(x, y, x + r, y)
      ctx.closePath()
      ctx.fillStyle = fill
      ctx.fill()
    }

    const strokeRoundRect = (x: number, y: number, w: number, h: number, r: number, stroke: string, lineWidth = 2) => {
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.lineTo(x + w - r, y)
      ctx.quadraticCurveTo(x + w, y, x + w, y + r)
      ctx.lineTo(x + w, y + h - r)
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
      ctx.lineTo(x + r, y + h)
      ctx.quadraticCurveTo(x, y + h, x, y + h - r)
      ctx.lineTo(x, y + r)
      ctx.quadraticCurveTo(x, y, x + r, y)
      ctx.closePath()
      ctx.strokeStyle = stroke
      ctx.lineWidth = lineWidth
      ctx.stroke()
    }

    const wrapText = (text: string, x: number, y: number, maxWidth: number, lineHeight: number, maxLines = 999) => {
      let line = ''
      let currentY = y
      let lines = 0
      for (const char of Array.from(text || '')) {
        const testLine = line + char
        if (ctx.measureText(testLine).width > maxWidth && line) {
          lines += 1
          if (lines >= maxLines) {
            ctx.fillText(`${line.slice(0, Math.max(0, line.length - 1))}...`, x, currentY)
            return currentY + lineHeight
          }
          ctx.fillText(line, x, currentY)
          line = char
          currentY += lineHeight
        } else {
          line = testLine
        }
      }
      if (line && lines < maxLines) ctx.fillText(line, x, currentY)
      return currentY + lineHeight
    }

    const loadCanvasImage = (src: string) =>
      new Promise<HTMLImageElement | null>(resolve => {
        const image = new Image()
        image.onload = () => resolve(image)
        image.onerror = () => resolve(null)
        image.src = src
      })

    const drawCoverImage = (image: HTMLImageElement, x: number, y: number, w: number, h: number, alpha = 1) => {
      const ratio = Math.max(w / image.width, h / image.height)
      const dw = image.width * ratio
      const dh = image.height * ratio
      ctx.save()
      ctx.globalAlpha = alpha
      ctx.drawImage(image, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
      ctx.restore()
    }

    const drawContainImage = (image: HTMLImageElement, x: number, y: number, w: number, h: number, alpha = 1) => {
      const ratio = Math.min(w / image.width, h / image.height)
      const dw = image.width * ratio
      const dh = image.height * ratio
      ctx.save()
      ctx.globalAlpha = alpha
      ctx.drawImage(image, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)
      ctx.restore()
    }

    const flagEmoji = (teamName: string) => {
      const code = getTeamInfo(teamName)?.flagCode?.toUpperCase()
      if (!code || code.length !== 2) return ''
      return String.fromCodePoint(...Array.from(code).map(char => 0x1f1e6 + char.charCodeAt(0) - 65))
    }

    const [backgroundImage, messiImage, logoImage] = await Promise.all([
      loadCanvasImage('/wc2026-site-background-v4.png'),
      loadCanvasImage('/wc2026-messi-trophy-overlay.png'),
      loadCanvasImage('/wc2026-logo.png'),
    ])

    const totalGoals = prediction.total_goals_prediction
    const mainLine = totalGoals?.lines.find(line => line.line === totalGoals.main_line) || totalGoals?.lines[0]
    const mainLineLabel = totalGoals ? `${totalGoals.main_line} 球` : '-'
    const overUnderLabel = mainLine
      ? `大 ${(mainLine.over_probability * 100).toFixed(1)}% / 小 ${(mainLine.under_probability * 100).toFixed(1)}%`
      : '-'
    const imageMarketCalibration = prediction.market_calibration
    const imageMarketOdds = prediction.market_odds
    const imageUpset = prediction.upset_prediction
    const imageSetPieceCards = prediction.set_piece_card_prediction
    const imageSkillAudit = prediction.skill_audit
    const imageKnockoutDecision = prediction.knockout_decision
    const imageEffectiveStage = getEffectiveMatchStage(selectedMatch)
    const hasImageKnockoutDecision = Boolean(imageEffectiveStage || prediction.is_knockout || imageKnockoutDecision)
    const imageExtraTimeProbability = prediction.extra_time_probability
      ?? imageKnockoutDecision?.regular_time_draw_probability
      ?? prediction.regular_time_probabilities?.draw
      ?? imageKnockoutDecision?.extra_time_probability
      ?? prediction.penalty_probability
      ?? 0
    const imagePenaltyDecisionProbability = prediction.penalty_probability
      ?? imageKnockoutDecision?.penalty_probability
      ?? 0
    const imageExtraTimeDecisiveProbability = prediction.extra_time_decisive_probability
      ?? imageKnockoutDecision?.extra_time_decisive_probability
      ?? Math.max(0, imageExtraTimeProbability - imagePenaltyDecisionProbability)
    const imageKnockoutProbabilityText = (value?: number | null) =>
      typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '-'
    const totalGoalsSideProbability = totalGoals
      ? totalGoals.side_probability || Math.max(totalGoals.over_probability, totalGoals.under_probability)
      : undefined
    const totalGoalsSignal = totalGoals
      ? totalGoals.signal_strength ?? totalGoals.confidence
      : undefined
    const upsetRiskLabel = imageUpset
      ? ({ low: '低', medium: '中', high: '高' } as Record<string, string>)[imageUpset.risk_level] || imageUpset.risk_level
      : '-'
    const upsetScoreProbability = typeof imageUpset?.score_probability === 'number'
      ? formatScoreProbability(imageUpset.score_probability)
      : typeof imageUpset?.probability === 'number'
        ? `${(imageUpset.probability * 100).toFixed(1)}%`
        : '-'
    const imageMarketStatusLabel: Record<string, string> = {
      connected: '已接入',
      aligned: '外部接近',
      disabled: '已关闭',
      not_configured: '待配置数据源',
      no_match: '未匹配',
      no_markets: '无外部信号',
      error: '连接异常',
      unsupported_provider: '数据源不支持',
      historical_prior: '历史样本参考',
    }
    const imageMarketStatusKey = imageMarketOdds?.status === 'historical_prior'
      ? 'historical_prior'
      : imageMarketCalibration?.level || imageMarketOdds?.status || ''
    const imageMarketStatus = imageMarketCalibration?.applied
      ? `已校准 ${(imageMarketCalibration.weight * 100).toFixed(0)}%`
      : `未校准 · ${imageMarketStatusLabel[imageMarketStatusKey] || imageMarketStatusKey || '未接入'}`
    const posterTotalGoalsSummary = totalGoals
      ? `主线${mainLineLabel} · ${totalGoals.recommendation} · ${((totalGoalsSideProbability || 0) * 100).toFixed(1)}% / 信号${((totalGoalsSignal || 0) * 100).toFixed(1)}%`
      : `${mainLineLabel} · ${overUnderLabel}`
    const metricCards = [
      [`${selectedMatch.home_team} xG`, prediction.xg_home.toString(), '#67e8f9'],
      [`${selectedMatch.away_team} xG`, prediction.xg_away.toString(), '#fda4af'],
      ['预期总进球', totalGoals?.expected_total?.toString() || '-', '#fde68a'],
      ['大小球主线', posterTotalGoalsSummary, '#a7f3d0'],
      ['外部信号', imageMarketStatus, '#bfdbfe'],
      ['冷门概率', imageUpset ? `${upsetRiskLabel} / ${imageUpset.score} ${upsetScoreProbability}` : '-', '#fed7aa'],
    ]
    const imageScorePicks = getScorePickRows(prediction, imageSkillAudit?.score_pool_top3 || [])
    const imageHalfTimeScore = estimateHalfTimeScore(prediction)
    const downloadBasisItems = buildPosterInsights(prediction, selectedMatch, selectedInjuryFeed)
    const posterKnockoutDecisionY = 1490
    const posterAnalysisY = hasImageKnockoutDecision ? posterKnockoutDecisionY + 212 : 1515
    const posterModeSubtitle = hasImageKnockoutDecision
      ? '淘汰赛复盘口径: 90分钟比分 + 加时 + 点球 + 晋级概率'
      : '小组赛复盘口径: 当前轮次 + 已完赛样本 + 出线形势'
    const posterAnalysisTextWidth = 1188
    const posterAnalysisLineHeight = 34
    const posterAnalysisHeight = Math.max(620, Math.min(930, 132 + downloadBasisItems.length * 88))
    const posterSideFactsY = posterAnalysisY + posterAnalysisHeight + 34
    const posterFooterY = posterSideFactsY + 182
    height = Math.max(2380, posterFooterY + 130)
    canvas.height = height

    const bg = ctx.createLinearGradient(0, 0, width, height)
    bg.addColorStop(0, '#07111f')
    bg.addColorStop(0.55, '#0b1628')
    bg.addColorStop(1, '#030712')
    ctx.fillStyle = bg
    ctx.fillRect(0, 0, width, height)
    if (backgroundImage) drawCoverImage(backgroundImage, 0, 0, width, height, 0.74)

    const darkVeil = ctx.createLinearGradient(0, 0, width, height)
    darkVeil.addColorStop(0, 'rgba(3,7,18,0.92)')
    darkVeil.addColorStop(0.44, 'rgba(7,17,31,0.72)')
    darkVeil.addColorStop(1, 'rgba(3,7,18,0.94)')
    ctx.fillStyle = darkVeil
    ctx.fillRect(0, 0, width, height)

    const glow = ctx.createRadialGradient(width * 0.52, 320, 30, width * 0.52, 320, 900)
    glow.addColorStop(0, 'rgba(103,232,249,0.30)')
    glow.addColorStop(0.42, 'rgba(59,130,246,0.10)')
    glow.addColorStop(1, 'rgba(3,7,18,0)')
    ctx.fillStyle = glow
    ctx.fillRect(0, 0, width, height)

    const goldGlow = ctx.createRadialGradient(width * 0.5, 640, 40, width * 0.5, 640, 760)
    goldGlow.addColorStop(0, 'rgba(250,204,21,0.16)')
    goldGlow.addColorStop(1, 'rgba(250,204,21,0)')
    ctx.fillStyle = goldGlow
    ctx.fillRect(0, 0, width, height)

    if (messiImage) drawContainImage(messiImage, 1000, 215, 650, 850, 0.62)
    const rightShade = ctx.createLinearGradient(780, 0, width, 0)
    rightShade.addColorStop(0, 'rgba(7,17,31,0)')
    rightShade.addColorStop(0.68, 'rgba(7,17,31,0.18)')
    rightShade.addColorStop(1, 'rgba(7,17,31,0.58)')
    ctx.fillStyle = rightShade
    ctx.fillRect(780, 0, width - 780, height)

    const topLine = ctx.createLinearGradient(0, 0, width, 0)
    topLine.addColorStop(0, '#67e8f9')
    topLine.addColorStop(0.5, '#facc15')
    topLine.addColorStop(1, '#67e8f9')
    ctx.fillStyle = topLine
    ctx.fillRect(0, 0, width, 8)

    if (logoImage) drawContainImage(logoImage, 118, 84, 78, 78, 0.96)
    drawRoundRect(214, 94, 320, 54, 27, 'rgba(255,255,255,0.10)')
    strokeRoundRect(214, 94, 320, 54, 27, 'rgba(255,255,255,0.16)')
    ctx.fillStyle = '#a5f3fc'
    ctx.font = '900 24px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('WORLD CUP LENS', 244, 129)
    ctx.fillStyle = '#e2e8f0'
    ctx.font = '800 24px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(`${formatMatchDate(selectedMatch.match_date)} · ${selectedMatch.group ? `${selectedMatch.group}组` : imageEffectiveStage ? getStageNameCN(imageEffectiveStage) : '小组赛'}`, 112, 205)
    ctx.fillStyle = '#94a3b8'
    ctx.font = '700 21px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(selectedMatch.venue || '赛场待确认', 112, 238)

    ctx.fillStyle = '#ffffff'
    ctx.font = '900 62px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('2026WC赛前简报', 112, 335)
    ctx.fillStyle = '#fde68a'
    ctx.font = '900 32px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(prediction.skill_audit?.match_type?.label || '模型综合判断', 112, 385)
    ctx.fillStyle = '#bae6fd'
    ctx.font = '800 24px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(posterModeSubtitle, 112, 427)

    const homeFlag = flagEmoji(selectedMatch.home_team)
    const awayFlag = flagEmoji(selectedMatch.away_team)
    const scoreText = prediction.predicted_score
    const primaryProbability = getPrimaryScoreProbability(prediction)
    const homeProb = prediction.home_win_probability * 100
    const drawProb = prediction.draw_probability * 100
    const awayProb = prediction.away_win_probability * 100

    drawRoundRect(112, 465, 1376, 404, 40, 'rgba(15,23,42,0.82)')
    strokeRoundRect(112, 465, 1376, 404, 40, 'rgba(255,255,255,0.14)')
    drawRoundRect(603, 548, 394, 190, 42, 'rgba(103,232,249,0.14)')
    strokeRoundRect(603, 548, 394, 190, 42, 'rgba(103,232,249,0.42)', 3)

    ctx.textAlign = 'center'
    ctx.fillStyle = '#e0f2fe'
    ctx.font = '900 42px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(`${homeFlag} ${selectedMatch.home_team}`, 365, 600)
    ctx.fillText(`${selectedMatch.away_team} ${awayFlag}`, 1235, 600)
    ctx.fillStyle = '#67e8f9'
    ctx.font = '900 128px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(scoreText, width / 2, 672)
    if (typeof primaryProbability === 'number') {
      ctx.fillStyle = '#fde68a'
      ctx.font = '900 28px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(`首选比分概率 ${formatScoreProbability(primaryProbability)}`, width / 2, 720)
    }
    if (imageHalfTimeScore) {
      drawRoundRect(675, 736, 250, 36, 18, 'rgba(255,255,255,0.10)')
      ctx.fillStyle = '#e2e8f0'
      ctx.font = '900 22px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(`半场 ${imageHalfTimeScore}`, width / 2, 761)
    }
    ctx.textAlign = 'left'

    const probabilityRows: [string, number, string][] = [
      [`${selectedMatch.home_team}${hasImageKnockoutDecision ? '晋级' : '胜'}`, homeProb, '#67e8f9'],
      [hasImageKnockoutDecision ? '90分钟平局' : '平局', hasImageKnockoutDecision ? imageExtraTimeProbability * 100 : drawProb, '#facc15'],
      [`${selectedMatch.away_team}${hasImageKnockoutDecision ? '晋级' : '胜'}`, awayProb, '#fda4af'],
    ]
    probabilityRows.forEach((row, index) => {
      const y = (imageHalfTimeScore ? 786 : 765) + index * (imageHalfTimeScore ? 39 : 50)
      const value = Math.max(0, Math.min(100, row[1]))
      ctx.fillStyle = '#cbd5e1'
      ctx.font = '800 20px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(row[0], 170, y)
      drawRoundRect(420, y - 22, 760, 24, 12, 'rgba(255,255,255,0.10)')
      drawRoundRect(420, y - 22, 760 * (value / 100), 24, 12, row[2])
      ctx.fillStyle = row[2]
      ctx.font = '900 24px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(`${value.toFixed(1)}%`, 1215, y + 2)
    })

    const drawMetric = (label: string, value: string, x: number, y: number, color: string) => {
      drawRoundRect(x, y, 430, 126, 26, 'rgba(15,23,42,0.78)')
      strokeRoundRect(x, y, 430, 126, 26, 'rgba(255,255,255,0.12)')
      ctx.fillStyle = '#94a3b8'
      ctx.font = '800 19px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(label, x + 26, y + 38)
      ctx.fillStyle = color
      ctx.font = `${value.length > 18 ? '900 27px' : '900 33px'} "Microsoft YaHei", Arial, sans-serif`
      wrapText(value, x + 26, y + 82, 374, 34, value.length > 18 ? 2 : 1)
    }
    metricCards.forEach((card, index) => {
      drawMetric(card[0], card[1], 112 + (index % 3) * 466, 930 + Math.floor(index / 3) * 150, card[2])
    })

    drawRoundRect(112, 1260, 1376, 194, 34, 'rgba(15,23,42,0.80)')
    strokeRoundRect(112, 1260, 1376, 194, 34, 'rgba(255,255,255,0.14)')
    ctx.fillStyle = '#a5f3fc'
    ctx.font = '900 24px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('比分池', 158, 1310)
    ctx.fillStyle = '#94a3b8'
    ctx.font = '800 18px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(`前三比分池 · 等权放大 · ${imageSkillAudit?.total_goals_range ? `总进球 ${imageSkillAudit.total_goals_range}` : '总进球按 xG 区间估计'} · ${imageSkillAudit?.btts_view ? `双方进球: ${imageSkillAudit.btts_view === 'yes' ? '是' : '否'}` : '双方进球倾向'}`, 158, 1344)
    const drawPosterScorePick = (pick: ScorePickDisplay, index: number) => {
      const x = 158 + index * 434
      const scoreCardAccent = ['#67e8f9', '#93c5fd', '#f9a8d4'][index] || '#67e8f9'
      drawRoundRect(x, 1362, 390, 82, 28, 'rgba(255,255,255,0.10)')
      strokeRoundRect(x, 1362, 390, 82, 28, `${scoreCardAccent}88`, 3)
      drawRoundRect(x + 16, 1378, 82, 36, 18, `${scoreCardAccent}33`)
      ctx.fillStyle = scoreCardAccent
      ctx.font = '900 20px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(pick.label, x + 32, 1402)
      ctx.fillStyle = '#f8fafc'
      ctx.font = '950 46px "Microsoft YaHei", Arial, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(pick.score, x + 205, 1412)
      ctx.textAlign = 'right'
      ctx.fillStyle = '#fde68a'
      ctx.font = '900 24px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(formatScoreProbability(pick.probability), x + 362, 1410)
      ctx.textAlign = 'left'
    }
    imageScorePicks.slice(0, 3).forEach((pick, index) => {
      drawPosterScorePick(pick, index)
    })

    const drawKnockoutDecisionMetric = (label: string, value: string, x: number, y: number, color: string) => {
      drawRoundRect(x, y, 386, 88, 28, 'rgba(255,255,255,0.08)')
      strokeRoundRect(x, y, 386, 88, 28, 'rgba(255,255,255,0.12)')
      ctx.fillStyle = '#94a3b8'
      ctx.font = '900 20px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(label, x + 28, y + 34)
      ctx.fillStyle = color
      ctx.font = '950 34px "Microsoft YaHei", Arial, sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(value, x + 356, y + 58)
      ctx.textAlign = 'left'
    }

    if (hasImageKnockoutDecision) {
      drawRoundRect(112, posterKnockoutDecisionY, 1376, 170, 34, 'rgba(15,23,42,0.82)')
      strokeRoundRect(112, posterKnockoutDecisionY, 1376, 170, 34, 'rgba(250,204,21,0.18)')
      ctx.fillStyle = '#fde68a'
      ctx.font = '900 28px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText('淘汰赛决胜层', 158, posterKnockoutDecisionY + 48)
      ctx.fillStyle = '#94a3b8'
      ctx.font = '800 18px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText('90分钟比分与晋级概率分开读取', 356, posterKnockoutDecisionY + 47)
      drawKnockoutDecisionMetric('90分钟平局', imageKnockoutProbabilityText(imageExtraTimeProbability), 158, posterKnockoutDecisionY + 76, '#fde047')
      drawKnockoutDecisionMetric('加时决胜', imageKnockoutProbabilityText(imageExtraTimeDecisiveProbability), 607, posterKnockoutDecisionY + 76, '#67e8f9')
      drawKnockoutDecisionMetric('点球决胜', imageKnockoutProbabilityText(imagePenaltyDecisionProbability), 1056, posterKnockoutDecisionY + 76, '#fda4af')
    }

    drawRoundRect(112, posterAnalysisY, 1376, posterAnalysisHeight, 34, 'rgba(15,23,42,0.82)')
    strokeRoundRect(112, posterAnalysisY, 1376, posterAnalysisHeight, 34, 'rgba(255,255,255,0.14)')
    ctx.fillStyle = '#ffffff'
    ctx.font = '900 30px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('核心观点', 158, posterAnalysisY + 56)
    ctx.fillStyle = '#94a3b8'
    ctx.font = '800 18px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText(`特征库 + xG + 外部数据 + 风险校验，共 ${downloadBasisItems.length} 条关键依据`, 306, posterAnalysisY + 55)
    let textY = posterAnalysisY + 108
    ;downloadBasisItems.forEach((factor, index) => {
      ctx.fillStyle = index === 0 ? '#fde68a' : '#67e8f9'
      ctx.font = '900 22px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(`${index + 1}.`, 158, textY)
      ctx.fillStyle = '#cbd5e1'
      ctx.font = '700 24px "Microsoft YaHei", Arial, sans-serif'
      textY = wrapText(factor, 202, textY, posterAnalysisTextWidth, posterAnalysisLineHeight)
      textY += 18
    })

    drawRoundRect(112, posterSideFactsY, 1376, 134, 34, 'rgba(15,23,42,0.82)')
    strokeRoundRect(112, posterSideFactsY, 1376, 134, 34, 'rgba(255,255,255,0.14)')
    ctx.fillStyle = '#fde68a'
    ctx.font = '900 26px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('附加参考', 158, posterSideFactsY + 48)
    const sideFacts = [
      ['角球', imageSetPieceCards ? `${imageSetPieceCards.corners.home}-${imageSetPieceCards.corners.away} / 总${imageSetPieceCards.corners.total}` : '-'],
      ['黄牌', imageSetPieceCards ? `${imageSetPieceCards.yellow_cards.home}-${imageSetPieceCards.yellow_cards.away} / 总${imageSetPieceCards.yellow_cards.total}` : '-'],
      ['冷门比分', imageUpset ? `${imageUpset.score} ${upsetScoreProbability}` : '-'],
    ]
    sideFacts.forEach((item, index) => {
      const x = 390 + index * 340
      const y = posterSideFactsY + 78
      drawRoundRect(x, posterSideFactsY + 32, 292, 68, 22, 'rgba(255,255,255,0.08)')
      ctx.fillStyle = '#94a3b8'
      ctx.font = '800 18px "Microsoft YaHei", Arial, sans-serif'
      ctx.fillText(item[0], x + 24, y - 14)
      ctx.fillStyle = '#67e8f9'
      ctx.font = '900 23px "Microsoft YaHei", Arial, sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(item[1], x + 266, y + 6)
      ctx.textAlign = 'left'
    })

    ctx.fillStyle = '#94a3b8'
    ctx.font = '800 20px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('Elo + xG + 状态权重 + 观点复核 · 模型研究参考', 112, posterFooterY)
    ctx.fillStyle = '#64748b'
    ctx.font = '800 21px "Microsoft YaHei", Arial, sans-serif'
    ctx.fillText('免责声明：仅作赛前分析参考，不构成赛果保证；临场阵容、红牌、伤停、天气和裁判尺度会显著改变结果。', 112, posterFooterY + 38)

    const fileName = `wc2026-match-prediction-${selectedMatch.home_team}-vs-${selectedMatch.away_team}.png`
    if (fallbackWindow && !fallbackWindow.closed) {
      const dataUrl = canvas.toDataURL('image/png')
      fallbackWindow.document.open()
      fallbackWindow.document.write(`<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${fileName}</title>
    <style>
      body { margin: 0; padding: 16px; background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; text-align: center; }
      img { width: 100%; max-width: 960px; height: auto; border-radius: 18px; box-shadow: 0 18px 60px rgba(0,0,0,.35); }
      a { display: inline-flex; margin: 16px auto 18px; padding: 12px 18px; border-radius: 999px; background: #2563eb; color: white; font-weight: 800; text-decoration: none; }
      p { color: #cbd5e1; }
    </style>
  </head>
  <body>
    <a href="${dataUrl}" download="${fileName}">下载图片</a>
    <p>手机端可长按下方图片保存，或点击上方按钮下载。</p>
    <img src="${dataUrl}" alt="世界杯预测结果" />
  </body>
</html>`)
      fallbackWindow.document.close()
      setDownloadStatus('图片已生成，请在新页面长按保存')
      return
    }

    if (isMobileLike) {
      window.location.href = canvas.toDataURL('image/png')
      setDownloadStatus('已打开图片页面，可长按保存')
      return
    }

    const blob = await new Promise<Blob | null>(resolve => {
      let settled = false
      const settle = (value: Blob | null) => {
        if (settled) return
        settled = true
        resolve(value)
      }

      canvas.toBlob(settle, 'image/png')
      window.setTimeout(async () => {
        if (settled) return
        try {
          const response = await fetch(canvas.toDataURL('image/png'))
          settle(await response.blob())
        } catch {
          settle(null)
        }
      }, 1200)
    })
    if (!blob) {
      setDownloadStatus('图片生成失败，请重试')
      fallbackWindow?.close()
      return
    }

    const file = new File([blob], fileName, { type: 'image/png' })
    const url = URL.createObjectURL(blob)
    const canShareFiles =
      typeof navigator !== 'undefined' &&
      typeof navigator.canShare === 'function' &&
      typeof navigator.share === 'function' &&
      navigator.canShare({ files: [file] })

    if (isMobileLike && canShareFiles) {
      try {
        await navigator.share({
          files: [file],
          title: '世界杯预测海报',
        })
        setDownloadStatus('已打开系统分享，可保存图片')
        fallbackWindow?.close()
        window.setTimeout(() => URL.revokeObjectURL(url), 30000)
        return
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          setDownloadStatus('已取消分享，已切换到图片保存页')
        }
      }
    }

    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    link.target = '_blank'
    link.rel = 'noopener'
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    setDownloadStatus('图片已生成，若未自动下载请检查浏览器下载权限')
    window.setTimeout(() => {
      URL.revokeObjectURL(url)
      link.remove()
    }, 30000)
  }, [getTeamInfo, loading, prediction, predictionMatchId, selectedInjuryFeed, selectedMatch])

  // 切换比赛或模型时自动预测
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void runPrediction()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [runPrediction])

  // 上一场/下一场导航
  const currentIndex = filteredMatches.findIndex(m => m.id === effectiveSelectedMatchId)
  const goPrev = () => {
    if (currentIndex > 0) selectMatch(filteredMatches[currentIndex - 1].id)
  }
  const goNext = () => {
    if (currentIndex < filteredMatches.length - 1) selectMatch(filteredMatches[currentIndex + 1].id)
  }

  const homeInfo = selectedMatch ? getTeamInfo(selectedMatch.home_team) : null
  const awayInfo = selectedMatch ? getTeamInfo(selectedMatch.away_team) : null
  const hasActualScore = selectedMatch?.status === 'completed'
    && selectedMatch.home_score !== undefined
    && selectedMatch.away_score !== undefined
  const scoreDisplay = hasActualScore
    ? `${selectedMatch?.home_score}-${selectedMatch?.away_score}`
    : prediction?.predicted_score
  const scoreLabel = hasActualScore ? '真实比分' : '预测比分'
  const primaryScoreProbability = getPrimaryScoreProbability(prediction)
  const halfTimeScore = estimateHalfTimeScore(prediction)
  const scorePickRows = getScorePickRows(prediction)
  const fallbackAlternativeScores = prediction?.possible_scores?.slice(1, 3) || []
  const alternativeScores = scorePickRows.slice(1).length > 0
    ? scorePickRows.slice(1)
    : fallbackAlternativeScores.map(score => ({
      label: '备选',
      score: score.score,
      probability: score.probability,
    }))
  const marketCalibration = prediction?.market_calibration
  const marketOdds = prediction?.market_odds
  const publicDataSources = prediction?.public_data_sources || []
  const upsetPrediction = prediction?.upset_prediction
  const setPieceCardPrediction = prediction?.set_piece_card_prediction
  const skillAudit = prediction?.skill_audit
  const skillBrief = skillAudit?.single_match_brief
  const skillScorePool = skillAudit?.score_pool_top3 || []
  const skillSecondaryScores = skillAudit?.secondary_scores || []
  const skillRiskFlags = skillAudit?.risk_flags || []
  const skillMacroTakeaways = skillAudit?.macro_takeaways || []
  const skillGroupNotes = skillAudit?.group_motivation?.notes || []
  const knockoutDecision = prediction?.knockout_decision
  const isKnockoutPrediction = Boolean(selectedEffectiveStage || prediction?.is_knockout)
  const extraTimeProbability = prediction?.extra_time_probability
    ?? knockoutDecision?.regular_time_draw_probability
    ?? knockoutDecision?.extra_time_probability
    ?? null
  const extraTimeDecisiveProbability = prediction?.extra_time_decisive_probability
    ?? knockoutDecision?.extra_time_decisive_probability
    ?? null
  const penaltyDecisionProbability = prediction?.penalty_probability
    ?? knockoutDecision?.penalty_probability
    ?? null
  const knockoutProbabilityText = (value?: number | null, digits = 1) =>
    typeof value === 'number' && !Number.isNaN(value) ? `${(value * 100).toFixed(digits)}%` : '-'
  const teamFeatureAdjustment = prediction?.team_feature_adjustment
  const teamFeatureProfiles = teamFeatureAdjustment?.team_profiles
  const teamFeatureReasons = teamFeatureAdjustment?.reasons || []
  const teamFeatureNotes = [
    ...(teamFeatureProfiles?.home?.next_prediction_notes || []),
    ...(teamFeatureProfiles?.away?.next_prediction_notes || []),
  ]
  const teamFeatureTags = Array.from(new Set([
    ...(teamFeatureProfiles?.home?.tactical_tags || []),
    ...(teamFeatureProfiles?.away?.tactical_tags || []),
  ])).slice(0, 5)
  const marketStatusLabel: Record<string, string> = {
    connected: '已接入',
    aligned: '市场接近',
    disabled: '已关闭',
    not_configured: '待配置赔率源',
    no_match: '未匹配',
    no_markets: '无市场信号',
    error: '连接异常',
    unsupported_provider: '数据源不支持',
    historical_prior: '历史样本参考',
  }
  const marketStatusKey = marketOdds?.status === 'historical_prior'
    ? 'historical_prior'
    : marketCalibration?.level || marketOdds?.status || ''
  const marketStatusText = marketStatusLabel[marketStatusKey] || marketCalibration?.level || marketOdds?.status || '未知'
  const marketCalibrationBadge = marketCalibration?.applied
    ? `已按 ${(marketCalibration.weight * 100).toFixed(0)}% 校准`
    : marketStatusText
  const marketSourceLabel = marketOdds?.source === 'the_odds_api'
    ? 'The Odds API 实时赔率'
    : marketOdds?.source === 'football_data_historical_prior' || marketOdds?.source === 'fallback'
      ? 'Football-Data 历史赔率样本'
      : marketOdds?.source || '待配置赔率源'
  const publicSourceStatusLabel: Record<string, string> = {
    connected: '已接入',
    configured: '已配置',
    standby: '备用',
    reference: '公开参考',
    historical_prior: '历史参考',
    not_configured: '待配置',
    no_match: '未匹配',
    no_markets: '无盘口',
    disabled: '已关闭',
    unsupported_provider: '不支持',
    error: '异常',
  }
  const publicSourceStatusClass = (status: string) => {
    if (status === 'connected' || status === 'configured') return 'border-emerald-100 bg-emerald-50 text-emerald-700'
    if (status === 'reference' || status === 'standby' || status === 'historical_prior') return 'border-blue-100 bg-blue-50 text-blue-700'
    if (status === 'not_configured' || status === 'no_match' || status === 'no_markets') return 'border-amber-100 bg-amber-50 text-amber-700'
    if (status === 'disabled' || status === 'unsupported_provider' || status === 'error') return 'border-red-100 bg-red-50 text-red-700'
    return 'border-slate-100 bg-slate-50 text-slate-600'
  }
  const totalGoals = prediction?.total_goals_prediction
  const totalGoalsMainProbability = totalGoals
    ? totalGoals.side_probability || Math.max(totalGoals.over_probability, totalGoals.under_probability)
    : 0
  const totalGoalsSignalStrength = totalGoals
    ? totalGoals.signal_strength ?? totalGoals.confidence
    : 0
  const totalGoalsRecommendationParts = totalGoals?.recommendation
    .split('/')
    .map(part => part.trim())
    .filter(Boolean) || []
  const totalGoalsPrimaryRecommendation = totalGoalsRecommendationParts[0] || totalGoals?.recommendation || '-'
  const totalGoalsProtectionRecommendation = totalGoalsRecommendationParts[1] || ''
  const publicSourceRows = publicDataSources.length
    ? publicDataSources
    : [{
        id: 'local_model_baseline',
        label: '本地模型基线',
        status: 'reference',
        role: 'Elo/xG/球队特征库',
        scope: '后端暂不可用时使用本地兜底预测',
        message: '等待后端返回公开源状态。',
      }]
  const publicSourceGaps = skillAudit?.missing_information || []
  const upsetRiskLabel = upsetPrediction?.risk_level === 'high'
    ? '高冷风险'
    : upsetPrediction?.risk_level === 'medium'
      ? '中等冷门'
      : '低冷风险'
  const upsetRiskClass = upsetPrediction?.risk_level === 'high'
    ? 'bg-red-50 text-red-700 border-red-100'
    : upsetPrediction?.risk_level === 'medium'
      ? 'bg-amber-50 text-amber-700 border-amber-100'
      : 'bg-slate-50 text-slate-600 border-slate-100'
  const matchStatusLabel = hasActualScore
    ? '已结束'
    : selectedMatch?.status === 'live'
      ? '进行中'
      : '未开赛'

  const groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
  const rounds = [
    { value: 0, label: '全部轮次' },
    { value: 1, label: '第1轮' },
    { value: 2, label: '第2轮' },
    { value: 3, label: '第3轮' },
  ]

  const modelOptions: { key: ModelType; label: string; desc: string; speed: string }[] = [
    { key: 'baseline', label: 'Baseline', desc: '基础Elo评分 + 主场优势', speed: '⚡ 快速' },
    { key: 'form_weighted', label: 'Form Weighted', desc: 'Elo + 状态 + 事实因子（推荐）', speed: '🔄 标准' },
    { key: 'monte_carlo', label: 'Monte Carlo', desc: '稳定概率矩阵，不再随机漂移', speed: '🎯 稳定' },
  ]

  const weatherOverrideOptions: { key: WeatherCode | 'auto'; label: string; icon: typeof CloudRain }[] = [
    { key: 'auto', label: '自动', icon: CloudRain },
    { key: 'rain', label: '雨天', icon: CloudRain },
    { key: 'hot', label: '高温', icon: Thermometer },
    { key: 'wind', label: '大风', icon: Wind },
  ]

  // 主场优势徽章颜色
  const getAdvantageBadgeStyle = (level: AdvantageLevel) => {
    if (level === 'full') return 'bg-amber-100 text-amber-800 border-amber-200'
    if (level === 'half') return 'bg-blue-100 text-blue-800 border-blue-200'
    return 'bg-gray-100 text-gray-600 border-gray-200'
  }

  const getAdvantageEmoji = (level: AdvantageLevel) => {
    if (level === 'full') return '🏠'
    if (level === 'half') return '🌎'
    return '⚖️'
  }

  // 按日期分组显示比赛
  const matchesByDate = useMemo(() => {
    const groups: Record<string, typeof filteredMatches> = {}
    filteredMatches.forEach(m => {
      const key = getScheduleDateLabel(m.match_date)
      if (!groups[key]) groups[key] = []
      groups[key].push(m)
    })
    return groups
  }, [filteredMatches])
  const scheduleDateEntries = Object.entries(matchesByDate)
  const activeScheduleDate = selectedMatch ? getScheduleDateLabel(selectedMatch.match_date) : scheduleDateEntries[0]?.[0]
  const activeDateMatches = activeScheduleDate ? matchesByDate[activeScheduleDate] || [] : []
  const activeScheduleDayKey = activeDateMatches[0] ? getScheduleDayKey(activeDateMatches[0].match_date) : undefined

  return (
    <div className="w-full max-w-full min-w-0 overflow-x-hidden space-y-3">
      {/* 标题 */}
      <div className="text-center">
        <h1 className="text-xl sm:text-2xl font-black text-gray-900 font-display tracking-wide">AI模型预测</h1>
        <p className="mx-auto mt-1 max-w-2xl px-2 text-xs leading-5 text-gray-500 sm:text-sm">基于真实赛程 · 美加墨世界杯AI预测模型 26.5 · 稳定概率矩阵 · 市场信号校准与智能事实因子</p>
      </div>

      {/* 近期赛程列表 */}
      <div className="glass-card overflow-hidden p-2.5 sm:p-3">
        <div className="mb-2 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-600" />
            选择比赛
            <span className="text-xs font-normal text-gray-400">
              {timeFilter === '3d' ? '近3日' : timeFilter === '7d' ? '近7日' : '全部'} · {filteredMatches.length}场
            </span>
          </h3>
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { key: '3d' as TimeFilter, label: '3日' },
              { key: '7d' as TimeFilter, label: '7日' },
              { key: 'all' as TimeFilter, label: '全部' },
            ].map(opt => (
              <button
                key={opt.key}
                onClick={() => { setTimeFilter(opt.key); setFilterGroup(''); setFilterRound(0) }}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition-all ${
                  timeFilter === opt.key
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'border border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setShowScheduleTools(value => !value)}
              className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-50"
            >
              筛选
              {showScheduleTools ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            <DailyPredictionsExport matches={matches} loading={matchesLoading}
              targetDayKey={activeScheduleDayKey}
              maxMatches={activeDateMatches.length}
            />
          </div>
        </div>

        {showScheduleTools && (
          <div className="mb-3 rounded-xl border border-gray-100 bg-white/70 p-2">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {rounds.map(r => (
                <button
                  key={r.value}
                  onClick={() => setFilterRound(r.value)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                    filterRound === r.value
                      ? 'bg-indigo-600 text-white'
                      : 'border border-gray-200 bg-white text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {r.label.replace('全部轮次', '全部')}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {groups.map(g => (
                <button
                  key={g}
                  onClick={() => setFilterGroup(filterGroup === g ? '' : g)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
                    filterGroup === g
                      ? 'bg-blue-600 text-white'
                      : 'border border-gray-200 bg-white text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
        )}

        {filteredMatches.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <Calendar className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p>{matchesLoading ? '正在同步实时赛程...' : matchesError || '近期暂无赛程安排'}</p>
            <button
              onClick={() => setTimeFilter('all')}
              className="text-blue-500 text-sm mt-2 hover:underline"
            >
              查看全部赛程 →
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex gap-1.5 overflow-x-auto pb-1">
              {scheduleDateEntries.map(([dateLabel, matches]) => {
                const isActive = dateLabel === activeScheduleDate
                return (
                  <button
                    key={dateLabel}
                    type="button"
                    onClick={() => matches[0] && selectMatch(matches[0].id)}
                    className={`flex min-w-[5.9rem] items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left transition-all ${
                      isActive
                        ? 'border-blue-300 bg-blue-600 text-white shadow-md shadow-blue-500/20'
                        : 'border-white/70 bg-white/80 text-gray-700 hover:bg-white'
                    }`}
                  >
                    <span className="text-sm font-black">{dateLabel}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'}`}>{matches.length}场</span>
                  </button>
                )
              })}
            </div>

            <div className="flex gap-2 overflow-x-auto pb-1">
              {activeDateMatches.map(match => {
                const home = getTeamInfo(match.home_team)
                const away = getTeamInfo(match.away_team)
                const isSelected = match.id === effectiveSelectedMatchId
                const matchAdv = detectVenueAdvantage(match)
                const matchEffectiveStage = getEffectiveMatchStage(match)
                const matchCompleted = match.status === 'completed' && match.home_score !== undefined && match.away_score !== undefined
                return (
                  <div
                    key={match.id}
                    data-testid="match-selector-card"
                    role="button"
                    tabIndex={0}
                    onClick={() => selectMatch(match.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        selectMatch(match.id)
                      }
                    }}
                    className={`relative min-w-[12.5rem] rounded-2xl border p-2.5 text-left transition-all sm:min-w-[14rem] ${
                      isSelected
                        ? 'border-blue-400 bg-blue-50/95 shadow-md shadow-blue-500/15'
                        : 'border-white/70 bg-white/80 hover:border-blue-200 hover:bg-white'
                    }`}
                  >
                    {matchAdv.level !== 'none' && (
                      <div className="absolute right-2 top-2 text-xs">{getAdvantageEmoji(matchAdv.level)}</div>
                    )}
                    <div className="mb-2 flex items-center gap-1.5 pr-5 text-[11px] font-bold text-gray-500">
                      <span className="rounded-md bg-blue-50 px-1.5 py-0.5 text-blue-700">{matchEffectiveStage ? getStageNameCN(matchEffectiveStage) : `${match.group}组`}</span>
                      <span>{matchEffectiveStage ? '淘汰赛' : `第${match.round}轮`}</span>
                      <span className="ml-auto">{getMatchTimeLabel(match.match_date)}</span>
                    </div>
                    <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-1.5 text-center">
                      <div className="min-w-0">
                        <TeamFlag teamName={match.home_team} flagCode={home?.flagCode} size="sm" />
                        <div className="mt-1 truncate text-xs font-black text-gray-900">{match.home_team}</div>
                      </div>
                      <div className="text-[11px] font-black text-gray-400">
                        {matchCompleted ? `${match.home_score}-${match.away_score}` : 'VS'}
                      </div>
                      <div className="min-w-0">
                        <TeamFlag teamName={match.away_team} flagCode={away?.flagCode} size="sm" />
                        <div className="mt-1 truncate text-xs font-black text-gray-900">{match.away_team}</div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {selectedMatch && (
          <div className="mt-3 border-t border-white/70 pt-3">
            <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-stretch gap-2">
              <button
                onClick={goPrev}
                disabled={currentIndex <= 0}
                className="flex h-12 w-11 flex-shrink-0 self-center items-center justify-center rounded-2xl bg-white/80 text-gray-700 shadow-sm transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-30"
                aria-label="上一场比赛"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>

              <div className="min-w-0 rounded-2xl border border-white/70 bg-white/80 p-3 shadow-sm sm:p-3.5">
                <div className="mb-2 flex flex-col gap-1.5 text-center sm:flex-row sm:items-center sm:justify-center sm:gap-2">
                  <div className="flex flex-wrap items-center justify-center gap-1.5">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-black ${hasActualScore ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                      {matchStatusLabel}
                    </span>
                    {selectedEffectiveStage ? (
                      <span className="rounded-full bg-orange-100 px-2.5 py-1 text-[11px] font-bold text-orange-700">{getStageNameCN(selectedEffectiveStage)}</span>
                    ) : (
                      <>
                        <span className="rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-bold text-blue-700">{selectedMatch.group}组</span>
                        <span className="rounded-full bg-green-100 px-2.5 py-1 text-[11px] font-bold text-green-700">第{selectedMatch.round}轮</span>
                      </>
                    )}
                  </div>
                  <div className="flex min-w-0 flex-wrap items-center justify-center gap-1 text-xs font-semibold text-gray-500">
                    <Clock className="h-3.5 w-3.5" />
                    {formatMatchDate(selectedMatch.match_date)}
                    <span className="mx-1">·</span>
                    <MapPin className="h-3.5 w-3.5" />
                    <span className="max-w-[14rem] truncate sm:max-w-[28rem]">{selectedMatch.venue}</span>
                  </div>
                </div>

                <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2 sm:gap-4">
                  <div className="min-w-0 text-center">
                    <div className="mb-1" data-testid="match-detail-home-team-link"><TeamFlagLink teamName={selectedMatch.home_team} flagCode={homeInfo?.flagCode} size="md" /></div>
                    <h2 className="truncate text-base font-black text-gray-900 sm:text-xl">{selectedMatch.home_team}</h2>
                    <div className="mt-1 text-[11px] font-semibold text-gray-500 sm:text-xs">
                      FIFA #{homeInfo?.fifa_rank} · Elo {homeInfo?.elo_rating}
                    </div>
                    {homeInfo?.is_host && <span className="mt-1 inline-block rounded-full bg-yellow-100 px-2 py-0.5 text-[11px] font-bold text-yellow-700">东道主</span>}
                  </div>

                  <div className="min-w-[88px] text-center sm:min-w-[140px]">
                    <div className="text-xl font-black text-gray-300 sm:text-3xl">VS</div>
                    <div className={`mx-auto mt-1 inline-flex max-w-[128px] items-center gap-1 truncate rounded-full border px-2 py-1 text-[11px] font-bold sm:max-w-none ${getAdvantageBadgeStyle(venueAdvantage?.level || 'none')}`}>
                      {getAdvantageEmoji(venueAdvantage?.level || 'none')}
                      <span className="truncate">{venueAdvantage?.reason || '中立场地'}</span>
                    </div>
                    <div className="mt-1.5 text-[11px] font-black tracking-wide text-gray-500">{scoreLabel}</div>
                    {scoreDisplay ? (
                      <>
                        <div className={`mt-0.5 text-2xl font-black sm:text-3xl ${hasActualScore ? 'text-emerald-600' : 'text-blue-600'}`}>{scoreDisplay}</div>
                        {!hasActualScore && typeof primaryScoreProbability === 'number' && (
                          <div className="mt-0.5 text-[11px] font-black text-blue-600">
                            首选概率 {formatScoreProbability(primaryScoreProbability)}
                          </div>
                        )}
                        {!hasActualScore && halfTimeScore && (
                          <div className="mt-0.5 text-[11px] font-black text-slate-500">
                            半场预测 {halfTimeScore}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="mt-1 text-xs font-bold text-gray-500">等待生成</div>
                    )}
                  </div>

                  <div className="min-w-0 text-center">
                    <div className="mb-1" data-testid="match-detail-away-team-link"><TeamFlagLink teamName={selectedMatch.away_team} flagCode={awayInfo?.flagCode} size="md" /></div>
                    <h2 className="truncate text-base font-black text-gray-900 sm:text-xl">{selectedMatch.away_team}</h2>
                    <div className="mt-1 text-[11px] font-semibold text-gray-500 sm:text-xs">
                      FIFA #{awayInfo?.fifa_rank} · Elo {awayInfo?.elo_rating}
                    </div>
                    {awayInfo?.is_host && <span className="mt-1 inline-block rounded-full bg-yellow-100 px-2 py-0.5 text-[11px] font-bold text-yellow-700">东道主</span>}
                  </div>
                </div>

                {alternativeScores.length > 0 && !hasActualScore && (
                  <div className="mt-2 text-center text-xs font-semibold text-gray-500">
                    其他可能：{alternativeScores.map((s, i) => (
                      <span key={i}>
                        {i > 0 && ' · '}
                        {s.score} ({formatScoreProbability(s.probability)})
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <button
                onClick={goNext}
                disabled={currentIndex >= filteredMatches.length - 1}
                className="flex h-12 w-11 flex-shrink-0 self-center items-center justify-center rounded-2xl bg-white/80 text-gray-700 shadow-sm transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-30"
                aria-label="下一场比赛"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 当前比赛预测 - 主区域 */}
      {selectedMatch && (
        <div className="space-y-4">
          {/* 战术与首发预测 */}
          {prediction && (prediction.tactical_analysis || prediction.lineup_prediction) && (
            <div className="glass-card overflow-hidden">
              <button
                type="button"
                onClick={() => setShowLineupSection(value => !value)}
                className="flex w-full items-center justify-between gap-3 border-b bg-gray-50/80 p-4 text-left"
              >
                <div>
                  <h3 className="flex items-center gap-2 text-base font-black text-gray-900">
                    <Target className="h-5 w-5 text-blue-600" />
                    战术与首发预测
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">赛事信息补充模块，默认收起，展开查看双方常用战术和预测首发</p>
                </div>
                {showLineupSection ? <ChevronUp className="h-5 w-5 text-gray-500" /> : <ChevronDown className="h-5 w-5 text-gray-500" />}
              </button>
              {showLineupSection && (
                <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
                  {prediction.tactical_matchup && (
                    <div className="rounded-xl border border-indigo-100 bg-indigo-50/70 p-4 lg:col-span-2">
                      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <h4 className="flex items-center gap-2 text-sm font-black text-indigo-900">
                          <BarChart3 className="h-4 w-4 text-indigo-600" />
                          阵型相克因子
                        </h4>
                        <div className="flex flex-wrap gap-2 text-xs font-bold">
                          <span className="rounded-full bg-white px-2.5 py-1 text-indigo-700">{prediction.tactical_matchup.home_formation} × {prediction.tactical_matchup.away_formation}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-blue-700">主队xG {prediction.tactical_matchup.home_xg_multiplier}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-red-700">客队xG {prediction.tactical_matchup.away_xg_multiplier}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-slate-700">节奏 {prediction.tactical_matchup.tempo_multiplier}</span>
                        </div>
                      </div>
                      <div className="grid gap-2 md:grid-cols-3">
                        {prediction.tactical_matchup.notes.map(note => (
                          <p key={note} className="rounded-lg bg-white/80 px-3 py-2 text-xs leading-5 text-indigo-800">{note}</p>
                        ))}
                      </div>
                    </div>
                  )}
                  {[selectedMatch.home_team, selectedMatch.away_team].map(teamName => {
                    const tactic = prediction.tactical_analysis?.find(item => item.team === teamName)
                    const lineup = prediction.lineup_prediction?.find(item => item.team === teamName)
                    if (!tactic && !lineup) return null
                    return (
                      <div key={teamName} className="overflow-hidden rounded-xl border border-gray-100 bg-white/80">
                        <div className="border-b bg-gray-50/80 p-4">
                          <h3 className="flex items-center gap-2 text-lg font-bold text-gray-900">
                            <TeamFlag teamName={teamName} size="md" />
                            {teamName} 战术与首发
                          </h3>
                          <p className="mt-1 text-xs text-gray-400">
                            {lineup?.formation || tactic?.formation} · {lineup?.note || '模型预测'}
                          </p>
                        </div>
                        <div className="space-y-4 p-4">
                          {tactic && (
                            <div className="grid grid-cols-1 gap-2 text-sm">
                              <div><span className="font-semibold text-gray-800">常用打法：</span><span className="text-gray-600">{tactic.style}</span></div>
                              <div><span className="font-semibold text-gray-800">进攻路径：</span><span className="text-gray-600">{tactic.attacking_pattern}</span></div>
                              <div><span className="font-semibold text-gray-800">防守结构：</span><span className="text-gray-600">{tactic.defensive_shape}</span></div>
                              <div><span className="font-semibold text-gray-800">定位球：</span><span className="text-gray-600">{tactic.set_piece}</span></div>
                              <div><span className="font-semibold text-gray-800">风险点：</span><span className="text-gray-600">{tactic.risk}</span></div>
                            </div>
                          )}
                          {lineup && (
                            <div>
                              <div className="mb-3 rounded-lg border border-amber-100 bg-amber-50/80 p-3 text-xs leading-5 text-amber-800">
                                <div className="mb-1 flex items-center gap-1.5 font-black">
                                  <ShieldAlert className="h-4 w-4" />
                                  红黄牌/停赛可用性
                                </div>
                                <p>{lineup.discipline_note || '暂无官方实时红黄牌数据，当前不做牌面修正'}</p>
                                {(lineup.suspended_players?.length || 0) > 0 && (
                                  <p className="mt-1 font-bold text-red-600">停赛：{lineup.suspended_players?.join('、')}</p>
                                )}
                                {(lineup.card_risk_players?.length || 0) > 0 && (
                                  <p className="mt-1 font-bold text-amber-700">黄牌风险：{lineup.card_risk_players?.join('、')}</p>
                                )}
                              </div>
                              <div className="mb-2 flex items-center justify-between">
                                <span className="text-sm font-bold text-gray-900">预测首发</span>
                                <span className="text-xs text-gray-400">可信度 {(lineup.confidence * 100).toFixed(0)}%</span>
                              </div>
                              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                                {lineup.starters.map((player, index) => (
                                  <div key={`${teamName}-${player}-${index}`} className="truncate rounded-lg bg-blue-50 px-2 py-1.5 text-xs font-semibold text-blue-800">
                                    {player}
                                  </div>
                                ))}
                              </div>
                              <p className="mt-2 text-xs text-gray-400">
                                替补变量：{lineup.bench_options.join('、')}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          <div className="glass-card p-3 sm:p-4">
            <div className="mb-3 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-blue-600">预测操作</p>
                <p className="mt-0.5 text-sm text-gray-500">
                  {prediction ? `当前预测 ${selectedMatch.home_team} ${prediction.predicted_score} ${selectedMatch.away_team}` : '先确认事实场景与模型，然后开始预测'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.25fr_0.75fr]">
              <section className="rounded-xl border border-blue-100 bg-blue-50/35 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Target className="h-4 w-4 text-orange-500" />
                  <h3 className="text-sm font-black text-gray-900">场景设置</h3>
                </div>
                <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
                  <div className={`rounded-lg border p-2.5 ${getAdvantageBadgeStyle(venueAdvantage?.level || 'none')}`}>
                    <div className="flex items-center gap-1.5 text-sm font-bold">
                      <Home className="h-4 w-4" />
                      主场优势
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs opacity-80">{venueAdvantage?.detail || '比赛在第三方场地进行'}</p>
                  </div>

                  <div className="rounded-lg border border-blue-100 bg-white/80 p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-1.5 text-sm font-bold text-blue-900">
                        <CloudRain className="h-4 w-4 text-blue-600" />
                        <span>天气/场地</span>
                      </div>
                      <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-bold text-blue-700">
                        {scenarioSettings.weatherOverride === 'auto' ? autoWeather?.label || '自动' : getWeatherLabel(effectiveWeather)}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-blue-700/80">
                      {autoWeather?.detail || '正在读取场馆天气画像'}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {weatherOverrideOptions.map(opt => (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => setScenarioSettings({ ...scenarioSettings, weatherOverride: opt.key })}
                        className={`inline-flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-bold transition-all ${
                          scenarioSettings.weatherOverride === opt.key
                            ? 'border-blue-500 bg-blue-600 text-white shadow-sm'
                            : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        <opt.icon className="h-3.5 w-3.5" />
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className={`mt-3 rounded-lg border px-3 py-2 ${getInjuryStatusStyle(selectedInjuryFeed)}`}>
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2 text-xs font-black">
                      <ShieldAlert className="h-4 w-4" />
                      <span>伤停数据：{getInjuryStatusLabel(selectedInjuryFeed)}</span>
                    </div>
                    <span className="text-[11px] font-bold opacity-80">
                      更新：{formatInjuryUpdatedAt(selectedInjuryFeed?.last_updated)}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-4 opacity-80">
                    {selectedInjuryFeed?.message || '正在读取公开伤停源；无可信源时不会自动计入模型'}
                  </p>
                </div>

                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {[
                    { key: 'forceNeutral' as BooleanScenarioKey, title: '强制中立', desc: '忽略自动检测的主场/半主场优势', visible: venueAdvantage?.level !== 'none', dashed: true },
                    { key: 'highPress' as BooleanScenarioKey, title: '高强度逼抢', desc: '比赛节奏和总xG上调', visible: true },
                    {
                      key: 'homeKeyAbsence' as BooleanScenarioKey,
                      title: '主队关键伤停',
                      desc: `${selectedMatch.home_team}：${formatInjuryTeamSummary(selectedInjuryFeed?.teams.home)}`,
                      visible: true,
                    },
                    {
                      key: 'awayKeyAbsence' as BooleanScenarioKey,
                      title: '客队关键伤停',
                      desc: `${selectedMatch.away_team}：${formatInjuryTeamSummary(selectedInjuryFeed?.teams.away)}`,
                      visible: true,
                    },
                    { key: 'homeFatigue' as BooleanScenarioKey, title: '主队体能负荷', desc: `${selectedMatch.home_team} 短休/连续作战`, visible: true },
                    { key: 'awayFatigue' as BooleanScenarioKey, title: '客队体能负荷', desc: `${selectedMatch.away_team} 短休/连续作战`, visible: true },
                  ].filter(item => item.visible).map(item => (
                    <label
                      key={item.key}
                      title={item.desc}
                      className={`flex min-h-[4.35rem] items-center justify-between gap-3 rounded-lg border bg-white/72 px-3 py-2.5 text-left transition-colors hover:bg-white/90 ${
                        item.dashed ? 'border-dashed border-gray-200' : 'border-gray-100'
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="block text-sm font-black leading-5 text-gray-800">{item.title}</span>
                        <span className="mt-0.5 block text-[11px] font-semibold leading-4 text-gray-500">{item.desc}</span>
                      </span>
                      <input
                        type="checkbox"
                        checked={Boolean(scenarioSettings[item.key])}
                        onChange={e => setScenarioSettings({ ...scenarioSettings, [item.key]: e.target.checked })}
                        className="h-4 w-4 shrink-0 rounded text-blue-600"
                      />
                    </label>
                  ))}
                </div>
              </section>

              <section className="rounded-xl border border-gray-100 bg-white/70 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  <h3 className="text-sm font-black text-gray-900">模型选择</h3>
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
                  {modelOptions.map(m => (
                    <label
                      key={m.key}
                      className={`flex cursor-pointer items-center justify-between gap-2 rounded-lg border px-3 py-2.5 transition-all ${
                        modelType === m.key ? 'border-blue-400 bg-blue-50' : 'border-gray-100 bg-white hover:bg-gray-50'
                      }`}
                    >
                      <div className="min-w-0">
                        <span className="block truncate text-sm font-black text-gray-800">{m.label}</span>
                        <p className="truncate text-xs text-gray-400">{m.desc}</p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="text-xs text-gray-400">{m.speed}</span>
                        <input
                          type="radio"
                          name="model"
                          value={m.key}
                          checked={modelType === m.key}
                          onChange={() => setModelType(m.key)}
                          className="h-4 w-4 text-blue-600"
                        />
                      </div>
                    </label>
                  ))}
                </div>
              </section>
            </div>

            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
              <button
                onClick={runPrediction}
                disabled={loading || !selectedInjuryFeed || selectedFixturePending}
                className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-blue-200 transition-all hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50"
              >
                {selectedFixturePending ? '等待对阵确认' : loading ? '分析中...' : '开始预测'}
              </button>
              <button
                type="button"
                onClick={downloadPredictionImage}
                disabled={!prediction || loading || !selectedInjuryFeed || predictionMatchId !== selectedMatch.id}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-bold text-blue-700 transition-colors hover:bg-blue-100 disabled:opacity-40"
              >
                <Download className="h-4 w-4" />
                下载图片
              </button>
              <button
                type="button"
                onClick={() => setShowModelGuide(true)}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-bold text-gray-700 transition-colors hover:bg-gray-50"
              >
                <FileText className="h-4 w-4" />
                模型说明
              </button>
            </div>
            {downloadStatus && (
              <p className="mt-3 text-center text-xs font-semibold text-blue-700 sm:text-right">
                {downloadStatus}
              </p>
            )}
            {selectedFixturePending && (
              <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold leading-5 text-amber-800">
                这场淘汰赛还只是官方席位占位，真实对阵确认前只展示赛程，不参与单场预测和预测海报下载。
              </p>
            )}
          </div>

          {/* 预测结果 */}
          {prediction && (
            <div className="space-y-6">
              {/* 概率卡片 */}
              <div className="glass-card p-5 sm:p-8">
                <div className="mb-5 text-center">
                  <h3 className="text-lg font-bold text-gray-900">预测结果</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    模型: {prediction.model_type === 'baseline' ? '基础Elo' : prediction.model_type === 'monte_carlo' ? '蒙特卡洛' : '状态加权'} · 预测比分: <span className="font-bold text-blue-600">{prediction.predicted_score}</span>
                  </p>
                </div>

                {/* 概率条 */}
                {!hasActualScore && (typeof primaryScoreProbability === 'number' || halfTimeScore) && (
                  <div className="mb-5 flex flex-wrap items-center justify-center gap-2 text-center">
                    {typeof primaryScoreProbability === 'number' && (
                      <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">
                        首选比分概率 {formatScoreProbability(primaryScoreProbability)}
                      </span>
                    )}
                    {halfTimeScore && (
                      <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-black text-white">
                        半场预测 {halfTimeScore}
                      </span>
                    )}
                  </div>
                )}

                <div className="mb-8 grid grid-cols-1 gap-4 sm:flex sm:items-center">
                  <div className="text-center sm:flex-1 sm:text-right">
                    <p className="text-sm text-gray-500">{selectedMatch.home_team}</p>
                    <p className="text-3xl font-black text-blue-600">{(prediction.home_win_probability * 100).toFixed(1)}%</p>
                  </div>
                  <div className="relative mx-auto flex h-32 w-32 items-center justify-center">
                    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                      <circle cx="50" cy="50" r="40" fill="none" stroke="#3b82f6" strokeWidth="8" strokeDasharray={`${prediction.home_win_probability * 251.3} 251.3`} strokeLinecap="round" />
                      {!isKnockoutPrediction && (
                        <circle cx="50" cy="50" r="40" fill="none" stroke="#6b7280" strokeWidth="8" strokeDasharray={`${prediction.draw_probability * 251.3} 251.3`} strokeDashoffset={`-${prediction.home_win_probability * 251.3}`} strokeLinecap="round" />
                      )}
                      <circle cx="50" cy="50" r="40" fill="none" stroke="#ef4444" strokeWidth="8" strokeDasharray={`${prediction.away_win_probability * 251.3} 251.3`} strokeDashoffset={isKnockoutPrediction ? `-${prediction.home_win_probability * 251.3}` : `-${(prediction.home_win_probability + prediction.draw_probability) * 251.3}`} strokeLinecap="round" />
                    </svg>
                    <div className="absolute text-center">
                      {isKnockoutPrediction ? (
                        <>
                          <p className="text-xs text-gray-400">90分钟平局</p>
                          <p className="text-lg font-bold">{knockoutProbabilityText(extraTimeProbability, 0)}</p>
                        </>
                      ) : (
                        <>
                          <p className="text-xs text-gray-400">平局</p>
                          <p className="text-lg font-bold">{(prediction.draw_probability * 100).toFixed(1)}%</p>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="text-center sm:flex-1 sm:text-left">
                    <p className="text-sm text-gray-500">{selectedMatch.away_team}</p>
                    <p className="text-3xl font-black text-red-600">{(prediction.away_win_probability * 100).toFixed(1)}%</p>
                  </div>
                </div>

                {isKnockoutPrediction && !hasActualScore && (
                  <div className="mb-6 rounded-2xl border border-amber-100 bg-amber-50/75 p-4">
                    <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <h4 className="text-sm font-black text-gray-900">淘汰赛决胜层</h4>
                      <span className="text-xs font-semibold text-amber-700">90分钟比分与晋级概率分开读取</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div className="rounded-xl bg-white/85 px-4 py-3 shadow-sm">
                        <p className="text-xs font-bold text-gray-500">90分钟平局</p>
                        <p className="mt-1 text-2xl font-black text-amber-600">{knockoutProbabilityText(extraTimeProbability)}</p>
                      </div>
                      <div className="rounded-xl bg-white/85 px-4 py-3 shadow-sm">
                        <p className="text-xs font-bold text-gray-500">加时决胜</p>
                        <p className="mt-1 text-2xl font-black text-blue-600">{knockoutProbabilityText(extraTimeDecisiveProbability)}</p>
                      </div>
                      <div className="rounded-xl bg-white/85 px-4 py-3 shadow-sm">
                        <p className="text-xs font-bold text-gray-500">点球决胜</p>
                        <p className="mt-1 text-2xl font-black text-red-600">{knockoutProbabilityText(penaltyDecisionProbability)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {alternativeScores.length > 0 && !hasActualScore && (
                  <div className="mb-6 rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
                    <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <h4 className="text-sm font-black text-gray-900">其他2个最有可能结果</h4>
                      <span className="text-xs font-semibold text-blue-600">来自同一比分概率矩阵</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {alternativeScores.map((score, index) => (
                        <div key={`${score.score}-${index}`} className="flex items-center justify-between rounded-xl bg-white/85 px-4 py-3 shadow-sm">
                          <span className="text-xs font-bold text-gray-500">备选 {index + 1}</span>
                          <span className="text-2xl font-black text-blue-600">{score.score}</span>
                          <span className="text-sm font-bold text-gray-600">{formatScoreProbability(score.probability)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* xG数据 */}
                <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 md:grid-cols-4">
                  <div className="bg-blue-50 rounded-xl p-4 text-center">
                    <p className="text-xs text-gray-500 mb-1">{selectedMatch.home_team} xG</p>
                    <p className="text-2xl font-bold text-blue-600">{prediction.xg_home}</p>
                  </div>
                  <div className="bg-red-50 rounded-xl p-4 text-center">
                    <p className="text-xs text-gray-500 mb-1">{selectedMatch.away_team} xG</p>
                    <p className="text-2xl font-bold text-red-600">{prediction.xg_away}</p>
                  </div>
                  <div className="bg-green-50 rounded-xl p-4 text-center">
                    <p className="text-xs text-gray-500 mb-1">置信度</p>
                    <p className="text-2xl font-bold text-green-600">{(prediction.confidence * 100).toFixed(0)}%</p>
                  </div>
                  <div className="bg-purple-50 rounded-xl p-4 text-center">
                    <p className="text-xs text-gray-500 mb-1">模型版本</p>
                    <p className="text-sm font-bold text-purple-600">{prediction.model_version}</p>
                  </div>
                </div>
              </div>

              {skillAudit && (
                <div className="glass-card overflow-hidden">
                  <div className="border-b border-white/70 bg-gradient-to-r from-slate-950 via-blue-950 to-slate-900 p-5 text-white sm:p-6">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.18em] text-cyan-200">
                          <ShieldAlert className="h-4 w-4" />
                          观点
                        </p>
                        <h3 className="mt-2 text-2xl font-black leading-tight">
                          {skillBrief?.title || `${selectedMatch.home_team} vs ${selectedMatch.away_team} 单场简析`}
                        </h3>
                        <p className="mt-2 max-w-3xl text-sm font-semibold leading-relaxed text-slate-300">
                          {skillAudit.match_type.label} · {skillAudit.match_type.reasoning}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="rounded-full bg-cyan-300/14 px-3 py-1 text-xs font-black text-cyan-100">
                          数据等级 {skillAudit.data_quality}
                        </span>
                        <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-black text-slate-200">
                          {evidenceStatusLabel(skillAudit.evidence_status)}
                        </span>
                        <span className="rounded-full bg-yellow-300/16 px-3 py-1 text-xs font-black text-yellow-100">
                          {scoreAdjustmentLabel(skillAudit.score_adjustment.action)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 p-5 lg:grid-cols-[1.35fr_0.65fr] sm:p-6">
                    <div className="rounded-2xl border border-blue-100 bg-white/78 p-4">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <p className="text-sm font-black text-slate-950">单场简析</p>
                        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-black text-blue-700">
                          总进球 {skillAudit.total_goals_range} · {bttsViewLabel(skillAudit.btts_view)}
                        </span>
                      </div>
                      <div className="space-y-3 text-sm font-semibold leading-7 text-slate-700">
                        {(skillBrief?.paragraphs || []).slice(0, 3).map(paragraph => (
                          <p key={paragraph}>{paragraph}</p>
                        ))}
                        {(skillBrief?.bullets || []).length > 0 && (
                          <div className="grid gap-2 pt-1 sm:grid-cols-2">
                            {(skillBrief?.bullets || []).slice(0, 4).map(item => (
                              <p key={item} className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-bold leading-5 text-slate-600">
                                {item}
                              </p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="rounded-2xl border border-cyan-100 bg-cyan-50/70 p-4">
                        <p className="text-xs font-black uppercase tracking-wide text-cyan-700">比分池</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className="rounded-full bg-slate-950 px-3 py-1.5 text-sm font-black text-white">
                            首选 {skillAudit.first_score_pick}
                          </span>
                          {skillScorePool.map(score => (
                            <span key={score} className="rounded-full bg-white px-3 py-1.5 text-sm font-black text-cyan-800 shadow-sm">
                              {score}
                            </span>
                          ))}
                        </div>
                        {skillSecondaryScores.length > 0 && (
                          <p className="mt-3 text-xs font-bold leading-5 text-cyan-800">
                            次级风险：{skillSecondaryScores.slice(0, 4).join(' / ')}
                          </p>
                        )}
                      </div>

                      <div className="rounded-2xl border border-amber-100 bg-amber-50/80 p-4">
                        <p className="text-xs font-black uppercase tracking-wide text-amber-700">风险校验</p>
                        <div className="mt-2 space-y-2">
                          {[...skillRiskFlags, ...skillAudit.score_adjustment.reasons].slice(0, 4).map(item => (
                            <p key={item} className="text-xs font-bold leading-5 text-amber-800">· {item}</p>
                          ))}
                          {skillRiskFlags.length === 0 && skillAudit.score_adjustment.reasons.length === 0 && (
                            <p className="text-xs font-bold leading-5 text-amber-800">暂无额外风险，保留主预测与相邻比分。</p>
                          )}
                        </div>
                      </div>
                    </div>

                    {(skillMacroTakeaways.length > 0 || skillGroupNotes.length > 0 || skillAudit.missing_information.length > 0 || publicDataSources.length > 0) && (
                      <div className="lg:col-span-2 grid gap-3 lg:grid-cols-3">
                        <div className="rounded-2xl border border-white/70 bg-white/72 p-4">
                          <p className="text-sm font-black text-slate-900">阶段判断</p>
                          <div className="mt-2 space-y-2">
                            {skillMacroTakeaways.slice(0, 3).map(item => (
                              <p key={item} className="text-xs font-semibold leading-5 text-slate-600">· {item}</p>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-2xl border border-white/70 bg-white/72 p-4">
                          <p className="text-sm font-black text-slate-900">小组战意</p>
                          <div className="mt-2 space-y-2">
                            {(skillGroupNotes.length ? skillGroupNotes : ['当前没有完整积分语境，暂按基础胜平负和xG处理。']).slice(0, 3).map(item => (
                              <p key={item} className="text-xs font-semibold leading-5 text-slate-600">· {item}</p>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-2xl border border-white/70 bg-white/72 p-4">
                          <p className="text-sm font-black text-slate-900">数据源状态</p>
                          <div className="mt-3 space-y-2">
                            {publicSourceRows.slice(0, 5).map(source => (
                              <div key={source.id} className="rounded-xl border border-white/80 bg-white/72 px-3 py-2 shadow-sm">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="min-w-0 truncate text-xs font-black text-slate-900">{source.label}</p>
                                  <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-black ${publicSourceStatusClass(source.status)}`}>
                                    {publicSourceStatusLabel[source.status] || source.status}
                                  </span>
                                </div>
                                <p className="mt-1 text-[11px] font-semibold leading-4 text-slate-600">
                                  {source.role} · {source.weight === 'low' ? '低权重' : source.weight === 'reference_only' ? '仅参考' : source.scope}
                                </p>
                              </div>
                            ))}
                            {(publicSourceGaps.length ? publicSourceGaps : ['暂无阻断性缺口。']).slice(0, 2).map(item => (
                              <p key={item} className="text-xs font-semibold leading-5 text-amber-700">· {item}</p>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {(marketCalibration || upsetPrediction) && (
                <div className="glass-card p-5 sm:p-6">
                  <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-blue-600" />
                      市场信号与冷门参考
                    </h3>
                    <span className={`w-fit rounded-full border px-3 py-1 text-xs font-bold ${
                      marketCalibration?.applied
                        ? 'border-blue-100 bg-blue-50 text-blue-700'
                        : 'border-gray-100 bg-gray-50 text-gray-600'
                    }`}>
                      {marketCalibrationBadge}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                    <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-black text-gray-900">赛前市场信号</p>
                          <p className="mt-1 text-xs font-semibold text-gray-500">
                            {marketSourceLabel} · {marketStatusText}
                          </p>
                        </div>
                        <p className="text-right text-xs font-bold text-blue-700">
                          分歧 {(marketCalibration?.difference ? marketCalibration.difference * 100 : 0).toFixed(1)}%
                        </p>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          ['主胜', marketCalibration?.market?.home, marketCalibration?.final?.home],
                          ['平局', marketCalibration?.market?.draw, marketCalibration?.final?.draw],
                          ['客胜', marketCalibration?.market?.away, marketCalibration?.final?.away],
                        ].map(([label, marketValue, finalValue]) => (
                          <div key={label as string} className="rounded-xl bg-white/80 p-3 text-center">
                            <p className="text-[11px] font-bold text-gray-500">{label}</p>
                            <p className="mt-1 text-lg font-black text-blue-600">
                              {typeof finalValue === 'number' ? `${(finalValue * 100).toFixed(1)}%` : '-'}
                            </p>
                            <p className="mt-0.5 text-[10px] font-semibold text-gray-400">
                              外部 {typeof marketValue === 'number' ? `${(marketValue * 100).toFixed(1)}%` : '-'}
                            </p>
                          </div>
                        ))}
                      </div>
                      <p className="mt-3 text-xs leading-5 text-gray-600">
                        {marketCalibration?.message || marketOdds?.message || '赛前市场信号暂无可用数据，本场保留模型独立判断。'}
                      </p>
                    </div>

                    {upsetPrediction && (
                      <div className={`rounded-2xl border p-4 ${upsetRiskClass}`}>
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <div>
                            <p className="text-sm font-black text-gray-900">冷门概率</p>
                            <p className="mt-1 text-xs font-semibold opacity-80">{upsetPrediction.label} · {upsetPrediction.team}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-3xl font-black">{(upsetPrediction.probability * 100).toFixed(1)}%</p>
                            <p className="text-[11px] font-bold opacity-70">{upsetRiskLabel}</p>
                          </div>
                        </div>
                        <div className="rounded-xl bg-white/75 px-4 py-3">
                          <p className="text-xs font-bold text-gray-500">冷门比分参考</p>
                          <p className="mt-1 text-2xl font-black text-gray-900">{upsetPrediction.score}</p>
                          <p className="mt-0.5 text-xs font-semibold text-gray-500">比分矩阵概率 {upsetPrediction.score_probability}%</p>
                        </div>
                        <ul className="mt-3 space-y-1.5 text-xs leading-5 text-gray-700">
                          {upsetPrediction.reasons.slice(0, 3).map(reason => (
                            <li key={reason}>· {reason}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 总进球与大小球 */}
              {totalGoals && (
                <div className="glass-card p-5 sm:p-6">
                  <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2">
                      <Target className="w-5 h-5 text-orange-500" />
                      总进球与大小球
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      <span className="w-fit rounded-full bg-orange-50 px-3 py-1 text-xs font-bold text-orange-700">
                        主线：{totalGoalsPrimaryRecommendation}
                      </span>
                      {totalGoalsProtectionRecommendation && (
                        <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                          保护：{totalGoalsProtectionRecommendation}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-3 min-[460px]:grid-cols-3">
                    <div className="rounded-xl bg-blue-50 p-4 text-center">
                      <p className="text-xs text-gray-500">预期总进球</p>
                      <p className="mt-1 text-3xl font-black text-blue-600">{totalGoals.expected_total}</p>
                    </div>
                    <div className="rounded-xl bg-green-50 p-4 text-center">
                      <p className="text-xs text-gray-500">主线方向概率</p>
                      <p className="mt-1 text-3xl font-black text-green-600">{(totalGoalsMainProbability * 100).toFixed(0)}%</p>
                      <p className="mt-1 text-[11px] font-bold text-green-500">
                        最可能 {totalGoals.most_likely_total} 球
                      </p>
                    </div>
                    <div className="rounded-xl bg-purple-50 p-4 text-center">
                      <p className="text-xs text-gray-500">主线信号强度</p>
                      <p className="mt-1 text-3xl font-black text-purple-600">{(totalGoalsSignalStrength * 100).toFixed(0)}%</p>
                      <p className="mt-1 text-[11px] font-bold text-purple-500">
                        概率差越大信号越硬
                      </p>
                    </div>
                  </div>
                  {totalGoals.risk_note && (
                    <div className="mt-4 rounded-2xl border border-orange-100 bg-orange-50/75 px-4 py-3 text-xs font-semibold leading-5 text-orange-800">
                      {totalGoals.risk_note}
                    </div>
                  )}

                  <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
                    {totalGoals.lines.map(line => {
                      const overWidth = `${Math.round(line.over_probability * 100)}%`
                      const lineRole =
                        Math.abs(line.line - totalGoals.main_line) < 0.01
                          ? '主线'
                          : totalGoalsProtectionRecommendation.includes(String(line.line))
                            ? '保护'
                            : ''
                      return (
                        <div
                          key={line.line}
                          className={`rounded-xl border p-3 ${
                            lineRole === '主线'
                              ? 'border-blue-100 bg-blue-50/80'
                              : lineRole === '保护'
                                ? 'border-slate-200 bg-slate-50/90'
                                : 'border-gray-100 bg-white/80'
                          }`}
                        >
                          <div className="mb-2 flex items-center justify-between text-sm">
                            <span className="font-bold text-gray-800">
                              {line.line} 球
                              {lineRole && (
                                <span className="ml-2 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-black text-blue-600">
                                  {lineRole}
                                </span>
                              )}
                            </span>
                            <span className="text-xs text-gray-400">大/小</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                            <div className="h-full rounded-full bg-blue-600" style={{ width: overWidth }} />
                          </div>
                          <div className="mt-2 flex justify-between text-xs font-semibold">
                            <span className="text-blue-600">大 {(line.over_probability * 100).toFixed(1)}%</span>
                            <span className="text-gray-500">小 {(line.under_probability * 100).toFixed(1)}%</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {setPieceCardPrediction && (
                <div className="glass-card p-5 sm:p-6">
                  <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-green-600" />
                      角球与黄牌预测
                    </h3>
                    <span className="w-fit rounded-full bg-green-50 px-3 py-1 text-xs font-bold text-green-700">
                      角球 {setPieceCardPrediction.corners.total} · 黄牌 {setPieceCardPrediction.yellow_cards.total}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    <div className="rounded-2xl border border-green-100 bg-green-50/70 p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <p className="text-sm font-black text-gray-900">角球预期</p>
                        <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-bold text-green-700">
                          优势：{setPieceCardPrediction.corners.edge}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">{selectedMatch.home_team}</p>
                          <p className="mt-1 text-2xl font-black text-green-600">{setPieceCardPrediction.corners.home}</p>
                        </div>
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">合计</p>
                          <p className="mt-1 text-2xl font-black text-green-700">{setPieceCardPrediction.corners.total}</p>
                        </div>
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">{selectedMatch.away_team}</p>
                          <p className="mt-1 text-2xl font-black text-green-600">{setPieceCardPrediction.corners.away}</p>
                        </div>
                      </div>
                    </div>

                    <div className="rounded-2xl border border-amber-100 bg-amber-50/70 p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <p className="text-sm font-black text-gray-900">黄牌预期</p>
                        <span className="rounded-full bg-white/80 px-3 py-1 text-xs font-bold text-amber-700">
                          风险：{setPieceCardPrediction.yellow_cards.risk}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">{selectedMatch.home_team}</p>
                          <p className="mt-1 text-2xl font-black text-amber-600">{setPieceCardPrediction.yellow_cards.home}</p>
                        </div>
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">合计</p>
                          <p className="mt-1 text-2xl font-black text-amber-700">{setPieceCardPrediction.yellow_cards.total}</p>
                        </div>
                        <div className="rounded-xl bg-white/80 p-3">
                          <p className="text-[11px] font-bold text-gray-500">{selectedMatch.away_team}</p>
                          <p className="mt-1 text-2xl font-black text-amber-600">{setPieceCardPrediction.yellow_cards.away}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 rounded-2xl border border-gray-100 bg-white/70 p-4">
                    <p className="mb-2 text-sm font-black text-gray-900">角球/黄牌依据</p>
                    <div className="space-y-2">
                      {setPieceCardPrediction.basis.slice(0, 4).map(item => (
                        <p key={item} className="text-xs leading-5 text-gray-600">· {item}</p>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 关键球员与进球球员预测 */}
              <div className="glass-card overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowKeyPlayersSection(value => !value)}
                  className="flex w-full items-center justify-between gap-3 border-b bg-gray-50/80 p-4 text-left"
                >
                  <div>
                    <h3 className="flex items-center gap-2 text-base font-black text-gray-900">
                      <Activity className="h-5 w-5 text-blue-600" />
                      关键球员与进球球员预测
                    </h3>
                    <p className="mt-1 text-xs text-gray-500">默认收起，展开查看球员影响力、xG/xA 和进球概率</p>
                  </div>
                  {showKeyPlayersSection ? <ChevronUp className="h-5 w-5 text-gray-500" /> : <ChevronDown className="h-5 w-5 text-gray-500" />}
                </button>
                {showKeyPlayersSection && (
                  <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-2">
                {prediction.key_players && prediction.key_players.length > 0 && (
                  <div className="overflow-hidden rounded-xl border border-gray-100 bg-white/80">
                    <div className="border-b bg-gray-50/80 p-4">
                      <h3 className="flex items-center gap-2 text-lg font-bold text-gray-900">
                        <Activity className="w-5 h-5 text-blue-600" />
                        关键球员数据分析
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {prediction.key_players.slice(0, 6).map(player => (
                        <div key={`${player.team}-${player.name}`} className="p-4">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <TeamFlag teamName={player.team} size="sm" />
                                <span className="font-bold text-gray-900">{player.name}</span>
                                <span className="text-xs text-gray-400">{player.position}</span>
                              </div>
                              <p className="mt-1 text-xs text-gray-500">{player.role} · {player.key_metric}</p>
                            </div>
                            <div className="shrink-0 text-right">
                              <p className="text-lg font-black text-blue-600">{player.rating}</p>
                              <p className="text-xs text-gray-400">影响力</p>
                            </div>
                          </div>
                          <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
                            <div className="rounded-lg bg-green-50 p-2">
                              <p className="font-bold text-green-700">{player.goals_projection}</p>
                              <p className="text-gray-400">进球xG</p>
                            </div>
                            <div className="rounded-lg bg-purple-50 p-2">
                              <p className="font-bold text-purple-700">{player.assist_projection}</p>
                              <p className="text-gray-400">助攻xA</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {prediction.goal_scorer_predictions && prediction.goal_scorer_predictions.length > 0 && (
                  <div className="overflow-hidden rounded-xl border border-gray-100 bg-white/80">
                    <div className="border-b bg-gray-50/80 p-4">
                      <h3 className="flex items-center gap-2 text-lg font-bold text-gray-900">
                        <Target className="w-5 h-5 text-red-500" />
                        进球球员预测
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {prediction.goal_scorer_predictions.map((player, index) => (
                        <div key={`${player.team}-${player.name}-scorer`} className="p-4">
                          <div className="flex items-center gap-3">
                            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${index < 3 ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 text-white' : 'bg-gray-200 text-gray-600'}`}>
                              {index + 1}
                            </div>
                            <TeamFlag teamName={player.team} size="sm" />
                            <div className="min-w-0 flex-1">
                              <p className="font-bold text-gray-900">{player.name}</p>
                              <p className="truncate text-xs text-gray-500">{player.team} · {player.reason}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xl font-black text-red-500">{(player.probability * 100).toFixed(0)}%</p>
                              <p className="text-xs text-gray-400">进球概率</p>
                            </div>
                          </div>
                          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-gray-100">
                            <div className="h-full rounded-full bg-red-500" style={{ width: `${Math.max(8, player.probability * 100)}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                  </div>
                )}
              </div>

              {/* 预测因素 */}
              <div className="glass-card p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-500" />
                  关键预测因素
                </h3>
                {teamFeatureAdjustment?.applied && (
                  <div className="mb-4 rounded-2xl border border-cyan-100 bg-cyan-50/70 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="flex items-center gap-2 text-sm font-black text-gray-900">
                          <Activity className="h-4 w-4 text-cyan-600" />
                          球队特征库校准
                        </p>
                        <p className="mt-1 text-xs leading-5 text-gray-600">
                          汇总已完赛技术统计、纪律事件、复盘要点和出线形势，作为低权重赛前画像修正。
                        </p>
                      </div>
                      <span className="w-fit rounded-full bg-white/85 px-3 py-1 text-xs font-bold text-cyan-700">
                        {teamFeatureAdjustment.strength || '低权重'}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                      <div className="rounded-xl bg-white/80 p-3">
                        <p className="text-[11px] font-bold text-gray-500">{selectedMatch?.home_team || '主队'} xG</p>
                        <p className="mt-1 text-lg font-black text-cyan-700">
                          {formatAdjustmentPercent(teamFeatureAdjustment.home_attack_delta)}
                        </p>
                      </div>
                      <div className="rounded-xl bg-white/80 p-3">
                        <p className="text-[11px] font-bold text-gray-500">{selectedMatch?.away_team || '客队'} xG</p>
                        <p className="mt-1 text-lg font-black text-cyan-700">
                          {formatAdjustmentPercent(teamFeatureAdjustment.away_attack_delta)}
                        </p>
                      </div>
                      <div className="rounded-xl bg-white/80 p-3">
                        <p className="text-[11px] font-bold text-gray-500">平局倾向</p>
                        <p className="mt-1 text-lg font-black text-amber-600">
                          {formatAdjustmentPercent(teamFeatureAdjustment.draw_probability_delta)}
                        </p>
                      </div>
                    </div>
                    {(teamFeatureReasons.length > 0 || teamFeatureTags.length > 0 || teamFeatureNotes.length > 0) && (
                      <div className="mt-3 space-y-2 text-xs leading-5 text-gray-700">
                        {teamFeatureReasons.slice(0, 2).map(item => (
                          <p key={item}>· {item}</p>
                        ))}
                        {teamFeatureNotes.slice(0, 2).map(item => (
                          <p key={item}>· {item}</p>
                        ))}
                        {teamFeatureTags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {teamFeatureTags.map(tag => (
                              <span key={tag} className="rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-bold text-cyan-700">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                <div className="space-y-2">
                  {prediction.factors?.map((factor: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 p-2 rounded-lg bg-gray-50">
                      <BarChart3 className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{factor}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {showModelGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
            <div className="sticky top-0 flex items-center justify-between border-b bg-white px-5 py-4">
              <div>
                <h2 className="text-xl font-black text-gray-900">美加墨世界杯AI预测模型 26.5 说明</h2>
                <p className="mt-1 text-sm text-gray-500">预测依据、外部因子和数据来源口径</p>
              </div>
              <button
                type="button"
                onClick={() => setShowModelGuide(false)}
                className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900"
                aria-label="关闭模型说明"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-5 p-5 text-sm leading-6 text-gray-700">
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">核心流程</h3>
                <p>模型先以 Elo、FIFA 官方排名、球队状态窗口和比赛阶段估算双方实力差，再换算为 xG；随后使用 0-8 球的泊松/Dixon-Coles 比分矩阵生成胜平负、比分、大小球、角球、黄牌和进球球员概率。大小球会同时看 1.5、2.5、3.5 三条线，不再只按 2.5 线单点判定。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">球队特征库</h3>
                <p>球队特征库默认启用，不需要页面手动打开。世界杯样本不足三场时，使用本届世界杯已赛均值 + 世界杯前 3 场正式赛均值；本届世界杯样本满三场后，抛弃赛前样本，全部用本届世界杯已赛样本均值。该层只使用目标比赛之前的数据，低权重修正双方 xG、平局倾向、纪律和复盘注意事项。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">数据源逻辑</h3>
                <p>赛前伤停优先读取 Transfermarkt 国家队公开伤停页，再结合 ESPN 伤停追踪、Sports Mole 单场阵容消息和本地人工复核。赛果、事件、赛程、历史赔率样本和球队特征库会分层展示，每个来源只在合适权重下参与模型，不把未核验信息硬塞进概率。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">基础排名数据</h3>
                <p>FIFA 排名使用 2026-06-11 官方男足排名快照，下一次官方更新日为 2026-07-20。模型启动时会用快照覆盖静态球队资料，避免页面显示旧排名；当官方发布新一期排名后再更新快照。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">市场信号与冷门</h3>
                <p>赛前市场信号优先使用可用实时赔率源；未启用实时源时自动使用 Football-Data 公开历史赔率样本低权重先验，只做冷门、平局和大小球风险参考，不伪装成实时市场共识。实时赔率分歧越大，校准权重从 8% 到 18% 递增；历史样本最多只给 4% 轻修正。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">角球与黄牌</h3>
                <p>角球与黄牌优先读取球队特征库同一套样本窗口：世界杯样本不足三场时结合赛前 3 场正式赛，三场后只用本届世界杯均值；没有可信窗口样本时才回退到球队长期画像、阵型宽度、xG、淘汰赛强度、高位逼抢和已知纪律风险。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">阵型相克与节奏</h3>
                <p>常用阵型会被归类为三中卫、三前锋、双后腰、双前锋或均衡结构。模型会判断三中卫对三前锋、双后腰对双前锋、高压逼抢对低位出球等相克关系，并分别修正双方 xG 倍率和比赛节奏倍率。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">主场与地域优势</h3>
                <p>小组赛阶段，美国、墨西哥、加拿大均按完整主场处理；淘汰赛阶段只有美国按完整主场处理。其他美洲球队不再自动获得半主场加成。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">外部勾选与实时变量</h3>
                <p>天气、场地、高压逼抢、伤停、体能和强制中立会进入 xG 和比分矩阵，不只是改变说明文字。红黄牌只在官方实时事件或可信赛后统计接入后参与模型，避免使用不准确的硬编码累计牌数。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">阵容与球员候选池</h3>
                <p>首发预测先从 48 队官方 26 人名单生成候选池，再结合常用阵型、出场记录、关键球员角色和红黄牌可用性生成。若 API-Football 返回临场 lineups，或人工录入官方首发，会覆盖候选首发；未接入前页面会明确标注为候选池预测。</p>
              </section>
              <section>
                <h3 className="mb-2 text-base font-bold text-gray-900">模型边界</h3>
                <p>预测不是赛果保证。若官方首发、临场伤停、天气或裁判尺度发生变化，模型会随着对应输入刷新。非强队阵容使用候选池补齐，置信度会低于数据更完整的强队。</p>
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
