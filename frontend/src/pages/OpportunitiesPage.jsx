import { useState, useMemo } from 'react'

const PRIORITY_COLOR = {
  alta:       '#16a34a',
  media:      '#ca8a04',
  baixa:      '#94a3b8',
  investigar: '#7c3aed',
}

const RISK_COLOR = {
  baixo: '#16a34a',
  medio: '#ca8a04',
  alto:  '#dc2626',
}

function ScoreBar({ label, value, color }) {
  const pct = Math.min(100, Math.max(0, value || 0))
  return (
    <div className="score-row">
      <span>{label}</span>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="score-num" style={{ color }}>{pct.toFixed(0)}</span>
    </div>
  )
}

function GrowthTag({ signal }) {
  if (signal == null) return null
  const label = signal > 0.003 ? 'crescimento acelerado'
              : signal > 0.001 ? 'crescimento moderado'
              : signal < -0.001 ? 'retração'
              : 'estável'
  const color = signal > 0.001 ? { bg: '#dcfce7', text: '#15803d' }
              : signal < -0.001 ? { bg: '#fee2e2', text: '#b91c1c' }
              : { bg: '#f1f5f9', text: '#64748b' }
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
      background: color.bg, color: color.text,
    }}>
      {label}
    </span>
  )
}

function OppCard({ row }) {
  const score = Math.max(row.score_residencial || 0, row.score_comercial || 0)
  const recs  = row.recommendations || []

  return (
    <div className="opp-card">
      <div className="opp-card-header">
        <div>
          <div className="opp-cell-id">{row.h3_id}</div>
          {row.zona && (
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{row.zona}</div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 5, flexDirection: 'column', alignItems: 'flex-end' }}>
          {row.priority && (
            <span className="badge" style={{ background: PRIORITY_COLOR[row.priority] ?? '#94a3b8' }}>
              {row.priority}
            </span>
          )}
          {row.risk_level && (
            <span className="badge" style={{ background: RISK_COLOR[row.risk_level] ?? '#94a3b8' }}>
              risco {row.risk_level}
            </span>
          )}
        </div>
      </div>

      <div className="score-bars">
        <ScoreBar label="Residencial" value={row.score_residencial} color="#2563eb" />
        <ScoreBar label="Comercial"   value={row.score_comercial}   color="#16a34a" />
      </div>

      {recs.length > 0 && (
        <div className="opp-uses">
          {recs.slice(0, 2).map((r, i) => (
            <div className="use-row" key={i}>
              <span className="use-label">{r.use}</span>
              <span style={{ color: '#64748b', fontSize: 12 }}>{r.why}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <GrowthTag signal={row.growth_signal} />
        <span style={{ fontSize: 11, color: '#94a3b8' }}>
          Score: {score.toFixed(0)}/100
        </span>
      </div>
    </div>
  )
}

export default function OpportunitiesPage({ scores }) {
  const [priority, setPriority] = useState('')
  const [risk, setRisk]         = useState('')
  const [sort, setSort]         = useState('score')

  const filtered = useMemo(() => {
    let rows = scores.filter(r => {
      if (priority && r.priority !== priority) return false
      if (risk     && r.risk_level !== risk)   return false
      return true
    })
    if (sort === 'score') {
      rows = [...rows].sort((a, b) =>
        Math.max(b.score_residencial || 0, b.score_comercial || 0) -
        Math.max(a.score_residencial || 0, a.score_comercial || 0)
      )
    } else if (sort === 'growth') {
      rows = [...rows].sort((a, b) => (b.growth_signal || 0) - (a.growth_signal || 0))
    }
    return rows
  }, [scores, priority, risk, sort])

  const highPriority = scores.filter(r => r.priority === 'alta').length
  const highRisk     = scores.filter(r => r.risk_level === 'alto').length

  return (
    <div className="page">
      <div className="page-header">
        <h2>Oportunidades de investimento</h2>
        <p>Células H3 rankeadas por potencial residencial e comercial, com justificativa por dados.</p>
      </div>

      <div className="kpi-strip">
        <div className="kpi-card">
          <span className="kpi-value">{scores.length}</span>
          <span className="kpi-label">Células analisadas</span>
        </div>
        <div className="kpi-card green">
          <span className="kpi-value">{highPriority}</span>
          <span className="kpi-label">Prioridade alta</span>
        </div>
        <div className="kpi-card red">
          <span className="kpi-value">{highRisk}</span>
          <span className="kpi-label">Risco alto</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-value">
            {(scores.reduce((s, r) => s + (r.score_residencial || 0), 0) / (scores.length || 1)).toFixed(1)}
          </span>
          <span className="kpi-label">Score residencial médio</span>
        </div>
      </div>

      <div className="filters-bar">
        <select value={priority} onChange={e => setPriority(e.target.value)}>
          <option value="">Todas as prioridades</option>
          <option value="alta">Alta</option>
          <option value="media">Média</option>
          <option value="baixa">Baixa</option>
          <option value="investigar">Investigar</option>
        </select>
        <select value={risk} onChange={e => setRisk(e.target.value)}>
          <option value="">Todos os riscos</option>
          <option value="baixo">Baixo</option>
          <option value="medio">Médio</option>
          <option value="alto">Alto</option>
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)}>
          <option value="score">Ordenar: maior score</option>
          <option value="growth">Ordenar: crescimento urbano</option>
        </select>
        <span className="count-tag">{filtered.length} células</span>
      </div>

      {filtered.length === 0
        ? <p style={{ color: '#64748b', textAlign: 'center', padding: 40 }}>Nenhuma célula com os filtros selecionados.</p>
        : <div className="card-grid">
            {filtered.map(row => <OppCard key={row.h3_id} row={row} />)}
          </div>
      }
    </div>
  )
}
