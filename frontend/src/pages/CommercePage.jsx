import { useEffect, useMemo, useState } from 'react'
import { fetchCommerceGaps } from '../api'

const distance = value => value == null ? 'distância indisponível' : value < 1000 ? `${value} m` : `${(value / 1000).toFixed(1)} km`

export default function CommercePage() {
  const [gaps, setGaps] = useState([]); const [filter, setFilter] = useState('all'); const [loading, setLoading] = useState(true); const [error, setError] = useState(null)
  useEffect(() => { fetchCommerceGaps().then(data => { if (data?.error) throw new Error(data.error); setGaps(Array.isArray(data) ? data : []) }).catch(err => setError(err.message)).finally(() => setLoading(false)) }, [])
  const visible = useMemo(() => gaps.filter(gap => filter === 'all' || gap.type === filter), [gaps, filter])
  return <div className="page">
    <div className="page-hero"><div className="page-hero-eyebrow">Inteligência Comercial</div><h2>Carências de serviços</h2><p>Déficits identificados a partir da distância e presença de equipamentos, crescimento urbano e zoneamento.</p></div>
    <div className="filters-bar"><div className="filter-group"><span className="filter-group-label">Serviço</span><div className="chip-row"><button className={`chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>Todos</button>{gaps.map(gap => <button key={gap.type} className={`chip ${filter === gap.type ? 'active' : ''}`} onClick={() => setFilter(gap.type)}>{gap.label}</button>)}</div></div></div>
    {loading && <div className="loading"><div className="loading-spinner" />Analisando cobertura de serviços…</div>}
    {error && <div className="error-msg">Não foi possível carregar as carências: {error}</div>}
    {!loading && !error && visible.length === 0 && <div className="empty-state"><h3>Nenhuma carência encontrada</h3><p>Execute ou atualize o pipeline territorial para gerar o diagnóstico.</p></div>}
    <div className="commerce-grid">{visible.map(gap => <section className="opp-card" key={gap.type}><div className="opp-card-header"><div><div className="opp-zona">{gap.label}</div><div className="opp-cell-id">{gap.cells_affected} células com possível déficit</div></div><span className="badge" style={{ background: '#F5EDD4', color: '#92400E' }}>Priorizar análise</span></div><p className="commerce-description">{gap.description}</p><div className="opp-uses">{gap.top_locations.map(location => <div className="commerce-location" key={location.h3_id}><strong>{location.zona} · {distance(location.dist_m)}</strong><span>{location.typology} · crescimento {location.growth_signal}</span><small>{location.reasons?.[0]}</small></div>)}</div></section>)}</div>
  </div>
}
