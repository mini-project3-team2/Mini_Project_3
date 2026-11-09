import { useCallback, useEffect, useRef } from 'react'
import { streamChat } from '../services/chatStream'
import { useChatStore } from '../store/chatStore'
import { errorMessage, serverMessage } from '../utils/errorMessage'
import { isRefusal } from '../utils/refusal'

export const CUT = '답변이 중간에 끊겼어요. 다시 질문해 주세요.'
const FAILED = '지금은 답변할 수 없습니다. 잠시 후 다시 시도해 주세요'

const isActive = (m) => m.status === 'waiting' || m.status === 'streaming'

const cleanSources = (d) =>
  Array.isArray(d)
    ? d
        .filter((s) => s && typeof s === 'object')
        .map((s) => ({
          documentId: s.documentId,
          documentName: typeof s.documentName === 'string' ? s.documentName : '',
          page: Number.isInteger(s.page) ? s.page : null,
        }))
    : []

export default function useChatStream() {
  const ctl = useRef(null)
  const busy = useChatStore((s) => s.messages.some(isActive))

  // 화면을 벗어나면 스트림 중단
  useEffect(() => () => ctl.current?.abort(), [])

  const send = useCallback(async (question) => {
    if (ctl.current) return
    const { add, append } = useChatStore.getState()
    const id = add(question)
    // 이미 done · error 로 끝난 메시지는 덮어쓰지 않는다
    const patch = (id2, v) => {
      const m = useChatStore.getState().messages.find((x) => x.id === id2)
      if (m && isActive(m)) useChatStore.getState().patch(id2, v)
    }
    const ac = new AbortController()
    ctl.current = ac

    const onEvent = (name, data) => {
      if (name === 'sources') patch(id, { sources: cleanSources(data), status: 'streaming' })
      else if (name === 'token') append(id, typeof data?.text === 'string' ? data.text : '')
      else if (name === 'done') {
        // 거절 답변은 서버 기록처럼 출처를 비운다 (관련 없는 출처를 보여 주지 않음)
        const answer = useChatStore.getState().messages.find((x) => x.id === id)?.answer ?? ''
        patch(id, { chatId: data?.chatId ?? null, status: 'done', ...(isRefusal(answer) && { sources: [] }) })
      }
      else if (name === 'error') patch(id, { status: 'error', error: { text: serverMessage(data) || FAILED } })
    }

    try {
      const ended = await streamChat(question, { signal: ac.signal, onEvent })
      if (!ended && !ac.signal.aborted) patch(id, { status: 'error', error: { text: CUT } })
    } catch (e) {
      if (ac.signal.aborted) patch(id, { status: 'stopped' })
      else patch(id, { status: 'error', error: { text: errorMessage(e), code: e?.response?.data?.code } })
    } finally {
      if (ctl.current === ac) ctl.current = null
    }
  }, [])

  const stop = useCallback(() => ctl.current?.abort(), [])

  return { send, stop, busy }
}
