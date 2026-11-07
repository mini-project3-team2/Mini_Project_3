import seed from '../../../mock-data/data/members.json'

const KEY = 'msw:db'
const ACCESS_TTL = 900

function load() {
  try {
    const s = JSON.parse(sessionStorage.getItem(KEY))
    if (s) return s
  } catch {
    // 저장된 값이 없거나 깨졌으면 초기값 사용
  }
  return { members: structuredClone(seed), access: {}, refresh: {}, seq: 0 }
}

export const db = load()

export function save() {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(db))
  } catch {
    // sessionStorage 사용 불가 시 무시
  }
}

const has = (o, k) => typeof k === 'string' && Object.hasOwn(o, k)

export const findByEmail = (email) => db.members.find((m) => m.email === email)
export const findById = (id) => db.members.find((m) => m.id === id)

export function issue(m) {
  db.seq += 1
  const at = `mock-access-token-${m.id}-${db.seq}`
  const rt = `mock-refresh-token-${m.id}-${db.seq}`
  db.access[at] = { id: m.id, exp: Date.now() + ACCESS_TTL * 1000 }
  db.refresh[rt] = m.id
  save()
  return {
    accessToken: at,
    refreshToken: rt,
    expiresIn: ACCESS_TTL,
    member: { uuid: m.uuid, email: m.email },
  }
}

export function consumeRefresh(rt) {
  if (!has(db.refresh, rt)) return null
  const id = db.refresh[rt]
  delete db.refresh[rt]
  save()
  return findById(id) ?? null
}

export function revokeRefresh(rt, id) {
  if (has(db.refresh, rt) && db.refresh[rt] === id) {
    delete db.refresh[rt]
    save()
  }
}

export function authMember(req) {
  const h = req.headers.get('Authorization') || ''
  const t = h.startsWith('Bearer ') ? h.slice(7) : ''
  if (!has(db.access, t)) return null
  const a = db.access[t]
  if (a.exp < Date.now()) return null
  return findById(a.id) ?? null
}

const pad = (n) => String(n).padStart(2, '0')

export function localIso(d = new Date()) {
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
  return `${date}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
