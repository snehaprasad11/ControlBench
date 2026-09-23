import { fmt, fmtSec } from '../format'

// The four numbers a radar engineer reads first, as glowing headline tiles.
export default function HeadlineStats({ result }) {
  const pn = result?.phase_noise
  if (!pn) return null
  const stats = [
    { label: 'Radar RF', value: `${(result.radar_rf_hz / 1e9).toFixed(1)} GHz`, tag: `×${result.n_mult}`, tone: 'cyan' },
    { label: 'Chirp settling', value: fmtSec(result.nominal.lock_time_s), tag: 'per chirp', tone: 'violet' },
    { label: 'Phase noise', value: `${fmt(pn.pn_at_1mhz_dbc, 0)} dBc/Hz`, tag: '@1 MHz, at RF', tone: 'amber' },
    { label: 'RMS jitter', value: fmtSec(pn.rms_jitter_s), tag: '12k–20M', tone: result.passes ? 'green' : 'red' },
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
