import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import LoadingSpinner from './LoadingSpinner'

export default function ProtectedRoute() {
  const token = useAuthStore((s) => s.accessToken)
  const ready = useAuthStore((s) => s.ready)
  const loc = useLocation()

  if (!ready) return <LoadingSpinner />
  if (!token) {
    const from = loc.pathname + loc.search
    return <Navigate to="/login" replace state={{ from }} />
  }
  return <Outlet />
}

export function GuestRoute() {
  const token = useAuthStore((s) => s.accessToken)
  const ready = useAuthStore((s) => s.ready)
  const loc = useLocation()

  if (!ready) return <LoadingSpinner />
  if (token) {
    const from = loc.state?.from
    const to = typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/chat'
    return <Navigate to={to} replace />
  }
  return <Outlet />
}
