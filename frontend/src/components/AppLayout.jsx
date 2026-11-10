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
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-line bg-white px-4 py-3 sm:flex-nowrap sm:gap-6 sm:px-6">
        <strong className="shrink-0 text-accent">AskNote</strong>
        <nav className="order-last flex w-full gap-4 sm:order-none sm:w-auto">
          {menus.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `whitespace-nowrap${isActive ? ' font-semibold text-accent' : ''}`}
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {email && <span className="ml-auto min-w-0 flex-1 truncate text-right text-sm">{email}</span>}
        <button
          type="button"
          onClick={onLogout}
          disabled={busy}
          className={`${email ? '' : 'ml-auto '}shrink-0 whitespace-nowrap rounded border border-line px-3 py-1 text-sm disabled:opacity-50`}
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
