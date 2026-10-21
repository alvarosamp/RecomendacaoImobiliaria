const BASE = '/api'

function getHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

// Token ausente/expirado em rota protegida: limpa a sessão e volta ao login.
// Rotas /auth ficam de fora (401 no login significa só senha errada).
function checkSession(res, path) {
  if (res.status === 401 && !path.startsWith('/auth/') && localStorage.getItem('token')) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  }
}

async function responseError(res) {
  const body = await res.json().catch(() => null)
  const detail = body?.detail
  const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(item => item.msg).join('; ') : res.statusText
  return new Error(`Erro ${res.status}: ${message}`)
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: getHeaders() })
  checkSession(res, path)
  if (!res.ok) throw await responseError(res)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })
  checkSession(res, path)
  if (!res.ok) throw await responseError(res)
  if (res.status === 204) return null
  return res.json()
}

async function patch(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })
  checkSession(res, path)
  if (!res.ok) throw await responseError(res)
  return res.json()
}

export const api = { get, post, patch };

export const fetchScores       = ()   => get('/scores')
export const predictPrice      = body => post('/predict', body)
export const compareMarket = ({ neighborhood, askingPrice, areaM2, propertyType }) => get(`/market/compare?${new URLSearchParams({ neighborhood, asking_price: askingPrice, area_m2: areaM2, property_type: propertyType, city: 'Pouso Alegre', transaction: 'venda' })}`)
export const fetchRuns         = ()   => get('/mlops/runs')
export const fetchTimeseries   = ()   => get('/indices/timeseries')
export const fetchCommerceGaps = ()   => get('/analytics/commerce-gaps')
export const fetchTypology     = ()   => get('/analytics/typology')
const CACHE_TTL_MS = 24 * 60 * 60 * 1000 // 24h — zoneamento/POIs mudam raramente
const GEOJSON_CACHE_KEYS = ['cache:zoning-geojson', 'cache:pois-geojson', 'cache:official-susceptibility-geojson', 'cache:neighborhoods-geojson']

export function clearMapDataCache() {
  GEOJSON_CACHE_KEYS.forEach(key => {
    try { localStorage.removeItem(key) } catch { /* localStorage indisponivel */ }
  })
}

async function getCached(path, cacheKey) {
  try {
    const raw = localStorage.getItem(cacheKey)
    if (raw) {
      const { data, ts } = JSON.parse(raw)
      if (Date.now() - ts < CACHE_TTL_MS) return data
    }
  } catch { /* cache corrompido, ignora e busca de novo */ }

  const data = await get(path)
  try {
    localStorage.setItem(cacheKey, JSON.stringify({ data, ts: Date.now() }))
  } catch { /* localStorage cheio/indisponível, segue sem cache */ }
  return data
}

export const fetchZoningGeojson = ()  => getCached('/analytics/zoning-geojson', 'cache:zoning-geojson')
export const fetchPoisGeojson   = ()  => getCached('/analytics/pois-geojson', 'cache:pois-geojson')
export const fetchOfficialSusceptibilityGeojson = () => getCached('/analytics/official-susceptibility-geojson', 'cache:official-susceptibility-geojson')
export const fetchNeighborhoodsGeojson = () => getCached('/analytics/neighborhoods-geojson', 'cache:neighborhoods-geojson')
export const runPipeline       = ()   => post('/pipeline/run', {})
export const refreshPipeline   = ()   => post('/pipeline/refresh', {})
export const getPipelineStatus = ()   => get('/pipeline/status')
export const resetPipeline     = ()   => post('/pipeline/reset', {})
export const analyzeConcept    = body => post('/concept/analyze', body)
export const generateConceptImage = body => post('/concept/generate-image', body)
export const downloadConceptReport = async body => {
  const res = await fetch(`${BASE}/concept/report`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await responseError(res)
  return res.blob()
}

export const fetchLeads = (params = {}) => {
  const query = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString()
  return get(`/leads${query ? `?${query}` : ''}`)
}
export const createLead       = body            => post('/leads', body)
export const updateLeadStatus = (id, status)     => patch(`/leads/${id}/status`, { status })
export const assessLegalCompatibility = ({ h3Id, intendedUse }) =>
  get(`/legal/assess?${new URLSearchParams({ h3_id: h3Id, intended_use: intendedUse })}`)

export const fetchProjects = () => get('/projects')
export const createProject = body => post('/projects', body)
export const saveProject = (id, body) => patch(`/projects/${id}`, body)
export const analyzeProject = (id, revision) => post(`/projects/${id}/analyze`, { revision })
export const downloadProjectReport = async id => {
  const res = await fetch(`${BASE}/projects/${id}/report`, { headers: getHeaders() })
  checkSession(res, '/projects')
  if (!res.ok) throw new Error(`Erro ${res.status}: não foi possível baixar o relatório`)
  return res.blob()
}
export const fetchPublicDiagnosis = (service, distance) => get(`/government/diagnosis?${new URLSearchParams({ service, target_distance_m: distance })}`)
export const fetchOrganizations = () => get('/organizations')
export const createOrganization = name => post('/organizations', { name })
export const fetchMembers = id => get(`/organizations/${id}/members`)
export const addMember = (id, body) => post(`/organizations/${id}/members`, body)
export const changeMemberRole = (id, userId, role) => patch(`/organizations/${id}/members/${userId}`, { role })
export const removeMember = async (id, userId) => {
  const path = `/organizations/${id}/members/${userId}`
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE', headers: getHeaders() })
  checkSession(res, path)
  if (!res.ok) throw await responseError(res)
}
export const shareProject = (id, organizationId, revision) => post(`/projects/${id}/share`, { organization_id: organizationId, revision })
export const fetchProjectHistory = (id, beforeRevision) => get(`/projects/${id}/history${beforeRevision ? `?before_revision=${beforeRevision}` : ''}`)
export const analyzeProjectPremises = (id, revision) => post(`/projects/${id}/analyze-premises`, { revision })
export const fetchProjectVersion = (id, revision) => get(`/projects/${id}/versions/${revision}`)
export const restoreProjectVersion = (id, version, revision) => post(`/projects/${id}/versions/${version}/restore`, { revision })
