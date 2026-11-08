import { create } from 'zustand'
import { deleteDocument, getDocuments, uploadDocument } from '../services/api'
import { errorMessage } from '../utils/errorMessage'
import { checkPdf } from '../utils/validate'
import { useAuthStore } from './authStore'

const TOO_LARGE = '10MB 이하의 PDF만 올릴 수 있어요.'
const TIMEOUT = '자료 처리 시간이 너무 오래 걸렸어요. 잠시 후 목록을 확인하거나 다시 시도해 주세요.'

// 서버 message 가 없을 때(nginx HTML 오류 등)만 쓰는 문구
const uploadErrors = {
  413: TOO_LARGE,
  502: '지금은 자료를 처리할 수 없어요. 잠시 후 다시 시도해 주세요.',
  504: TIMEOUT,
}

const uploadMessage = (e) => (e?.code === 'ECONNABORTED' || e?.code === 'ETIMEDOUT' ? TIMEOUT : errorMessage(e, uploadErrors))

const initial = {
  items: null, // null: 아직 못 불러옴
  loadError: '',
  uploading: null, // { name, size }
  uploadError: '',
  deletingId: null,
  actionError: '',
  notice: '',
}

// gen: 로그아웃 후 늦게 도착한 응답이 다음 회원 화면에 섞이지 않게 / seq: 오래된 목록 응답 무시
let gen = 0
let seq = 0

export const useDocumentStore = create((set, get) => ({
  ...initial,

  load: async () => {
    const g = gen
    const s = ++seq
    set({ loadError: '' })
    try {
      const items = await getDocuments()
      if (g === gen && s === seq) set({ items })
    } catch (e) {
      if (g === gen && s === seq && !get().items) set({ loadError: errorMessage(e) })
    }
  },

  upload: async (file) => {
    if (get().uploading) return
    const bad = checkPdf(file)
    if (bad) return set({ uploadError: bad, notice: '' })

    const g = gen
    set({ uploading: { name: file.name, size: file.size }, uploadError: '', actionError: '', notice: '' })
    try {
      const d = await uploadDocument(file)
      if (g !== gen) return
      seq += 1
      const items = get().items
      set({
        uploading: null,
        items: items ? [d, ...items.filter((x) => x.id !== d.id)] : null,
        notice: `${d.originalFilename} 자료를 올렸어요.`,
      })
      if (!items) get().load()
    } catch (e) {
      if (g === gen) set({ uploading: null, uploadError: uploadMessage(e) })
    }
  },

  remove: async (id) => {
    if (get().deletingId != null) return
    const g = gen
    const drop = () => {
      seq += 1
      set({ items: (get().items ?? []).filter((x) => x.id !== id) })
    }
    set({ deletingId: id, actionError: '', uploadError: '', notice: '' })
    try {
      await deleteDocument(id)
      if (g !== gen) return
      drop()
      set({ notice: '자료를 삭제했어요.' })
    } catch (e) {
      if (g !== gen) return
      if (e?.response?.status === 404) drop()
      set({ actionError: errorMessage(e) })
    } finally {
      if (g === gen) set({ deletingId: null })
    }
  },

  setUploadError: (uploadError) => set({ uploadError, notice: '' }),

  reset: () => {
    gen += 1
    set(initial)
  },
}))

// 로그아웃 · 세션 만료 시 이전 회원의 자료 목록을 지운다
useAuthStore.subscribe((s, prev) => {
  if (prev.member && !s.member) useDocumentStore.getState().reset()
})
