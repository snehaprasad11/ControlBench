// Per-controller colours, reused by the leaderboard and the step chart.
export const CONTROLLER_COLORS = {
  P: '#e8873b',
  PI: '#7e57c2',
  PID: '#1f6feb',
  Lead: '#1a9e6a',
  Lag: '#d64545',
}

// Format a metric. null/non-finite -> infinity symbol (an unstable design never
// settles; a 2nd-order plant has an infinite gain margin -- both read as infinite).
export function fmt(x, digits = 2) {
  if (x === null || x === undefined || !isFinite(x)) return '∞'
  return Number(x).toFixed(digits)
}
