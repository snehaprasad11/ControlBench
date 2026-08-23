// Thin client for the LockBench REST API.
//   dev  : VITE_API_BASE is empty -> relative /api, Vite proxies to the backend.
//   prod : set VITE_API_BASE to the backend origin (e.g. https://xxx.onrender.com)
//          in Vercel's environment variables -> the frontend calls it directly.
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
