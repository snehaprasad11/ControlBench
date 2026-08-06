import { fmt, CONTROLLER_COLORS } from '../format'

export default function Leaderboard({ results, recommended }) {
  const maxScore = Math.max(...results.map((r) => r.score), 0.0001)
  return (
    <table>
      <thead>
        <tr>
          <th>#</th><th>Controller</th><th>Score</th>
          <th>Rise</th><th>Settle</th><th>Over %</th>
          <th>SS err</th><th>GM dB</th><th>PM °</th>
        </tr>
      </thead>
      <tbody>
        {results.map((r, i) => {
          const m = r.metrics
          const cls = r.name === recommended ? 'win' : (m.stable ? '' : 'unstable')
          return (
            <tr key={r.name} className={cls}>
              <td className="rank">{i + 1}</td>
              <td>
                <span style={{ color: CONTROLLER_COLORS[r.name], fontWeight: 700 }}>{r.name}</span>
                <span className="tag"> {r.method}</span>
              </td>
              <td>
                <span className="scorebar" style={{ width: `${(r.score / maxScore) * 46}px` }} />
                {r.score.toFixed(3)}
              </td>
              <td>{fmt(m.rise_time)}</td>
              <td>{fmt(m.settling_time)}</td>
              <td>{fmt(m.overshoot, 1)}</td>
              <td>{fmt(m.steady_state_error)}</td>
              <td>{fmt(m.gain_margin_db, 1)}</td>
              <td>{fmt(m.phase_margin_deg, 1)}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
