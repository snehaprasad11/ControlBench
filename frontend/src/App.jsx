import { useState, useEffect, useCallback } from 'react'
import { getDevices, design, explore, recommend, health } from './api'
import Controls from './components/Controls'
import Verdict from './components/Verdict'
import { LoopFilterCard, MetricsTable, CornerTable } from './components/DesignResult'
import { BodeChart, JitterChart, LockChart } from './components/Charts'
import Explore from './components/Explore'
import Recommend from './components/Recommend'

// Sensible starting point for a freshly-selected device.
function defaultsFor(dev) {
  const vcoMid = Math.sqrt(dev.vco_min_hz * dev.vco_max_hz)
  const pfd = Math.min(dev.pfd_max_hz, 10e6)
  return {
    vcoGHz: +(vcoMid / 1e9).toFixed(3),
    pfdMHz: +(pfd / 1e6).toFixed(2),
    fcKHz: +((pfd / 500) / 1e3).toFixed(1),   // ~fPFD/500, a safe loop bandwidth
    pmDeg: 50,
    icpMa: '',
  }
}

function buildBody(form) {
  return {
    device_id: form.deviceId,
    f_out_hz: Number(form.vcoGHz) * 1e9,
    f_pfd_hz: Number(form.pfdMHz) * 1e6,
    fc_hz: Number(form.fcKHz) * 1e3,
    phase_margin_deg: Number(form.pmDeg),
    icp_ma: form.icpMa === '' ? null : Number(form.icpMa),
    corner: { kvco_tol: Number(form.kvcoTolPct) / 100, icp_tol: Number(form.icpTolPct) / 100 },
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

  const device = devices.find((d) => d.id === form?.deviceId)
  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  // Boot: check health, load the real device library, seed the form.
  useEffect(() => {
    health().then(() => setOnline(true)).catch(() => setOnline(false))
    getDevices().then((devs) => {
      setDevices(devs)
      const d = devs[0]
      setForm({
        deviceId: d.id, ...defaultsFor(d),
        kvcoTolPct: 30, icpTolPct: 10, minPmDeg: 45, maxPeakDb: 4,
      })
    }).catch((e) => setError(e.message))
  }, [])

  // Re-seed operating point when the device changes.
  useEffect(() => {
    if (!device) return
    setForm((f) => ({ ...f, ...defaultsFor(device) }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form?.deviceId])

  const runDesign = useCallback(async (override) => {
    setError(null); setBusy(true)
    try {
      const body = buildBody({ ...form, ...override })
      const r = await design(body)
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
    return <div className="app"><div className="card loading">{error || 'Loading device library…'}</div></div>
  }

  return (
    <div className="app">
      <div className="header">
        <div className="status">
          {online === null ? '' : (
            <><span className={'dot ' + (online ? 'up' : 'down')} />{online ? 'API connected' : 'API offline'}</>
          )}
        </div>
        <h1>Lock<span className="accent">Bench</span></h1>
        <p>Design a charge-pump PLL loop filter for a <b>real synthesizer IC</b>, then prove it holds
           phase margin, lock time and jitter peaking across every <b>PVT corner</b>.</p>
      </div>

      <div className="grid">
        <div>
          <Controls
            devices={devices} device={device} form={form} setField={setField}
            onDesign={() => runDesign()} onExplore={runExplore} onRecommend={runRecommend}
            busy={busy}
          />
        </div>

        <div className="results">
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
              <Verdict passes={result.passes} violations={result.violations} />

              <div className="card">
                <h2>Open-loop Bode <span className="sub">crossover = loop bandwidth; phase gap to −180° = phase margin</span></h2>
                <BodeChart bode={result.bode} bandwidthHz={result.nominal.loop_bandwidth_hz} />
              </div>

              <div className="grid two-col">
                <div className="card">
                  <h2>Jitter peaking <span className="sub">peak of |H|</span></h2>
                  <JitterChart bode={result.bode} />
                </div>
                <div className="card">
                  <h2>Lock transient <span className="sub">phase step</span></h2>
                  <LockChart step={result.step_response} />
                </div>
              </div>

              <MetricsTable nominal={result.nominal} worst={result.worst} />
              <LoopFilterCard lf={result.loop_filter} icpMa={result.icp_ma} n={result.n} kvco={result.kvco_mhz_per_v} />
              <CornerTable corners={result.corners} minPm={Number(form.minPmDeg)} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
