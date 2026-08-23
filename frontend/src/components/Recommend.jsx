import { fmt, fmtHz, fmtSec } from '../format'

// ML inverse design: the surrogate's suggested design point from the target specs.
export default function Recommend({ result, onApply }) {
  if (!result) return null
  if (!result.model_available) {
    return <div className="card note">{result.note}</div>
  }
  if (result.recommended_fc_hz == null) {
    return <div className="card note">⚡ {result.note}</div>
  }
  return (
    <div className="card recommend">
      <h2>⚡ ML recommendation <span className="sub">instant, from the surrogate</span></h2>
      <div className="kv">
        <div><span>Loop BW</span><b>{fmtHz(result.recommended_fc_hz)}</b></div>
        <div><span>Phase margin</span><b>{fmt(result.recommended_phase_margin_deg, 0)}°</b></div>
        <div><span>Icp</span><b>{fmt(result.recommended_icp_ma, 2)} mA</b></div>
        <div><span>pred. worst PM</span><b>{fmt(result.predicted_worst_phase_margin_deg, 1)}°</b></div>
        <div><span>pred. worst lock</span><b>{fmtSec(result.predicted_worst_lock_time_s)}</b></div>
        <div><span>pred. worst peak</span><b>{fmt(result.predicted_worst_jitter_peaking_db, 2)} dB</b></div>
      </div>
      <button className="primary" onClick={() => onApply(result)}>Apply & verify against model</button>
      <p className="fine">{result.note}</p>
    </div>
  )
}
