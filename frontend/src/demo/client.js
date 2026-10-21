import { gridDisk, latLngToCell, cellToLatLng } from 'h3-js'
import examples from './examples.json'

export const DEMO_MODE = import.meta.env.VITE_PUBLIC_DEMO === 'true'
export const DEMO_NOTICE = 'Demonstração pública · dados fictícios · alterações salvas apenas neste navegador.'
const KEY = 'urbia:public-demo:v1'
export const demoUser = () => ({ id: 1, name: 'Visitante', email: 'visitante@example.invalid', role: localStorage.getItem('urbia:demo-profile') || 'investidor', is_admin: false })
const now = () => new Date().toISOString()
const copy = data => JSON.parse(JSON.stringify(data))
let state
function store() {
  if (state) return state
  try { state = JSON.parse(localStorage.getItem(KEY)) } catch { /* empty demo */ }
  if (!state || state.version !== 1) state = { version: 1, cases: [], projects: [], leads: [{ id: 1, name: 'Contato ilustrativo', email: 'exemplo@example.invalid', phone: '', budget: 400000, score: 50, label: 'Exemplo demonstrativo', timeline: 'pesquisando', property_type: 'casa', explain: [{ label: 'Origem', value: 'Contato fictício' }], status: 'novo', notes: 'Contato fictício para apresentação', created_at: now() }], organizations: [{ id: 1, name: 'Equipe demonstrativa', role: 'owner' }], members: [{ user_id: 1, name: 'Visitante', email: 'visitante@example.invalid', role: 'owner' }] }
  return state
}
const save = () => localStorage.setItem(KEY, JSON.stringify(store()))
const nextId = rows => Math.max(0, ...rows.map(row => row.id)) + 1
const scores = gridDisk(latLngToCell(-22.2303, -45.9489, 8), 2).map((id, i) => {
  const [latitude, longitude] = cellToLatLng(id)
  return { h3_id: id, latitude, longitude, zona: 'Zona ilustrativa', neighborhood: `Região demonstrativa ${i + 1}`, score_residencial: 48 + (i * 7) % 43, score_comercial: 42 + (i * 11) % 48, priority: i % 3 === 0 ? 'alta' : 'media', risk_level: i % 3 === 0 ? 'baixo' : 'medio', confidence: .6, main_use: i % 2 ? 'residencial' : 'comercial', opportunity_type: 'investigar', pop_estimated: 700 + i * 80, dist_min_school_m: 600 + i * 120, poi_school_cnt: i % 2, dist_min_pharmacy_m: 500 + i * 90, poi_pharmacy_cnt: i % 3, growth_signal: .003, ndvi_mean_180: .45, ndbi_mean_180: .2, explainability: [{ label: 'Origem', value: 'Dados fictícios de apresentação' }], reasons: ['Exemplo sintético; não constitui recomendação de investimento.'], restrictions: ['Parâmetros legais não verificados'], score_updated_at: now() }
})

async function calculate(action, value, extras = {}) {
  const response = await fetch('/api/demo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action, value, ...extras }) })
  const result = await response.json()
  if (!response.ok) throw new Error(result.detail || 'Não foi possível calcular a demonstração')
  return result
}

const legal = { status: 'analisar', zone: 'Exemplo demonstrativo', notes: 'Não houve consulta ao zoneamento nem a restrições reais do lote.', parameters: {}, articles: [], sources: [], spatial_overlays_verified: false, disclaimer: 'Demonstração fictícia. Não utilizar para decisões legais ou de investimento.' }
const diagnosis = (service = 'schools', distance = 2000) => ({ service, service_label: 'Equipamentos públicos — exemplo', target_distance_m: Number(distance), captured_at: now(), methodology: 'Demonstração sintética', formula: 'Exemplo de priorização para apresentação', limitations: ['Dados fictícios, capacidade e cobertura pública não verificadas.'], sources: [], summary: { ranked: scores.length, high_priority: 7, pending: 0 }, report_markdown: '# Demonstração\n\nDados fictícios. Não utilizar para decisões.', rows: scores.map((r, i) => ({ h3_id: r.h3_id, neighborhood: r.neighborhood, population: r.pop_estimated, population_basis: 'simulation', count: i % 2, distance_m: 800 + i * 130, priority: i % 3 ? 'media' : 'alta', investigation_score: 50 + i, reason: 'Exemplo fictício de agenda de investigação.' })) })

async function route(path, method, body) {
  const url = new URL(path, location.origin), route = url.pathname.replace(/^\/api/, ''), parts = route.split('/').filter(Boolean)
  const db = store()
  if (route === '/auth/me') return demoUser()
  if (route === '/auth/me/profile') { localStorage.setItem('urbia:demo-profile', body.profile); return demoUser() }
  if (route === '/scores') return scores
  if (route === '/municipalities') return [{ ibge: '3152501', name: 'Pouso Alegre', state: 'MG', coverage_status: 'demonstration' }]
  if (route === '/indices/timeseries') return { dates: [], records: [] }
  if (route.startsWith('/analytics/') && route.endsWith('geojson')) return { type: 'FeatureCollection', features: [] }
  if (route === '/analytics/typology') return []
  if (route === '/analytics/commerce-gaps') return [{ type: 'pharmacy', label: 'Farmácia — exemplo', cells_affected: scores.length, description: 'Dados fictícios para demonstrar a investigação de pontos comerciais.', top_locations: scores.slice(0, 5).map(r => ({ ...r, dist_m: r.dist_min_pharmacy_m, typology: 'Área ilustrativa' })) }]
  if (route === '/government/diagnosis') return diagnosis(url.searchParams.get('service'), url.searchParams.get('target_distance_m'))
  if (route === '/legal/assess') return legal
  if (route === '/mlops/runs') return []
  if (route === '/pipeline/status') return { running: false, done: true, success: true, steps: [], message: 'Dados demonstrativos; sem coleta real.' }
  if (route.startsWith('/pipeline/')) throw new Error('Esta apresentação usa dados fictícios; a coleta real está desativada.')
  if (route === '/predict') {
    const price = Number(body.area_m2 || 100) * 4000
    return { predicted_price: price, price_per_m2: 4000, price_low: price * .8, price_high: price * 1.2, data_quality: 'demo', model_status: 'public_demo', warning: 'Simulação: R$ 4.000/m² fictícios, sem modelo de mercado real.', explain: ['Fórmula demonstrativa: área informada × R$ 4.000/m².'] }
  }
  if (route === '/market/compare') return { status: 'sem_dados', recommendation: 'Demonstração sem anúncios reais de mercado.' }
  if (route === '/concept/analyze') return calculate('concept', body)
  if (route === '/concept/generate-image') {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="600" viewBox="0 0 960 600"><rect width="960" height="600" fill="#edf1e8"/><circle cx="780" cy="115" r="45" fill="#e1bf75"/><path d="M0 450L960 420V600H0" fill="#b5c49e"/><path d="M180 430V230L480 120L780 230V430Z" fill="#f3e9d7" stroke="#566751" stroke-width="5"/><path d="M180 230L480 120L780 230" fill="none" stroke="#566751" stroke-width="18"/><path d="M250 430V290H390V430M480 280H690V370H480Z" fill="#adc4c6" stroke="#566751" stroke-width="5"/><path d="M585 280V370" stroke="#566751" stroke-width="5"/><rect x="0" y="510" width="960" height="90" fill="#273c32"/><text x="40" y="547" fill="white" font-family="sans-serif" font-size="24">Conceito ilustrativo — demonstração pública</text><text x="40" y="578" fill="white" font-family="sans-serif" font-size="17">Esquema fictício. Não é imagem de IA, projeto executivo ou imóvel real.</text></svg>'
    return { status: 'demo', image: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg), message: 'Esquema ilustrativo local. Geração por IA requer integração; nenhum crédito foi utilizado.', provider: 'Esquema demonstrativo', prompt: 'Ilustração fictícia para apresentar a área de conceitos.' }
  }
  if (route === '/concept/report') {
    const data = await calculate('concept_report', body)
    return new Response(Uint8Array.from(atob(data.pdf), char => char.charCodeAt(0)), { headers: { 'Content-Type': 'application/pdf' } })
  }
  if (parts[0] === 'case-demos') {
    const example = examples[parts[1]]
    if (!example) throw new Error('Exemplo não encontrado')
    const record = { ...copy(example), id: nextId(db.cases), kind: parts[1], city_ibge: '3152501', municipality_name: 'Pouso Alegre', demonstration: true, revision: 1, tasks: [], stale: false, can_edit: true, updated_at: now(), created_at: now(), project_id: null, organization_id: null }
    record.result = await calculate('case', record)
    db.cases.push(record); save(); return record
  }
  if (parts[0] === 'cases') {
    if (parts.length === 1) {
      if (method === 'GET') return db.cases.filter(item => String(item.demonstration) === url.searchParams.get('demonstration'))
      const item = { ...body, id: nextId(db.cases), demonstration: true, revision: 1, tasks: [], result: null, stale: true, can_edit: true, updated_at: now(), created_at: now() }
      db.cases.push(item); save(); return item
    }
    const item = db.cases.find(row => row.id === Number(parts[1]))
    if (!item) throw new Error('Análise demonstrativa não encontrada neste navegador')
    if (parts[2] === 'report') return new Response(await calculate('report', item, { format: url.searchParams.get('format') }), { headers: { 'Content-Type': url.searchParams.get('format') === 'html' ? 'text/html;charset=utf-8' : 'text/markdown;charset=utf-8' } })
    if (parts[2] === 'history') return [{ revision: item.revision, action: 'analyzed', actor_name: 'Visitante (demonstração)', occurred_at: item.updated_at }]
    if (parts[2] === 'interactions') return { ok: true }
    if (parts[2] === 'analyze' || parts[2] === 'reset-demo') {
      if (parts[2] === 'reset-demo') { item.inputs = copy(examples[item.kind].inputs); item.tasks = [] }
      item.result = await calculate('case', item); item.stale = false
    } else if (parts[2] === 'tasks') {
      const task = { ...body, id: parts[3] ? Number(parts[3]) : nextId(item.tasks) }
      item.tasks = [...item.tasks.filter(t => t.id !== task.id), task]
    } else if (method === 'PATCH') { Object.assign(item, body, { demonstration: true }); item.stale = true; item.result = null }
    if (method !== 'GET') { item.revision++; item.updated_at = now(); save() }
    return item
  }
  if (parts[0] === 'projects') {
    if (parts.length === 1) {
      if (method === 'GET') return db.projects
      const item = { ...body, id: nextId(db.projects), revision: 1, analysis: null, can_edit: true, updated_at: now() }
      db.projects.push(item); save(); return item
    }
    const item = db.projects.find(row => row.id === Number(parts[1]))
    if (!item) throw new Error('Projeto demonstrativo não encontrado')
    if (parts[2] === 'history') return { items: [{ revision: item.revision, action: 'updated', occurred_at: item.updated_at, actor_name: 'Visitante', changed_fields: [], snapshot_available: true }], next_before_revision: null }
    if (parts[2] === 'versions') return { ...item, inputs: item, saved_at: item.updated_at, current_revision: item.revision, differences: [] }
    if (parts[2] === 'report') return new Response('# Projeto demonstrativo\n\n' + item.name + '\n\nDados fictícios.\n\n' + JSON.stringify(item.analysis, null, 2), { headers: { 'Content-Type': 'text/markdown;charset=utf-8' } })
    if (parts[2]?.startsWith('analyze')) item.analysis = await calculate('project', item)
    else if (method === 'PATCH' || parts[2] === 'share') Object.assign(item, body)
    if (method !== 'GET') { item.revision++; item.updated_at = now(); save() }
    return item
  }
  if (parts[0] === 'organizations') {
    if (parts[2] === 'members') {
      if (method === 'GET') return db.members
      if (method === 'DELETE') db.members = db.members.filter(row => row.user_id !== Number(parts[3]))
      else if (method === 'PATCH') Object.assign(db.members.find(row => row.user_id === Number(parts[3])) || {}, body)
      else db.members.push({ ...body, name: 'Participante fictício', user_id: db.members.length + 1 })
      save(); return {}
    }
    if (method === 'GET') return db.organizations
    const item = { ...body, id: nextId(db.organizations), role: 'owner' }; db.organizations.push(item); save(); return item
  }
  if (parts[0] === 'leads') {
    if (method === 'GET') return db.leads
    if (parts[1]) { const item = db.leads.find(row => row.id === Number(parts[1])); Object.assign(item, body); save(); return item }
    const item = { ...body, id: nextId(db.leads), score: 50, label: 'Exemplo demonstrativo', explain: [{ label: 'Origem', value: 'Pontuação fictícia de apresentação' }], timeline: body.timeline || 'pesquisando', status: 'novo', created_at: now() }; db.leads.push(item); save(); return item
  }
  throw new Error('Recurso indisponível na apresentação pública: ' + route)
}

export async function demoFetch(path, options = {}) {
  try {
    const result = await route(path, options.method || 'GET', options.body ? JSON.parse(options.body) : {})
    return result instanceof Response ? result : new Response(JSON.stringify(copy(result)), { headers: { 'Content-Type': 'application/json' } })
  } catch (error) { return new Response(JSON.stringify({ detail: error.message }), { status: 422, headers: { 'Content-Type': 'application/json' } }) }
}
