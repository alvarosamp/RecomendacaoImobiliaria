import { useState, useEffect, useCallback, useRef } from 'react'
import MapPage from './pages/MapPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import CommercePage from './pages/CommercePage'
import ValuationPage from './pages/ValuationPage'
import SetupScreen from './components/SetupScreen'
import { fetchScores, fetchTimeseries } from './api'

const NAV = [
  { id: 'map',           label: 'Mapa da cidade',         icon: '◉' },
  { id: 'opportunities', label: 'Oportunidades',           icon: '◈' },
  { id: 'commerce',      label: 'Comércios faltantes',     icon: '◫' },
  { id: 'valuation',     label: 'Avaliar imóvel',          icon: '◧' },
]

function RefreshStatus({ status, onDismiss }) {
  if (!status) return null
  const colors = { running: '#2563eb', done: '#16a34a', error: '#dc2626' }
  const labels = {
    running: '↻ Atualizando…',
    done:    '✓ Dados atualizados',
    error:   '✕ Falha na atualização',
  }
  return (
    <div style={{
      background: colors[status] ?? '#64748b',
      color: '#fff', fontSize: 11, fontWeight: 600,
      padding: '6px 12px', borderRadius: 6, textAlign: 'center',
      margin: '8px 0 0', cursor: status !== 'running' ? 'pointer' : 'default',
    }} onClick={status !== 'running' ? onDismiss : undefined}>
      {labels[status]}
    </div>
  )
}

export default function App() {
  const [page, setPage]     = useState('map')
  const [scores, setScores] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [refreshStatus, setRefreshStatus] = useState(null)
  const refreshRef = useRef(null)

  // Time series (lazy — loaded once when map is first opened)
  const [timeDates, setTimeDates]       = useState([])
  const [timeRecords, setTimeRecords]   = useState([])
  const [timeLoaded, setTimeLoaded]     = useState(false)
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

  // ── Quick refresh pipeline ───────────────────────────────────────
  const handleRefresh = async () => {
    if (refreshStatus === 'running') return
    setRefreshStatus('running')
    try {
      await fetch('/api/pipeline/refresh', { method: 'POST' })
    } catch {
      setRefreshStatus('error')
      return
    }
    clearInterval(refreshRef.current)
    refreshRef.current = setInterval(async () => {
      try {
        const s = await fetch('/api/pipeline/status').then(r => r.json())
        if (s.done) {
          clearInterval(refreshRef.current)
          setRefreshStatus(s.success ? 'done' : 'error')
          if (s.success) {
            loadScores()
            setTimeLoaded(false) // reload time series too
          }
        }
      } catch (_) {}
    }, 1500)
  }

  useEffect(() => () => clearInterval(refreshRef.current), [])

  const handleSetupComplete = () => {
    loadScores()
    setTimeLoaded(false)
  }

  const handleRefreshDone = () => {
    loadScores()
    setTimeLoaded(false)
  }

  // ── Empty state: show setup screen ──────────────────────────────
  const isEmpty = !loading && !error && scores.length === 0

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
              disabled={isEmpty}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        {!loading && !error && scores.length > 0 && (
          <div className="sidebar-footer">
            <div className="sidebar-stats">
              {scores.length} células · {scores.filter(r => r.priority === 'alta').length} alta prioridade
            </div>
            <button
              className="sidebar-refresh-btn"
              onClick={handleRefresh}
              disabled={refreshStatus === 'running'}
            >
              ↻ Atualizar dados
            </button>
            <RefreshStatus
              status={refreshStatus}
              onDismiss={() => setRefreshStatus(null)}
            />
          </div>
        )}
      </aside>

      {/* ── Main ── */}
      <main className="main">
        {loading && <div className="loading">Verificando banco de dados…</div>}
        {error   && <div className="error-msg">Erro: {error}</div>}

        {/* First-time setup */}
        {isEmpty && (
          <SetupScreen
            onComplete={handleSetupComplete}
            onRefreshDone={handleRefreshDone}
          />
        )}

        {!loading && !error && scores.length > 0 && (
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
