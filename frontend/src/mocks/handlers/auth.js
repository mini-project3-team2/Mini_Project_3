import { http } from 'msw'
import invalidCred from '../../../../mock-data/responses/auth/login.401-invalid-credentials.json'
import locked from '../../../../mock-data/responses/auth/login.423-account-locked.json'
import invalidRefresh from '../../../../mock-data/responses/auth/refresh.401-invalid-refresh-token.json'
import signupInvalid from '../../../../mock-data/responses/auth/signup.400-invalid-input.json'
import duplicate from '../../../../mock-data/responses/auth/signup.409-duplicate-email.json'
import invalidInput from '../../../../mock-data/responses/common/400-invalid-input.json'
import unauthorized from '../../../../mock-data/responses/common/401-unauthorized.json'
import {
  authMember,
  db,
  findByEmail,
  issue,
  localIso,
  revokeRefresh,
  save,
  consumeRefresh,
} from '../db'
import { isEmail, isPassword } from '../../utils/validate'
import { API, fail, noContent, ok, readJson } from '../respond'

const MAX_FAIL = 5
const LOCK_MIN = 15

const isLocked = (m) => m.lockedUntil && new Date(m.lockedUntil) > new Date()
const lockedRes = (m) => fail(423, { ...locked, data: { lockedUntil: m.lockedUntil } })

export const authHandlers = [
  http.post(`${API}/auth/signup`, async ({ request }) => {
    const { email, password } = await readJson(request)
    if (!isEmail(email)) return fail(400, invalidInput)
    if (!isPassword(password)) return fail(400, signupInvalid)
    if (findByEmail(email)) return fail(409, duplicate)

    const m = {
      id: Math.max(...db.members.map((x) => x.id)) + 1,
      uuid: crypto.randomUUID(),
      email,
      password,
      role: 'MEMBER',
      failedLoginCount: 0,
      lockedUntil: null,
      createdAt: localIso(),
    }
    db.members.push(m)
    save()
    return ok({ uuid: m.uuid, email: m.email }, 201)
  }),

  http.post(`${API}/auth/login`, async ({ request }) => {
    const { email, password } = await readJson(request)
    const m = findByEmail(email)
    if (!m) return fail(401, invalidCred)
    if (isLocked(m)) return lockedRes(m)
    if (m.lockedUntil) {
      m.lockedUntil = null
      m.failedLoginCount = 0
    }

    if (m.password !== password) {
      m.failedLoginCount += 1
      if (m.failedLoginCount >= MAX_FAIL) {
        m.lockedUntil = localIso(new Date(Date.now() + LOCK_MIN * 60 * 1000))
      }
      save()
      return isLocked(m) ? lockedRes(m) : fail(401, invalidCred)
    }

    m.failedLoginCount = 0
    return ok(issue(m))
  }),

  http.post(`${API}/auth/refresh`, async ({ request }) => {
    const { refreshToken } = await readJson(request)
    if (typeof refreshToken !== 'string' || !refreshToken.trim()) return fail(400, invalidInput)
    const m = consumeRefresh(refreshToken)
    if (!m) return fail(401, invalidRefresh)
    return ok(issue(m))
  }),

  http.post(`${API}/auth/logout`, async ({ request }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    const { refreshToken } = await readJson(request)
    if (typeof refreshToken !== 'string' || !refreshToken.trim()) return fail(400, invalidInput)
    revokeRefresh(refreshToken, m.id)
    return noContent()
  }),
]
