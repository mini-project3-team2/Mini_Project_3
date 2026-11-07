import axios from 'axios'
import { getRefresh, useAuthStore } from '../store/authStore'

const base = import.meta.env.VITE_API_URL || '/api'
const noRetry = ['/auth/login', '/auth/signup', '/auth/refresh']

export const api = axios.create({ baseURL: base, timeout: 60000 })

const auth = () => useAuthStore.getState()

let pending = null

export function refresh() {
  if (pending) return pending
  const rt = getRefresh()
  if (!rt) {
    auth().clear()
    return Promise.reject(new Error('NO_REFRESH_TOKEN'))
  }
  pending = axios
    .post(`${base}/auth/refresh`, { refreshToken: rt }, { timeout: 60000 })
    .then(({ data }) => {
      auth().setAuth(data.data)
      return data.data.accessToken
    })
    .catch((e) => {
      auth().clear()
      throw e
    })
    .finally(() => {
      pending = null
    })
  return pending
}

export function restore() {
  if (auth().ready) return Promise.resolve()
  const p = getRefresh() ? refresh().catch(() => {}) : Promise.resolve()
  return p.finally(() => auth().setReady())
}

api.interceptors.request.use((c) => {
  const t = auth().accessToken
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

api.interceptors.response.use(
  (r) => r,
  async (e) => {
    const c = e.config
    if (e.response?.status !== 401 || !c || c._retry || c._skip || noRetry.includes(c.url)) {
      throw e
    }
    c._retry = true
    const cur = auth().accessToken
    if (!cur || c.headers.Authorization === `Bearer ${cur}`) await refresh()
    return api(c)
  },
)

export async function logout() {
  const send = () => {
    const rt = getRefresh()
    if (!rt) return Promise.resolve()
    return api.post('/auth/logout', { refreshToken: rt }, { _skip: true })
  }
  try {
    await send()
  } catch (e) {
    if (e.response?.status === 401) {
      try {
        await refresh()
        await send()
      } catch {
        // 실패해도 화면 토큰은 지운다
      }
    }
  } finally {
    auth().clear()
  }
}
