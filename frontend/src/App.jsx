import { useState, useEffect } from 'react'
import KpiBar from './components/KpiBar'
import H3Map from './components/H3Map'
import OpportunitiesTable from './components/OpportunitiesTable'
import PricePanel from './components/PricePanel'
import MlopsPanel from './components/MlopsPanel'
import { fetchScores } from './api'

const TABS = ['Oportunidades', 'Mapa H3', 'Previsão ML', 'MLOps']

export default function App() {
  const [scores, setScores] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('Oportunidades')
  const [filters, setFilters] = useState({ priority: '', risk: '' })

  useEffect(() => {
    fetchScores()
      .then(setScores)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = scores.filter(row => {
    if (filters.priority && row.priority !== filters.priority) return false
    if (filters.risk && row.risk_level !== filters.risk) return false
    return true
  })

  return (
    <div className="app">
      <header className="header">
        <h1>Recomendação Imobiliária</h1>
        <span className="subtitle">Inteligência territorial · Pouso Alegre MG</span>
      </header>

      {loading && <div className="loading">Carregando dados do PostGIS…</div>}

      {error && (
        <div className="loading" style={{ color: '#dc2626' }}>
          Erro ao carregar: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <KpiBar data={filtered} />

          <div className="filters">
            <select
              value={filters.priority}
              onChange={e => setFilters(f => ({ ...f, priority: e.target.value }))}
            >
              <option value="">Todas as prioridades</option>
              <option value="alta">Alta</option>
              <option value="media">Média</option>
              <option value="baixa">Baixa</option>
              <option value="investigar">Investigar</option>
            </select>
            <select
              value={filters.risk}
              onChange={e => setFilters(f => ({ ...f, risk: e.target.value }))}
            >
              <option value="">Todos os riscos</option>
              <option value="baixo">Baixo</option>
              <option value="medio">Médio</option>
              <option value="alto">Alto</option>
            </select>
            <span style={{ color: '#64748b', fontSize: 12, alignSelf: 'center' }}>
              {filtered.length} células
            </span>
          </div>

          <nav className="tabs">
            {TABS.map(tab => (
              <button
                key={tab}
                className={`tab${activeTab === tab ? ' active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab}
              </button>
            ))}
          </nav>

          <main className="content">
            {activeTab === 'Oportunidades' && <OpportunitiesTable data={filtered} />}
            {activeTab === 'Mapa H3'       && <H3Map data={filtered} />}
            {activeTab === 'Previsão ML'   && <PricePanel />}
            {activeTab === 'MLOps'         && <MlopsPanel />}
          </main>
        </>
      )}
    </div>
  )
}
