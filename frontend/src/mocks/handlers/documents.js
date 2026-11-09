import { http } from 'msw'
import notFound from '../../../../mock-data/responses/documents/delete.404-document-not-found.json'
import emptyFile from '../../../../mock-data/responses/documents/upload.400-empty-file.json'
import invalidType from '../../../../mock-data/responses/documents/upload.400-invalid-file-type.json'
import tooLarge from '../../../../mock-data/responses/documents/upload.413-file-too-large.json'
import extractFailed from '../../../../mock-data/responses/documents/upload.422-text-extraction-failed.json'
import aiDown from '../../../../mock-data/responses/documents/upload.503-ai-unavailable.json'
import invalidInput from '../../../../mock-data/responses/common/400-invalid-input.json'
import unauthorized from '../../../../mock-data/responses/common/401-unauthorized.json'
import forbidden from '../../../../mock-data/responses/common/403-forbidden.json'
import { authMember, db, localIso, save } from '../db'
import { API, fail, noContent, ok } from '../respond'

const MAX_FILE = 10 * 1024 * 1024
const MAGIC = '%PDF-'

const view = (d) => ({
  id: d.id,
  originalFilename: d.originalFilename,
  fileSize: d.fileSize,
  status: d.status,
  createdAt: d.createdAt,
})

// 최신순, 같은 시각이면 id 큰 순 (Backend 와 같음)
const latest = (a, b) => (a.createdAt < b.createdAt ? 1 : a.createdAt > b.createdAt ? -1 : b.id - a.id)

// Backend DocumentService.sanitizeFilename 과 같은 규칙
function sanitize(name) {
  if (!name || !name.trim()) return 'document.pdf'
  let n = name.replaceAll('\\', '/')
  n = n.slice(n.lastIndexOf('/') + 1)
  // eslint-disable-next-line no-control-regex
  n = n.replace(/[\u0000-\u001f\u007f]/g, '').trim()
  if (!n) return 'document.pdf'
  return n.length > 255 ? n.slice(-255) : n
}

async function isPdf(file) {
  const head = new Uint8Array(await file.slice(0, MAGIC.length).arrayBuffer())
  return String.fromCharCode(...head) === MAGIC
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

export const documentHandlers = [
  http.get(`${API}/documents`, ({ request }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    return ok(db.documents.filter((d) => d.memberId === m.id).sort(latest).map(view))
  }),

  // 검증 오류는 바로, 적재(AI) 결과는 1.5~3초 뒤
  http.post(`${API}/documents`, async ({ request }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    let file
    try {
      file = (await request.formData()).get('file')
    } catch {
      return fail(400, invalidInput)
    }
    if (!(file instanceof File)) return fail(400, invalidInput)
    if (file.size === 0) return fail(400, emptyFile)
    if (file.size > MAX_FILE) return fail(413, tooLarge)
    if (!file.name.trim().toLowerCase().endsWith('.pdf') || !(await isPdf(file))) return fail(400, invalidType)

    const name = sanitize(file.name)
    await wait(1500 + Math.random() * 1500)
    const low = name.toLowerCase()
    if (low.includes('scan')) return fail(422, extractFailed)
    if (low.includes('ai-down')) return fail(503, aiDown)

    const d = {
      id: Math.max(0, ...db.documents.map((x) => x.id)) + 1,
      memberId: m.id,
      originalFilename: name,
      fileSize: file.size,
      status: 'READY',
      createdAt: localIso(),
    }
    db.documents.push(d)
    save()
    return ok(view(d), 201)
  }),

  http.delete(`${API}/documents/:id`, ({ request, params }) => {
    const m = authMember(request)
    if (!m) return fail(401, unauthorized)
    if (!/^\d+$/.test(params.id)) return fail(400, invalidInput)
    const i = db.documents.findIndex((d) => d.id === Number(params.id))
    if (i < 0) return fail(404, notFound)
    if (db.documents[i].memberId !== m.id) return fail(403, forbidden)
    db.documents.splice(i, 1)
    save()
    return noContent()
  }),
]
