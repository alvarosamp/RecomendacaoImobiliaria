import { useState, useMemo } from 'react'

const PRIORITY_CONFIG = {
  alta:       { bg: '#F5EDD4', text: '#92400E', accent: '#C9A84C', label: '★ Alta' },
  media:      { bg: '#FEF3C7', text: '#92400E', accent: '#D97706', label: 'Média' },
  baixa:      { bg: '#F4F2EE', text: '#57534E', accent: '#A8A29E', label: 'Baixa' },
  investigar: { bg: '#EDE9FE', text: '#5B21B6', accent: '#7C3AED', label: 'Investigar' },
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

function distanceLabel(value) {
  const meters = Number(value)
  if (!Number.isFinite(meters)) return 'sem dado'
  return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`
}

function OppCard({ row, onOpenConcept }) {
  const [expanded, setExpanded] = useState(false)
  const score = Math.max(row.score_residencial || 0, row.score_comercial || 0)
  const recs  = row.recommendations || []
  const pCfg  = PRIORITY_CONFIG[row.priority]
  const rCfg  = RISK_CONFIG[row.risk_level]

  const bairroName = row.neighborhood || 'Região em análise'

  return (
    <div className={`opp-card priority-${row.priority || 'baixa'}`}>
      {/* Header */}
      <div className="opp-card-header">
        <div>
          <div className="opp-zona">{bairroName}</div>
          <div className="opp-cell-id">Bairro de referência • Zona {row.zona || 'não identificada'}</div>
        </div>
        <div className="opp-badges">
          {row.priority && pCfg && (
            <span className="badge" style={{ background: pCfg.bg, color: pCfg.text }}>
              {pCfg.label}
            </span>
          )}
          {row.risk_level && rCfg && (
            <span className="badge" style={{ background: rCfg.bg, color: rCfg.text }}>
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

      <div className="opp-context-grid">
        <div><span>Farmácia</span><strong>{distanceLabel(row.dist_min_pharmacy_m)}</strong></div>
        <div><span>Mercado</span><strong>{distanceLabel(row.dist_min_supermarket_m)}</strong></div>
        <div><span>Escola</span><strong>{distanceLabel(row.dist_min_school_m)}</strong></div>
        <div><span>Hospitais</span><strong>{row.poi_hospital_cnt ?? 0} no entorno</strong></div>
      </div>

      {/* Main use recommendation */}
      {recs.length > 0 && (
        <div className="opp-uses">
          {recs.slice(0, expanded ? 3 : 1).map((r, i) => (
            <div className="use-row" key={i}>
              <span className="use-label">{r.use}</span>
              <span style={{ color: 'var(--muted)', fontSize: 12 }}>{r.why}</span>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="opp-card-footer">
        <GrowthTag signal={row.growth_signal} />
        <span className="opp-score-label">Score {score.toFixed(0)}/100</span>
      </div>

      {/* Details toggle */}
      {row.explainability?.length > 0 && (
        <>
          <button
            className="opp-details-toggle"
            onClick={() => setExpanded(e => !e)}
          >
            {expanded ? '↑ Menos detalhes' : '↓ Ver fatores explicativos'}
          </button>

          {expanded && (
            <div className="explain-list">
              {row.explainability.slice(0, 5).map(item => (
                <div key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Concept button */}
      {onOpenConcept && (
        <button className="opp-concept-btn" onClick={() => onOpenConcept(row)}>
          Abrir conceito desta área →
        </button>
      )}
    </div>
  )
}

export default function OpportunitiesPage({ scores, onOpenConcept }) {
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

  // Count by priority for chip badges
  const countByPriority = (p) => scores.filter(r => r.priority === p).length
  const countByRisk     = (r) => scores.filter(s => s.risk_level === r).length

  return (
    <div className="page">
      {/* Hero */}
      <div className="page-hero">
        <div className="page-hero-eyebrow">Ranqueamento territorial</div>
        <h2>Oportunidades de Investimento</h2>
        <p>
          Áreas rankeadas por potencial residencial e comercial, com justificativa
          baseada em dados. Clique em uma área para ver os fatores explicativos.
        </p>
        <div className="page-hero-stats">
          <div className="page-hero-stat">
            <span className="page-hero-stat-value">{scores.length}</span>
            <span className="page-hero-stat-label">Áreas analisadas</span>
          </div>
          <div className="page-hero-stat">
            <span className="page-hero-stat-value">{highPriority}</span>
            <span className="page-hero-stat-label">Alta prioridade</span>
          </div>
          <div className="page-hero-stat">
            <span className="page-hero-stat-value">{highRisk}</span>
            <span className="page-hero-stat-label">Risco alto</span>
          </div>
          <div className="page-hero-stat">
            <span className="page-hero-stat-value">{avgScore.toFixed(0)}</span>
            <span className="page-hero-stat-label">Score médio</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        {/* Priority chips */}
        <div className="filter-group">
          <span className="filter-group-label">Prioridade</span>
          <div className="chip-row">
            <button
              className={`chip${priority === '' ? ' active' : ''}`}
              onClick={() => setPriority('')}
            >
              Todas
            </button>
            {[
              { id: 'alta',       label: '★ Alta',       cls: 'gold' },
              { id: 'media',      label: 'Média',         cls: 'orange' },
              { id: 'baixa',      label: 'Baixa',         cls: '' },
              { id: 'investigar', label: 'Investigar',    cls: 'purple' },
            ].map(p => (
              <button
                key={p.id}
                className={`chip${priority === p.id ? ` active ${p.cls}` : ''}`}
                onClick={() => setPriority(v => v === p.id ? '' : p.id)}
              >
                {p.label}
                <span className="chip-count">{countByPriority(p.id)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Risk chips */}
        <div className="filter-group">
          <span className="filter-group-label">Risco</span>
          <div className="chip-row">
            <button
              className={`chip${risk === '' ? ' active' : ''}`}
              onClick={() => setRisk('')}
            >
              Todos
            </button>
            {[
              { id: 'baixo', label: 'Baixo', cls: 'green' },
              { id: 'medio', label: 'Médio', cls: 'orange' },
              { id: 'alto',  label: 'Alto',  cls: 'red' },
            ].map(r => (
              <button
                key={r.id}
                className={`chip${risk === r.id ? ` active ${r.cls}` : ''}`}
                onClick={() => setRisk(v => v === r.id ? '' : r.id)}
              >
                {r.label}
                <span className="chip-count">{countByRisk(r.id)}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Sort toggle */}
        <div className="filter-group">
          <span className="filter-group-label">Ordenar por</span>
          <div className="sort-toggle">
            <button
              className={`sort-toggle-btn${sort === 'score' ? ' active' : ''}`}
              onClick={() => setSort('score')}
            >
              Maior score
            </button>
            <button
              className={`sort-toggle-btn${sort === 'growth' ? ' active' : ''}`}
              onClick={() => setSort('growth')}
            >
              Crescimento
            </button>
          </div>
        </div>

        <span className="count-tag">{filtered.length} áreas</span>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h3>Nenhuma área encontrada</h3>
          <p>Tente ajustar os filtros acima para ver mais resultados.</p>
        </div>
      ) : (
        <div className="card-grid">
          {filtered.map(row => (
            <OppCard key={row.h3_id} row={row} onOpenConcept={onOpenConcept} />
          ))}
        </div>
      )}
    </div>
  )
}
