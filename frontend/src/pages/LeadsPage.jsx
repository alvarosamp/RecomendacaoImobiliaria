import { useState } from 'react'

const LEADS = [
  { id: '1', name: 'Carlos Eduardo', budget: 'R$ 800k - 1.2M', score: 92, status: 'Quente', interest: 'Pinheiros, 2 Dorms' },
  { id: '2', name: 'Mariana Silva', budget: 'R$ 400k - 600k', score: 78, status: 'Morno', interest: 'Vila Mariana, Studio' },
  { id: '3', name: 'Investimentos Alpha', budget: 'R$ 2M - 5M', score: 95, status: 'Quente', interest: 'Itaim Bibi, Comercial' },
  { id: '4', name: 'Roberto Almeida', budget: 'R$ 1.5M - 2M', score: 45, status: 'Frio', interest: 'Moema, 3 Dorms' }
]

export default function LeadsPage() {
  const [filter, setFilter] = useState('all')

  const items = LEADS.filter(l => filter === 'all' || l.status.toLowerCase() === filter).sort((a, b) => b.score - a.score)

  return (
    <div className="page">
      <div className="page-hero">
        <div className="page-hero-eyebrow">Gestão de Clientes</div>
        <h2>Lead Scoring</h2>
        <p>Priorize seus clientes baseado na probabilidade de fechamento. O score analisa o perfil, orçamento e cruzamento territorial de interesses.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <span className="filter-group-label">Temperatura do Lead</span>
          <div className="chip-row">
            <button className={`chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>Todos</button>
            <button className={`chip gold ${filter === 'quente' ? 'active' : ''}`} onClick={() => setFilter('quente')}>Quentes</button>
            <button className={`chip orange ${filter === 'morno' ? 'active' : ''}`} onClick={() => setFilter('morno')}>Mornos</button>
            <button className={`chip ${filter === 'frio' ? 'active' : ''}`} onClick={() => setFilter('frio')}>Frios</button>
          </div>
        </div>
      </div>

      <div className="card-grid">
        {items.map(lead => (
          <div key={lead.id} className={`opp-card priority-${lead.status === 'Quente' ? 'alta' : lead.status === 'Morno' ? 'media' : 'baixa'}`}>
            <div className="opp-card-header">
              <div>
                <div className="opp-zona">{lead.name}</div>
                <div className="opp-cell-id">{lead.interest}</div>
              </div>
              <div className="opp-badges">
                <span className="badge" style={{
                  background: lead.status === 'Quente' ? '#F5EDD4' : lead.status === 'Morno' ? '#FEF3C7' : '#F4F2EE',
                  color: lead.status === 'Quente' ? '#92400E' : lead.status === 'Morno' ? '#D97706' : '#57534E'
                }}>
                  {lead.status}
                </span>
              </div>
            </div>

            <div className="score-bars" style={{ marginTop: 16 }}>
              <div className="score-row">
                <span className="score-row-label">Prob. de Conversão</span>
                <div className="score-track">
                  <div className="score-fill" style={{ width: `${lead.score}%`, background: lead.status === 'Quente' ? '#C9A84C' : lead.status === 'Morno' ? '#D97706' : '#A8A29E' }} />
                </div>
                <span className="score-num" style={{ color: lead.status === 'Quente' ? '#C9A84C' : lead.status === 'Morno' ? '#D97706' : '#A8A29E' }}>{lead.score}</span>
              </div>
            </div>

            <div className="opp-uses" style={{ marginTop: 16 }}>
              <div className="use-row">
                <span className="use-label">Orçamento estimado</span>
                <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: 13 }}>{lead.budget}</span>
              </div>
            </div>

            <button className="landing-btn-outline" style={{ marginTop: 16, width: '100%', padding: '8px', fontSize: '13px' }}>
              Ver perfil completo
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
