import { useState, useEffect, useRef } from 'react'

const STEP_ICONS = {
  pending: '○',
  running: '◌',
  done:    '●',
  error:   '✕',
}

const STEP_COLORS = {
  pending: '#94a3b8',
  running: '#2563eb',
  done:    '#16a34a',
  error:   '#dc2626',
}

function StepRow({ step, index, total }) {
  const pct = step.status === 'done' ? 100 : step.status === 'running' ? 50 : 0
  const color = STEP_COLORS[step.status] ?? '#94a3b8'
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <span style={{ color, fontSize: 14, width: 16, textAlign: 'center', flexShrink: 0 }}>
          {step.status === 'running'
            ? <SpinIcon />
            : STEP_ICONS[step.status] ?? '○'}
        </span>
        <span style={{ fontSize: 13, color: step.status === 'pending' ? '#94a3b8' : '#1e293b', fontWeight: step.status === 'running' ? 600 : 400 }}>
          {step.label}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#94a3b8' }}>
          {index + 1}/{total}
        </span>
      </div>
      <div style={{ height: 3, background: '#e2e8f0', borderRadius: 99, overflow: 'hidden', marginLeft: 26 }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: color,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

function SpinIcon() {
  const [frame, setFrame] = useState(0)
  const chars = ['◐', '◓', '◑', '◒']
  useEffect(() => {
    const t = setInterval(() => setFrame(f => (f + 1) % 4), 220)
    return () => clearInterval(t)
  }, [])
  return <span>{chars[frame]}</span>
}

export default function SetupScreen({ onComplete, onRefreshDone }) {
  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const [steps, setSteps] = useState([])
  const [mode, setMode] = useState(null)
  const intervalRef = useRef(null)

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  useEffect(() => {
    // Resume polling if pipeline was already running when component mounted
    fetch('/api/pipeline/status')
      .then(r => r.json())
      .then(s => {
        if (s.running) {
          setPhase('running')
          setMode(s.mode)
          setSteps(s.steps)
          startPolling()
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => () => stopPolling(), [])

  const startPolling = () => {
    intervalRef.current = setInterval(async () => {
      try {
        const s = await fetch('/api/pipeline/status').then(r => r.json())
        setSteps([...s.steps])
        if (s.done) {
          stopPolling()
          setPhase(s.success ? 'done' : 'error')
          if (s.success) {
            setTimeout(() => {
              if (s.mode === 'refresh') onRefreshDone?.()
              else onComplete?.()
            }, 1000)
          }
        }
      } catch (_) {}
    }, 1500)
  }

  const launch = async (endpoint) => {
    setPhase('running')
    setSteps([])
    setMode(endpoint === '/api/pipeline/run' ? 'full' : 'refresh')
    try {
      await fetch(endpoint, { method: 'POST' })
      startPolling()
    } catch (err) {
      setPhase('error')
    }
  }

  // ── Idle (empty DB) ──────────────────────────────────────────────
  if (phase === 'idle') {
    return (
      <div className="setup-screen">
        <div className="setup-card">
          <div className="setup-icon">◎</div>
          <h2 className="setup-title">Banco de dados vazio</h2>
          <p className="setup-desc">
            O mapa e as análises precisam dos dados de Pouso Alegre.
            Clique abaixo para carregar tudo automaticamente — leva cerca de 2 a 5 minutos.
          </p>

          <div className="setup-what">
            <div className="setup-what-title">O que será carregado:</div>
            <ul>
              <li>Grade hexagonal H3 sobre o município</li>
              <li>Pontos de interesse (OpenStreetMap)</li>
              <li>Estabelecimentos de saúde (CNES / DataSUS)</li>
              <li>Estimativa de população por célula (IBGE Censo 2022)</li>
              <li>Scores de oportunidade e risco por área</li>
            </ul>
          </div>

          <button className="setup-btn" onClick={() => launch('/api/pipeline/run')}>
            Inicializar dados
          </button>
        </div>
      </div>
    )
  }

  // ── Running ──────────────────────────────────────────────────────
  if (phase === 'running') {
    const total = steps.length || (mode === 'refresh' ? 5 : 8)
    const done  = steps.filter(s => s.status === 'done').length
    const pct   = total > 0 ? Math.round((done / total) * 100) : 0

    return (
      <div className="setup-screen">
        <div className="setup-card">
          <div className="setup-icon">⟳</div>
          <h2 className="setup-title">
            {mode === 'refresh' ? 'Atualizando dados…' : 'Carregando dados…'}
          </h2>
          <div className="setup-progress-bar">
            <div style={{ width: `${pct}%` }} />
          </div>
          <p style={{ fontSize: 12, color: '#64748b', textAlign: 'center', margin: '4px 0 20px' }}>
            {done} de {total} etapas concluídas
          </p>
          <div className="setup-steps">
            {steps.map((s, i) => (
              <StepRow key={s.cmd} step={s} index={i} total={total} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Done ─────────────────────────────────────────────────────────
  if (phase === 'done') {
    return (
      <div className="setup-screen">
        <div className="setup-card">
          <div className="setup-icon" style={{ color: '#16a34a' }}>✓</div>
          <h2 className="setup-title" style={{ color: '#16a34a' }}>Dados carregados!</h2>
          <p className="setup-desc">Abrindo o mapa…</p>
        </div>
      </div>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────
  return (
    <div className="setup-screen">
      <div className="setup-card">
        <div className="setup-icon" style={{ color: '#dc2626' }}>✕</div>
        <h2 className="setup-title" style={{ color: '#dc2626' }}>Erro na inicialização</h2>
        <p className="setup-desc">
          Uma etapa falhou. Verifique se o PostGIS está acessível e tente novamente.
        </p>
        <div className="setup-steps" style={{ marginBottom: 20 }}>
          {steps.map((s, i) => (
            <StepRow key={s.cmd} step={s} index={i} total={steps.length} />
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="setup-btn" onClick={() => launch('/api/pipeline/run')}>
            Tentar novamente
          </button>
          <button
            className="setup-btn"
            style={{ background: '#64748b' }}
            onClick={async () => {
              await fetch('/api/pipeline/reset', { method: 'POST' })
              setPhase('idle'); setSteps([])
            }}
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  )
}
