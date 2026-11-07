import { create } from 'zustand'

const KEY = 'refreshToken'

export function getRefresh() {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

function setRefresh(v) {
  try {
    if (v) sessionStorage.setItem(KEY, v)
    else sessionStorage.removeItem(KEY)
  } catch {
    // sessionStorage 사용 불가 시 무시
  }
}

export const useAuthStore = create((set) => ({
  accessToken: null,
  member: null,
  ready: false,
  expired: false,
  setAuth: (d) => {
    setRefresh(d.refreshToken)
    set({ accessToken: d.accessToken, member: d.member ?? null, expired: false })
  },
  clear: ({ expired = false } = {}) => {
    setRefresh(null)
    set({ accessToken: null, member: null, expired })
  },
  setReady: () => set({ ready: true }),
}))
