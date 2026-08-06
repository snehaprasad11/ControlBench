import Plot from 'react-plotly.js'
import { CONTROLLER_COLORS } from '../format'

export default function StepChart({ results, recommended }) {
  const traces = results.map((r) => ({
    x: r.step_response.time,
    y: r.step_response.output,
    type: 'scatter',
    mode: 'lines',
    name: r.name,
    line: {
      color: CONTROLLER_COLORS[r.name] || '#888',
      width: r.name === recommended ? 3 : 1.6,
    },
  }))

  const layout = {
    autosize: true,
    height: 380,
    margin: { l: 50, r: 16, t: 10, b: 60 },
    xaxis: { title: 'time (s)', gridcolor: '#eef3f8', zeroline: false },
    yaxis: { title: 'output', gridcolor: '#eef3f8', zeroline: false },
    legend: { orientation: 'h', y: -0.22 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#1c2733', size: 11 },
    shapes: [{
      type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 1, y1: 1,
      line: { color: '#b0bccb', dash: 'dot', width: 1 },
    }],
  }

  return (
    <Plot
      className="plot"
      data={traces}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%' }}
    />
  )
}
