import { useMemo, useState } from 'react'

const FACTORS = [
  ['Score residencial', 'score_residencial'],
  ['Score comercial', 'score_comercial'],
  ['Índice de vegetação (NDVI)', 'ndvi_mean_90'],
  ['Índice de área construída (NDBI)', 'ndbi_mean_90'],
  ['Confiabilidade dos dados', 'confidence'],
]

const number = (value, digits = 1) => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(digits) : '—'
}

export default function ScoreExplainPage({ scores }) {
  const [selectedId, setSelectedId] = useState('')
  const ordered = useMemo(() => [...scores].sort((a, b) =>
    Math.max(b.score_residencial || 0, b.score_comercial || 0) - Math.max(a.score_residencial || 0, a.score_comercial || 0)
  ), [scores])
  const selected = ordered.find(row => row.h3_id === selectedId) || ordered[0]

  if (!selected) return null
  const finalScore = Math.max(Number(selected.score_residencial) || 0, Number(selected.score_comercial) || 0)

  return (
    <div className="page explain-page">
      <div className="page-header">
        <div className="page-eyebrow">Transparência metodológica</div>
        <h2>Score explicável</h2>
        <p>Veja os sinais, evidências e restrições que sustentam a recomendação de cada célula territorial.</p>
      </div>

      <div className="explain-toolbar">
        <label htmlFor="score-cell">Área analisada</label>
        <select id="score-cell" value={selected.h3_id} onChange={event => setSelectedId(event.target.value)}>
          {ordered.map(row => <option key={row.h3_id} value={row.h3_id}>{row.neighborhood || row.zona || row.h3_id} · {row.h3_id}</option>)}
        </select>
      </div>

      <div className="explain-grid">
        <section className="explain-card explain-score-card">
          <div className="explain-card-heading"><span>Célula H3</span><strong>{selected.h3_id}</strong></div>
          <div className="explain-score-head"><div><h3>{selected.neighborhood || selected.zona || 'Área em análise'}</h3><p>{selected.zona || 'Zoneamento ainda não identificado'}</p></div><div><span>Score final</span><strong>{number(finalScore, 0)}</strong></div></div>
          <div className="factor-list">
            {FACTORS.map(([label, key]) => {
              const raw = Number(selected[key])
              const normalized = key === 'confidence' && raw <= 1 ? raw * 100 : raw
              const value = Number.isFinite(normalized) ? Math.max(0, Math.min(100, normalized)) : 0
              return <div className="factor-row" key={key}><div><span>{label}</span><strong>{key === 'confidence' ? `${number(value, 0)}%` : number(raw, key.startsWith('nd') ? 3 : 0)}</strong></div><div className="factor-track"><i style={{ width: `${value}%` }} /></div></div>
            })}
          </div>
        </section>

        <aside className="explain-card">
          <div className="explain-card-heading"><span>Evidências auditáveis</span></div>
          <div className="evidence-list">
            {(selected.explainability || []).map(item => <div key={item.label}><strong>{item.label}</strong><p>{item.value}</p></div>)}
          </div>
          {selected.legal_notes && <p className="legal-callout"><strong>Verificação legal:</strong> {selected.legal_notes}</p>}
          <p className="explain-disclaimer">O score é um instrumento de triagem. A decisão deve incluir diligência urbanística, técnica e comercial.</p>
        </aside>
      </div>
    </div>
  )
}
