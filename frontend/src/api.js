const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Erro ${res.status}: ${res.statusText}`)
  return res.json()
}

export const fetchScores      = ()   => get('/scores')
export const predictPrice     = body => post('/predict', body)
export const fetchRuns        = ()   => get('/mlops/runs')
export const fetchTimeseries  = ()   => get('/indices/timeseries')
export const fetchCommerceGaps = ()  => get('/analytics/commerce-gaps')
export const fetchTypology    = ()   => get('/analytics/typology')
