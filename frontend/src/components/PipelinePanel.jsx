import { useState, useEffect, useRef } from 'react'

const STEP_ORDER = [
  'fetch-boundary',
  'build-grid',
  'fetch-pois',
  'build-features',
  'update-index-features',
  'score-db',
]

const STEP_LABELS = {
  'fetch-boundary':        'Buscar limite do município',
  'build-grid':            'Gerar grade H3',
  'fetch-pois':            'Coletar POIs (OpenStreetMap)',
  'build-features':        'Calcular features de acessibilidade',
  'update-index-features': 'Processar índices Sentinel-2',
  'score-db':              'Calcular e salvar scores',
}

function StepRow({ cmd, step }) {
  const status = step?.status ?? 'pending'
  const label  = step?.label ?? STEP_LABELS[cmd] ?? cmd

  const bg = {
    pending: '#f8fafc', running: '#eff6ff', done: '#f0fdf4', error: '#fef2f2',
  }[status]
  const border = {
    pending: '#e2e8f0', running: '#bfdbfe', done: '#bbf7d0', error: '#fecaca',
  }[status]
  const icon = {
    pending: <span style={{ color: '#cbd5e1' }}>○</span>,
    running: <span className="spin" style={{ color: '#2563eb' }}>◌</span>,
    done:    <span style={{ color: '#16a34a', fontWeight: 700 }}>✓</span>,
    error:   <span style={{ color: '#dc2626', fontWeight: 700 }}>✗</span>,
  }[status]

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12,
      padding: '11px 14px', borderRadius: 8,
      background: bg, border: `1px solid ${border}`,
      transition: 'background 0.3s, border-color 0.3s',
    }}>
      <span style={{ fontSize: 16, lineHeight: 1.3, minWidth: 18, textAlign: 'center' }}>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: 13 }}>{label}</div>
        {step?.output && (
          <pre style={{
            marginTop: 6, fontSize: 11, color: status === 'error' ? '#b91c1c' : '#64748b',
            whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            maxHeight: 100, overflow: 'auto', background: 'transparent', padding: 0,
          }}>
            {step.output}
          </pre>
        )}
      </div>
    </div>
  )
}

export default function PipelinePanel({ onComplete }) {
  const [state, setState] = useState({ running: false, steps: [], done: false, success: null })
  const [starting, setStarting] = useState(false)
  const pollRef = useRef(null)

  const stopPoll = () => { clearInterval(pollRef.current); pollRef.current = null }

  const poll = async () => {
    try {
      const res = await fetch('/api/pipeline/status')
      const data = await res.json()
      setState(data)
      if (data.done) {
        stopPoll()
        if (data.success && onComplete) onComplete()
      }
    } catch {
      stopPoll()
    }
  }

  const start = async () => {
    setStarting(true)
    try {
      const res = await fetch('/api/pipeline/run', { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert(err.detail ?? 'Erro ao iniciar pipeline')
        return
      }
      setState({ running: true, steps: [], done: false, success: null })
      pollRef.current = setInterval(poll, 1500)
    } finally {
      setStarting(false)
    }
  }

  useEffect(() => {
    // Check if a pipeline is already running on mount
    poll()
    return stopPoll
  }, [])

  // Resume polling if a run was already in progress when we mounted
  useEffect(() => {
    if (state.running && !pollRef.current) {
      pollRef.current = setInterval(poll, 1500)
    }
  }, [state.running])

  const stepMap = Object.fromEntries((state.steps ?? []).map(s => [s.cmd, s]))
  const isRunning = state.running || starting

  return (
    <div className="panel" style={{ maxWidth: 820 }}>
      <div className="panel-header">
        <div>
          <h2>Pipeline de Dados</h2>
          <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Recalcula grid H3, POIs, NDVI/NDBI e scores. Atualiza o mapa automaticamente ao concluir.
          </p>
        </div>
        <button
          onClick={start}
          disabled={isRunning}
          style={{
            padding: '10px 24px',
            background: isRunning ? '#94a3b8' : '#2563eb',
            color: '#fff', border: 'none', borderRadius: 8,
            cursor: isRunning ? 'default' : 'pointer',
            fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap',
            transition: 'background 0.2s',
          }}
        >
          {isRunning ? 'Executando…' : 'Atualizar dados'}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
        {STEP_ORDER.map(cmd => (
          <StepRow key={cmd} cmd={cmd} step={stepMap[cmd]} />
        ))}
      </div>

      {state.done && (
        <div style={{
          marginTop: 20, padding: '14px 18px', borderRadius: 10,
          background: state.success ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${state.success ? '#86efac' : '#fecaca'}`,
          fontWeight: 700, fontSize: 14,
          color: state.success ? '#15803d' : '#b91c1c',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          {state.success
            ? '✓  Pipeline concluído. Dados e mapa atualizados.'
            : '✗  Pipeline encerrado com erro. Verifique os logs acima.'}
        </div>
      )}
    </div>
  )
}
