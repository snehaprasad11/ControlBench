const EXAMPLES = [
  { label: '1/(s+1)³', num: '1', den: '1, 3, 3, 1' },
  { label: 'Underdamped', num: '1', den: '1, 0.4, 1' },
  { label: 'First-order', num: '1', den: '1, 2' },
  { label: 'Integrator', num: '1', den: '1, 1, 0' },
  { label: 'With zero', num: '1, 3', den: '1, 3, 2' },
]

const WEIGHT_PRESETS = ['Balanced', 'Min overshoot', 'Fastest', 'Most robust']

export default function PlantInput({
  numText, denText, setNumText, setDenText,
  weightKey, setWeightKey, onSubmit, loading, error,
}) {
  return (
    <div className="card">
      <h2>Plant transfer function <span className="sub">G(s) = num / den</span></h2>

      <label>Numerator coefficients</label>
      <input type="text" value={numText} onChange={(e) => setNumText(e.target.value)}
             placeholder="e.g. 1" />
      <label>Denominator coefficients</label>
      <input type="text" value={denText} onChange={(e) => setDenText(e.target.value)}
             placeholder="e.g. 1, 3, 3, 1" />
      <p className="eq">descending powers of s, comma-separated</p>

      <label>Examples</label>
      <div className="chips">
        {EXAMPLES.map((ex) => (
          <span key={ex.label} className="chip"
                onClick={() => { setNumText(ex.num); setDenText(ex.den) }}>
            {ex.label}
          </span>
        ))}
      </div>

      <label>Ranking priority</label>
      <div className="chips">
        {WEIGHT_PRESETS.map((w) => (
          <span key={w} className={'chip' + (w === weightKey ? ' active' : '')}
                onClick={() => setWeightKey(w)}>
            {w}
          </span>
        ))}
      </div>

      <button className="btn" onClick={onSubmit} disabled={loading}>
        {loading ? 'Comparing…' : 'Compare controllers'}
      </button>

      {error && <div className="error">{error}</div>}
    </div>
  )
}

export { WEIGHT_PRESETS }
