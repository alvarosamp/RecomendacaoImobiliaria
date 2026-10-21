import { lazy, Suspense, useEffect, useState } from 'react'
import { analyzeProject, analyzeProjectPremises, createProject, downloadProjectReport, fetchProjects, saveProject, fetchOrganizations, shareProject, restoreProjectVersion } from '../api'
import { BusinessPremises, BusinessResults } from '../components/BusinessStudy'
import ProjectHistory from '../components/ProjectHistory'
import { TechnicalPremises, TechnicalResults } from '../components/TechnicalStudy'
import { FinancialPremises, FinancialResults } from '../components/FinancialStudy'
const MapPage = lazy(() => import('./MapPage'))
const STEPS = ['Terreno e região', 'Premissas', 'Restrições e cenários', 'Relatório']
const empty = () => ({ name: '', h3_id: null, intended_use: 'residencial', premises: { lotArea: 300, frontage: 10, buildArea: 165, floors: 2, typology: 'casa', finish: 'medio', style: 'contemporaneo' }, notes: '', organization_id: null, financial: null, technical: null, business: null })
const legalLabel = status => ({ allowed: 'Permitido na triagem', conditioned: 'Condicionado', blocked: 'Bloqueado na triagem', analisar: 'Requer análise' }[status] || 'Requer análise')
const money = value => Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

export default function LandStudyPage({ scores, workspaceProfile = 'incorporadora', onStudyStateChange, ...mapProps }) {
  useEffect(() => () => onStudyStateChange?.({dirty:false,busy:false}), [onStudyStateChange])
  const newDraft = () => ({...empty(), technical:workspaceProfile === 'construtora' ? {} : null, business:workspaceProfile === 'empreendedor' ? {} : null, intended_use:workspaceProfile === 'empreendedor' ? 'comercial' : workspaceProfile === 'governo' ? 'institucional' : 'residencial'})
  const [teams, setTeams] = useState([])
  const [shareTeam, setShareTeam] = useState('')
  const [projects, setProjects] = useState([])
  const [project, setProject] = useState(null)
  const [draft, setDraft] = useState(newDraft)
  const [dirty, setDirty] = useState(false)
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [listLoading, setListLoading] = useState(true)
  useEffect(() => { onStudyStateChange?.({dirty,busy}) }, [dirty,busy,onStudyStateChange])
  useEffect(() => {
    if (!dirty) return
    const warn = event => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  const selected = scores.find(row => row.h3_id === draft.h3_id)
  const canEdit = project?.can_edit !== false
  const analysis = dirty ? null : project?.analysis
  useEffect(() => {
    let active = true
    fetchOrganizations().then(rows => { if (active) setTeams(rows) }).catch(err => { if (active) setError(err.message) })
    fetchProjects().then(rows => { if (active) setProjects(rows) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setListLoading(false) })
    return () => { active = false }
  }, [])
  const edit = changes => { setDraft(current => ({ ...current, ...changes })); setDirty(true); setStatus('Alterações ainda não salvas') }
  const accept = saved => {
    setProject(saved); setDraft(saved); setDirty(false)
    setProjects(current => [saved, ...current.filter(item => item.id !== saved.id)])
    setStatus('Projeto salvo')
  }
  const open = saved => {
    if (dirty && !window.confirm('Descartar as alterações não salvas para abrir outro estudo?')) return
    setProject(saved); setDraft(saved || newDraft()); setDirty(false); setStep(0); setError(''); setStatus('')
  }
  const persist = async () => {
    const body = { name: draft.name, h3_id: draft.h3_id, intended_use: draft.intended_use, premises: draft.premises, notes: draft.notes, organization_id: draft.organization_id || null, financial: draft.financial || null, technical: draft.technical || null, business: draft.business || null }
    const saved = project ? await saveProject(project.id, { ...body, revision: project.revision }) : await createProject(body)
    accept(saved)
    return saved
  }
  const run = async task => {
    setBusy(true); setError('')
    try { await task() } catch (err) { setError(err.message); setStatus('A operação não foi concluída. Suas alterações continuam nesta tela.') }
    finally { setBusy(false) }
  }
  const analyze = (premisesOnly = false) => run(async () => {
    const saved = dirty || !project ? await persist() : project
    accept(await (premisesOnly ? analyzeProjectPremises : analyzeProject)(saved.id, saved.revision)); setStep(2); setStatus('Análise calculada e salva')
  })
  const download = () => run(async () => {
    const saved = canEdit && (dirty || !project) ? await persist() : project
    const blob = await downloadProjectReport(saved.id)
    const url = URL.createObjectURL(blob)
    const link = Object.assign(document.createElement('a'), { href: url, download: `urbia-projeto-${saved.id}.md` })
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  })
  const setPremise = (key, value) => edit({ premises: { ...draft.premises, [key]: value } })
  return <section className="page land-study">
    <div className="page-header"><div className="page-eyebrow">{workspaceProfile === 'construtora' ? 'Urbia Obras' : workspaceProfile === 'empreendedor' ? 'Urbia Negócios' : 'Estudos territoriais'}</div><h2>Estudo preliminar de terreno</h2><p>Um projeto reúne a região escolhida, premissas, triagem urbanística e cenários. A região H3 não representa o limite cadastral do lote.</p></div>
    {error && <div className="error-msg" role="alert">{error}</div>}
    <div className="study-toolbar">
      <label>Retomar estudo<select disabled={busy || listLoading} value={project?.id || ''} onChange={event => open(projects.find(item => item.id === Number(event.target.value)) || null)}><option value="">Novo estudo</option>{projects.map(item => <option value={item.id} key={item.id}>{item.name} · revisão {item.revision}</option>)}</select></label>
      <button disabled={busy} onClick={() => open(null)}>Novo projeto</button>
      <button disabled={busy} onClick={() => run(async () => { const rows = await fetchProjects(); setProjects(rows); setStatus('Lista atualizada. Reabra o estudo para carregar a versão salva.') })}>Atualizar lista</button>
      <button disabled={busy || !canEdit || !draft.name.trim()} onClick={() => run(persist)}>{busy ? 'Processando…' : 'Salvar projeto'}</button>
      <span role="status">{listLoading ? 'Carregando projetos…' : status}</span>
    </div>
    <fieldset disabled={busy || !canEdit} className="study-fields"><label>Contexto do projeto<select disabled={!!project} value={draft.organization_id || ''} onChange={event => edit({ organization_id: event.target.value ? Number(event.target.value) : null })}><option value="">Pessoal e privado</option>{teams.filter(team => !project ? team.role !== 'viewer' : team.id === project.organization_id).map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label><label>Nome do projeto<input value={draft.name} maxLength={160} onChange={event => edit({ name: event.target.value })} placeholder="Ex.: Estudo residencial — região central" /></label><label>Região de referência<select value={draft.h3_id || ''} onChange={event => edit({ h3_id: event.target.value || null })}><option value="">Selecione uma região</option>{draft.h3_id && !selected && <option value={draft.h3_id}>{draft.h3_id} · indisponível nos dados atuais</option>}{scores.map(row => <option key={row.h3_id} value={row.h3_id}>{row.neighborhood || row.zona || 'Região'} · {row.h3_id}</option>)}</select></label><label>Uso pretendido<select value={draft.intended_use} onChange={event => edit({ intended_use: event.target.value })}>{['residencial', 'comercial', 'misto', 'industrial', 'institucional'].map(use => <option key={use} value={use}>{use}</option>)}</select></label></fieldset>
    {project && !canEdit && <p role="status">Acesso de leitor: você pode consultar e baixar o relatório, mas não alterar ou recalcular o projeto.</p>}
    {project && !project.organization_id && <div className="study-toolbar"><label>Compartilhar projeto com equipe<select disabled={busy || dirty} value={shareTeam} onChange={event => setShareTeam(event.target.value)}><option value="">Selecione uma equipe</option>{teams.filter(team => team.role !== 'viewer').map(team => <option key={team.id} value={team.id}>{team.name}</option>)}</select></label><button disabled={busy || dirty || !shareTeam} onClick={() => { if (window.confirm('Compartilhar este projeto, incluindo seu histórico e as versões preservadas, com todos os membros da equipe? O acesso passará a seguir as permissões da equipe.')) run(async () => { accept(await shareProject(project.id, Number(shareTeam), project.revision)); setStatus('Projeto compartilhado com a equipe') }) }}>Compartilhar projeto salvo</button></div>}
    <nav className="journey-nav" aria-label="Etapas do estudo"><ol>{STEPS.map((label, index) => <li key={label}><button disabled={busy} aria-current={step === index ? 'step' : undefined} onClick={() => setStep(index)}>{index + 1}. {label}</button></li>)}</ol></nav>
    {step === 0 && <><p>Selecione a região no campo acima ou clique em uma célula no mapa. A seleção acompanha todas as etapas.</p>{scores.length ? <Suspense fallback={<p>Carregando mapa…</p>}><MapPage {...mapProps} scores={scores} profile={workspaceProfile} selectedAreaId={draft.h3_id} onSelectArea={row => { if (!busy && canEdit && row) edit({ h3_id: row.h3_id }) }} /></Suspense> : <p>Sem dados territoriais carregados. Você pode salvar as premissas e selecionar a região mais tarde.</p>}</>}
    {step === 1 && <fieldset disabled={busy || !canEdit} className="study-fields">
      {[['lotArea', 'Área informada do lote (m²)', 40], ['frontage', 'Frente (m)', 3], ['buildArea', 'Área construída prevista (m²)', 20], ['floors', 'Pavimentos', 1]].map(([key, label, min]) => <label key={key}>{label}<input type="number" min={min} max={key === 'floors' ? 30 : undefined} step={key === 'floors' ? 1 : 'any'} value={draft.premises[key] ?? ''} onChange={event => setPremise(key, event.target.value === '' ? null : Number(event.target.value))} /></label>)}
      <label>Tipologia<select value={draft.premises.typology} onChange={event => setPremise('typology', event.target.value)}>{['casa', 'apartamento', 'uso misto', 'comercial'].map(item => <option key={item}>{item}</option>)}</select></label>
      <label>Padrão de acabamento<select value={draft.premises.finish} onChange={event => setPremise('finish', event.target.value)}>{['economico', 'medio', 'alto'].map(item => <option key={item}>{item}</option>)}</select></label>
      <label className="study-notes">Observações e fontes informadas<textarea maxLength={10000} rows={5} value={draft.notes} onChange={event => edit({ notes: event.target.value })} placeholder="Registre documentos, levantamento do lote e premissas que precisam de confirmação." /></label>
    </fieldset>}
    {step === 1 && <BusinessPremises value={draft.business ?? null} disabled={busy || !canEdit} onChange={business => edit({business})} />}
    {step === 1 && <TechnicalPremises value={draft.technical ?? null} disabled={busy || !canEdit} onChange={technical => edit({technical})} />}
    {step === 1 && <FinancialPremises value={draft.financial ?? null} disabled={busy || !canEdit} onChange={financial => edit({ financial })} />}
    {step === 2 && <div className="study-results"><button disabled={busy || !canEdit || !draft.h3_id || !draft.name.trim()} onClick={() => analyze(false)}>Salvar e calcular análise integrada</button><button disabled={busy || !canEdit || !draft.name.trim() || (!draft.financial && !draft.technical && !draft.business)} onClick={() => analyze(true)}>Calcular somente premissas declaradas</button><p>O cálculo usa a região selecionada e as premissas salvas. Resultados serão invalidados se essas informações mudarem.</p>{analysis ? <>
      {analysis.mode === 'premises_only' && <p className="study-caution">Análise somente de premissas: localização, zoneamento e restrições espaciais não foram consultados nesta execução.</p>}
      <h3>Triagem urbanística: {legalLabel(analysis.legal.status)}</h3>{analysis.legal.notes && <p>{analysis.legal.notes}</p>}{analysis.legal.disclaimer && <p>{analysis.legal.disclaimer}</p>}
      <p>Zona: {analysis.legal.zone || 'não identificada'} · Camadas espaciais: {analysis.legal.spatial_overlays_verified ? 'verificadas' : 'pendentes'}</p>
      <ul>{(analysis.legal.articles || []).map(article => <li key={article}>{article}</li>)}{(analysis.legal.sources || []).map((source, index) => <li key={index}>{source.title}{source.url && <> · <a href={source.url} target="_blank" rel="noreferrer">Consultar fonte</a></>}</li>)}</ul>
      {!!analysis.concept.scenarios.length && <><h3>Cenários heurísticos</h3><p>Custos e retornos são estimativas preliminares; não comprovam compatibilidade legal.</p><div className="workspace-grid">{analysis.concept.scenarios.map(item => <article className="workspace-card" key={item.id}><h4>{item.label}</h4><p>Área: {item.buildArea} m²</p><p>Custo estimado: {money(item.cost)}</p><p>Prazo: {item.months} meses · ROI anual estimado: {item.roiYear}%</p><p>Viabilidade heurística: {item.viabilityScore}/100</p></article>)}</div></>}
      <BusinessResults result={analysis.business} />
      <TechnicalResults result={analysis.technical} />
      <FinancialResults result={analysis.financial} />
      <p>Captura: {new Date(analysis.captured_at).toLocaleString('pt-BR')} · a data de captura não equivale à atualização das fontes.</p>
    </> : <p>A análise está pendente. Se você alterou a área ou as premissas, execute novamente o cálculo.</p>}</div>}
    {project && <ProjectHistory project={project} dirty={dirty} operationBusy={busy} onRestore={revision=>run(async()=>{accept(await restoreProjectVersion(project.id,revision,project.revision));setStatus('Premissas recuperadas em nova revisão. Execute a análise novamente.')} )} />}
    {step === 3 && <div className="workspace-card"><h3>Relatório único do projeto</h3><p>Inclui região, premissas, observações, indicadores, triagem legal, fontes, cenários e limitações.</p><p>{analysis ? 'A análise salva será incluída no relatório.' : 'Análise pendente: o relatório identificará a ausência de resultados atuais.'}</p><button disabled={busy || !draft.name.trim()} onClick={download}>{canEdit ? 'Salvar e baixar relatório (.md)' : 'Baixar relatório (.md)'}</button></div>}
  </section>
}
