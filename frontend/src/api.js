const BASE = '/api'

function getHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: getHeaders() })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = { get, post };

export const fetchScores       = ()   => get('/scores')
export const predictPrice      = body => post('/predict', body)
export const fetchRuns         = ()   => get('/mlops/runs')
export const fetchTimeseries   = ()   => get('/indices/timeseries')
export const fetchCommerceGaps = ()   => get('/analytics/commerce-gaps')
export const fetchTypology     = ()   => get('/analytics/typology')
const CACHE_TTL_MS = 24 * 60 * 60 * 1000 // 24h — zoneamento/POIs mudam raramente

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
export const runPipeline       = ()   => post('/pipeline/run', {})
export const refreshPipeline   = ()   => post('/pipeline/refresh', {})
export const getPipelineStatus = ()   => get('/pipeline/status')
export const analyzeConcept    = body => post('/concept/analyze', body)
export const generateConceptImage = body => post('/concept/generate-image', body)
export const downloadConceptReport = async body => {
  const res = await fetch(`${BASE}/concept/report`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.blob()
}
