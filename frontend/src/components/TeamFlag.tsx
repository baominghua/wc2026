import { TEAMS } from '../services/wc2026-data'
import { getFlagUrl } from '../utils/flags'

// 国旗图片组件 - 替代emoji国旗，兼容所有系统
interface TeamFlagProps {
  flagCode?: string
  teamName?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const sizeMap = {
  sm: { width: 20, height: 14, img: 20 },
  md: { width: 32, height: 22, img: 40 },
  lg: { width: 48, height: 33, img: 80 },
  xl: { width: 64, height: 44, img: 80 },
}

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

function resolveFlagCode(teamName?: string): string | undefined {
  if (!teamName) return undefined
  const normalizedName = teamNameAliases[teamName] || teamName
  return TEAMS.find(t => t.name === normalizedName || t.code === teamName)?.flagCode
}

export default function TeamFlag({ flagCode, teamName, size = 'md', className = '' }: TeamFlagProps) {
  const code = flagCode || resolveFlagCode(teamName)
  const s = sizeMap[size]

  if (!code) {
    return <span className={`inline-block ${className}`} style={{ width: s.width, height: s.height, background: '#e5e7eb', borderRadius: 2 }} />
  }

  return (
    <img
      src={getFlagUrl(code, s.img)}
      alt={teamName || code}
      className={`inline-block object-cover ${className}`}
      style={{ width: s.width, height: s.height, borderRadius: 2, boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }}
      loading="lazy"
      onError={(e) => {
        // 图片加载失败时显示国旗emoji作为后备
        const target = e.target as HTMLImageElement
        const team = TEAMS.find(t => t.flagCode === code)
        if (team?.flag) {
          target.style.display = 'none'
          const span = document.createElement('span')
          span.textContent = team.flag
          span.style.fontSize = `${s.width * 0.7}px`
          target.parentNode?.appendChild(span)
        }
      }}
    />
  )
}
