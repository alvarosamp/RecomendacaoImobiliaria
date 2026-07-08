import { useState, useEffect, useCallback, useRef, Suspense, lazy } from 'react'
import SetupScreen from './components/SetupScreen'
import { fetchScores, fetchTimeseries } from './api'

const MapPage           = lazy(() => import('./pages/MapPage'))
const OpportunitiesPage = lazy(() => import('./pages/OpportunitiesPage'))
const CommercePage      = lazy(() => import('./pages/CommercePage'))
const ValuationPage     = lazy(() => import('./pages/ValuationPage'))

// ── SVG Icons (real estate themed) ──────────────────────────────
function IconMap() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 1.5C6.51 1.5 4.5 3.51 4.5 6c0 3.75 4.5 10.5 4.5 10.5s4.5-6.75 4.5-10.5c0-2.49-2.01-4.5-4.5-4.5z"/>
      <circle cx="9" cy="6" r="1.5"/>
    </svg>
  )
}

function IconOpp() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="6" height="8" rx="1"/>
      <rect x="10" y="6" width="6" height="10" rx="1"/>
      <rect x="2" y="12" width="6" height="4" rx="1"/>
    </svg>
  )
}

function IconCommerce() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 7l1.5-4.5h11L16 7"/>
      <path d="M2 7v8a1 1 0 001 1h12a1 1 0 001-1V7"/>
      <path d="M2 7h14"/>
      <path d="M7 15V10h4v5"/>
    </svg>
  )
}

function IconValuation() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="14" height="14" rx="2"/>
      <path d="M6 9h6M9 6v6"/>
    </svg>
  )
}

const NAV = [
  { id: 'map',           label: 'Mapa da Cidade',       Icon: IconMap },
  { id: 'opportunities', label: 'Oportunidades',          Icon: IconOpp },
  { id: 'commerce',      label: 'Comércios Faltantes',   Icon: IconCommerce },
  { id: 'valuation',     label: 'Avaliar Imóvel',        Icon: IconValuation },
]

function RefreshStatus({ status, onDismiss }) {
  if (!status) return null
  const labels = {
    running: '↻ Atualizando dados…',
    done:    '✓ Dados atualizados',
    error:   '✕ Falha na atualização',
  }
  return (
    <div
      className={`refresh-status ${status}`}
      onClick={status !== 'running' ? onDismiss : undefined}
      style={{ cursor: status !== 'running' ? 'pointer' : 'default' }}
    >
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
            setTimeLoaded(false)
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

  const isEmpty = !loading && !error && scores.length === 0

  return (
    <div className="layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        {/* Brand */}
        <div className="sidebar-brand">
          <div className="sidebar-logo-row">
            <div className="sidebar-logo-badge">IT</div>
            <div>
              <div className="sidebar-brand-name">Inteligência{'\n'}Territorial</div>
            </div>
          </div>
          <div className="sidebar-brand-sub">
            <span className="sidebar-city-dot" />
            Pouso Alegre · MG
          </div>
        </div>

        {/* Nav */}
        <div className="sidebar-section-label">Módulos</div>
        <nav className="sidebar-nav">
          {NAV.map(item => (
            <button
              key={item.id}
              className={`nav-item${page === item.id ? ' active' : ''}`}
              onClick={() => setPage(item.id)}
              disabled={isEmpty}
            >
              <item.Icon />
              {item.label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        {!loading && !error && scores.length > 0 && (
          <div className="sidebar-footer">
            <div className="sidebar-stats">
              {scores.length} áreas · {scores.filter(r => r.priority === 'alta').length} alta prioridade
            </div>
            <button
              className="sidebar-refresh-btn"
              onClick={handleRefresh}
              disabled={refreshStatus === 'running'}
            >
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M11.5 2.5A5.5 5.5 0 1 0 12 7"/>
                <path d="M12 2.5V5h-2.5"/>
              </svg>
              Atualizar dados
            </button>
            <RefreshStatus
              status={refreshStatus}
              onDismiss={() => setRefreshStatus(null)}
            />
            
            <button className="sidebar-refresh-btn" style={{marginTop: '8px', opacity: 0.8}} onClick={() => {
              localStorage.removeItem('token');
              window.location.href = '/login';
            }}>
              Sair da conta
            </button>
          </div>
        )}
      </aside>

      {/* ── Main ── */}
      <main className="main">
        {loading && (
          <div className="loading">
            <div className="loading-spinner" />
            Verificando banco de dados…
          </div>
        )}
        {error && <div className="error-msg">Erro: {error}</div>}

        {/* First-time setup */}
        {isEmpty && (
          <SetupScreen
            onComplete={handleSetupComplete}
            onRefreshDone={handleRefreshDone}
          />
        )}

        {!loading && !error && scores.length > 0 && (
          <Suspense fallback={<div className="loading"><div className="loading-spinner" />Carregando módulo…</div>}>
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
          </Suspense>
        )}
      </main>
    </div>
  )
}
