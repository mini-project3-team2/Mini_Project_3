import { HttpResponse } from 'msw'

export const API = import.meta.env.VITE_API_URL || '/api'

export const ok = (data, status = 200) =>
  HttpResponse.json({ success: true, data, message: '' }, { status })

export const fail = (status, body) => HttpResponse.json(body, { status })

export const noContent = () => new HttpResponse(null, { status: 204 })

export async function readJson(req) {
  try {
    return (await req.json()) ?? {}
  } catch {
    return {}
  }
}
