import axios from 'axios'
import { getRefresh, useAuthStore } from '../store/authStore'

const base = import.meta.env.VITE_API_URL || '/api'
const noRetry = ['/auth/login', '/auth/signup', '/auth/refresh']

export const api = axios.create({ baseURL: base, timeout: 60000 })

const auth = () => useAuthStore.getState()

let pending = null
let leaving = false

// 로그아웃 중이 아니고 로그인 상태였으면 세션 만료로 표시
const expire = (was) => auth().clear({ expired: was && !leaving })

export function refresh() {
  if (pending) return pending
  const rt = getRefresh()
  if (!rt) {
    expire(!!auth().accessToken)
    return Promise.reject(new Error('NO_REFRESH_TOKEN'))
  }
  pending = axios
    .post(`${base}/auth/refresh`, { refreshToken: rt }, { timeout: 60000 })
    .then(({ data }) => {
      auth().setAuth(data.data)
      return data.data.accessToken
    })
    .catch((e) => {
      expire(true)
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

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  auth().setAuth(data.data)
}

export async function signup(email, password) {
  const { data } = await api.post('/auth/signup', { email, password })
  return data.data
}

export async function getDocuments() {
  const { data } = await api.get('/documents')
  return Array.isArray(data.data) ? data.data : []
}

// 업로드는 적재가 끝난 뒤 응답하므로 이 요청만 180초 (API 설계서 4.1)
export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/documents', form, { timeout: 180000 })
  return data.data
}

export async function deleteDocument(id) {
  await api.delete(`/documents/${encodeURIComponent(id)}`)
}

// 질문 기록 페이지 (page 는 0부터, size 는 서버 허용 1~50)
export async function getChats(page, size) {
  const { data } = await api.get('/chats', { params: { page, size } })
  return data.data
}

export async function sendFeedback(chatId, feedback) {
  const { data } = await api.patch(`/chats/${encodeURIComponent(chatId)}/feedback`, { feedback })
  return data.data
}

export async function logout() {
  const send = () => {
    const rt = getRefresh()
    if (!rt) return Promise.resolve()
    return api.post('/auth/logout', { refreshToken: rt }, { _skip: true })
  }
  leaving = true
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
    leaving = false
    auth().clear()
  }
}
