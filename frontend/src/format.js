// Formatting helpers for engineering quantities.

// A generic engineering-notation formatter with an SI suffix.
function si(x, unit, digits = 2) {
  if (x === null || x === undefined || !isFinite(x)) return '—'
  const prefixes = [
    { p: 1e9, s: 'G' }, { p: 1e6, s: 'M' }, { p: 1e3, s: 'k' },
    { p: 1, s: '' }, { p: 1e-3, s: 'm' }, { p: 1e-6, s: 'µ' },
    { p: 1e-9, s: 'n' }, { p: 1e-12, s: 'p' },
  ]
  const ax = Math.abs(x)
  if (ax === 0) return `0 ${unit}`
  const match = prefixes.find((pf) => ax >= pf.p) || prefixes[prefixes.length - 1]
  return `${(x / match.p).toFixed(digits)} ${match.s}${unit}`
}

export const fmtHz = (x, d = 2) => si(x, 'Hz', d)
export const fmtSec = (x, d = 2) => si(x, 's', d)
export const fmtOhm = (x, d = 1) => si(x, 'Ω', d)
export const fmtFarad = (x, d = 2) => si(x, 'F', d)

// Format a plain number; null/non-finite -> em dash (undefined margin, etc.).
export function fmt(x, digits = 2) {
  if (x === null || x === undefined || !isFinite(x)) return '—'
  return Number(x).toFixed(digits)
}
