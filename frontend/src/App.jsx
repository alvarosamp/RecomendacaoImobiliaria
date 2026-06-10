import { useState, useEffect, useCallback } from 'react'
import MapPage from './pages/MapPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import CommercePage from './pages/CommercePage'
import ValuationPage from './pages/ValuationPage'
import { fetchScores, fetchTimeseries } from './api'

const NAV = [
  { id: 'map',           label: 'Mapa da cidade',         icon: '◉' },
  { id: 'opportunities', label: 'Oportunidades',           icon: '◈' },
  { id: 'commerce',      label: 'Comércios faltantes',     icon: '◫' },
  { id: 'valuation',     label: 'Avaliar imóvel',          icon: '◧' },
]

export default function App() {
  const [page, setPage]   = useState('map')
  const [scores, setScores]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  // Time series (lazy — loaded once when map is first opened)
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
    if (page === 'map' && !timeLoaded) {
      fetchTimeseries()
        .then(data => {
          setTimeDates(data.dates ?? [])
          setTimeRecords(data.records ?? [])
        })
        .catch(() => {})
        .finally(() => setTimeLoaded(true))
    }
  }, [page, timeLoaded])

  return (
    <div className="layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Inteligência Territorial</h1>
          <span>Pouso Alegre · MG</span>
        </div>

        <nav className="sidebar-nav">
          {NAV.map(item => (
            <button
              key={item.id}
              className={`nav-item${page === item.id ? ' active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        {!loading && !error && scores.length > 0 && (
          <div className="sidebar-footer">
            {scores.length} células · {scores.filter(r => r.priority === 'alta').length} prioridade alta
          </div>
        )}
      </aside>

      {/* ── Main ── */}
      <main className="main">
        {loading && <div className="loading">Carregando dados do PostGIS…</div>}
        {error   && <div className="error-msg">Erro: {error}</div>}

        {!loading && !error && (
          <>
            {page === 'map' && (
              <MapPage
                scores={scores}
                timeDates={timeDates}
                timeRecords={timeRecords}
                selectedDate={selectedDate}
                onDateChange={setSelectedDate}
              />
            )}
            {page === 'opportunities' && <OpportunitiesPage scores={scores} />}
            {page === 'commerce'      && <CommercePage />}
            {page === 'valuation'     && <ValuationPage />}
          </>
        )}
      </main>
    </div>
  )
}
