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
      <header>
        <strong>AskNote</strong>
        <nav>
          {menus.map(([to, label]) => (
            <NavLink key={to} to={to}>
              {label}
            </NavLink>
          ))}
        </nav>
        {email && <span>{email}</span>}
        <button type="button" onClick={onLogout} disabled={busy}>
          로그아웃
        </button>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  )
}
