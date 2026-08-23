import { fmt, fmtHz, fmtSec } from '../format'

// The four numbers a PLL designer reads first, as glowing headline tiles.
export default function HeadlineStats({ result }) {
  const pn = result?.phase_noise
  if (!pn) return null
  const stats = [
    { label: 'RMS jitter', value: fmtSec(pn.rms_jitter_s), tag: '12k–20M', tone: 'cyan' },
    { label: 'Worst-case PM', value: `${fmt(result.worst.min_phase_margin_deg, 1)}°`, tag: 'across PVT', tone: result.passes ? 'green' : 'red' },
    { label: 'Lock time', value: fmtSec(result.nominal.lock_time_s), tag: 'nominal', tone: 'violet' },
    { label: 'Ref. spur', value: `${fmt(pn.reference_spur_dbc, 0)} dBc`, tag: 'estimate', tone: 'amber' },
  ]
  return (
    <div className="headline">
      {stats.map((s) => (
        <div key={s.label} className={'stat ' + s.tone}>
          <span className="stat-label">{s.label}</span>
          <b className="stat-value">{s.value}</b>
          <span className="stat-tag">{s.tag}</span>
        </div>
      ))}
    </div>
  )
}
