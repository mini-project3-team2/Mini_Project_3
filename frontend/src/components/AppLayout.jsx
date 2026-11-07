import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { logout } from '../services/api'
import { useAuthStore } from '../store/authStore'

const menus = [
  ['/chat', 'AI 학습 채팅'],
  ['/documents', '내 자료'],
  ['/history', '질문 기록'],
]

export default function AppLayout() {
  const email = useAuthStore((s) => s.member?.email)
  const nav = useNavigate()
  const [busy, setBusy] = useState(false)

  const onLogout = async () => {
    setBusy(true)
    await logout()
    nav('/login', { replace: true })
  }

  return (
    <>
      <header className="flex items-center gap-6 border-b border-line bg-white px-6 py-3">
        <strong className="text-accent">AskNote</strong>
        <nav className="flex gap-4">
          {menus.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => (isActive ? 'font-semibold text-accent' : '')}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {email && <span className="ml-auto text-sm">{email}</span>}
        <button
          type="button"
          onClick={onLogout}
          disabled={busy}
          className={`${email ? '' : 'ml-auto '}rounded border border-line px-3 py-1 text-sm disabled:opacity-50`}
        >
          로그아웃
        </button>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </>
  )
}
