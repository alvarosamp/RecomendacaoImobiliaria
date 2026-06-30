import { useState, useMemo } from 'react'

const PRIORITY_COLOR = {
  alta:       '#1B2A4A',
  media:      '#D97706',
  baixa:      '#78716C',
  investigar: '#7C3AED',
}

const PRIORITY_BG = {
  alta:       '#1B2A4A',
  media:      '#FEF3C7',
  baixa:      '#F4F2EE',
  investigar: '#EDE9FE',
}

const PRIORITY_TEXT = {
  alta:       '#fff',
  media:      '#92400E',
  baixa:      '#57534E',
  investigar: '#5B21B6',
}

const RISK_CONFIG = {
  baixo: { bg: '#DCFCE7', text: '#15803D' },
  medio: { bg: '#FEF3C7', text: '#92400E' },
  alto:  { bg: '#FEE2E2', text: '#B91C1C' },
}

function ScoreBar({ label, value, color }) {
  const pct = Math.min(100, Math.max(0, value || 0))
  return (
    <div className="score-row">
      <span className="score-row-label">{label}</span>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="score-num" style={{ color }}>{pct.toFixed(0)}</span>
    </div>
  )
}

function GrowthTag({ signal }) {
  if (signal == null) return null
  const label = signal > 0.003 ? 'Crescimento acelerado'
              : signal > 0.001 ? 'Crescimento moderado'
              : signal < -0.001 ? 'Retração'
              : 'Estável'
  const style = signal > 0.001
    ? { background: '#DCFCE7', color: '#15803D' }
    : signal < -0.001
    ? { background: '#FEE2E2', color: '#B91C1C' }
    : { background: '#F4F2EE', color: '#78716C' }

  return (
    <span className="growth-tag" style={style}>
      {signal > 0.001 ? '↑ ' : signal < -0.001 ? '↓ ' : '→ '}{label}
    </span>
  )
}

function OppCard({ row }) {
  const score = Math.max(row.score_residencial || 0, row.score_comercial || 0)
  const recs  = row.recommendations || []
  const pCfg  = PRIORITY_COLOR[row.priority]
  const pBg   = PRIORITY_BG[row.priority]
  const pTxt  = PRIORITY_TEXT[row.priority]
  const rCfg  = RISK_CONFIG[row.risk_level]

  return (
    <div className="opp-card">
      {/* Header */}
      <div className="opp-card-header">
        <div>
          <div className="opp-zona">{row.zona || 'Área sem nome'}</div>
          <div className="opp-cell-id">{row.h3_id}</div>
        </div>
        <div className="opp-badges">
          {row.priority && (
            <span
              className="badge"
              style={{ background: pBg, color: pTxt, border: `1px solid ${pCfg}20` }}
            >
              {row.priority === 'alta' ? '★ ' : ''}{row.priority}
            </span>
          )}
          {row.risk_level && rCfg && (
            <span
              className="badge"
              style={{ background: rCfg.bg, color: rCfg.text }}
            >
              Risco {row.risk_level}
            </span>
          )}
        </div>
      </div>

      {/* Scores */}
      <div className="score-bars">
        <ScoreBar label="Residencial" value={row.score_residencial} color="#1B2A4A" />
        <ScoreBar label="Comercial"   value={row.score_comercial}   color="#C9A84C" />
      </div>

      {/* Recommendations */}
      {recs.length > 0 && (
        <div className="opp-uses">
          {recs.slice(0, 2).map((r, i) => (
            <div className="use-row" key={i}>
              <span className="use-label">{r.use}</span>
              <span style={{ color: '#78716C', fontSize: 12 }}>{r.why}</span>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 }}>
        <GrowthTag signal={row.growth_signal} />
        <span style={{ fontSize: 11, color: '#A8A29E', fontWeight: 600 }}>
          Score {score.toFixed(0)}/100
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
  const avgScore     = (scores.reduce((s, r) => s + (r.score_residencial || 0), 0) / (scores.length || 1))

  return (
    <div className="page">
      <div className="page-header">
        <h2>Oportunidades de Investimento</h2>
        <p>Áreas rankeadas por potencial residencial e comercial, com justificativa baseada em dados.</p>
      </div>

      {/* KPIs */}
      <div className="kpi-strip">
        <div className="kpi-card navy">
          <span className="kpi-value">{scores.length}</span>
          <span className="kpi-label">Áreas analisadas</span>
        </div>
        <div className="kpi-card gold">
          <span className="kpi-value">{highPriority}</span>
          <span className="kpi-label">Alta prioridade</span>
        </div>
        <div className="kpi-card red">
          <span className="kpi-value">{highRisk}</span>
          <span className="kpi-label">Risco alto</span>
        </div>
        <div className="kpi-card green">
          <span className="kpi-value">{avgScore.toFixed(1)}</span>
          <span className="kpi-label">Score residencial médio</span>
        </div>
      </div>

      {/* Filters */}
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
        <span className="count-tag">{filtered.length} áreas</span>
      </div>

      {filtered.length === 0
        ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#78716C' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Nenhuma área encontrada</div>
            <div style={{ fontSize: 13, marginTop: 6 }}>Tente ajustar os filtros acima.</div>
          </div>
        )
        : (
          <div className="card-grid">
            {filtered.map(row => <OppCard key={row.h3_id} row={row} />)}
          </div>
        )
      }
    </div>
  )
}
