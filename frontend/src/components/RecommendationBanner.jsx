import { fmt } from '../format'

export default function RecommendationBanner({ result }) {
  const m = result.metrics
  return (
    <div className="banner">
      <div className="win">
        <small>RECOMMENDED</small>
        {result.name}
      </div>
      <div>
        <div className="method">designed by {result.method}</div>
        <div className="method">
          settling {fmt(m.settling_time)} s · overshoot {fmt(m.overshoot)} % ·
          steady-state error {fmt(m.steady_state_error)}
        </div>
      </div>
      <div className="scorebox">
        <b>{result.score.toFixed(3)}</b>
        <span>score</span>
      </div>
    </div>
  )
}
