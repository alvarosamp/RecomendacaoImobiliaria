import { DEMO_MODE, DEMO_NOTICE } from './demo/client'
import { useState, useEffect, useCallback, useRef, Suspense, lazy, useContext } from 'react'
import SetupScreen from './components/SetupScreen'
import { ProductIcon } from './components/ProductVisuals'
import WorkspacePage, { JourneyNavigation } from './pages/WorkspacePage'
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
const ProjectComparePage = lazy(() => import('./pages/ProjectComparePage'))
const TeamsPage = lazy(() => import('./pages/TeamsPage'))
const PublicDiagnosisPage = lazy(() => import('./pages/PublicDiagnosisPage'))
const LandStudyPage = lazy(() => import('./pages/LandStudyPage'))
const DecisionCasePage = lazy(() => import('./pages/DecisionCasePage'))
const CaseStudyPage = lazy(() => import('./pages/CaseStudyPage'))
const HelpDialog = lazy(() => import('./components/HelpDialog'))
const INDEPENDENT_PAGES = ['home', 'cases', 'teams', 'project-compare', 'government', 'study', 'leads', 'valuation', 'concept']

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
  { label: 'Ambiente de trabalho', items: [{ id: 'home', label: 'Início', Icon: IconOpp }, { id: 'cases', label: 'Minhas análises', Icon: IconReports }, { id: 'teams', label: 'Equipes e acesso', Icon: IconLead }] },
  {
    label: 'Análise territorial',
    items: [
      { id: 'opportunities', label: 'Oportunidades', Icon: IconOpp },
      { id: 'map', label: 'Confirmar no mapa', Icon: IconMap },
      { id: 'legal', label: 'Validar uso', Icon: IconLegal },
      { id: 'score', label: 'Entender score', Icon: IconScore },
      { id: 'compare', label: 'Comparar áreas', Icon: IconCompare },
      { id: 'reports', label: 'Gerar relatório', Icon: IconReports },
    ],
  },
  {
    label: 'Ferramentas',
    items: [
      { id: 'leads', label: 'CRM de leads', Icon: IconLead },
      { id: 'valuation', label: 'Avaliação de imóveis', Icon: IconValuation },
      { id: 'government', label: 'Equipamentos públicos', Icon: IconMap },
      { id: 'project-compare', label: 'Comparar estudos', Icon: IconCompare },
      { id: 'study', label: 'Projetos de terrenos', Icon: IconConcept },
      { id: 'concept', label: 'Estúdio de conceitos', Icon: IconConcept },
      { id: 'commerce', label: 'Oportunidades comerciais', Icon: IconCommerce },
      { id: 'case-study', label: 'Estudo de caso', Icon: IconCaseStudy },
    ],
  },
]

const PROFILE_CONFIG = {
  investidor: {
    label: 'Investidor',
    defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'valuation', 'case-study'],
  },
  corretor: {
    label: 'Corretor',
    defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'leads', 'valuation', 'concept'],
  },
  incorporadora: {
    label: 'Incorporadora',
    defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'concept', 'case-study'],
  },
  construtora: {
    label: 'Construtora', defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'map', 'legal', 'concept', 'compare', 'reports', 'score'],
  },
  empreendedor: {
    label: 'Empreendedor', defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'commerce', 'map', 'legal', 'compare', 'reports', 'score'],
  },
  governo: {
    label: 'Poder Público',
    defaultPage: 'home',
    pages: ['home', 'teams', 'study', 'project-compare', 'opportunities', 'map', 'legal', 'score', 'compare', 'reports', 'government', 'commerce', 'case-study'],
  },
}

function getProfile(role) {
  return PROFILE_CONFIG[role] ? role : 'investidor'
}

Object.values(PROFILE_CONFIG).forEach(config => { if (!config.pages.includes('cases')) config.pages.push('cases') })

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

function Sidebar({ page, setPage, scores, isEmpty, loading, error, refreshStatus, onRefresh, onDismissRefresh, user, profile, onProfileChange, profileBusy, onLogout, isOpen, onClose, onHelp }) {
  const userData = user || {}
  const navigation = getNavigation(profile)

  const initials = (userData.name || '?').split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase()



  return (
    <aside className={`sidebar${isOpen ? ' mobile-open' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-logo-row">
          <div className="sidebar-logo-badge"><ProductIcon name="building" size={23}/></div>
          <div className="sidebar-brand-name">urbia<span>.</span></div>
          <button className="sidebar-close" onClick={onClose} aria-label="Fechar menu">×</button>
        </div>
        <div className="sidebar-brand-sub">
          <span className="sidebar-city-dot" />
          Inteligência territorial
        </div>
      </div>

      <div className="sidebar-mode-panel">
        <label className="sidebar-mode">Modo de trabalho<select value={profile} disabled={profileBusy} onChange={event => onProfileChange(event.target.value)}>{Object.entries(PROFILE_CONFIG).map(([id, config]) => <option key={id} value={id}>{config.label}</option>)}</select></label>
      </div>

      {/* Keep everyday work visible; specialist tools remain available on demand. */}
      {navigation.slice(0,1).map(group=><nav key={group.label} className="sidebar-nav sidebar-primary-nav">{group.items.map(item=><button key={item.id} className={`nav-item${page===item.id?' active':''}`} onClick={()=>{if(setPage(item.id)!==false)onClose?.()}} disabled={profileBusy}><item.Icon/>{item.label}</button>)}</nav>)}
      <div className="sidebar-nav sidebar-help-nav"><button className="nav-item" aria-haspopup="dialog" onClick={onHelp}><ProductIcon name="help" size={18} className="nav-icon"/>Como usar</button></div>
      <details className="sidebar-extra-tools" open={!['home','cases','teams'].includes(page)}><summary>Mais ferramentas <span aria-hidden="true">+</span></summary>{navigation.slice(1).map(group=><div key={group.label} className="sidebar-group"><span className="sidebar-group-label">{group.label}</span><nav className="sidebar-nav">{group.items.map(item=><button key={item.id} className={`nav-item${page===item.id?' active':''}`} onClick={()=>{if(setPage(item.id)!==false)onClose?.()}} disabled={profileBusy}><item.Icon/>{item.label}</button>)}</nav></div>)}</details>

      {/* Footer */}
      <div className="sidebar-footer">
        {/* User row */}
        <div className="sidebar-user-row">
          <div className="sidebar-user-avatar">{initials}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{userData.name || 'Usuário'}</div>
            <div className="sidebar-user-role">{PROFILE_CONFIG[profile].label}</div>
          </div>
          <button className="sidebar-logout-btn" onClick={onLogout} title="Sair">
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
  const { user, updateProfile, logout } = useContext(AuthContext)
  const profile = getProfile(user?.role)
  const [page, setPage]     = useState(PROFILE_CONFIG[profile].defaultPage)
  const [helpOpen,setHelpOpen] = useState(false)
  const [casesEntry,setCasesEntry] = useState('library')
  const [casesNavigation,setCasesNavigation] = useState(0)
  const [scores, setScores] = useState([])
  const [conceptSeed, setConceptSeed] = useState(null)
  const [journey, setJourney] = useState(null)
  useEffect(() => { setJourney(null) }, [profile])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [refreshStatus, setRefreshStatus] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const refreshRef = useRef(null)
  const studyStateRef = useRef({dirty:false,busy:false})
  const onStudyStateChange = useCallback(state => { studyStateRef.current = state }, [])
  const [profileBusy,setProfileBusy] = useState(false)
  const [profileError,setProfileError] = useState('')
  const canLeaveStudy = () => {
    if (page !== 'study' && page !== 'cases') return true
    if (studyStateRef.current.busy) return false
    return !studyStateRef.current.dirty || window.confirm('Existem alterações não salvas no estudo. Deseja sair e descartá-las?')
  }
  const navigatePage = next => {
    if(profileBusy)return false
    if(next===page&&next!=='cases')return true
    if(!canLeaveStudy())return false
    if(next==='cases'){setCasesEntry('library');setCasesNavigation(current=>current+1)}
    setJourney(null);setPage(next);return true
  }
  const openFromHelp = mode => {
    if(profileBusy||!canLeaveStudy())return
    setCasesEntry(mode);setCasesNavigation(current=>current+1);setJourney(null);setPage('cases');setSidebarOpen(false);setHelpOpen(false)
  }
  const handleLogout = () => { if (canLeaveStudy()) logout() }

  const [timeDates, setTimeDates]       = useState([])
  const [timeRecords, setTimeRecords]   = useState([])
  const [timeLoaded, setTimeLoaded]     = useState(false)
  const [selectedDate, setSelectedDate] = useState(null)

  const loadScores = useCallback(() => {
    setLoading(true)
    setError(null)
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
    if ((page === 'map' || page === 'study' || page === 'government') && !timeLoaded) {
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
    if (profileBusy || nextProfile === profile || !canLeaveStudy()) return
    setProfileBusy(true);setProfileError('')
    try {
      await updateProfile(nextProfile)
      setCasesEntry('library')
      setPage(PROFILE_CONFIG[nextProfile].defaultPage)
    } catch {
      setProfileError('Não foi possível alterar o modo de trabalho. Tente novamente.')
    } finally { setProfileBusy(false) }
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
        setPage={navigatePage}
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
        profileBusy={profileBusy}
        onLogout={handleLogout}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onHelp={()=>setHelpOpen(true)}
      />

      {helpOpen&&<Suspense fallback={null}><HelpDialog profile={profile} onClose={()=>setHelpOpen(false)} onNavigate={openFromHelp}/></Suspense>}
      <main className="main" inert={profileBusy ? '' : undefined}>
        {DEMO_MODE && <div className="demo-notice" role="note"><strong>Modo de apresentação</strong><span>{DEMO_NOTICE} Não insira informações pessoais.</span><a href="/app">Recomeçar navegação</a></div>}
        {page === 'home' && <WorkspacePage disabled={profileBusy} profile={profile} onPrimary={()=>{setJourney(null);setCasesEntry('new');setPage('cases')}} onStart={selected => { if (selected.steps[0][0] === 'government') { setJourney(null); setPage('government') } else if (selected.steps[0][0] === 'study') { setJourney(null); setPage('study') } else { setJourney(selected); setPage(selected.steps[0][0]) } }} />}
        {page !== 'home' && journey && <JourneyNavigation journey={journey} page={page} onNavigate={setPage} onClose={() => { setJourney(null); setPage('home') }} />}
        {loading && page !== 'home' && (
          <div className="loading">
            <div className="loading-spinner" />
            Verificando banco de dados…
          </div>
        )}
        {profileError && <div className="error-msg" role="alert">{profileError}</div>}
        {error && page !== 'home' && page !== 'cases' && <div className="error-msg" role="alert">Não foi possível carregar os dados territoriais: {error} <button onClick={loadScores}>Tentar novamente</button></div>}

        {isEmpty && requiresTerritorialData && (
          <SetupScreen
            onOpenAnalyses={()=>navigatePage('cases')}
            isAdmin={!!user?.is_admin}
            onComplete={handleSetupComplete}
            onRefreshDone={handleRefreshDone}
          />
        )}

        {((!loading && !error && scores.length > 0) || !requiresTerritorialData) && (
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
            {page === 'project-compare' && <ProjectComparePage />}
            {page === 'teams' && <TeamsPage />}
            {page === 'cases' && <DecisionCasePage key={profile+casesEntry+casesNavigation} initialView={casesEntry} profile={profile} scores={scores} onStudyStateChange={onStudyStateChange} onOpenProjects={()=>navigatePage('study')} />}
            {page === 'government' && <PublicDiagnosisPage scores={scores} timeDates={timeDates} timeRecords={timeRecords} selectedDate={selectedDate} onDateChange={setSelectedDate} />}
            {page === 'study' && <LandStudyPage workspaceProfile={profile} onStudyStateChange={onStudyStateChange} scores={scores} timeDates={timeDates} timeRecords={timeRecords} selectedDate={selectedDate} onDateChange={setSelectedDate} />}
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
