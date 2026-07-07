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
export const runPipeline       = ()   => post('/pipeline/run', {})
export const refreshPipeline   = ()   => post('/pipeline/refresh', {})
export const getPipelineStatus = ()   => get('/pipeline/status')
