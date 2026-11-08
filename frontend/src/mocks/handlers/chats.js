import { http, HttpResponse } from 'msw'
import notFound from '../../../../mock-data/responses/chats/feedback.404-chat-not-found.json'
import noDocument from '../../../../mock-data/responses/chats/stream.400-no-document.json'
import invalidInput from '../../../../mock-data/responses/common/400-invalid-input.json'
import unauthorized from '../../../../mock-data/responses/common/401-unauthorized.json'
import forbidden from '../../../../mock-data/responses/common/403-forbidden.json'
import errorEvents from '../../../../mock-data/sse/stream-error.events.json'
import notFoundEvents from '../../../../mock-data/sse/stream-not-found.events.json'
import successEvents from '../../../../mock-data/sse/stream-success.events.json'
import { authMember, db, localIso, save } from '../db'
import { API, fail, ok, readJson } from '../respond'

const MAX_SIZE = 50
const MAX_Q = 1000
const INT_MAX = 2147483647
const FEEDBACK = ['HELPFUL', 'NOT_HELPFUL']

const invalid = (message) => fail(400, { ...invalidInput, message })

// Spring @RequestParam(int) 처럼: 없거나 빈 값은 기본값, 정수가 아니면 NaN
function intParam(v, def) {
  if (v == null || v === '') return def
  const n = Number(v)
  return /^-?\d+$/.test(v) && Math.abs(n) <= INT_MAX ? n : NaN
}

const view = (c) => ({
  id: c.id,
  question: c.question,
  answer: c.answer,
  sources: c.sources,
  feedback: c.feedback,
  createdAt: c.createdAt,
})

const rand = (a, b) => a + Math.random() * (b - a)
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

// Spring SseEmitter 는 콜론 뒤 공백 없음, mock-data/sse/*.txt 는 공백 있음
const frame = (sp) => (event, data) => `event:${sp}${event}\ndata:${sp}${JSON.stringify(data)}\n\n`
const spring = frame('')
const spaced = frame(' ')

// 예시 출처를 로그인 회원의 READY 자료로 바꾼다
const ownSources = (list, ready) =>
  list.map((s) => {
    const d = ready.find((x) => x.id === s.documentId) ?? ready[0]
    return { documentId: d.id, documentName: d.originalFilename, page: s.page }
  })

function scenario(question, ready) {
  const body = (list) => list.filter((e) => e.event === 'token' || e.event === 'error')
  if (question.includes('오류')) {
    const src = errorEvents.find((e) => e.event === 'sources').data
    return { fmt: spring, sources: ownSources(src, ready), events: body(errorEvents), fail: true }
  }
  if (question.includes('없는내용')) {
    return { fmt: spaced, sources: [], events: body(notFoundEvents) }
  }
  // 긴 답변 확인용: 정상 답변 조각을 문단으로 4번 반복
  if (question.includes('긴답변')) {
    const src = successEvents.find((e) => e.event === 'sources').data
    const tokens = body(successEvents)
    const events = [1, 2, 3, 4].flatMap((n) => [
      ...(n > 1 ? [{ event: 'token', data: { text: '\n\n' } }] : []),
      { event: 'token', data: { text: `${n}. ` } },
      ...tokens,
    ])
    return { fmt: spring, sources: ownSources(src, ready), events }
  }
  const src = successEvents.find((e) => e.event === 'sources').data
  return { fmt: spring, sources: ownSources(src, ready), events: body(successEvents) }
}

function streamAnswer(request, m, question, ready) {
  const s = scenario(question, ready)
  const enc = new TextEncoder()
  let stop = false
  request.signal?.addEventListener('abort', () => {
    stop = true
  })

  const stream = new ReadableStream({
    async start(ctl) {
      const send = (event, data) => {
        if (stop) return false
        ctl.enqueue(enc.encode(s.fmt(event, data)))
        return true
      }
      try {
        await wait(rand(1500, 2000))
        if (!send('sources', s.sources)) return
        for (const e of s.events) {
          await wait(rand(40, 80))
          if (!send(e.event, e.data)) return
        }
        if (!s.fail) {
          await wait(rand(40, 80))
          if (stop) return
          const chat = {
            id: Math.max(0, ...db.chats.map((c) => c.id)) + 1,
            memberId: m.id,
            question,
            answer: s.events.map((e) => e.data.text).join(''),
            sources: s.sources,
            feedback: null,
            createdAt: localIso(),
          }
          db.chats.unshift(chat)
          save()
          send('done', { chatId: chat.id })
        }
        if (!stop) ctl.close()
      } catch {
        stop = true
      }
    },
    cancel() {
      stop = true
    },
  })

  return new HttpResponse(stream, {
    headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
  })
}

export const chatHandlers = [
  http.get(`${API}/chats`, ({ request }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    const q = new URL(request.url).searchParams
    const page = intParam(q.get('page'), 0)
    const size = intParam(q.get('size'), 10)
    if (!(page >= 0) || !(size >= 1 && size <= MAX_SIZE)) return fail(400, invalidInput)

    const mine = db.chats.filter((c) => c.memberId === m.id)
    return ok({
      content: mine.slice(page * size, page * size + size).map(view),
      page,
      size,
      totalElements: mine.length,
      totalPages: Math.ceil(mine.length / size),
    })
  }),

  http.patch(`${API}/chats/:id/feedback`, async ({ request, params }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    const { feedback } = await readJson(request)
    if (!/^\d+$/.test(params.id) || !FEEDBACK.includes(feedback)) return fail(400, invalidInput)

    const c = db.chats.find((x) => x.id === Number(params.id))
    if (!c) return fail(404, notFound)
    if (c.memberId !== m.id) return fail(403, forbidden)
    c.feedback = feedback
    save()
    return ok({ id: c.id, feedback: c.feedback })
  }),

  // 검증 · 자료 확인은 스트림 시작 전 → 실패하면 Accept 와 상관없이 JSON
  http.post(`${API}/chats/stream`, async ({ request }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    let body
    try {
      body = await request.json()
    } catch {
      return fail(400, invalidInput)
    }
    const q = body?.question
    if (q != null && typeof q !== 'string') return fail(400, invalidInput)
    if (!q || !q.trim()) return invalid('질문을 입력해 주세요')
    if (q.length > MAX_Q) return invalid('질문은 1000자 이하여야 합니다')

    const ready = db.documents.filter((d) => d.memberId === m.id && d.status === 'READY')
    if (!ready.length) return fail(400, noDocument)

    return streamAnswer(request, m, q.trim(), ready)
  }),
]
