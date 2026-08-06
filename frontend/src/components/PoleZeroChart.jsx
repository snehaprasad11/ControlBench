import Plot from 'react-plotly.js'

export default function PoleZeroChart({ plant }) {
  const poles = {
    x: plant.poles.map((p) => p.re),
    y: plant.poles.map((p) => p.im),
    mode: 'markers', type: 'scatter', name: 'poles',
    marker: { symbol: 'x', size: 12, color: '#d64545', line: { width: 2 } },
  }
  const zeros = {
    x: plant.zeros.map((z) => z.re),
    y: plant.zeros.map((z) => z.im),
    mode: 'markers', type: 'scatter', name: 'zeros',
    marker: { symbol: 'circle-open', size: 12, color: '#1f6feb', line: { width: 2 } },
  }

  const layout = {
    autosize: true,
    height: 300,
    margin: { l: 46, r: 16, t: 20, b: 40 },
    xaxis: { title: 'Real', zeroline: true, zerolinecolor: '#aab', gridcolor: '#eef3f8' },
    yaxis: { title: 'Imag', zeroline: true, zerolinecolor: '#aab', gridcolor: '#eef3f8', scaleanchor: 'x' },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#1c2733', size: 11 },
    legend: { orientation: 'h', y: -0.25 },
    shapes: [{
      type: 'line', yref: 'paper', y0: 0, y1: 1, x0: 0, x1: 0,
      line: { color: '#e8873b', dash: 'dash', width: 1.5 },
    }],
    annotations: [{
      x: 0, y: 1.06, yref: 'paper', text: 'stability boundary (Re = 0)',
      showarrow: false, font: { size: 10, color: '#e8873b' },
    }],
  }

  return (
    <Plot
      className="plot"
      data={[poles, zeros]}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%' }}
    />
  )
}
