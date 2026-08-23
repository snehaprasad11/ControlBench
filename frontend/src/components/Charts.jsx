import Plot from 'react-plotly.js'

const BASE_LAYOUT = {
  autosize: true,
  height: 300,
  margin: { l: 56, r: 56, t: 10, b: 44 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#8ea3bd', size: 11, family: 'JetBrains Mono, monospace' },
  legend: { orientation: 'h', y: -0.25 },
}
const GRID = 'rgba(255,255,255,0.07)'
const CONFIG = { displayModeBar: false, responsive: true }

// Open-loop Bode: magnitude (dB) + phase (deg) vs frequency, on twin y-axes.
// The crossover (|L| = 0 dB) and the -180 line make the phase margin visible.
export function BodeChart({ bode, bandwidthHz }) {
  const data = [
    {
      x: bode.freq_hz, y: bode.open_mag_db, type: 'scatter', mode: 'lines',
      name: '|L| (dB)', line: { color: '#22d3ee', width: 2.4 }, yaxis: 'y',
    },
    {
      x: bode.freq_hz, y: bode.open_phase_deg, type: 'scatter', mode: 'lines',
      name: '∠L (°)', line: { color: '#fbbf24', width: 2.4 }, yaxis: 'y2',
    },
  ]
  const layout = {
    ...BASE_LAYOUT,
    xaxis: { title: 'frequency (Hz)', type: 'log', gridcolor: GRID, zeroline: false },
    yaxis: { title: '|L| (dB)', gridcolor: GRID, zeroline: false },
    yaxis2: { title: '∠L (°)', overlaying: 'y', side: 'right', showgrid: false },
    shapes: [
      { type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0, yref: 'y',
        line: { color: '#8090a4', dash: 'dot', width: 1 } },
      bandwidthHz && {
        type: 'line', x0: bandwidthHz, x1: bandwidthHz, yref: 'paper', y0: 0, y1: 1,
        line: { color: '#5a6b80', dash: 'dash', width: 1 },
      },
    ].filter(Boolean),
  }
  return <Plot className="plot" data={data} layout={layout} config={CONFIG} useResizeHandler style={{ width: '100%' }} />
}

// Closed-loop |H(jf)| — its peak above 0 dB is the jitter peaking.
export function JitterChart({ bode }) {
  const data = [{
    x: bode.freq_hz, y: bode.closed_mag_db, type: 'scatter', mode: 'lines',
    name: '|H| (dB)', line: { color: '#34d399', width: 2.4 },
  }]
  const layout = {
    ...BASE_LAYOUT, height: 240,
    xaxis: { title: 'frequency (Hz)', type: 'log', gridcolor: GRID, zeroline: false },
    yaxis: { title: '|H| (dB)', gridcolor: GRID, zeroline: false },
    shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 0, y1: 0,
      line: { color: '#8090a4', dash: 'dot', width: 1 } }],
  }
  return <Plot className="plot" data={data} layout={layout} config={CONFIG} useResizeHandler style={{ width: '100%' }} />
}

// Normalised phase-step (lock) transient — where it settles is the lock time.
export function LockChart({ step }) {
  const data = [{
    x: step.x, y: step.y, type: 'scatter', mode: 'lines',
    name: 'phase step', line: { color: '#a78bfa', width: 2.4 },
  }]
  const layout = {
    ...BASE_LAYOUT, height: 240,
    xaxis: { title: 'time (s)', gridcolor: GRID, zeroline: false },
    yaxis: { title: 'normalised phase', gridcolor: GRID, zeroline: false },
    shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 1, y1: 1,
      line: { color: '#8090a4', dash: 'dot', width: 1 } }],
  }
  return <Plot className="plot" data={data} layout={layout} config={CONFIG} useResizeHandler style={{ width: '100%' }} />
}
