import { useState, useEffect, useCallback, useRef, Suspense, lazy, useContext } from 'react'
import SetupScreen from './components/SetupScreen'
import { clearMapDataCache, fetchNeighborhoodsGeojson, fetchScores, fetchTimeseries, getPipelineStatus, refreshPipeline } from './api'
import { withNeighborhoods } from './utils/neighborhoods'
import { AuthContext } from './contexts/AuthContext'

const MapPage           = lazy(() => import('./pages/MapPage'))
const OpportunitiesPage = lazy(() => import('./pages/OpportunitiesPage'))
const ScoreExplainPage  = lazy(() => import('./pages/ScoreExplainPage'))
const CompareAreasPage  = lazy(() => import('./pages/CompareAreasPage'))
const ReportsPage       = lazy(() => import('./pages/ReportsPage'))
const LegalAuditPage    = lazy(() => import('./pages/LegalAuditPage'))
const CommercePage = lazy(() => import('./pages/CommercePage'))
const ValuationPage = lazy(() => import('./pages/ValuationPage'))
const LeadsPage = lazy(() => import('./pages/LeadsPage'))
const ConceptStudioPage = lazy(() => import('./pages/ConceptStudioPage'))
const CaseStudyPage = lazy(() => import('./pages/CaseStudyPage'))
const INDEPENDENT_PAGES = ['leads', 'valuation', 'concept']

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

function IconScore() {
  return <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 15V9M9 15V3M15 15V6"/><path d="M1.5 15.5h15"/></svg>
}

function IconCompare() {
  return <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3h12M3 9h12M3 15h12"/><circle cx="6" cy="3" r="1"/><circle cx="12" cy="9" r="1"/><circle cx="8" cy="15" r="1"/></svg>
}

function IconReports() {
  return <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 2h7l3 3v11H4z"/><path d="M11 2v3h3M6.5 9h5M6.5 12h5"/></svg>
}

function IconLegal() {
  return <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M9 2v13M4 5h10M5.5 5 3 11h5L5.5 5ZM12.5 5 10 11h5l-2.5-6ZM5 15h8"/></svg>
}

// ── Nav groups ──────────────────────────────────────────
const NAV_GROUPS = [
  {
    label: 'Jornada de análise',
    items: [
      { id: 'opportunities', label: '1. Oportunidades', Icon: IconOpp },
      { id: 'map', label: '2. Confirmar no mapa', Icon: IconMap },
      { id: 'legal', label: '3. Validar uso', Icon: IconLegal },
      { id: 'score', label: '4. Entender score', Icon: IconScore },
      { id: 'compare', label: '5. Comparar áreas', Icon: IconCompare },
      { id: 'reports', label: '6. Gerar relatório', Icon: IconReports },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { id: 'leads', label: 'CRM de leads', Icon: IconLead },
      { id: 'valuation', label: 'Avaliação de imóveis', Icon: IconValuation },
      { id: 'concept', label: 'Estúdio de conceitos', Icon: IconConcept },
      { id: 'commerce', label: 'Oportunidades comerciais', Icon: IconCommerce },
      { id: 'case-study', label: 'Estudo de caso', Icon: IconCaseStudy },
    ],
  },
]

const PROFILE_CONFIG = {
  investidor: {
    label: 'Investidor',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'valuation', 'case-study'],
  },
  corretor: {
    label: 'Corretor',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'leads', 'valuation', 'concept'],
  },
  incorporadora: {
    label: 'Incorporadora',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'concept', 'case-study'],
  },
  governo: {
    label: 'Poder Público',
    defaultPage: 'opportunities',
    pages: ['opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'commerce', 'case-study'],
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

function Sidebar({ page, setPage, scores, isEmpty, loading, error, refreshStatus, onRefresh, onDismissRefresh, user, profile, onProfileChange, isOpen, onClose }) {
  const userData = user || {}
  const navigation = getNavigation(profile)

  const initials = (userData.name || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }

  return (
    <aside className={`sidebar${isOpen ? ' mobile-open' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo-badge">Ur</div>
          <div className="sidebar-brand-name">Urbia</div>
          <button className="sidebar-close" onClick={onClose} aria-label="Fechar menu">×</button>
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
                onClick={() => { setPage(item.id); onClose?.() }}
                disabled={isEmpty && !INDEPENDENT_PAGES.includes(item.id)}
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

        {!loading && !error && scores.length > 0 && (
          <>
            <div className="sidebar-stats">
              {scores.length} áreas · {scores.filter(r => r.priority === 'alta').length} alta prioridade
            </div>
            {userData.is_admin && <button
              className="sidebar-refresh-btn"
              onClick={onRefresh}
              disabled={refreshStatus === 'running'}
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M10.5 2.5A5 5 0 1 0 11 6"/>
                <path d="M11 2.5V5H8.5"/>
              </svg>
              Atualizar dados
            </button>}
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
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const refreshRef = useRef(null)

  const [timeDates, setTimeDates]       = useState([])
  const [timeRecords, setTimeRecords]   = useState([])
  const [timeLoaded, setTimeLoaded]     = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)

  const loadScores = useCallback(() => {
    setLoading(true)
    Promise.all([fetchScores(), fetchNeighborhoodsGeojson().catch(() => null)])
      .then(([rows, neighborhoods]) => setScores(withNeighborhoods(rows, neighborhoods)))
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
      await refreshPipeline()
    } catch {
      setRefreshStatus('error')
      return
    }
    clearInterval(refreshRef.current)
    refreshRef.current = setInterval(async () => {
      try {
        const s = await getPipelineStatus()
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

  const requiresTerritorialData = !INDEPENDENT_PAGES.includes(page)
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
      <button
        className="mobile-menu-trigger"
        onClick={() => setSidebarOpen(true)}
        aria-label="Abrir menu"
        aria-expanded={sidebarOpen}
      >
        <span /><span /><span />
      </button>
      {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Fechar menu" />}
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
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main">
        {loading && (
          <div className="loading">
            <div className="loading-spinner" />
            Verificando banco de dados…
          </div>
        )}
        {error && <div className="error-msg">Erro: {error}</div>}

        {isEmpty && requiresTerritorialData && (
          <SetupScreen
            isAdmin={!!user?.is_admin}
            onComplete={handleSetupComplete}
            onRefreshDone={handleRefreshDone}
          />
        )}

        {!loading && !error && (scores.length > 0 || !requiresTerritorialData) && (
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
            {page === 'score'         && <ScoreExplainPage scores={scores} />}
            {page === 'compare'       && <CompareAreasPage scores={scores} />}
            {page === 'reports'       && <ReportsPage scores={scores} />}
            {page === 'legal'         && <LegalAuditPage scores={scores} />}
            {page === 'leads' && <LeadsPage />}
            {page === 'valuation' && <ValuationPage />}
            {page === 'concept' && <ConceptStudioPage seed={conceptSeed} />}
            {page === 'commerce' && <CommercePage />}
            {page === 'case-study' && <CaseStudyPage scores={scores} />}
          </Suspense>
        )}
      </main>
    </div>
  )
}
