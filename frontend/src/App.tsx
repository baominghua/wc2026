import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import PredictPage from './pages/PredictPage'
import TeamsPage from './pages/TeamsPage'
import MatchesPage from './pages/MatchesPage'
import TeamDetail from './pages/TeamDetail'
import MatchDetail from './pages/MatchDetail'
import StatsPage from './pages/StatsPage'
import LotteryPage from './pages/LotteryPage'
import LoginPage from './pages/LoginPage'
import ReviewPage from './pages/ReviewPage'
import TournamentPage from './pages/TournamentPage'
import { authAPI, type AuthStatus } from './services/api'

function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null)

  useEffect(() => {
    let mounted = true
    authAPI.getStatus()
      .then((status) => {
        if (mounted) setAuthStatus(status)
      })
      .catch(() => {
        if (mounted) setAuthStatus({ enabled: false, authenticated: true })
      })

    const handleAuthRequired = () => {
      setAuthStatus({ enabled: true, authenticated: false })
    }
    window.addEventListener('wc2026-auth-required', handleAuthRequired)

    return () => {
      mounted = false
      window.removeEventListener('wc2026-auth-required', handleAuthRequired)
    }
  }, [])

  const handleLoginSuccess = () => {
    setAuthStatus({ enabled: true, authenticated: true })
  }

  const handleLogout = async () => {
    await authAPI.logout()
    setAuthStatus({ enabled: true, authenticated: false })
  }

  if (!authStatus) {
    return (
      <div className="relative z-10 flex min-h-screen items-center justify-center px-4">
        <div className="glass-card px-6 py-5 text-center text-sm font-black text-slate-800">
          正在检查访问权限...
        </div>
      </div>
    )
  }

  if (authStatus.enabled && !authStatus.authenticated) {
    return <LoginPage onSuccess={handleLoginSuccess} />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout authEnabled={authStatus.enabled} onLogout={handleLogout} />}>
          <Route index element={<HomePage />} />
          <Route path="predict" element={<PredictPage />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="teams/:id" element={<TeamDetail />} />
          <Route path="matches" element={<MatchesPage />} />
          <Route path="matches/:id" element={<MatchDetail />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="lottery" element={<LotteryPage />} />
          <Route path="reviews" element={<ReviewPage />} />
          <Route path="tournament" element={<TournamentPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
