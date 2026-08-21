import { useState, useEffect, useCallback, useRef, Suspense, lazy, useContext } from 'react'
import SetupScreen from './components/SetupScreen'
import { clearMapDataCache, fetchScores, fetchTimeseries } from './api'
import { AuthContext } from './contexts/AuthContext'

const MapPage           = lazy(() => import('./pages/MapPage'))
const OpportunitiesPage = lazy(() => import('./pages/OpportunitiesPage'))
const CommercePage      = lazy(() => import('./pages/CommercePage'))
const ValuationPage     = lazy(() => import('./pages/ValuationPage'))
const ConceptPage       = lazy(() => import('./pages/ConceptStudioPage'))
const CaseStudyPage     = lazy(() => import('./pages/CaseStudyPage'))
const LeadsPage         = lazy(() => import('./pages/LeadsPage'))

// ── SVG Icons ──────────────────────────────────────────
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

function IconConcept() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 15V7l6-4 6 4v8"/>
      <path d="M6 15v-4h6v4"/>
      <path d="M5 8.5h8"/>
    </svg>
  )
}

function IconCaseStudy() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 2h8l2 2v12H4z"/>
      <path d="M11 2v3h3"/>
      <path d="M6.5 8h5M6.5 11h5M6.5 14h3"/>
    </svg>
  )
}

function IconLead() {
  return (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="6" r="3"/>
      <path d="M3 16c0-3 2.7-5 6-5s6 2 6 5"/>
      <circle cx="14" cy="4" r="1.4"/>
    </svg>
  )
}

function IconLogout() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 14H2a1 1 0 01-1-1V2a1 1 0 011-1h3"/>
      <path d="M10 11l4-4-4-4"/>
      <path d="M14 7.5H5"/>
    </svg>
  )
}

// ── Nav groups ──────────────────────────────────────────
const NAV_GROUPS = [
  {
    label: 'Explorar',
    items: [
      { id: 'map',      label: 'Mapa da Cidade',     Icon: IconMap },
      { id: 'opportunities', label: 'Oportunidades',  Icon: IconOpp },
      { id: 'commerce', label: 'Comércios Faltantes', Icon: IconCommerce },
    ],
  },
  {
    label: 'Analisar',
    items: [
      { id: 'valuation', label: 'Avaliar Imóvel',   Icon: IconValuation },
      { id: 'leads',     label: 'Lead Scoring',      Icon: IconLead },
    ],
  },
  {
    label: 'Criar',
    items: [
      { id: 'concept',    label: 'Conceito e Obra',  Icon: IconConcept },
      { id: 'case-study', label: 'Estudo de Caso',   Icon: IconCaseStudy },
    ],
  },
]

const PROFILE_CONFIG = {
  investidor: {
    label: 'Investidor',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'valuation', 'case-study'],
  },
  corretor: {
    label: 'Corretor',
    defaultPage: 'leads',
    pages: ['leads', 'valuation', 'map', 'concept'],
  },
  incorporadora: {
    label: 'Incorporadora',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'concept', 'case-study'],
  },
  governo: {
    label: 'Poder Público',
    defaultPage: 'map',
    pages: ['map', 'commerce', 'opportunities', 'case-study'],
  },
}

function getProfile(role) {
  return PROFILE_CONFIG[role] ? role : 'investidor'
}

function getNavigation(profile) {
  const allowedPages = new Set(PROFILE_CONFIG[profile].pages)
  return NAV_GROUPS
    .map(group => ({ ...group, items: group.items.filter(item => allowedPages.has(item.id)) }))
    .filter(group => group.items.length > 0)
}

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

function Sidebar({ page, setPage, scores, isEmpty, loading, error, refreshStatus, onRefresh, onDismissRefresh, user, profile, onProfileChange }) {
  const userData = user || {}
  const navigation = getNavigation(profile)

  const initials = (userData.name || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo-badge">Ur</div>
          <div className="sidebar-brand-name">Urbia</div>
        </div>
        <div className="sidebar-brand-sub">
          <span className="sidebar-city-dot" />
          Inteligência territorial
        </div>
      </div>

      {/* Nav groups */}
      {navigation.map(group => (
        <div key={group.label} className="sidebar-group">
          <span className="sidebar-group-label">{group.label}</span>
          <nav className="sidebar-nav">
            {group.items.map(item => (
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
        </div>
      ))}

      {/* Footer */}
      <div className="sidebar-footer">
        {/* User row */}
        <div className="sidebar-user-row">
          <div className="sidebar-user-avatar">{initials}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{userData.name || 'Usuário'}</div>
            <div className="sidebar-user-role">{PROFILE_CONFIG[profile].label}</div>
          </div>
          <button className="sidebar-logout-btn" onClick={handleLogout} title="Sair">
            <IconLogout />
          </button>
        </div>

        <label className="profile-switcher-label" htmlFor="profile-switcher">Modo de trabalho</label>
        <select
          id="profile-switcher"
          className="profile-switcher"
          value={profile}
          onChange={event => onProfileChange(event.target.value)}
        >
          {Object.entries(PROFILE_CONFIG).map(([id, config]) => (
            <option key={id} value={id}>{config.label}</option>
          ))}
        </select>

        {!loading && !error && scores.length > 0 && (
          <>
            <div className="sidebar-stats">
              {scores.length} áreas · {scores.filter(r => r.priority === 'alta').length} alta prioridade
            </div>
            <button
              className="sidebar-refresh-btn"
              onClick={onRefresh}
              disabled={refreshStatus === 'running'}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M10.5 2.5A5 5 0 1 0 11 6"/>
                <path d="M11 2.5V5H8.5"/>
              </svg>
              Atualizar dados
            </button>
            <RefreshStatus status={refreshStatus} onDismiss={onDismissRefresh} />
          </>
        )}
      </div>
    </aside>
  )
}

export default function App() {
  const { user, updateProfile } = useContext(AuthContext)
  const profile = getProfile(user?.role)
  const [page, setPage]     = useState(PROFILE_CONFIG[profile].defaultPage)
  const [scores, setScores] = useState([])
  const [conceptSeed, setConceptSeed] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [refreshStatus, setRefreshStatus] = useState(null)
  const refreshRef = useRef(null)

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
    const { pages, defaultPage } = PROFILE_CONFIG[profile]
    if (!pages.includes(page)) setPage(defaultPage)
  }, [page, profile])

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
            clearMapDataCache()
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
  const openConcept = row => {
    if (!PROFILE_CONFIG[profile].pages.includes('concept')) return
    setConceptSeed(row)
    setPage('concept')
  }

  const handleProfileChange = async nextProfile => {
    if (nextProfile === profile) return
    try {
      await updateProfile(nextProfile)
      setPage(PROFILE_CONFIG[nextProfile].defaultPage)
    } catch {
      setRefreshStatus('error')
    }
  }

  return (
    <div className="layout">
      <Sidebar
        page={page}
        setPage={setPage}
        scores={scores}
        isEmpty={isEmpty}
        loading={loading}
        error={error}
        refreshStatus={refreshStatus}
        onRefresh={handleRefresh}
        onDismissRefresh={() => setRefreshStatus(null)}
        user={user}
        profile={profile}
        onProfileChange={handleProfileChange}
      />

      <main className="main">
        {loading && (
          <div className="loading">
            <div className="loading-spinner" />
            Verificando banco de dados…
          </div>
        )}
        {error && <div className="error-msg">Erro: {error}</div>}

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
                onOpenConcept={PROFILE_CONFIG[profile].pages.includes('concept') ? openConcept : undefined}
                profile={profile}
              />
            )}
            {page === 'opportunities' && <OpportunitiesPage scores={scores} onOpenConcept={PROFILE_CONFIG[profile].pages.includes('concept') ? openConcept : undefined} />}
            {page === 'leads'         && <LeadsPage />}
            {page === 'commerce'      && <CommercePage scores={scores} />}
            {page === 'valuation'     && <ValuationPage />}
            {page === 'concept'       && <ConceptPage seed={conceptSeed} />}
            {page === 'case-study'    && <CaseStudyPage scores={scores} />}
          </Suspense>
        )}
      </main>
    </div>
  )
}
