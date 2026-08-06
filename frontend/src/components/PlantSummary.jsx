function complexStr(c) {
  const im = c.im
  const sign = im >= 0 ? '+' : '−'
  return `${c.re.toFixed(2)} ${sign} ${Math.abs(im).toFixed(2)}j`
}

export default function PlantSummary({ plant }) {
  return (
    <>
      <div className="stats">
        <div className="stat"><b>{plant.order}</b><span>order</span></div>
        <div className="stat">
          <b>{plant.stable
            ? <span className="pill ok">stable</span>
            : <span className="pill no">unstable</span>}</b>
          <span>open loop</span>
        </div>
        <div className="stat"><b>{plant.damping_ratio.toFixed(2)}</b><span>damping ζ</span></div>
        <div className="stat"><b>{plant.natural_frequency.toFixed(2)}</b><span>ωₙ (rad/s)</span></div>
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>
        poles: {plant.poles.map(complexStr).join(',  ')}
        {plant.zeros.length > 0 && <> &nbsp;·&nbsp; zeros: {plant.zeros.map(complexStr).join(',  ')}</>}
      </p>
    </>
  )
}
