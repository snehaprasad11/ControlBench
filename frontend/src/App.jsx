import { useState, useEffect, useCallback } from 'react'
import { getDevices, design, explore, recommend } from './api'
import Controls from './components/Controls'
import Verdict from './components/Verdict'
import HeadlineStats from './components/HeadlineStats'
import { LoopFilterCard, MetricsTable, CornerTable } from './components/DesignResult'
import { BodeChart, JitterChart, LockChart, PhaseNoiseChart } from './components/Charts'
import Explore from './components/Explore'
import Recommend from './components/Recommend'

// Automotive temperature grades -> representative Kvco/Icp drift the PVT sweep uses.
// (First-order mapping from temperature range to gain drift; see README limitations.)
export const TEMP_GRADES = {
  'Commercial (0–70 °C)': { kvco: 15, icp: 5 },
  'Industrial (−40–85 °C)': { kvco: 22, icp: 7 },
  'AEC-Q100 Grade 2 (−40–105 °C)': { kvco: 26, icp: 9 },
  'AEC-Q100 Grade 1 (−40–125 °C)': { kvco: 30, icp: 10 },
  'AEC-Q100 Grade 0 (−40–150 °C)': { kvco: 35, icp: 12 },
}
const DEFAULT_GRADE = 'AEC-Q100 Grade 1 (−40–125 °C)'

// Ready-made automotive-radar operating points (synth output × multiplier → RF band).
export const RADAR_PRESETS = {
  '77 GHz LRR (long-range)':  { deviceId: 'lmx2594', vcoGHz: 9.625, pfdMHz: 100, fcKHz: 300, pmDeg: 55, nMult: 8 },
  '77 GHz MRR (mid-range)':   { deviceId: 'lmx2594', vcoGHz: 9.625, pfdMHz: 150, fcKHz: 500, pmDeg: 55, nMult: 8 },
  '24 GHz SRR (short-range)': { deviceId: 'adf5355', vcoGHz: 6.0,   pfdMHz: 50,  fcKHz: 200, pmDeg: 55, nMult: 4 },
}

// Defaults when a device is picked manually (keeps the current multiplier).
function defaultsFor(dev) {
  const vcoMid = Math.sqrt(dev.vco_min_hz * dev.vco_max_hz)
  const pfd = Math.min(dev.pfd_max_hz, 50e6)
  return {
    vcoGHz: +(vcoMid / 1e9).toFixed(3),
    pfdMHz: +(pfd / 1e6).toFixed(2),
    fcKHz: +((pfd / 300) / 1e3).toFixed(1),
    pmDeg: 55,
    icpMa: '',
  }
}

function buildBody(form) {
  const g = TEMP_GRADES[form.tempGrade] || { kvco: 30, icp: 10 }
  return {
    device_id: form.deviceId,
    f_out_hz: Number(form.vcoGHz) * 1e9,
    f_pfd_hz: Number(form.pfdMHz) * 1e6,
    fc_hz: Number(form.fcKHz) * 1e3,
    phase_margin_deg: Number(form.pmDeg),
    icp_ma: form.icpMa === '' ? null : Number(form.icpMa),
    n_mult: Number(form.nMult) || 1,
    corner: { kvco_tol: g.kvco / 100, icp_tol: g.icp / 100 },
    spec: {
      min_phase_margin_deg: Number(form.minPmDeg),
      max_jitter_peaking_db: form.maxPeakDb === '' ? null : Number(form.maxPeakDb),
    },
  }
}

export default function App() {
  const [devices, setDevices] = useState([])
  const [form, setForm] = useState(null)
  const [result, setResult] = useState(null)
  const [exploreRes, setExploreRes] = useState(null)
  const [recommendRes, setRecommendRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [online, setOnline] = useState(null)
  const [bootMsg, setBootMsg] = useState('Loading device library…')

  const device = devices.find((d) => d.id === form?.deviceId)
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  // Boot: load the real device library (retrying so a cold free-tier backend wakes up
  // gracefully), then seed the 77 GHz long-range-radar preset.
  useEffect(() => {
    let cancelled = false
    async function boot() {
      for (let attempt = 1; attempt <= 15 && !cancelled; attempt++) {
        try {
          const devs = await getDevices()
          if (cancelled) return
          setOnline(true)
          setDevices(devs)
          setForm({
            ...RADAR_PRESETS['77 GHz LRR (long-range)'],
            tempGrade: DEFAULT_GRADE, minPmDeg: 45, maxPeakDb: 4, icpMa: '',
          })
          return
        } catch {
          if (cancelled) return
          setOnline(false)
          setBootMsg(attempt < 3
            ? 'Loading device library…'
            : `Waking the backend… free hosting can take ~30 s to spin up (attempt ${attempt})`)
          await new Promise((r) => setTimeout(r, 3000))
        }
      }
      if (!cancelled) setBootMsg('Backend unavailable — confirm the API is running and VITE_API_BASE is set.')
    }
    boot()
    return () => { cancelled = true }
  }, [])

  const runDesign = useCallback(async (override) => {
    setError(null); setBusy(true)
    try {
      const r = await design(buildBody({ ...form, ...override }))
      setResult(r)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }, [form])

  const runExplore = useCallback(async () => {
    setError(null); setBusy(true); setExploreRes(null)
    try { setExploreRes(await explore(buildBody(form))) }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }, [form])

  const runRecommend = useCallback(async () => {
    setError(null); setBusy(true); setRecommendRes(null)
    try { setRecommendRes(await recommend(buildBody(form))) }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }, [form])

  // Apply a whole radar preset, then design it.
  const applyPreset = (name) => {
    const p = RADAR_PRESETS[name]
    if (!p) return
    setForm((f) => ({ ...f, ...p, icpMa: '' }))
    runDesign({ ...p, icpMa: '' })
  }

  // Manual device change re-seeds a safe operating point for that part.
  const changeDevice = (id) => {
    const d = devices.find((x) => x.id === id)
    const seed = d ? defaultsFor(d) : {}
    setForm((f) => ({ ...f, deviceId: id, ...seed }))
    runDesign({ deviceId: id, ...seed })
  }

  // Apply a design point (from Explore or ML) into the form and verify it.
  const applyPoint = (fc_hz, pm, icp_ma) => {
    const override = { fcKHz: +(fc_hz / 1e3).toFixed(3), pmDeg: Math.round(pm), icpMa: icp_ma }
    setForm((f) => ({ ...f, ...override }))
    runDesign(override)
  }

  // Auto-run one design once the form is seeded, so the page isn't empty.
  useEffect(() => {
    if (form && !result) runDesign()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form])

  if (!form) {
    return <div className="app"><div className="card loading">{bootMsg}</div></div>
  }

  const radarRfGHz = (Number(form.vcoGHz) * (Number(form.nMult) || 1)).toFixed(1)

  return (
    <div className="app">
      <div className="header">
        <div className="status">
          {online === null ? '' : (
            <><span className={'dot ' + (online ? 'up' : 'down')} />{online ? 'API connected' : 'API offline'}</>
          )}
        </div>
        <h1>Lock<span className="accent">Bench</span> <span className="tagline-badge">automotive radar</span></h1>
        <p>Design the <b>chirp-synthesizer PLL</b> for an <b>FMCW automotive radar</b> — and prove it holds
           chirp settling, phase noise and jitter across the full <b>automotive temperature range</b>.</p>
      </div>

      <div className="grid">
        <div>
          <Controls
            devices={devices} device={device} form={form} setField={setField}
            presets={Object.keys(RADAR_PRESETS)} grades={Object.keys(TEMP_GRADES)}
            radarRfGHz={radarRfGHz}
            onApplyPreset={applyPreset} onChangeDevice={changeDevice}
            onDesign={() => runDesign()} onExplore={runExplore} onRecommend={runRecommend}
            busy={busy}
          />
        </div>

        <div className={'results' + (busy ? ' recomputing' : '')}>
          {error && <div className="card error">{error}</div>}

          {recommendRes && (
            <Recommend result={recommendRes}
              onApply={(r) => applyPoint(r.recommended_fc_hz, r.recommended_phase_margin_deg, r.recommended_icp_ma)} />
          )}

          {exploreRes && (
            <Explore result={exploreRes}
              onApply={(c) => applyPoint(c.fc_hz, c.phase_margin_deg, c.icp_ma)} />
          )}

          {result && (
            <>
              <Verdict passes={result.passes} violations={result.violations} grade={form.tempGrade} />
              <HeadlineStats result={result} />

              <details className="card explain">
                <summary>What do these outputs mean?</summary>
                <ul>
                  <li><b>Radar RF</b> — the final carrier the chirp is transmitted at (synth output × multiplier).</li>
                  <li><b>Chirp settling</b> — how long the synth needs to settle before each chirp; shorter means a faster radar frame rate and higher measurable velocity.</li>
                  <li><b>Phase noise (@1 MHz)</b> — the carrier's spectral purity at the RF frequency; lower (more negative) lets the radar detect small targets next to large ones.</li>
                  <li><b>RMS jitter</b> — the phase noise integrated into a single timing-error number.</li>
                  <li><b>Loop filter R / C</b> — the actual resistor and capacitor values you would build on the board.</li>
                  <li><b>Verdict</b> — green only if phase margin, lock and jitter all stay in-spec at <em>every</em> temperature corner, not just at room temperature.</li>
                </ul>
              </details>

              {result.phase_noise && (
                <div className="card">
                  <h2>Phase noise <span className="sub">at {(result.phase_noise.carrier_hz / 1e9).toFixed(0)} GHz RF — sets radar detection sensitivity</span></h2>
                  <PhaseNoiseChart pn={result.phase_noise} />
                </div>
              )}

              <div className="card">
                <h2>Chirp lock transient <span className="sub">how fast the synth settles before each chirp</span></h2>
                <LockChart step={result.step_response} />
              </div>

              <div className="grid two-col">
                <div className="card">
                  <h2>Open-loop Bode <span className="sub">crossover = loop BW; gap to −180° = phase margin</span></h2>
                  <BodeChart bode={result.bode} bandwidthHz={result.nominal.loop_bandwidth_hz} />
                </div>
                <div className="card">
                  <h2>Jitter peaking <span className="sub">peak of |H|</span></h2>
                  <JitterChart bode={result.bode} />
                </div>
              </div>

              <MetricsTable nominal={result.nominal} worst={result.worst} />
              <LoopFilterCard lf={result.loop_filter} icpMa={result.icp_ma} n={result.n}
                kvco={result.kvco_mhz_per_v} radarRfHz={result.radar_rf_hz} nMult={result.n_mult} />
              <CornerTable corners={result.corners} minPm={Number(form.minPmDeg)} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
