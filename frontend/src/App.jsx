import { useState, useEffect, useCallback } from 'react'
import KpiBar from './components/KpiBar'
import H3Map from './components/H3Map'
import TimeSlider from './components/TimeSlider'
import OpportunitiesTable from './components/OpportunitiesTable'
import PricePanel from './components/PricePanel'
import MlopsPanel from './components/MlopsPanel'
import PipelinePanel from './components/PipelinePanel'
import { fetchScores, fetchTimeseries } from './api'

const TABS = ['Oportunidades', 'Mapa H3', 'Previsão ML', 'MLOps', 'Pipeline']

export default function App() {
  const [scores, setScores]       = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [activeTab, setActiveTab] = useState('Oportunidades')
  const [filters, setFilters]     = useState({ priority: '', risk: '' })

  // Time series state — lazy loaded when Mapa H3 tab is first opened
  const [timeDates, setTimeDates]     = useState([])
  const [timeRecords, setTimeRecords] = useState([])
  const [timeLoaded, setTimeLoaded]   = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)

  const loadScores = useCallback(() => {
    setLoading(true)
    fetchScores()
      .then(setScores)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadScores() }, [loadScores])

  useEffect(() => {
    if (activeTab === 'Mapa H3' && !timeLoaded) {
      fetchTimeseries()
        .then(data => {
          setTimeDates(data.dates ?? [])
          setTimeRecords(data.records ?? [])
          setTimeLoaded(true)
        })
        .catch(() => setTimeLoaded(true)) // fail silently
    }
  }, [activeTab, timeLoaded])

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
      {error   && <div className="loading" style={{ color: '#dc2626' }}>Erro: {error}</div>}

      {!loading && !error && (
        <>
          <KpiBar data={filtered} />

          <div className="filters">
            <select value={filters.priority} onChange={e => setFilters(f => ({ ...f, priority: e.target.value }))}>
              <option value="">Todas as prioridades</option>
              <option value="alta">Alta</option>
              <option value="media">Média</option>
              <option value="baixa">Baixa</option>
              <option value="investigar">Investigar</option>
            </select>
            <select value={filters.risk} onChange={e => setFilters(f => ({ ...f, risk: e.target.value }))}>
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

            {activeTab === 'Mapa H3' && (
              <>
                <TimeSlider
                  dates={timeDates}
                  selectedDate={selectedDate}
                  onChange={setSelectedDate}
                />
                <H3Map
                  data={filtered}
                  timeData={timeRecords}
                  selectedDate={selectedDate}
                />
              </>
            )}

            {activeTab === 'Previsão ML' && <PricePanel />}
            {activeTab === 'MLOps'       && <MlopsPanel />}
            {activeTab === 'Pipeline'    && (
              <PipelinePanel onComplete={() => { loadScores(); setTimeLoaded(false) }} />
            )}
          </main>
        </>
      )}
    </div>
  )
}
