export default function Verdict({ passes, violations, grade }) {
  return (
    <div className={'verdict ' + (passes ? 'pass' : 'fail')}>
      <div className="verdict-icon">{passes ? '✓' : '✕'}</div>
      <div>
        <strong>{passes ? 'Qualified across temperature' : 'Fails temperature spec'}</strong>
        {passes ? (
          <p>This loop filter holds every spec across {grade || 'the selected temperature grade'}.</p>
        ) : (
          <ul>{violations.map((v, i) => <li key={i}>{v}</li>)}</ul>
        )}
      </div>
    </div>
  )
}
