// Thin client for the ControlBench REST API. In dev, Vite proxies /api to the
// FastAPI backend (see vite.config.js), so these relative URLs just work.

async function post(path, body) {
  const res = await fetch(path, {
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

export const compare = (num, den, weights) => post('/api/compare', { num, den, weights })
export const predict = (num, den) => post('/api/predict', { num, den })

export async function health() {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error('backend unavailable')
  return res.json()
}
