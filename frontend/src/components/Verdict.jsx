export default function Verdict({ passes, violations }) {
  return (
    <div className={'verdict ' + (passes ? 'pass' : 'fail')}>
      <div className="verdict-icon">{passes ? '✓' : '✕'}</div>
      <div>
        <strong>{passes ? 'Robust across PVT' : 'Fails PVT spec'}</strong>
        {passes ? (
          <p>This loop filter holds every spec at all corners.</p>
        ) : (
          <ul>{violations.map((v, i) => <li key={i}>{v}</li>)}</ul>
        )}
      </div>
    </div>
  )
}
