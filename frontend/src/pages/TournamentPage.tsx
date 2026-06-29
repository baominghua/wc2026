import { useEffect, useMemo, useRef, useState } from 'react'
import { toBlob } from 'html-to-image'
import {
  AlertCircle,
  Crown,
  Download,
  GitBranch,
  Play,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react'
import TeamFlag from '../components/TeamFlag'
import {
  tournamentAPI,
  type TournamentGroupProjection,
  type TournamentProjectedMatch,
  type TournamentProjection,
} from '../services/api'
import { TEAMS } from '../services/wc2026-data'

const LEFT_CLUSTERS = [
  { r32: [74, 77], r16: 89, qf: 97 },
  { r32: [73, 75], r16: 90, qf: 97 },
  { r32: [83, 84], r16: 93, qf: 98 },
  { r32: [81, 82], r16: 94, qf: 98 },
]

const RIGHT_CLUSTERS = [
  { r32: [76, 78], r16: 91, qf: 99 },
  { r32: [79, 80], r16: 92, qf: 99 },
  { r32: [86, 88], r16: 95, qf: 100 },
  { r32: [85, 87], r16: 96, qf: 100 },
]

function getFlagCode(teamName: string) {
  return TEAMS.find(team => team.name === teamName || team.code === teamName)?.flagCode
}

function formatDate(value?: string | null) {
  if (!value) return '待排定'
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return value
  }
}

function scoreText(match?: TournamentProjectedMatch) {
  if (!match || match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) {
    return '-'
  }
  return `${match.home_score}-${match.away_score}`
}

function regulationScoreText(match?: TournamentProjectedMatch) {
  const home = match?.regulation_home_score
  const away = match?.regulation_away_score
  if (home === null || home === undefined || away === null || away === undefined) return null
  return `${home}-${away}`
}

function extraTimeScoreText(match?: TournamentProjectedMatch) {
  const home = match?.extra_time_home_score
  const away = match?.extra_time_away_score
  if (home === null || home === undefined || away === null || away === undefined) return null
  return `${home}-${away}`
}

function penaltyScoreText(match?: TournamentProjectedMatch) {
  const home = match?.penalty_home_score
  const away = match?.penalty_away_score
  if (home === null || home === undefined || away === null || away === undefined) return null
  return `${home}-${away}`
}

function decisionLabel(match?: TournamentProjectedMatch) {
  if (!match) return '待定'
  if (match.decided_by === 'penalties' || match.resolution === 'penalties') return '点球'
  if (match.decided_by === 'extra_time' || match.resolution === 'extra_time') return '加时'
  if (match.decided_by === 'regular_time' || match.resolution === 'normal_time') return '90分钟'
  if (match.resolution === 'extra_time_or_penalties') return '加时/点球'
  return match.score_source === 'actual' ? '全场' : '预测'
}

function decisionDetail(match?: TournamentProjectedMatch) {
  if (!match) return '待定'
  const regulation = regulationScoreText(match)
  const extraTime = extraTimeScoreText(match)
  const penalties = penaltyScoreText(match)
  if (penalties) return `90' ${regulation || scoreText(match)} · 点球 ${penalties}`
  if (match.decided_by === 'extra_time' || match.resolution === 'extra_time') {
    return `90' ${regulation || scoreText(match)} · 加时 ${extraTime || scoreText(match)}`
  }
  if (regulation && regulation !== scoreText(match)) return `90' ${regulation}`
  return decisionLabel(match)
}

function sourceText(match?: TournamentProjectedMatch) {
  if (!match) return '待定'
  if (match.score_source === 'actual') return '真实比分'
  if (match.score_source === 'model') return '模型预测'
  return match.stage ? '模拟' : '待定'
}

function skillAdjustmentLabel(value?: string) {
  if (!value || value === 'keep') return '首选保留'
  if (value.includes('draw_protection') && value.includes('overflow_watch')) return '防平+溢出'
  if (value.includes('draw_protection')) return '防平'
  if (value.includes('overflow_watch')) return '溢出'
  return value
}

function auditLine(match?: TournamentProjectedMatch) {
  const audit = match?.prediction?.skill_audit
  if (!audit) return null
  return `${audit.match_type.primary} · ${skillAdjustmentLabel(audit.score_adjustment.action)} · ${audit.total_goals_range}球`
}

function buildMatchMap(projection: TournamentProjection) {
  const matches = [
    ...(projection.knockout?.rounds['Round of 32'] || projection.round_of_32 || []),
    ...(projection.knockout?.rounds['Round of 16'] || []),
    ...(projection.knockout?.rounds['Quarter-final'] || []),
    ...(projection.knockout?.rounds['Semi-final'] || []),
    ...(projection.knockout?.rounds.Final || []),
    ...(projection.knockout?.rounds['Third place'] || []),
  ]
  return new Map(matches.map(match => [match.id, match]))
}

type MobilePosterPreviewState = {
  imageUrl: string
  fileName: string
}

type PosterExportKind = 'bracket-landscape' | 'bracket-portrait' | 'groups-landscape' | 'groups-portrait'

function usePosterExport() {
  const [exporting, setExporting] = useState<string | null>(null)
  const [mobilePoster, setMobilePoster] = useState<MobilePosterPreviewState | null>(null)

  const isMobileLike = () => (
    typeof navigator !== 'undefined' &&
    /Android|iPhone|iPad|iPod|Mobile|MicroMessenger/i.test(navigator.userAgent)
  )

  const withTimeout = async <T,>(promise: Promise<T>, ms: number, message: string): Promise<T> => {
    let timeoutId: number | undefined
    try {
      return await Promise.race([
        promise,
        new Promise<T>((_, reject) => {
          timeoutId = window.setTimeout(() => reject(new Error(message)), ms)
        }),
      ])
    } finally {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId)
    }
  }

  const showMobilePoster = (poster: MobilePosterPreviewState) => {
    setMobilePoster(current => {
      if (current) URL.revokeObjectURL(current.imageUrl)
      return poster
    })
  }

  const closeMobilePoster = () => {
    setMobilePoster(current => {
      if (current) URL.revokeObjectURL(current.imageUrl)
      return null
    })
  }

  const waitForImages = async (node: HTMLElement) => {
    const images = Array.from(node.querySelectorAll('img'))
    await Promise.all(images.map(image => {
      image.loading = 'eager'
      if (image.complete) return Promise.resolve()
      return Promise.race([
        new Promise(resolve => {
          image.onload = resolve
          image.onerror = resolve
        }),
        new Promise(resolve => window.setTimeout(resolve, 3500)),
      ])
    }))
  }

  const exportNode = async (
    node: HTMLElement | null,
    fileName: string,
    label: string,
  ) => {
    if (!node || exporting) return
    setExporting(label)
    const mobile = isMobileLike()
    let imageUrl: string | null = null
    try {
      if (document.fonts?.ready) {
        await withTimeout(document.fonts.ready, 4000, '字体加载超时，已继续使用系统字体生成')
          .catch(() => undefined)
      }
      await waitForImages(node)
      await new Promise(resolve => window.setTimeout(resolve, 350))
      const blob = await withTimeout(toBlob(node, {
        cacheBust: true,
        pixelRatio: 1.35,
        backgroundColor: '#07111f',
        skipFonts: true,
      }), mobile ? 45000 : 60000, '海报生成超时')
      if (!blob) throw new Error('海报生成失败，浏览器没有返回图片数据')

      imageUrl = URL.createObjectURL(blob)
      if (mobile) {
        showMobilePoster({ imageUrl, fileName })
        imageUrl = null
        return
      }
      const link = document.createElement('a')
      link.href = imageUrl
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => {
        if (imageUrl) URL.revokeObjectURL(imageUrl)
      }, 30000)
    } catch (err) {
      console.error('Poster export failed', err)
      window.alert(err instanceof Error ? err.message : '海报生成失败，请稍后重试。')
    } finally {
      setExporting(null)
    }
  }

  return { exporting, exportNode, mobilePoster, closeMobilePoster }
}

function MobilePosterPreview({
  poster,
  onClose,
}: {
  poster: MobilePosterPreviewState
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-[100] bg-slate-950/88 px-3 py-4 backdrop-blur-xl sm:px-6">
      <div className="mx-auto flex h-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-white/15 bg-slate-950 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-white/10 px-4 py-4 sm:px-6">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-cyan-200">Poster Ready</p>
            <h2 className="mt-1 text-xl font-black text-white sm:text-2xl">海报已生成</h2>
            <p className="mt-1 text-sm font-semibold text-slate-300">手机端与电脑端使用同一版高清海报，长按图片保存；也可以打开图片页面后再保存。</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/10 text-white transition hover:bg-white/18"
            aria-label="关闭海报预览"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto bg-[#07111f] p-3 sm:p-5">
          <img
            src={poster.imageUrl}
            alt="世界杯预测海报"
            className="mx-auto block w-full max-w-4xl rounded-2xl shadow-[0_24px_80px_rgba(0,0,0,0.42)]"
          />
        </div>
        <div className="flex flex-col gap-2 border-t border-white/10 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p className="text-xs font-semibold text-slate-400">如果浏览器不支持直接下载，请点“打开图片页面”后长按图片。</p>
          <div className="flex gap-2">
            <a
              href={poster.imageUrl}
              download={poster.fileName}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-blue-600 px-4 py-2 text-sm font-black text-white shadow-lg shadow-blue-950/30 transition hover:bg-blue-500"
            >
              <Download className="h-4 w-4" />
              下载图片
            </a>
            <a
              href={poster.imageUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center rounded-full bg-white/10 px-4 py-2 text-sm font-black text-white transition hover:bg-white/18"
            >
              打开图片页面
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

function TeamRow({
  team,
  winner,
  align = 'left',
  dark = false,
  compact = false,
  micro = false,
  large = false,
}: {
  team: string
  winner?: boolean
  align?: 'left' | 'right'
  dark?: boolean
  compact?: boolean
  micro?: boolean
  large?: boolean
}) {
  const textSize = large ? 'text-lg' : micro ? 'text-[10px]' : compact ? 'text-xs' : 'text-sm'
  const flagSize = large ? 'lg' : compact ? 'sm' : 'md'
  return (
    <div className={`flex min-w-0 items-center gap-2 ${align === 'right' ? 'justify-end text-right' : ''}`}>
      {align === 'left' && <TeamFlag teamName={team} flagCode={getFlagCode(team)} size={flagSize} />}
      <span className={`min-w-0 truncate font-black ${textSize} ${winner ? (dark ? 'text-cyan-200' : 'text-blue-700') : (dark ? 'text-slate-100' : 'text-slate-900')}`}>
        {team}
      </span>
      {winner && <ShieldCheck className={`shrink-0 ${compact ? 'h-3.5 w-3.5' : 'h-4 w-4'} ${dark ? 'text-cyan-300' : 'text-blue-600'}`} />}
      {align === 'right' && <TeamFlag teamName={team} flagCode={getFlagCode(team)} size={flagSize} />}
    </div>
  )
}

function StatusTile({ label, value, hint, tone = 'blue' }: { label: string; value: string | number; hint: string; tone?: 'blue' | 'green' | 'amber' | 'slate' }) {
  const toneClass = {
    blue: 'text-blue-700 bg-blue-50',
    green: 'text-emerald-700 bg-emerald-50',
    amber: 'text-amber-700 bg-amber-50',
    slate: 'text-slate-700 bg-slate-50',
  }[tone]

  return (
    <div className="metric-tile">
      <p className="text-xs font-black uppercase tracking-wide text-slate-500">{label}</p>
      <div className={`mt-3 inline-flex min-h-10 items-center rounded-2xl px-3 text-2xl font-black ${toneClass}`}>{value}</div>
      <p className="mt-3 text-xs font-semibold leading-relaxed text-slate-500">{hint}</p>
    </div>
  )
}

function BasisSection({ projection }: { projection: TournamentProjection }) {
  const basis = projection.model_basis?.length
    ? projection.model_basis
    : [
      'FIFA 2026淘汰赛规则: 90分钟打平后进入加时，加时仍平进入点球',
      '90分钟比分沿用当前Elo/FIFA排名/状态权重/xG概率矩阵模型',
      '加时与点球层按历史世界杯淘汰赛经验先验，并结合双方强度差修正',
    ]
  return (
    <section className="glass-card p-5 sm:p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-blue-600">
            <ShieldCheck className="h-4 w-4" />
            预测依据
          </p>
          <h2 className="mt-2 text-2xl font-black text-slate-950">淘汰赛预测依据</h2>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-relaxed text-slate-600">
            每场淘汰赛先生成90分钟比分，再按FIFA规则进入加时或点球决胜；晋级方由当前模型胜率、球队强度差和历史淘汰赛先验共同决定。
          </p>
        </div>
        <div className="grid flex-1 gap-2 md:grid-cols-2">
          {basis.map(item => (
            <div key={item} className="rounded-2xl border border-white/60 bg-white/70 px-4 py-3 text-xs font-bold leading-relaxed text-slate-700 shadow-sm">
              {item}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function GroupCard({ group }: { group: TournamentGroupProjection }) {
  return (
    <article className="rounded-3xl border border-white/60 bg-white/78 p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-base font-black text-slate-950">{group.group} 组</h3>
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-black text-slate-600">前 2 + 最佳第三</span>
      </div>
      <div className="space-y-2">
        {group.standings.map(row => (
          <div
            key={row.team}
            className={`grid grid-cols-[1.5rem_minmax(0,1fr)_2.5rem_2.5rem_2.5rem] items-center gap-2 rounded-2xl px-2.5 py-2 text-xs font-bold ${
              row.rank <= 2
                ? 'bg-emerald-50 text-emerald-950'
                : row.qualified
                  ? 'bg-amber-50 text-amber-950'
                  : 'bg-slate-50 text-slate-700'
            }`}
          >
            <span className="text-center font-black">{row.rank}</span>
            <TeamRow team={row.team} winner={row.qualified} compact />
            <span className="text-right tabular-nums">{row.points} 分</span>
            <span className="text-right tabular-nums">{row.goal_diff >= 0 ? '+' : ''}{row.goal_diff}</span>
            <span className="text-right tabular-nums">{row.goals_for}/{row.goals_against}</span>
          </div>
        ))}
      </div>
    </article>
  )
}

function ExportButton({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="wc-button-gold inline-flex items-center gap-2 px-4 py-2 text-sm"
      disabled={disabled}
    >
      <Download className="h-4 w-4" />
      {children}
    </button>
  )
}

function BracketMatchNode({
  match,
  side = 'left',
  dark = false,
  tiny = false,
}: {
  match?: TournamentProjectedMatch
  side?: 'left' | 'right' | 'center'
  dark?: boolean
  tiny?: boolean
}) {
  const homeWinner = match?.winner === match?.home_team
  const awayWinner = match?.winner === match?.away_team
  const align = side === 'right' ? 'right' : 'left'
  const audit = auditLine(match)
  const base = dark
    ? 'border-white/10 bg-white/[0.07] text-slate-100 shadow-black/20'
    : 'border-white/70 bg-white/86 text-slate-900 shadow-sm'
  const teamClass = dark ? 'bg-slate-900/70' : 'bg-white/84'

  return (
    <article className={`${tiny ? 'w-[7.8rem] p-1.5' : 'w-44 p-2.5'} shrink-0 rounded-2xl border ${base} shadow`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className={`rounded-full px-2 py-0.5 font-black ${tiny ? 'text-[9px]' : 'text-[10px]'} ${dark ? 'bg-cyan-400/10 text-cyan-200' : 'bg-slate-100 text-slate-600'}`}>
          M{match?.id || '--'}
        </span>
        <span className={`truncate rounded-full px-2 py-0.5 font-black ${tiny ? 'max-w-[4.2rem] text-[9px]' : 'max-w-[5rem] text-[10px]'} ${dark ? 'bg-white/10 text-slate-300' : 'bg-blue-50 text-blue-700'}`}>
          {sourceText(match)}
        </span>
      </div>
      <div className={tiny ? 'space-y-1' : 'space-y-1.5'}>
        <div className={`rounded-xl px-2 ${tiny ? 'py-1' : 'py-1.5'} ${homeWinner ? (dark ? 'bg-cyan-400/14' : 'bg-blue-50') : teamClass}`}>
          <TeamRow team={match?.home_team || '待定'} winner={homeWinner} align={align} dark={dark} compact micro={tiny} />
        </div>
        <div className={`flex items-center justify-between px-1 font-black ${tiny ? 'text-[8px]' : 'text-[11px]'} ${dark ? 'text-slate-400' : 'text-slate-500'}`}>
          <span>{match?.home_slot || match?.home_source || '主'}</span>
          <span className={`rounded-full ${tiny ? 'px-2 py-0.5' : 'px-2.5 py-1'} ${dark ? 'bg-cyan-300 text-slate-950' : 'bg-slate-950 text-white'}`}>{scoreText(match)}</span>
          <span>{match?.away_slot || match?.away_source || '客'}</span>
        </div>
        {!tiny && match?.decided_by && match.decided_by !== 'regular_time' && (
          <div className={`rounded-full px-2 py-1 text-center text-[10px] font-black ${dark ? 'bg-white/10 text-cyan-100' : 'bg-cyan-50 text-cyan-700'}`}>
            {decisionDetail(match)}
          </div>
        )}
        {!tiny && audit && (
          <div className={`truncate rounded-full px-2 py-1 text-center text-[10px] font-black ${dark ? 'bg-yellow-300/12 text-yellow-100' : 'bg-yellow-50 text-yellow-700'}`}>
            {audit}
          </div>
        )}
        <div className={`rounded-xl px-2 ${tiny ? 'py-1' : 'py-1.5'} ${awayWinner ? (dark ? 'bg-cyan-400/14' : 'bg-blue-50') : teamClass}`}>
          <TeamRow team={match?.away_team || '待定'} winner={awayWinner} align={align} dark={dark} compact micro={tiny} />
        </div>
      </div>
    </article>
  )
}

function HalfBracket({
  side,
  matchMap,
  dark = false,
  poster = false,
}: {
  side: 'left' | 'right'
  matchMap: Map<number, TournamentProjectedMatch>
  dark?: boolean
  poster?: boolean
}) {
  const clusters = side === 'left' ? LEFT_CLUSTERS : RIGHT_CLUSTERS
  const r32 = clusters.flatMap(cluster => cluster.r32)
  const r16 = clusters.map(cluster => cluster.r16)
  const qf = Array.from(new Set(clusters.map(cluster => cluster.qf)))
  const sf = side === 'left' ? [101] : [102]
  const mirrored = side === 'right'
  const cardGap = poster ? 'gap-1.5' : 'gap-1.5'
  const titleColor = dark ? 'text-slate-300' : 'text-slate-600'
  const columnWidth = poster ? 'w-44' : 'w-36'

  const columns = [
    { label: '32 强淘汰赛', ids: r32, width: columnWidth },
    { label: '16 强淘汰赛', ids: r16, width: columnWidth },
    { label: '四分之一决赛', ids: qf, width: columnWidth },
    { label: '半决赛', ids: sf, width: columnWidth },
  ]
  const ordered = mirrored ? [...columns].reverse() : columns

  return (
    <div className={`relative flex items-center ${poster ? 'gap-5' : 'gap-3'}`}>
      {ordered.map((column, columnIndex) => (
        <div key={column.label} className={`${column.width} flex shrink-0 flex-col`}>
          <div className={`mb-3 h-5 text-center text-[10px] font-black uppercase tracking-wide ${titleColor}`}>
            {column.label}
          </div>
          <div
            className={`flex ${poster ? 'min-h-[39rem]' : 'min-h-[34rem]'} flex-col justify-around ${cardGap} ${
              column.ids.length === 1 ? (poster ? 'py-48' : 'py-36') : column.ids.length === 2 ? (poster ? 'py-24' : 'py-16') : column.ids.length === 4 ? (poster ? 'py-8' : 'py-6') : ''
            }`}
          >
            {column.ids.map(matchId => (
              <BracketMatchNode
                key={matchId}
                match={matchMap.get(matchId)}
                side={side}
                dark={dark}
                tiny
              />
            ))}
          </div>
          {columnIndex < ordered.length - 1 && (
            <div className={`pointer-events-none absolute top-28 bottom-12 ${mirrored ? 'left-[calc(100%-11.6rem)]' : 'right-[calc(100%-11.6rem)]'} hidden`} />
          )}
        </div>
      ))}
    </div>
  )
}

function CenterPodium({
  projection,
  matchMap,
  dark = false,
  poster = false,
}: {
  projection: TournamentProjection
  matchMap: Map<number, TournamentProjectedMatch>
  dark?: boolean
  poster?: boolean
}) {
  const final = matchMap.get(104)
  const third = matchMap.get(103)
  const champion = projection.knockout?.champion || final?.winner || '-'
  const runnerUp = projection.knockout?.runner_up || final?.loser || '-'
  const thirdPlace = projection.knockout?.third_place || third?.winner || '-'

  return (
    <div className={`${poster ? 'w-72' : 'w-60'} shrink-0 text-center`}>
      <div className={`mx-auto rounded-[2rem] border p-5 ${dark ? 'border-yellow-300/25 bg-yellow-300/8 text-white' : 'border-yellow-200 bg-yellow-50/90 text-slate-950'}`}>
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-yellow-400/16">
          <Crown className="h-8 w-8 text-yellow-500" />
        </div>
        <p className="mt-4 text-xs font-black uppercase tracking-wide text-yellow-500">2026 冠军预测</p>
        <div className="mt-3 flex justify-center">
          <TeamRow team={champion} winner dark={dark} />
        </div>
        <p className={`mt-2 text-xs font-bold ${dark ? 'text-slate-400' : 'text-slate-500'}`}>由当前模型模拟淘汰赛路径生成</p>
      </div>
      <div className="mt-6">
        <p className={`mb-2 text-xs font-black uppercase tracking-wide ${dark ? 'text-slate-400' : 'text-slate-500'}`}>决赛 M104</p>
        <BracketMatchNode match={final} side="center" dark={dark} tiny={!poster} />
      </div>
      <div className={`mt-5 grid gap-3 text-left ${poster ? '' : 'text-xs'}`}>
        <div className={`rounded-2xl border p-3 ${dark ? 'border-white/10 bg-white/[0.06]' : 'border-white/70 bg-white/80'}`}>
          <p className={`text-[10px] font-black uppercase ${dark ? 'text-slate-400' : 'text-slate-500'}`}>亚军</p>
          <TeamRow team={runnerUp} dark={dark} compact />
        </div>
        <div className={`rounded-2xl border p-3 ${dark ? 'border-white/10 bg-white/[0.06]' : 'border-white/70 bg-white/80'}`}>
          <p className={`text-[10px] font-black uppercase ${dark ? 'text-slate-400' : 'text-slate-500'}`}>季军</p>
          <TeamRow team={thirdPlace} dark={dark} compact />
        </div>
      </div>
    </div>
  )
}

function BracketTree({
  projection,
  dark = false,
  poster = false,
}: {
  projection: TournamentProjection
  dark?: boolean
  poster?: boolean
}) {
  const matchMap = buildMatchMap(projection)
  return (
    <div className={`flex w-max items-center justify-start ${poster ? 'gap-10' : 'gap-7'}`}>
      <HalfBracket side="left" matchMap={matchMap} dark={dark} poster={poster} />
      <CenterPodium projection={projection} matchMap={matchMap} dark={dark} poster={poster} />
      <HalfBracket side="right" matchMap={matchMap} dark={dark} poster={poster} />
    </div>
  )
}

type PosterPathOrientation = 'landscape' | 'portrait'

type PosterPathPosition = {
  x: number
  y: number
  kind?: 'regular' | 'final' | 'third'
}

const POSTER_PATH_EDGES = [
  ...LEFT_CLUSTERS.flatMap(cluster => [
    [cluster.r32[0], cluster.r16],
    [cluster.r32[1], cluster.r16],
    [cluster.r16, cluster.qf],
  ] as Array<[number, number]>),
  ...RIGHT_CLUSTERS.flatMap(cluster => [
    [cluster.r32[0], cluster.r16],
    [cluster.r32[1], cluster.r16],
    [cluster.r16, cluster.qf],
  ] as Array<[number, number]>),
  [97, 101],
  [98, 101],
  [99, 102],
  [100, 102],
  [101, 104],
  [102, 104],
] as Array<[number, number]>

function buildPosterPathPositions(orientation: PosterPathOrientation) {
  const positions = new Map<number, PosterPathPosition>()

  if (orientation === 'landscape') {
    const clusterY = [10, 29, 63, 82]
    LEFT_CLUSTERS.forEach((cluster, index) => {
      const y = clusterY[index]
      positions.set(cluster.r32[0], { x: 9, y: y - 5 })
      positions.set(cluster.r32[1], { x: 9, y: y + 5 })
      positions.set(cluster.r16, { x: 24, y })
    })
    positions.set(97, { x: 37, y: 20 })
    positions.set(98, { x: 37, y: 72 })
    positions.set(101, { x: 37, y: 49 })

    RIGHT_CLUSTERS.forEach((cluster, index) => {
      const y = clusterY[index]
      positions.set(cluster.r32[0], { x: 91, y: y - 5 })
      positions.set(cluster.r32[1], { x: 91, y: y + 5 })
      positions.set(cluster.r16, { x: 76, y })
    })
    positions.set(99, { x: 63, y: 20 })
    positions.set(100, { x: 63, y: 72 })
    positions.set(102, { x: 63, y: 49 })
    positions.set(104, { x: 50, y: 50, kind: 'final' })
    positions.set(103, { x: 50, y: 73, kind: 'third' })
    return positions
  }

  const r32X = [8, 20, 32, 44, 56, 68, 80, 92]
  const r16X = [14, 38, 62, 86]
  LEFT_CLUSTERS.forEach((cluster, index) => {
    positions.set(cluster.r32[0], { x: r32X[index * 2], y: 8 })
    positions.set(cluster.r32[1], { x: r32X[index * 2 + 1], y: 8 })
    positions.set(cluster.r16, { x: r16X[index], y: 21 })
  })
  positions.set(97, { x: 26, y: 33 })
  positions.set(98, { x: 74, y: 33 })
  positions.set(101, { x: 50, y: 43 })

  RIGHT_CLUSTERS.forEach((cluster, index) => {
    positions.set(cluster.r32[0], { x: r32X[index * 2], y: 94 })
    positions.set(cluster.r32[1], { x: r32X[index * 2 + 1], y: 94 })
    positions.set(cluster.r16, { x: r16X[index], y: 81 })
  })
  positions.set(99, { x: 26, y: 69 })
  positions.set(100, { x: 74, y: 69 })
  positions.set(102, { x: 50, y: 59 })
  positions.set(104, { x: 50, y: 51, kind: 'final' })
  positions.set(103, { x: 83, y: 51, kind: 'third' })
  return positions
}

function PosterPathCard({
  match,
  compact = false,
  featured = false,
}: {
  match?: TournamentProjectedMatch
  compact?: boolean
  featured?: boolean
}) {
  const homeWinner = match?.winner === match?.home_team
  const awayWinner = match?.winner === match?.away_team
  return (
    <article className={`w-full rounded-2xl border border-white/16 bg-slate-950/88 shadow-2xl shadow-black/35 ${featured ? 'p-3 ring-1 ring-yellow-200/50' : compact ? 'p-1.5' : 'p-3'}`}>
      <div className="mb-1.5 flex items-center justify-between gap-1.5">
        <span className={`rounded-full bg-cyan-300/16 font-black text-cyan-100 ${compact ? 'px-1.5 py-0.5 text-[8px]' : 'px-2.5 py-0.5 text-xs'}`}>
          M{match?.id || '--'}
        </span>
        <span className={`rounded-full bg-cyan-200 text-center font-black text-slate-950 ${compact ? 'min-w-9 px-1.5 py-0.5 text-[10px]' : 'min-w-16 px-3 py-1 text-base'}`}>
          {scoreText(match)}
        </span>
      </div>
      <div className={compact ? 'space-y-1' : 'space-y-1.5'}>
        <div className={`rounded-xl px-1.5 py-1 ${homeWinner ? 'bg-cyan-300/18' : 'bg-white/[0.055]'}`}>
          <TeamRow team={match?.home_team || '待定'} winner={homeWinner} dark compact={compact} micro={compact} />
        </div>
        <div className={`rounded-xl px-1.5 py-1 ${awayWinner ? 'bg-cyan-300/18' : 'bg-white/[0.055]'}`}>
          <TeamRow team={match?.away_team || '待定'} winner={awayWinner} dark compact={compact} micro={compact} />
        </div>
      </div>
      {!compact && (
        <p className="mt-1.5 truncate rounded-full bg-white/10 px-2 py-1 text-center text-[10px] font-black text-yellow-100">
          {decisionDetail(match)}
        </p>
      )}
    </article>
  )
}

function PosterFinalHub({
  projection,
  matchMap,
  compact = false,
}: {
  projection: TournamentProjection
  matchMap: Map<number, TournamentProjectedMatch>
  compact?: boolean
}) {
  const final = matchMap.get(104)
  const third = matchMap.get(103)
  const champion = projection.knockout?.champion || final?.winner || '-'
  const runnerUp = projection.knockout?.runner_up || final?.loser || '-'
  const thirdPlace = projection.knockout?.third_place || third?.winner || '-'
  const finalHomeWinner = final?.winner === final?.home_team
  const finalAwayWinner = final?.winner === final?.away_team
  const thirdHomeWinner = third?.winner === third?.home_team
  const thirdAwayWinner = third?.winner === third?.away_team

  return (
    <section className={`rounded-[2rem] border border-yellow-200/38 bg-slate-950/90 text-white shadow-2xl shadow-black/40 ring-1 ring-cyan-200/16 ${compact ? 'w-[340px] p-3' : 'w-[520px] p-4'}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`flex items-center justify-center rounded-2xl border border-yellow-200/30 bg-yellow-300/16 ${compact ? 'h-8 w-8' : 'h-11 w-11'}`}>
            <Crown className={`${compact ? 'h-4 w-4' : 'h-6 w-6'} text-yellow-300`} />
          </span>
          <div>
            <p className={`${compact ? 'text-[9px]' : 'text-[11px]'} font-black uppercase tracking-[0.18em] text-yellow-100/80`}>M104 决赛</p>
            <p className={`${compact ? 'text-base' : 'text-2xl'} font-black text-white`}>冠军 {champion}</p>
          </div>
        </div>
        <div className={`rounded-full bg-cyan-200 text-center font-black text-slate-950 ${compact ? 'min-w-14 px-3 py-1 text-xl' : 'min-w-24 px-6 py-2 text-4xl'}`}>
          {scoreText(final)}
        </div>
      </div>

      <div className={`mt-4 grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 ${compact ? 'text-xs' : 'text-sm'}`}>
        <div className={`rounded-2xl px-3 py-2 ${finalHomeWinner ? 'bg-cyan-300/18' : 'bg-white/[0.07]'}`}>
          <TeamRow team={final?.home_team || '待定'} winner={finalHomeWinner} dark compact={compact} large={!compact} />
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 font-black text-yellow-100">{decisionDetail(final)}</span>
        <div className={`rounded-2xl px-3 py-2 ${finalAwayWinner ? 'bg-cyan-300/18' : 'bg-white/[0.07]'}`}>
          <TeamRow team={final?.away_team || '待定'} winner={finalAwayWinner} align="right" dark compact={compact} large={!compact} />
        </div>
      </div>

      <div className={`mt-4 grid grid-cols-3 gap-3 ${compact ? 'text-[10px]' : 'text-sm'}`}>
        <div className="rounded-2xl bg-yellow-300/14 px-3 py-2">
          <p className="font-black uppercase text-yellow-100/75">冠军</p>
          <TeamRow team={champion} winner dark compact={compact} micro={compact} />
        </div>
        <div className="rounded-2xl bg-white/[0.08] px-3 py-2">
          <p className="font-black uppercase text-slate-400">亚军</p>
          <TeamRow team={runnerUp} dark compact={compact} micro={compact} />
        </div>
        <div className="rounded-2xl bg-white/[0.08] px-3 py-2">
          <p className="font-black uppercase text-slate-400">季军</p>
          <TeamRow team={thirdPlace} dark compact={compact} micro={compact} />
        </div>
      </div>

      {!compact && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.065] px-4 py-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[11px] font-black uppercase tracking-[0.16em] text-cyan-100/70">M103 季军战</p>
            <span className="rounded-full bg-cyan-200 px-3 py-1 text-sm font-black text-slate-950">{scoreText(third)}</span>
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
            <TeamRow team={third?.home_team || '待定'} winner={thirdHomeWinner} dark />
            <span className="text-[10px] font-black text-yellow-100">{decisionDetail(third)}</span>
            <TeamRow team={third?.away_team || '待定'} winner={thirdAwayWinner} align="right" dark />
          </div>
        </div>
      )}
    </section>
  )
}

function PosterPathDiagram({
  projection,
  orientation,
}: {
  projection: TournamentProjection
  orientation: PosterPathOrientation
}) {
  const matchMap = buildMatchMap(projection)
  const positions = buildPosterPathPositions(orientation)
  const landscape = orientation === 'landscape'
  const nodeWidth = (position: PosterPathPosition) => {
    if (position.kind === 'final') return landscape ? 'w-[520px]' : 'w-[215px]'
    if (position.kind === 'third') return landscape ? 'w-[270px]' : 'w-[168px]'
    return landscape ? 'w-[280px]' : 'w-[128px]'
  }

  return (
      <div className={`relative overflow-hidden rounded-[2.3rem] border border-white/14 bg-slate-950 shadow-inner ${landscape ? 'h-[1080px]' : 'h-[1280px]'}`}>
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id={`posterRoute-${orientation}`} x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="#67e8f9" stopOpacity="0.24" />
            <stop offset="0.5" stopColor="#fde68a" stopOpacity="0.9" />
            <stop offset="1" stopColor="#67e8f9" stopOpacity="0.24" />
          </linearGradient>
        </defs>
        {POSTER_PATH_EDGES.map(([from, to]) => {
          const start = positions.get(from)
          const end = positions.get(to)
          if (!start || !end) return null
          const midX = (start.x + end.x) / 2
          const midY = (start.y + end.y) / 2
          const d = landscape
            ? `M ${start.x} ${start.y} C ${midX} ${start.y}, ${midX} ${end.y}, ${end.x} ${end.y}`
            : `M ${start.x} ${start.y} C ${start.x} ${midY}, ${end.x} ${midY}, ${end.x} ${end.y}`
          return <path key={`${from}-${to}`} d={d} fill="none" stroke={`url(#posterRoute-${orientation})`} strokeWidth={landscape ? 0.46 : 0.38} strokeLinecap="round" />
        })}
      </svg>

      {landscape && (
        <div className="absolute left-1/2 top-[50%] z-30 -translate-x-1/2 -translate-y-1/2">
          <PosterFinalHub projection={projection} matchMap={matchMap} />
        </div>
      )}

      {Array.from(positions.entries()).map(([id, position]) => (
        landscape && (position.kind === 'final' || position.kind === 'third') ? null : (
        <div
          key={id}
          className={`absolute z-20 -translate-x-1/2 -translate-y-1/2 ${nodeWidth(position)}`}
          style={{ left: `${position.x}%`, top: `${position.y}%` }}
        >
          <PosterPathCard match={matchMap.get(id)} compact={position.kind !== 'final' && !landscape} featured={position.kind === 'final'} />
        </div>
        )
      ))}
    </div>
  )
}

function PosterShell({
  width,
  height,
  padding,
  children,
  imagePosition = 'center center',
}: {
  width: number
  height: number
  padding: number
  children: React.ReactNode
  imagePosition?: string
}) {
  const portrait = height > width

  return (
    <div
      className="relative overflow-hidden bg-slate-950 text-white"
      style={{ width, height, padding }}
    >
      <img
        src="/wc2026-hero-north-america-stadium.png"
        alt=""
        className="absolute inset-0 h-full w-full object-cover"
        style={{
          objectPosition: imagePosition,
          filter: 'saturate(1.12) contrast(1.05) brightness(0.8)',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(90deg, rgba(3,7,18,0.96), rgba(8,15,34,0.86) 28%, rgba(8,16,36,0.80) 50%, rgba(8,15,34,0.86) 72%, rgba(3,7,18,0.96))',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(circle at 50% 18%, rgba(103,232,249,0.28), transparent 30%), radial-gradient(circle at 50% 68%, rgba(250,204,21,0.16), transparent 28%)',
        }}
      />
      <img
        src="/wc2026-messi-trophy-overlay.png"
        alt=""
        className="absolute z-[1] object-contain"
        style={{
          width: portrait ? width * 0.68 : width * 0.38,
          right: portrait ? -width * 0.24 : -width * 0.035,
          top: portrait ? height * 0.16 : height * 0.12,
          opacity: portrait ? 0.42 : 0.46,
          filter: 'saturate(1.04) contrast(1.12) brightness(1.02)',
          mixBlendMode: 'normal',
        }}
      />
      <div
        className="absolute inset-y-0 right-0 z-[2]"
        style={{
          width: portrait ? '58%' : '44%',
          background: 'linear-gradient(90deg, transparent, rgba(7,17,31,0.14) 44%, rgba(7,17,31,0.38))',
        }}
      />
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-cyan-300 via-yellow-300 to-cyan-300" />
      <div className="relative z-10 h-full">{children}</div>
    </div>
  )
}

function PosterMetaStrip({ projection, compact = false }: { projection: TournamentProjection; compact?: boolean }) {
  const items = [
    ['真实比分', `${projection.summary.actual_group_match_count} 场`],
    ['模型补齐', `${projection.summary.model_group_match_count} 场`],
    ['32 强', `${projection.summary.qualified_count} 队`],
    ['第三名规则', `Annex C #${projection.summary.third_place_option}`],
  ]

  return (
    <div className={`mx-auto mt-5 grid max-w-5xl ${compact ? 'grid-cols-2 gap-2' : 'grid-cols-4 gap-3'}`}>
      {items.map(([label, value]) => (
        <div key={label} className="rounded-2xl border border-white/12 bg-white/10 px-4 py-3 text-center shadow-2xl shadow-black/10">
          <p className={`${compact ? 'text-[10px]' : 'text-xs'} font-black uppercase text-cyan-100/70`}>{label}</p>
          <p className={`${compact ? 'text-lg' : 'text-2xl'} mt-1 font-black text-white`}>{value}</p>
        </div>
      ))}
    </div>
  )
}

function PosterHeader({
  projection,
  title,
  subtitle,
  compact = false,
}: {
  projection: TournamentProjection
  title: string
  subtitle?: string
  compact?: boolean
}) {
  return (
    <header className="text-center">
      <div className="inline-flex items-center gap-4 rounded-full border border-white/14 bg-white/10 px-5 py-2.5 shadow-2xl shadow-black/20">
        <img src="/wc2026-logo.png" alt="" className={`${compact ? 'h-10 w-10' : 'h-12 w-12'} object-contain`} />
        <span className={`${compact ? 'text-sm' : 'text-base'} font-black uppercase tracking-[0.24em] text-cyan-200`}>
          World Cup Lens
        </span>
      </div>
      <h2 className={`mx-auto mt-5 max-w-[12em] font-black leading-[1.05] text-white ${compact ? 'text-5xl' : 'text-7xl'}`}>
        {title}
      </h2>
      {subtitle && (
        <p className={`mt-4 font-black text-yellow-200 ${compact ? 'text-2xl' : 'text-3xl'}`}>{subtitle}</p>
      )}
      <PosterMetaStrip projection={projection} compact={compact} />
    </header>
  )
}

function PosterMatchCard({
  match,
  side = 'left',
  mini = false,
  featured = false,
  wide = false,
}: {
  match?: TournamentProjectedMatch
  side?: 'left' | 'right' | 'center'
  mini?: boolean
  featured?: boolean
  wide?: boolean
}) {
  const homeWinner = match?.winner === match?.home_team
  const awayWinner = match?.winner === match?.away_team
  const align = side === 'right' ? 'right' : 'left'
  const decision = decisionDetail(match)
  const audit = auditLine(match)

  if (wide) {
    return (
      <article className={`min-w-0 rounded-[1.45rem] border border-white/14 bg-slate-950/68 p-4 shadow-2xl shadow-black/25 ${featured ? 'ring-1 ring-yellow-300/40' : ''}`}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-cyan-300/18 px-3 py-1 text-sm font-black text-cyan-100">M{match?.id || '--'}</span>
            <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-slate-300">{decisionLabel(match)}</span>
          </div>
          <span className="truncate rounded-full bg-white/10 px-3 py-1 text-[11px] font-black text-slate-300">{sourceText(match)}</span>
        </div>
        <div className="grid grid-cols-[minmax(0,1fr)_6.5rem_minmax(0,1fr)] items-center gap-4">
          <div className={`rounded-2xl px-4 py-3 ${homeWinner ? 'bg-cyan-300/17' : 'bg-white/[0.065]'}`}>
            <TeamRow team={match?.home_team || '待定'} winner={homeWinner} align="left" dark large />
          </div>
          <div className="text-center">
            <div className="rounded-full bg-cyan-200 px-4 py-2 text-2xl font-black text-slate-950">{scoreText(match)}</div>
            <div className="mt-1 text-[10px] font-black uppercase tracking-wide text-slate-400">
              {match?.home_slot || match?.home_source || '主'} / {match?.away_slot || match?.away_source || '客'}
            </div>
          </div>
          <div className={`rounded-2xl px-4 py-3 ${awayWinner ? 'bg-cyan-300/17' : 'bg-white/[0.065]'}`}>
            <TeamRow team={match?.away_team || '待定'} winner={awayWinner} align="right" dark large />
          </div>
        </div>
        <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
          <p className="truncate rounded-full bg-white/[0.07] px-3 py-1.5 text-xs font-black text-cyan-100/86">
            {decision}
          </p>
          {match?.prediction?.confidence !== undefined && (
            <p className="rounded-full bg-yellow-300/14 px-3 py-1.5 text-xs font-black text-yellow-100">
              置信 {Math.round((match.prediction.confidence || 0) * 100)}%
            </p>
          )}
        </div>
        {audit && (
          <p className="mt-2 truncate rounded-full bg-yellow-300/12 px-3 py-1.5 text-xs font-black text-yellow-100">
            观点 {audit}
          </p>
        )}
      </article>
    )
  }

  return (
    <article className={`min-w-0 rounded-2xl border border-white/12 bg-slate-950/62 shadow-2xl shadow-black/20 ${featured ? 'p-4 ring-1 ring-yellow-300/35' : mini ? 'p-2' : 'p-3'}`}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className={`rounded-full bg-cyan-300/14 px-2 py-0.5 font-black text-cyan-100 ${mini ? 'text-[9px]' : 'text-xs'}`}>M{match?.id || '--'}</span>
        <span className={`truncate rounded-full bg-white/10 px-2 py-0.5 font-black text-slate-300 ${mini ? 'max-w-[4.5rem] text-[9px]' : 'max-w-[6rem] text-[10px]'}`}>{decisionLabel(match)}</span>
      </div>
      <div className="space-y-1.5">
        <div className={`rounded-xl px-2 py-1.5 ${homeWinner ? 'bg-cyan-300/16' : 'bg-white/[0.055]'}`}>
          <TeamRow team={match?.home_team || '待定'} winner={homeWinner} align={align} dark compact micro={mini} />
        </div>
        <div className={`grid grid-cols-[1fr_auto_1fr] items-center gap-2 font-black text-slate-400 ${mini ? 'text-[8px]' : 'text-[10px]'}`}>
          <span className="truncate">{match?.home_slot || match?.home_source || '主'}</span>
          <span className={`rounded-full bg-cyan-200 text-slate-950 ${mini ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-sm'}`}>{scoreText(match)}</span>
          <span className="truncate text-right">{match?.away_slot || match?.away_source || '客'}</span>
        </div>
        {!mini && match?.decided_by && match.decided_by !== 'regular_time' && (
          <p className="truncate rounded-full bg-white/[0.07] px-2 py-1 text-center text-[10px] font-black text-cyan-100/85">
            {decision}
          </p>
        )}
        {!mini && audit && (
          <p className="truncate rounded-full bg-yellow-300/12 px-2 py-1 text-center text-[10px] font-black text-yellow-100">
            观点 {audit}
          </p>
        )}
        <div className={`rounded-xl px-2 py-1.5 ${awayWinner ? 'bg-cyan-300/16' : 'bg-white/[0.055]'}`}>
          <TeamRow team={match?.away_team || '待定'} winner={awayWinner} align={align} dark compact micro={mini} />
        </div>
      </div>
    </article>
  )
}

function PosterChampionPanel({
  projection,
  matchMap,
  compact = false,
}: {
  projection: TournamentProjection
  matchMap: Map<number, TournamentProjectedMatch>
  compact?: boolean
}) {
  const final = matchMap.get(104)
  const third = matchMap.get(103)
  const champion = projection.knockout?.champion || final?.winner || '-'
  const runnerUp = projection.knockout?.runner_up || final?.loser || '-'
  const thirdPlace = projection.knockout?.third_place || third?.winner || '-'

  return (
    <section className="rounded-[2rem] border border-yellow-200/26 bg-slate-950/56 p-5 text-center shadow-2xl shadow-black/30">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl border border-yellow-200/30 bg-yellow-300/16">
        <Crown className="h-9 w-9 text-yellow-300" />
      </div>
      <p className="mt-4 text-xs font-black uppercase tracking-[0.2em] text-yellow-200">冠军预测</p>
      <div className="mt-3 flex justify-center">
        <TeamRow team={champion} winner dark compact={compact} />
      </div>
      <div className="mt-5">
        <PosterMatchCard match={final} side="center" featured mini={compact} />
      </div>
      <div className={`mt-4 grid ${compact ? 'grid-cols-2' : 'grid-cols-1'} gap-3 text-left`}>
        <div className="rounded-2xl bg-white/[0.07] px-3 py-2">
          <p className="text-[10px] font-black uppercase text-slate-400">亚军</p>
          <TeamRow team={runnerUp} dark compact micro={compact} />
        </div>
        <div className="rounded-2xl bg-white/[0.07] px-3 py-2">
          <p className="text-[10px] font-black uppercase text-slate-400">季军</p>
          <TeamRow team={thirdPlace} dark compact micro={compact} />
        </div>
      </div>
    </section>
  )
}

function PosterHalfSummary({
  side,
  matchMap,
}: {
  side: 'left' | 'right'
  matchMap: Map<number, TournamentProjectedMatch>
}) {
  const clusters = side === 'left' ? LEFT_CLUSTERS : RIGHT_CLUSTERS
  const stages = [
    { label: '32 强', ids: clusters.flatMap(cluster => cluster.r32), columns: 'grid-cols-2' },
    { label: '16 强', ids: clusters.map(cluster => cluster.r16), columns: 'grid-cols-2' },
    { label: '1/4 决赛', ids: Array.from(new Set(clusters.map(cluster => cluster.qf))), columns: 'grid-cols-2' },
    { label: '半决赛', ids: side === 'left' ? [101] : [102], columns: 'grid-cols-1' },
  ]

  return (
    <section className="rounded-[2rem] border border-white/12 bg-white/[0.075] p-4 shadow-2xl shadow-black/20">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-2xl font-black text-cyan-100">{side === 'left' ? '左半区' : '右半区'}</h3>
        <span className="rounded-full bg-cyan-300/14 px-3 py-1 text-xs font-black text-cyan-100">
          {side === 'left' ? 'M73-M84' : 'M85-M96'}
        </span>
      </div>
      <div className="space-y-3">
        {stages.map(stage => (
          <div key={stage.label} className="rounded-3xl border border-white/10 bg-slate-950/28 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-xs font-black uppercase tracking-wide text-yellow-100">{stage.label}</p>
              <span className="text-[10px] font-black text-slate-400">{stage.ids.length} 场</span>
            </div>
            <div className={`grid ${stage.columns} gap-2`}>
              {stage.ids.map(id => (
                <PosterMatchCard key={id} match={matchMap.get(id)} side={side} mini />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

const R32_IDS = [73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88]
const R16_IDS = [89, 90, 91, 92, 93, 94, 95, 96]
const QF_IDS = [97, 98, 99, 100]
const SF_IDS = [101, 102]

function PosterSectionTitle({ label, count, accent = 'cyan' }: { label: string; count?: string; accent?: 'cyan' | 'yellow' }) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h3 className={`text-2xl font-black ${accent === 'yellow' ? 'text-yellow-100' : 'text-cyan-100'}`}>{label}</h3>
      {count && (
        <span className={`rounded-full px-4 py-1.5 text-xs font-black uppercase tracking-wide ${
          accent === 'yellow' ? 'bg-yellow-300/16 text-yellow-100' : 'bg-cyan-300/14 text-cyan-100'
        }`}>
          {count}
        </span>
      )}
    </div>
  )
}

function PosterRouteCard({ match }: { match?: TournamentProjectedMatch }) {
  const homeWinner = match?.winner === match?.home_team
  const awayWinner = match?.winner === match?.away_team
  return (
    <article className="rounded-2xl border border-white/12 bg-slate-950/60 p-3 shadow-xl shadow-black/20">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="rounded-full bg-cyan-300/14 px-2.5 py-1 text-[11px] font-black text-cyan-100">M{match?.id || '--'}</span>
        <span className="truncate rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-black text-slate-300">{decisionLabel(match)}</span>
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_4.4rem_minmax(0,1fr)] items-center gap-2">
        <TeamRow team={match?.home_team || '待定'} winner={homeWinner} dark compact micro />
        <div className="rounded-full bg-cyan-200 px-2 py-1 text-center text-sm font-black text-slate-950">{scoreText(match)}</div>
        <TeamRow team={match?.away_team || '待定'} winner={awayWinner} align="right" dark compact micro />
      </div>
      {match?.decided_by && match.decided_by !== 'regular_time' && (
        <p className="mt-2 truncate rounded-full bg-white/[0.07] px-2 py-1 text-center text-[10px] font-black text-cyan-100/82">
          {decisionDetail(match)}
        </p>
      )}
    </article>
  )
}

function LandscapeBracketPoster({ projection, matchMap }: { projection: TournamentProjection; matchMap: Map<number, TournamentProjectedMatch> }) {
  const useSymmetricPathPoster = projection.summary.qualified_count >= 0
  if (useSymmetricPathPoster) {
    return (
      <PosterShell width={3200} height={1800} padding={70} imagePosition="center center">
        <PosterHeader
          projection={projection}
          title="我的 2026 世界杯完整路径预测"
        />
        <div className="mt-5">
          <PosterPathDiagram projection={projection} orientation="landscape" />
        </div>
      </PosterShell>
    )
  }

  return (
    <PosterShell width={3200} height={1800} padding={70} imagePosition="center center">
      <div className="grid grid-cols-[minmax(0,1fr)_520px] items-start gap-8">
        <div>
          <PosterHeader projection={projection} title="我的 2026 世界杯完整对阵图预测" subtitle="32 强横向大卡 · 加时/点球决胜" />
        </div>
        <div className="pt-6">
          <PosterChampionPanel projection={projection} matchMap={matchMap} />
        </div>
      </div>

      <section className="mt-7 rounded-[2.25rem] border border-white/12 bg-white/[0.07] p-5 shadow-2xl shadow-black/25">
        <PosterSectionTitle label="32 强淘汰赛对阵" count="16 场 · 横向大卡" />
        <p className="mb-3 text-xs font-black uppercase tracking-wide text-cyan-100/70">
          依据：2026世界杯加时/点球规则 · Elo/FIFA排名/xG比分矩阵 · 1998-2022淘汰赛先验
        </p>
        <div className="grid grid-cols-4 gap-4">
          {R32_IDS.map(id => (
            <PosterMatchCard key={id} match={matchMap.get(id)} wide />
          ))}
        </div>
      </section>

      <section className="mt-5 grid grid-cols-[minmax(0,1.35fr)_minmax(0,0.9fr)_minmax(0,0.55fr)] gap-5">
        <div className="rounded-[2rem] border border-white/12 bg-slate-950/45 p-4 shadow-2xl shadow-black/20">
          <PosterSectionTitle label="16 强路径" count="8 场" />
          <div className="grid grid-cols-4 gap-3">
            {R16_IDS.map(id => <PosterRouteCard key={id} match={matchMap.get(id)} />)}
          </div>
        </div>
        <div className="rounded-[2rem] border border-white/12 bg-slate-950/45 p-4 shadow-2xl shadow-black/20">
          <PosterSectionTitle label="1/4 与半决赛" count="6 场" />
          <div className="grid grid-cols-2 gap-3">
            {[...QF_IDS, ...SF_IDS].map(id => <PosterRouteCard key={id} match={matchMap.get(id)} />)}
          </div>
        </div>
        <div className="rounded-[2rem] border border-yellow-200/20 bg-yellow-300/10 p-4 shadow-2xl shadow-black/20">
          <PosterSectionTitle label="决赛与季军" count="M104 / M103" accent="yellow" />
          <div className="space-y-3">
            <PosterRouteCard match={matchMap.get(104)} />
            <PosterRouteCard match={matchMap.get(103)} />
          </div>
        </div>
      </section>
    </PosterShell>
  )
}

function BracketPoster({ projection, orientation }: { projection: TournamentProjection; orientation: 'landscape' | 'portrait' }) {
  const landscape = orientation === 'landscape'
  const matchMap = buildMatchMap(projection)

  if (!landscape) {
    const useSymmetricPathPoster = projection.summary.qualified_count >= 0
    if (useSymmetricPathPoster) {
      return (
        <PosterShell width={1080} height={1920} padding={52} imagePosition="center center">
          <PosterHeader
            projection={projection}
            title="2026 世界杯淘汰赛路径预测"
            compact
          />
          <div className="mt-6">
            <PosterPathDiagram projection={projection} orientation="portrait" />
          </div>
        </PosterShell>
      )
    }

    return (
      <PosterShell width={1080} height={1920} padding={52} imagePosition="center center">
        <PosterHeader projection={projection} title="2026 世界杯淘汰赛预测" subtitle="冠军路径 · 淘汰赛模拟" compact />
        <div className="mt-7">
          <PosterChampionPanel projection={projection} matchMap={matchMap} compact />
        </div>
        <div className="mt-6 grid grid-cols-2 gap-5">
          <PosterHalfSummary side="left" matchMap={matchMap} />
          <PosterHalfSummary side="right" matchMap={matchMap} />
        </div>
        <div className="mt-5 grid grid-cols-[1fr_1.15fr_1fr] items-end gap-4">
          <PosterMatchCard match={matchMap.get(101)} mini />
          <PosterMatchCard match={matchMap.get(104)} side="center" featured />
          <PosterMatchCard match={matchMap.get(102)} side="right" mini />
        </div>
      </PosterShell>
    )
  }

  return <LandscapeBracketPoster projection={projection} matchMap={matchMap} />
}

function PosterGroupCard({ group, compact = false }: { group: TournamentGroupProjection; compact?: boolean }) {
  return (
    <article className={`rounded-3xl border border-white/12 bg-slate-950/52 shadow-2xl shadow-black/20 ${compact ? 'p-3' : 'p-4'}`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className={`${compact ? 'text-lg' : 'text-2xl'} font-black text-cyan-100`}>{group.group} 组</h3>
        <span className="rounded-full bg-white/10 px-3 py-1 text-[10px] font-black uppercase text-slate-300">积分 / 净胜 / 进球</span>
      </div>
      <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
        {group.standings.map(row => (
          <div
            key={row.team}
            className={`grid grid-cols-[1.5rem_minmax(0,1fr)_2.2rem_2.2rem_2.2rem] items-center gap-2 rounded-2xl px-2.5 ${compact ? 'py-1.5 text-[11px]' : 'py-2 text-sm'} font-black ${
              row.rank <= 2
                ? 'bg-emerald-300/16 text-emerald-50'
                : row.qualified
                  ? 'bg-yellow-300/16 text-yellow-50'
                  : 'bg-white/[0.055] text-slate-300'
            }`}
          >
            <span className="text-center text-cyan-100">{row.rank}</span>
            <TeamRow team={row.team} winner={row.qualified} dark compact micro={compact} />
            <span className="text-right tabular-nums">{row.points}</span>
            <span className="text-right tabular-nums">{row.goal_diff >= 0 ? '+' : ''}{row.goal_diff}</span>
            <span className="text-right tabular-nums">{row.goals_for}</span>
          </div>
        ))}
      </div>
    </article>
  )
}

function PosterGroupLegend({ compact = false }: { compact?: boolean }) {
  const items = [
    { label: '小组前二直接出线', className: 'bg-emerald-300/22 border-emerald-200/35 text-emerald-50' },
    { label: '最佳第三晋级', className: 'bg-yellow-300/22 border-yellow-200/35 text-yellow-50' },
    { label: '未出线', className: 'bg-white/[0.06] border-white/12 text-slate-300' },
  ]

  return (
    <div className={`mx-auto flex flex-wrap items-center justify-center ${compact ? 'mt-4 gap-2' : 'mt-5 gap-3'}`}>
      {items.map(item => (
        <span
          key={item.label}
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-black ${compact ? 'text-[10px]' : 'text-xs'} ${item.className}`}
        >
          <span className="h-2.5 w-2.5 rounded-full bg-current" />
          {item.label}
        </span>
      ))}
    </div>
  )
}

function GroupPoster({ projection, orientation }: { projection: TournamentProjection; orientation: 'landscape' | 'portrait' }) {
  const landscape = orientation === 'landscape'

  if (!landscape) {
    return (
      <PosterShell width={1080} height={1920} padding={44} imagePosition="center center">
        <PosterHeader projection={projection} title="2026 世界杯小组出线预测" subtitle="排名色块标注 32 强归属" compact />
        <PosterGroupLegend compact />
        <div className="mt-6 grid grid-cols-2 gap-3">
          {projection.groups.map(group => (
            <PosterGroupCard key={group.group} group={group} compact />
          ))}
        </div>
      </PosterShell>
    )
  }

  return (
    <PosterShell width={1920} height={1080} padding={44} imagePosition="center center">
      <PosterHeader projection={projection} title="2026 世界杯小组出线预测" subtitle="小组排名即 32 强归属 · 颜色区分出线状态" />
      <PosterGroupLegend />
      <div className="mt-5 grid grid-cols-4 gap-3">
        {projection.groups.map(group => (
          <PosterGroupCard key={group.group} group={group} compact />
        ))}
      </div>
    </PosterShell>
  )
}

function BracketSection({
  projection,
  onExport,
  exporting,
}: {
  projection: TournamentProjection
  onExport: (kind: PosterExportKind) => void
  exporting: string | null
}) {
  return (
    <section className="glass-card p-5 sm:p-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-blue-600">
            <GitBranch className="h-4 w-4" />
            淘汰赛路径
          </p>
          <h2 className="mt-2 text-2xl font-black text-slate-950 sm:text-3xl">淘汰赛对阵模拟</h2>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-relaxed text-slate-600">
            当前模型逐场补齐 32 强淘汰赛，导出图会突出晋级路径、决赛和三甲结果。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ExportButton onClick={() => onExport('bracket-landscape')} disabled={Boolean(exporting)}>
            {exporting === 'bracket-landscape' ? '导出中...' : '横版淘汰赛海报'}
          </ExportButton>
          <ExportButton onClick={() => onExport('bracket-portrait')} disabled={Boolean(exporting)}>
            {exporting === 'bracket-portrait' ? '导出中...' : '竖版淘汰赛海报'}
          </ExportButton>
        </div>
      </div>

      {projection.knockout && (
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-3xl border border-yellow-200 bg-yellow-50/85 p-4">
            <p className="text-xs font-black uppercase text-yellow-700">冠军</p>
            <div className="mt-2"><TeamRow team={projection.knockout.champion} winner /></div>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white/80 p-4">
            <p className="text-xs font-black uppercase text-slate-500">亚军</p>
            <div className="mt-2"><TeamRow team={projection.knockout.runner_up} /></div>
          </div>
          <div className="rounded-3xl border border-amber-200 bg-amber-50/70 p-4">
            <p className="text-xs font-black uppercase text-amber-700">季军</p>
            <div className="mt-2"><TeamRow team={projection.knockout.third_place} /></div>
          </div>
        </div>
      )}

      <div className="mt-6 -mx-5 overflow-x-auto px-5 pb-4 sm:-mx-7 sm:px-7">
        <div className="min-w-[1900px] rounded-[2rem] border border-slate-900/10 bg-slate-950/92 p-4 shadow-inner sm:p-5">
          {!projection.knockout && projection.round_of_32.length === 0 ? (
            <BracketTree projection={projection} />
          ) : (
            <PosterPathDiagram projection={projection} orientation="landscape" />
          )}
        </div>
      </div>
    </section>
  )
}

export default function TournamentPage() {
  const [projection, setProjection] = useState<TournamentProjection | null>(null)
  const [loading, setLoading] = useState(true)
  const [simulating, setSimulating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { exporting, exportNode, mobilePoster, closeMobilePoster } = usePosterExport()
  const bracketLandscapeRef = useRef<HTMLDivElement>(null)
  const bracketPortraitRef = useRef<HTMLDivElement>(null)
  const groupLandscapeRef = useRef<HTMLDivElement>(null)
  const groupPortraitRef = useRef<HTMLDivElement>(null)

  const loadProjection = async (simulate = true) => {
    setLoading(!projection)
    setSimulating(Boolean(projection) && simulate)
    setError(null)
    try {
      const payload = await tournamentAPI.getProjection(simulate)
      setProjection(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
      setSimulating(false)
    }
  }

  useEffect(() => {
    void loadProjection(true)
  }, [])

  const qualifiedThirdGroups = useMemo(() => (
    projection?.best_thirds.filter(row => row.qualified).map(row => row.group).join(' / ') || '-'
  ), [projection])

  const handleExport = (kind: PosterExportKind) => {
    if (!projection) return
    const stamp = new Date().toISOString().slice(0, 10)
    const targets = {
      'bracket-landscape': [bracketLandscapeRef.current, `wc2026-knockout-bracket-landscape-${stamp}.png`, 'bracket-landscape'],
      'bracket-portrait': [bracketPortraitRef.current, `wc2026-knockout-bracket-portrait-${stamp}.png`, 'bracket-portrait'],
      'groups-landscape': [groupLandscapeRef.current, `wc2026-group-qualification-landscape-${stamp}.png`, 'groups-landscape'],
      'groups-portrait': [groupPortraitRef.current, `wc2026-group-qualification-portrait-${stamp}.png`, 'groups-portrait'],
    } as const
    const [node, fileName, label] = targets[kind]
    void exportNode(node, fileName, label)
  }

  return (
    <div className="space-y-6">
      {mobilePoster && <MobilePosterPreview poster={mobilePoster} onClose={closeMobilePoster} />}
      <section className="glass-card p-5 sm:p-7">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-blue-600">
              <Sparkles className="h-4 w-4" />
              出线预测
            </p>
            <h1 className="mt-2 text-3xl font-black text-slate-950 sm:text-4xl">小组出线与淘汰赛预测</h1>
            <p className="mt-3 max-w-4xl text-sm font-semibold leading-relaxed text-slate-600">
              已完赛场次优先使用真实比分；未完赛场次使用当前模型预测比分补齐，再按 2026 世界杯官方规则生成 32 强路径和左右半区淘汰赛树。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadProjection(false)}
              className="wc-button-gold inline-flex items-center gap-2"
              disabled={loading || simulating}
            >
              <RefreshCw className="h-4 w-4" />
              刷新出线
            </button>
            <button
              type="button"
              onClick={() => loadProjection(true)}
              className="wc-button-primary inline-flex items-center gap-2"
              disabled={loading || simulating}
            >
              <Play className="h-4 w-4" />
              {simulating ? '模拟中...' : '一键模拟冠军'}
            </button>
          </div>
        </div>
      </section>

      {loading && (
        <div className="glass-card p-10 text-center text-sm font-black text-slate-700">
          正在合并真实比分、补齐模型预测并生成淘汰赛路径...
        </div>
      )}

      {error && (
        <div className="glass-card flex items-center gap-3 p-5 text-sm font-bold text-red-700">
          <AlertCircle className="h-5 w-5" />
          出线预测加载失败：{error}
        </div>
      )}

      {projection && (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <StatusTile label="已用真实比分" value={projection.summary.actual_group_match_count} hint="来自后端 live/status 合流后的完赛比分" tone="green" />
            <StatusTile label="模型补齐场次" value={projection.summary.model_group_match_count} hint="未赛和缺比分场次由当前模型预测" tone="blue" />
            <StatusTile label="32 强名额" value={projection.summary.qualified_count} hint={`最佳第三组别：${qualifiedThirdGroups}`} tone="slate" />
            <StatusTile label="第三名规则" value={`Annex C #${projection.summary.third_place_option}`} hint="按 FIFA 2026 附录 C 对位表落位" tone="amber" />
            <StatusTile label="冠军模拟" value={projection.knockout?.champion || '-'} hint={`生成于 ${formatDate(projection.generated_at)}`} tone="green" />
          </section>

          <BasisSection projection={projection} />

          <section className="glass-card p-5 sm:p-7">
            <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-blue-600">
                  <ShieldCheck className="h-4 w-4" />
                  小组排名
                </p>
                <h2 className="mt-2 text-2xl font-black text-slate-950">小组出线表</h2>
                <div className="mt-3 flex flex-wrap gap-2 text-xs font-black">
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-950 ring-1 ring-emerald-200">小组前二直接出线</span>
                  <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-950 ring-1 ring-amber-200">最佳第三晋级</span>
                  <span className="rounded-full bg-slate-50 px-3 py-1 text-slate-600 ring-1 ring-slate-200">未出线</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <ExportButton onClick={() => handleExport('groups-landscape')} disabled={Boolean(exporting)}>
                  {exporting === 'groups-landscape' ? '导出中...' : '横版小组海报'}
                </ExportButton>
                <ExportButton onClick={() => handleExport('groups-portrait')} disabled={Boolean(exporting)}>
                  {exporting === 'groups-portrait' ? '导出中...' : '竖版小组海报'}
                </ExportButton>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {projection.groups.map(group => <GroupCard key={group.group} group={group} />)}
            </div>
          </section>

          <BracketSection projection={projection} onExport={handleExport} exporting={exporting} />

          <div className="pointer-events-none fixed -left-[10000px] top-0">
            <div ref={bracketLandscapeRef} style={{ width: 3200, height: 1800 }}><BracketPoster projection={projection} orientation="landscape" /></div>
            <div ref={bracketPortraitRef} style={{ width: 1080, height: 1920 }}><BracketPoster projection={projection} orientation="portrait" /></div>
            <div ref={groupLandscapeRef} style={{ width: 1920, height: 1080 }}><GroupPoster projection={projection} orientation="landscape" /></div>
            <div ref={groupPortraitRef} style={{ width: 1080, height: 1920 }}><GroupPoster projection={projection} orientation="portrait" /></div>
          </div>
        </>
      )}
    </div>
  )
}
