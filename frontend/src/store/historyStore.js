import { create } from 'zustand'
import { getChats } from '../services/api'
import { errorMessage } from '../utils/errorMessage'
import { useAuthStore } from './authStore'

export const PAGE_SIZE = 10

const initial = {
  data: null, // { content, page, size, totalElements, totalPages } — 마지막으로 받은 페이지
  loading: false,
  error: '',
}

// gen: 로그아웃 후 늦은 응답 무시 / seq: 페이지를 빠르게 옮길 때 오래된 응답 무시
let gen = 0
let seq = 0

export const useHistoryStore = create((set) => ({
  ...initial,

  load: async (page) => {
    const g = gen
    const s = ++seq
    set({ loading: true, error: '' })
    try {
      const data = await getChats(page, PAGE_SIZE)
      if (g === gen && s === seq) set({ data, loading: false })
    } catch (e) {
      if (g === gen && s === seq) set({ loading: false, error: errorMessage(e) })
    }
  },

  reset: () => {
    gen += 1
    set(initial)
  },
}))

// 로그아웃 · 세션 만료 시 이전 회원의 기록을 지운다
useAuthStore.subscribe((s, prev) => {
  if (prev.member && !s.member) useHistoryStore.getState().reset()
})
