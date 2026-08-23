// Thin client for the LockBench REST API.
//   In production the FastAPI backend serves this frontend from the same origin, so the
//   default empty base -> relative "/api" just works. In dev, Vite proxies "/api" to the
//   backend. VITE_API_BASE remains an optional override for a separately hosted API.
const BASE = import.meta.env.VITE_API_BASE || ''

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      detail = (await res.json()).detail || detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}

async function get(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json()
}

export const getDevices = () => get('/api/devices')
export const design = (body) => post('/api/design', body)
export const explore = (body) => post('/api/explore', body)
export const recommend = (body) => post('/api/recommend', body)

export async function health() {
  const res = await fetch(BASE + '/api/health')
  if (!res.ok) throw new Error('backend unavailable')
  return res.json()
}
