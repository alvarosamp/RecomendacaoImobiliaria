export default function KpiBar({ data }) {
  const total = data.length
  const avg = (key) => (data.reduce((s, r) => s + (r[key] || 0), 0) / (total || 1)).toFixed(1)
  const count = (pred) => data.filter(pred).length

  return (
    <div className="kpi-bar">
      <Card label="Células H3" value={total} />
      <Card label="Score residencial médio" value={avg('score_residencial')} />
      <Card label="Score comercial médio"   value={avg('score_comercial')} />
      <Card
        label="Prioridade alta"
        value={count(r => r.priority === 'alta')}
        highlight={count(r => r.priority === 'alta') > 0}
      />
      <Card
        label="Risco alto"
        value={count(r => r.risk_level === 'alto')}
        danger={count(r => r.risk_level === 'alto') > 0}
      />
    </div>
  )
}

function Card({ label, value, highlight, danger }) {
  return (
    <div className={`kpi-card${highlight ? ' kpi-highlight' : ''}${danger ? ' kpi-danger' : ''}`}>
      <span className="kpi-value">{value}</span>
      <span className="kpi-label">{label}</span>
    </div>
  )
}
