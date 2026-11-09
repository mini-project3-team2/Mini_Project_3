import { create } from 'zustand'
import { useAuthStore } from './authStore'

// status: waiting(첫 이벤트 전) · streaming · done · error · stopped(직접 중단)
let seq = 0

const update = (id, fn) => (s) => ({ messages: s.messages.map((m) => (m.id === id ? fn(m) : m)) })

export const useChatStore = create((set) => ({
  messages: [],
  add: (question) => {
    seq += 1
    const m = { id: seq, question, answer: '', sources: [], chatId: null, feedback: null, status: 'waiting', error: null }
    set((s) => ({ messages: [...s.messages, m] }))
    return m.id
  },
  patch: (id, v) => set(update(id, (m) => ({ ...m, ...v }))),
  append: (id, text) =>
    set(update(id, (m) => ({ ...m, answer: m.answer + text, status: m.status === 'waiting' ? 'streaming' : m.status }))),
  reset: () => set({ messages: [] }),
}))

// 로그아웃 · 세션 만료 시 이전 회원의 대화를 지운다
useAuthStore.subscribe((s, prev) => {
  if (prev.member && !s.member) useChatStore.getState().reset()
})
