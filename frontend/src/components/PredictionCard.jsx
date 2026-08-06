import { fmt } from '../format'

export default function PredictionCard({ prediction, recommended }) {
  if (!prediction) {
    return <p className="muted">ML model not available — run <code>python scripts/build_ml.py</code>.</p>
  }
  const match = prediction.recommended_controller === recommended
  return (
    <div>
      <p style={{ margin: '0 0 8px' }}>
        The ML model predicts&nbsp;
        <b style={{ color: '#1f6feb' }}>{prediction.recommended_controller}</b>
        {match
          ? <span className="pill ok" style={{ marginLeft: 8 }}>matches simulation ✓</span>
          : <span className="pill no" style={{ marginLeft: 8 }}>simulation picked {recommended}</span>}
      </p>
      <p className="muted" style={{ margin: 0 }}>
        predicted settling ≈ {fmt(prediction.predicted_settling_time)} s,
        overshoot ≈ {fmt(prediction.predicted_overshoot, 1)} % — computed instantly, without simulation.
      </p>
    </div>
  )
}
