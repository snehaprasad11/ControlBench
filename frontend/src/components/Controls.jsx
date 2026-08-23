import { fmtHz } from '../format'

function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}{hint && <em>{hint}</em>}</span>
      {children}
    </label>
  )
}

export default function Controls({ devices, device, form, setField, onDesign, onExplore, onRecommend, busy }) {
  return (
    <div className="card controls">
      <h2>1 · Pick a real chip</h2>
      <Field label="Synthesizer IC">
        <select value={form.deviceId} onChange={(e) => setField('deviceId', e.target.value)}>
          {devices.map((d) => (
            <option key={d.id} value={d.id}>{d.name} — {d.vendor}</option>
          ))}
        </select>
      </Field>

      {device && (
        <div className="device-facts">
          <div>{device.category}</div>
          <div>VCO {fmtHz(device.vco_min_hz, 1)}–{fmtHz(device.vco_max_hz, 1)} · Kvco {device.kvco_mhz_per_v} MHz/V · PFD ≤ {fmtHz(device.pfd_max_hz, 0)}</div>
          <a href={device.datasheet} target="_blank" rel="noreferrer">datasheet ↗</a>
        </div>
      )}

      <h2>2 · Operating point</h2>
      <div className="two">
        <Field label="VCO freq" hint="GHz">
          <input type="number" step="0.01" value={form.vcoGHz}
                 onChange={(e) => setField('vcoGHz', e.target.value)} />
        </Field>
        <Field label="PFD freq" hint="MHz">
          <input type="number" step="0.1" value={form.pfdMHz}
                 onChange={(e) => setField('pfdMHz', e.target.value)} />
        </Field>
      </div>

      <h2>3 · Loop targets</h2>
      <div className="two">
        <Field label="Loop BW" hint="kHz">
          <input type="number" step="1" value={form.fcKHz}
                 onChange={(e) => setField('fcKHz', e.target.value)} />
        </Field>
        <Field label="Phase margin" hint="°">
          <input type="number" step="1" value={form.pmDeg}
                 onChange={(e) => setField('pmDeg', e.target.value)} />
        </Field>
      </div>
      <Field label="Charge-pump Icp" hint="mA">
        <select value={form.icpMa} onChange={(e) => setField('icpMa', e.target.value)}>
          <option value="">device default ({(+device?.icp_default_ma).toFixed(2)} mA)</option>
          {device?.icp_options_ma.map((v) => (
            <option key={v} value={v}>{(+v).toFixed(2)} mA</option>
          ))}
        </select>
      </Field>

      <h2>4 · PVT corners</h2>
      <div className="two">
        <Field label="Kvco ±" hint="%">
          <input type="number" step="5" value={form.kvcoTolPct}
                 onChange={(e) => setField('kvcoTolPct', e.target.value)} />
        </Field>
        <Field label="Icp ±" hint="%">
          <input type="number" step="5" value={form.icpTolPct}
                 onChange={(e) => setField('icpTolPct', e.target.value)} />
        </Field>
      </div>

      <h2>5 · Spec (must hold at every corner)</h2>
      <div className="two">
        <Field label="Min phase margin" hint="°">
          <input type="number" step="1" value={form.minPmDeg}
                 onChange={(e) => setField('minPmDeg', e.target.value)} />
        </Field>
        <Field label="Max jitter peaking" hint="dB">
          <input type="number" step="0.5" value={form.maxPeakDb}
                 onChange={(e) => setField('maxPeakDb', e.target.value)} />
        </Field>
      </div>

      <div className="actions">
        <button className="primary" onClick={onDesign} disabled={busy}>
          {busy ? <span className="spinner" /> : null}{busy ? 'Working…' : 'Design & check PVT'}
        </button>
        <button onClick={onExplore} disabled={busy}>Find robust design</button>
        <button onClick={onRecommend} disabled={busy}>⚡ ML recommend</button>
      </div>
    </div>
  )
}
