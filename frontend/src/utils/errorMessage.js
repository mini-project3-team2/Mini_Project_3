export const NETWORK = '서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.'

// 서버 message 를 쓸 수 없을 때의 공통 기본 문구
export const DEFAULTS = {
  400: '입력값을 확인해 주세요',
  401: '로그인이 필요합니다',
  403: '접근 권한이 없습니다',
  404: '요청한 내용을 찾을 수 없습니다',
  500: '일시적인 오류가 발생했습니다',
  503: '지금은 처리할 수 없습니다. 잠시 후 다시 시도해 주세요',
}

const MAX = 200

const pick = (o, k) => (k != null && Object.hasOwn(o, k) ? o[k] : undefined)

// JSON 이 아닌 응답(nginx HTML 오류 등)은 문자열이라 body 로 보지 않는다
const bodyOf = (res) => (res?.data && typeof res.data === 'object' ? res.data : null)

export function serverMessage(body) {
  if (typeof body?.message !== 'string') return ''
  return Array.from(body.message.trim()).slice(0, MAX).join('')
}

// 우선순위: 서버 message → 화면별 map(code → 상태) → DEFAULTS → 500 문구
// 응답 자체가 없으면(네트워크 오류 · 타임아웃) NETWORK
export function errorMessage(err, map = {}) {
  const res = err?.response
  if (!res) return NETWORK
  const body = bodyOf(res)
  const msg = serverMessage(body)
  if (msg) return msg
  const m = pick(map, body?.code) ?? pick(map, res.status) ?? pick(DEFAULTS, res.status) ?? DEFAULTS[500]
  return typeof m === 'function' ? m(body ?? {}) : m
}

const fmt = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul',
  month: 'long',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

const NO_ZONE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?$/

// 서버 날짜는 시간대 표시가 없는 한국 시간
export function formatDateTime(s) {
  if (typeof s !== 'string') return ''
  const d = new Date(NO_ZONE.test(s) ? `${s}+09:00` : s)
  return Number.isNaN(d.getTime()) ? '' : fmt.format(d)
}

export function lockedText(err) {
  const res = err?.response
  if (res?.status !== 423) return ''
  const t = formatDateTime(bodyOf(res)?.data?.lockedUntil)
  return t ? `${t}까지 잠겨 있어요` : ''
}
