import { Link, useLocation, Outlet } from 'react-router-dom'
import { BarChart3, CalendarDays, ClipboardCheck, GitBranch, Home, LogOut, Menu, Radio, Target, Ticket, Trophy, X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import clsx from 'clsx'
import type { Match } from '../services/wc2026-data'
import { matchAPI } from '../services/api'
import { getPredictMatchPath } from '../utils/navigation'

const navItems: { path: string; label: string; icon: LucideIcon }[] = [
  { path: '/', label: '首页', icon: Home },
  { path: '/predict', label: '预测', icon: Target },
  { path: '/lottery', label: '竞猜', icon: Ticket },
  { path: '/matches', label: '比赛', icon: CalendarDays },
  { path: '/teams', label: '球队', icon: Trophy },
  { path: '/stats', label: '数据', icon: BarChart3 },
  { path: '/reviews', label: '复盘', icon: ClipboardCheck },
  { path: '/tournament', label: '出线', icon: GitBranch },
]

interface LayoutProps {
  authEnabled?: boolean
  onLogout?: () => void | Promise<void>
}

export default function Layout({ authEnabled = false, onLogout }: LayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [liveMatch, setLiveMatch] = useState<Match | null>(null)
  const location = useLocation()
  const liveGoal = liveMatch?.report?.goals?.[liveMatch.report.goals.length - 1]
  const isWideWorkspace = location.pathname === '/tournament'

  useEffect(() => {
    let active = true
    const fetchLiveMatch = async () => {
      try {
        const matches = await matchAPI.getMatchesStrict(undefined, 'live')
        if (active) setLiveMatch(matches[0] || null)
      } catch {
        if (active) setLiveMatch(null)
      }
    }

    void fetchLiveMatch()
    const timer = window.setInterval(fetchLiveMatch, 60000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    const originalTitle = document.title
    if (liveGoal && liveMatch) {
      document.title = `进球! ${liveGoal.team} ${liveGoal.player} | World Cup 26`
    } else if (liveMatch) {
      document.title = `比赛进行中 ${liveMatch.home_team} vs ${liveMatch.away_team} | World Cup 26`
    }
    return () => {
      document.title = originalTitle
    }
  }, [liveGoal, liveMatch])

  const handleLogout = async () => {
    await onLogout?.()
    setMobileMenuOpen(false)
  }

  return (
    <div className={clsx('app-shell flex min-h-screen flex-col', liveMatch && 'live-event-active')}>
      {/* 桌面端 Apple 风格侧边 Dock */}
      <aside className="apple-sidebar hidden lg:flex">
        <Link to="/" className="mb-5 flex flex-col items-center gap-2 text-center">
          <img src="/wc2026-logo.png" alt="FIFA World Cup 2026" className="wc-hero-logo h-12 w-12 object-contain" />
          <span className="text-[10px] font-black uppercase leading-tight text-slate-700">World Cup 26</span>
        </Link>

        <nav className="flex w-full flex-1 flex-col items-center justify-center gap-3">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'apple-dock-link',
                location.pathname === item.path ? 'apple-dock-link-active' : ''
              )}
            >
              <item.icon className="h-5 w-5" strokeWidth={1.85} aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {authEnabled && (
          <button type="button" onClick={handleLogout} className="apple-dock-link mt-4">
            <LogOut className="h-5 w-5" strokeWidth={1.85} aria-hidden="true" />
            <span>退出</span>
          </button>
        )}
      </aside>

      {/* 移动端顶部导航栏 */}
      <header className="sticky top-0 z-50 px-4 sm:px-6 lg:hidden">
        <div className="nav-shell mx-auto max-w-[1400px] px-4 sm:px-5">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-3">
              <img src="/wc2026-logo.png" alt="FIFA World Cup 2026" className="wc-hero-logo w-10 h-10 object-contain" />
              <div>
                <h1 className="text-sm md:text-base font-black text-slate-900 font-display">FIFA WORLD CUP 26</h1>
                <p className="text-xs text-slate-500">美加墨世界杯AI预测模型</p>
              </div>
            </Link>

            {/* 移动端菜单按钮 */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-600 hover:bg-slate-200/60"
              aria-label={mobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'}
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* 移动端导航菜单 */}
        {mobileMenuOpen && (
          <div className="mobile-nav-panel mx-auto max-w-[1400px]">
            <nav className="px-4 py-2 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={clsx(
                    'nav-link w-full',
                    location.pathname === item.path
                      ? 'nav-link-active'
                      : ''
                  )}
                >
                  <item.icon className="w-4 h-4" aria-hidden="true" />
                  {item.label}
                </Link>
              ))}
              {authEnabled && (
                <button
                  type="button"
                  onClick={handleLogout}
                  className="nav-link w-full"
                >
                  <LogOut className="w-4 h-4" aria-hidden="true" />
                  退出登录
                </button>
              )}
            </nav>
          </div>
        )}
      </header>

      {liveMatch && (
        <Link
          to={getPredictMatchPath(liveMatch.id)}
          className="live-event-banner mx-auto mt-2 flex w-[calc(100%-2rem)] max-w-[1400px] items-center gap-3 rounded-lg border border-red-200 bg-white/90 px-4 py-2 text-sm font-bold text-slate-900 shadow-lg shadow-red-100/60 backdrop-blur transition-transform hover:-translate-y-0.5 lg:ml-[12rem]"
        >
          <span className="live-event-dot inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-600 text-white">
            <Radio className="h-4 w-4" />
          </span>
          <span className="min-w-0 flex-1 truncate">
            {liveGoal
              ? `实时进球 · ${liveGoal.minute}' ${liveGoal.team} ${liveGoal.player}${liveGoal.assist ? `，助攻 ${liveGoal.assist}` : ''}`
              : `比赛进行中 · ${liveMatch.home_team} vs ${liveMatch.away_team}`}
          </span>
          <span className="hidden rounded-full bg-red-50 px-2.5 py-1 text-xs text-red-700 sm:inline">点击进入预测</span>
        </Link>
      )}

      {/* 主要内容区 */}
      <main
        className={clsx(
          'relative z-10 mx-auto w-full flex-1 px-4 py-5 sm:px-6 md:py-8 lg:ml-[12rem] lg:w-[calc(100%-13.5rem)] lg:px-8',
          isWideWorkspace ? 'max-w-none' : 'max-w-[1500px]'
        )}
      >
        <Outlet />
      </main>

      {/* 页脚 */}
      <footer className="relative z-10 mt-auto border-t border-white/30 bg-white/20 backdrop-blur-xl lg:ml-[10.5rem]">
        <div className="mx-auto max-w-[1400px] px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-slate-500">
            © 2026 FIFA World Cup Prediction Model. Built for football fans.
          </p>
        </div>
      </footer>
    </div>
  )
}
