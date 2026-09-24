import { fmt, fmtHz, fmtSec, fmtOhm, fmtFarad } from '../format'

// Loop-filter component values (the "controller" LockBench synthesised) + the chirp chain.
export function LoopFilterCard({ lf, icpMa, n, kvco, radarRfHz, nMult }) {
  return (
    <div className="card">
      <h2>Designed loop filter <span className="sub">buildable R / C values · order {lf.order}</span></h2>
      <div className="kv">
        <div><span>R</span><b>{fmtOhm(lf.r_ohm)}</b></div>
        <div><span>C_main</span><b>{fmtFarad(lf.c_main_nf * 1e-9)}</b></div>
        <div><span>C_shunt</span><b>{lf.c_shunt_nf > 0 ? fmtFarad(lf.c_shunt_nf * 1e-9) : '—'}</b></div>
        <div><span>zero</span><b>{fmtHz(lf.zero_hz)}</b></div>
        <div><span>3rd pole</span><b>{lf.pole3_hz ? fmtHz(lf.pole3_hz) : '—'}</b></div>
        <div><span>N (divider)</span><b>{Math.round(n)}</b></div>
        <div><span>Icp</span><b>{fmt(icpMa)} mA</b></div>
        <div><span>Kvco</span><b>{fmt(kvco, 0)} MHz/V</b></div>
        {radarRfHz ? <div><span>chirp chain</span><b>×{nMult} → {(radarRfHz / 1e9).toFixed(1)} GHz</b></div> : null}
      </div>
    </div>
  )
}

// Nominal vs worst-case-across-PVT metrics side by side.
export function MetricsTable({ nominal, worst }) {
  // Gain margin is null when the phase never reaches -180 deg -> infinite gain margin.
  const gm = (x) => (x === null || x === undefined ? '∞ dB' : `${fmt(x, 1)} dB`)
  const infiniteGm = nominal.gain_margin_db === null || nominal.gain_margin_db === undefined
  const rows = [
    ['Loop bandwidth', fmtHz(nominal.loop_bandwidth_hz), `${fmtHz(worst.min_bandwidth_hz)} – ${fmtHz(worst.max_bandwidth_hz)}`],
    ['Phase margin', `${fmt(nominal.phase_margin_deg, 1)}°`, `${fmt(worst.min_phase_margin_deg, 1)}° (worst)`],
    ['Gain margin', gm(nominal.gain_margin_db), `${gm(worst.min_gain_margin_db)} (worst)`],
    ['Lock time', fmtSec(nominal.lock_time_s), `${fmtSec(worst.max_lock_time_s)} (worst)`],
    ['Jitter peaking', `${fmt(nominal.jitter_peaking_db, 2)} dB`, `${fmt(worst.max_jitter_peaking_db, 2)} dB (worst)`],
  ]
  return (
    <div className="card">
      <h2>Loop performance</h2>
      <table className="metrics">
        <thead><tr><th></th><th>nominal (TT)</th><th>across PVT</th></tr></thead>
        <tbody>
          {rows.map(([k, a, b]) => (
            <tr key={k}><td>{k}</td><td>{a}</td><td className="pvt">{b}</td></tr>
          ))}
        </tbody>
      </table>
      {infiniteGm && (
        <p className="section-note" style={{ marginTop: 10 }}>
          ∞ gain margin: the loop's phase never reaches −180°, so it cannot be destabilised
          by gain alone — phase margin is the binding stability limit.
        </p>
      )}
    </div>
  )
}

// Per-corner phase margin / lock / peaking, worst row highlighted.
export function CornerTable({ corners, minPm }) {
  return (
    <div className="card">
      <h2>PVT corner sweep</h2>
      <table className="metrics corners">
        <thead>
          <tr><th>corner</th><th>Kvco</th><th>Icp</th><th>PM</th><th>lock</th><th>peak</th></tr>
        </thead>
        <tbody>
          {corners.map((c) => {
            const pm = c.metrics.phase_margin_deg
            const bad = pm !== null && pm < minPm
            return (
              <tr key={c.name} className={(c.is_nominal ? 'nominal ' : '') + (bad ? 'bad' : '')}>
                <td>{c.name}</td>
                <td>{c.kvco_mult.toFixed(2)}×</td>
                <td>{c.icp_mult.toFixed(2)}×</td>
                <td>{fmt(pm, 1)}°</td>
                <td>{fmtSec(c.metrics.lock_time_s)}</td>
                <td>{fmt(c.metrics.jitter_peaking_db, 2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
