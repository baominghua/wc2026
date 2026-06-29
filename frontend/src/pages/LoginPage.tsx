import { useState, type FormEvent } from 'react'
import { Loader2, LockKeyhole, ShieldCheck, Trophy } from 'lucide-react'
import { authAPI } from '../services/api'

interface LoginPageProps {
  onSuccess: () => void
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!password.trim()) {
      setError('请输入管理员密码')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const status = await authAPI.login(password)
      if (status.authenticated) onSuccess()
    } catch (err) {
      setError(err instanceof Error && err.message === 'PASSWORD_INVALID'
        ? '管理员密码不正确'
        : '登录失败，请稍后再试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="relative z-10 flex min-h-screen items-center justify-center px-4 py-8">
      <section className="glass-card w-full max-w-md overflow-hidden p-6 sm:p-8">
        <div className="mb-7 flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-[26px] border border-white/80 bg-white/70 shadow-lg shadow-slate-900/10 backdrop-blur">
            <img src="/wc2026-logo.png" alt="World Cup 26" className="h-11 w-11 object-contain" />
          </div>
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-xs font-black uppercase tracking-normal text-blue-600">
              <Trophy className="h-3.5 w-3.5" />
              World Cup 26
            </p>
            <h1 className="mt-1 text-2xl font-black leading-tight text-slate-950 sm:text-3xl">管理员登录</h1>
            <p className="mt-1 text-sm font-semibold text-slate-600">美加墨世界杯AI预测模型</p>
          </div>
        </div>

        <div className="mb-6 rounded-[24px] border border-white/70 bg-white/62 p-4 text-sm font-semibold leading-6 text-slate-700 shadow-inner">
          <div className="mb-2 flex items-center gap-2 text-slate-950">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            访问保护已开启
          </div>
          外部访问会先进入此登录页，赛事数据、预测接口和统计接口需要管理员会话后才会开放。
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-2 flex items-center gap-2 text-sm font-black text-slate-800">
              <LockKeyhole className="h-4 w-4 text-blue-600" />
              管理员密码
            </span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="w-full rounded-[22px] border border-white/80 bg-white/84 px-4 py-3 text-base font-bold text-slate-950 outline-none transition focus:border-blue-400 focus:ring-4 focus:ring-blue-500/15"
              placeholder="输入 ADMIN_PASSWORD"
            />
          </label>

          {error && (
            <div className="rounded-[18px] border border-red-200 bg-red-50/86 px-4 py-3 text-sm font-bold text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="wc-button-primary flex w-full items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShieldCheck className="h-5 w-5" />}
            {submitting ? '正在验证' : '进入系统'}
          </button>
        </form>
      </section>
    </main>
  )
}
