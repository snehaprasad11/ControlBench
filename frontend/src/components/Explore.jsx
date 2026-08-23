import { fmt, fmtHz, fmtSec } from '../format'

// Ranked robust-design candidates from the design-space search.
export default function Explore({ result, onApply }) {
  if (!result) return null
  return (
    <div className="card">
      <h2>Robust design search
        <span className="sub">{result.any_pass ? 'passing designs, best first' : 'closest attempts (none pass)'}</span>
      </h2>
      <table className="metrics explore">
        <thead>
          <tr><th>BW</th><th>PM target</th><th>Icp</th><th>worst PM</th><th>worst lock</th><th>margin</th><th></th></tr>
        </thead>
        <tbody>
          {result.candidates.map((c, i) => (
            <tr key={i} className={c.passes ? 'ok' : 'bad'}>
              <td>{fmtHz(c.fc_hz)}</td>
              <td>{fmt(c.phase_margin_deg, 0)}°</td>
              <td>{fmt(c.icp_ma, 2)} mA</td>
              <td>{fmt(c.worst.min_phase_margin_deg, 1)}°</td>
              <td>{fmtSec(c.worst.max_lock_time_s)}</td>
              <td>{c.robustness_margin_deg >= 0 ? '+' : ''}{fmt(c.robustness_margin_deg, 1)}°</td>
              <td><button className="link" onClick={() => onApply(c)}>use</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
