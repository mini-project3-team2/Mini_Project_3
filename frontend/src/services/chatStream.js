import { useAuthStore } from '../store/authStore'
import { refresh } from './api'

const base = import.meta.env.VITE_API_URL || '/api'

// SSE 파서: 청크 경계에서 잘린 줄은 다음 청크와 이어 붙이고, "data:" · "data: " 둘 다 처리
export function createParser(onEvent) {
  let buf = ''
  let event = ''
  let data = []

  const flush = () => {
    if (data.length) {
      try {
        onEvent(event || 'message', JSON.parse(data.join('\n')))
      } catch {
        // JSON 이 아닌 data 는 무시
      }
    }
    event = ''
    data = []
  }

  const line = (raw) => {
    const l = raw.endsWith('\r') ? raw.slice(0, -1) : raw
    if (l === '') return flush()
    if (l.startsWith(':')) return
    const i = l.indexOf(':')
    const key = i < 0 ? l : l.slice(0, i)
    let val = i < 0 ? '' : l.slice(i + 1)
    if (val.startsWith(' ')) val = val.slice(1)
    if (key === 'event') event = val
    else if (key === 'data') data.push(val)
  }

  return {
    push(chunk) {
      buf += chunk
      const lines = buf.split('\n')
      buf = lines.pop()
      lines.forEach(line)
    },
    end() {
      if (buf) line(buf)
      buf = ''
      flush()
    },
  }
}

async function httpError(res) {
  let data = null
  try {
    data = await res.json()
  } catch {
    // JSON 이 아닌 응답 (nginx HTML 오류 등)
  }
  return Object.assign(new Error('HTTP_ERROR'), { response: { status: res.status, data } })
}

async function post(question, signal, retried) {
  const t = useAuthStore.getState().accessToken
  const headers = { 'Content-Type': 'application/json', Accept: 'text/event-stream, application/json' }
  if (t) headers.Authorization = `Bearer ${t}`
  const res = await fetch(`${base}/chats/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ question }),
    signal,
  })

  // axios 인터셉터와 같은 조건: 보낸 토큰이 아직 현재 토큰이면 재발급, 이미 바뀌었으면 바로 재시도
  if (res.status === 401 && !retried) {
    res.body?.cancel().catch(() => {})
    const cur = useAuthStore.getState().accessToken
    if (!cur || cur === t) await refresh()
    return post(question, signal, true)
  }
  if (!res.ok) throw await httpError(res)
  return res
}

// done · error 를 받으면 true, 그 전에 스트림이 끝나면 false. 타임아웃은 두지 않는다 (서버가 끊음)
export async function streamChat(question, { signal, onEvent }) {
  const res = await post(question, signal, false)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let ended = false
  const parser = createParser((name, data) => {
    if (ended) return
    if (name === 'done' || name === 'error') ended = true
    onEvent(name, data)
  })

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    parser.push(dec.decode(value, { stream: true }))
    if (ended) {
      reader.cancel().catch(() => {})
      return true
    }
  }
  parser.push(dec.decode())
  parser.end()
  return ended
}
