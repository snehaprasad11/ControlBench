import { useState, useEffect, useCallback } from 'react'
import { compare, predict, health } from './api'
import PlantInput from './components/PlantInput'
import RecommendationBanner from './components/RecommendationBanner'
import PlantSummary from './components/PlantSummary'
import Leaderboard from './components/Leaderboard'
import StepChart from './components/StepChart'
import PoleZeroChart from './components/PoleZeroChart'
import PredictionCard from './components/PredictionCard'

const WEIGHTS = {
  Balanced: null,
  'Min overshoot': { overshoot: 0.5, settling_time: 0.15, rise_time: 0.1, steady_state_error: 0.15, gain_margin_db: 0.05, phase_margin_deg: 0.05 },
  Fastest: { settling_time: 0.4, rise_time: 0.3, overshoot: 0.1, steady_state_error: 0.1, gain_margin_db: 0.05, phase_margin_deg: 0.05 },
  'Most robust': { gain_margin_db: 0.35, phase_margin_deg: 0.35, overshoot: 0.1, settling_time: 0.1, rise_time: 0.05, steady_state_error: 0.05 },
}

function parseCoeffs(text) {
  const arr = text.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean).map(Number)
  if (arr.length === 0 || arr.some((x) => Number.isNaN(x))) {
    throw new Error('Enter numbers separated by commas, e.g. 1, 3, 3, 1')
  }
  return arr
}

export default function App() {
  const [numText, setNumText] = useState('1')
  const [denText, setDenText] = useState('1, 3, 3, 1')
  const [weightKey, setWeightKey] = useState('Balanced')
  const [data, setData] = useState(null)
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [online, setOnline] = useState(null)

  useEffect(() => {
    health().then(() => setOnline(true)).catch(() => setOnline(false))
  }, [])

  const run = useCallback(async () => {
    setError(null)
    let num, den
    try {
      num = parseCoeffs(numText)
      den = parseCoeffs(denText)
    } catch (e) {
      setError(e.message)
      return
    }
    setLoading(true)
    try {
      const result = await compare(num, den, WEIGHTS[weightKey])
      setData(result)
      // ML prediction is best-effort; a missing model shouldn't block the comparison.
      predict(num, den).then(setPrediction).catch(() => setPrediction(null))
    } catch (e) {
      setError(e.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [numText, denText, weightKey])

  // Run once on load with the default example.
  useEffect(() => { run() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="app">
      <div className="header">
        <div className="status">
          {online === null ? '' : (
            <><span className={'dot ' + (online ? 'up' : 'down')} />
            {online ? 'API connected' : 'API offline'}</>
          )}
        </div>
        <h1>Control<span className="accent">Bench</span></h1>
        <p>Describe a system; it tells you the best way to control it — compare, rank &amp; predict classical controllers.</p>
      </div>

      <div className="grid">
        <div>
          <PlantInput
            numText={numText} denText={denText}
            setNumText={setNumText} setDenText={setDenText}
            weightKey={weightKey} setWeightKey={setWeightKey}
            onSubmit={run} loading={loading} error={error}
          />
        </div>

        <div>
          {!data && loading && <div className="card loading">Comparing controllers…</div>}
          {!data && !loading && <div className="card loading">Enter a transfer function to begin.</div>}

          {data && (
            <>
              <RecommendationBanner result={data.results.find((r) => r.name === data.recommended)} />

              <div className="card">
                <h2>Plant analysis</h2>
                <PlantSummary plant={data.plant} />
              </div>

              <div className="card">
                <h2>Closed-loop step response <span className="sub">target = 1</span></h2>
                <StepChart results={data.results} recommended={data.recommended} />
              </div>

              <div className="card">
                <h2>Controller leaderboard</h2>
                <Leaderboard results={data.results} recommended={data.recommended} />
              </div>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="card">
                  <h2>Pole–zero map</h2>
                  <PoleZeroChart plant={data.plant} />
                </div>
                <div className="card">
                  <h2>Instant ML prediction</h2>
                  <PredictionCard prediction={prediction} recommended={data.recommended} />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
