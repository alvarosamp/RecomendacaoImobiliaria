import { useState, useEffect, useRef } from 'react'

const STEP_COLORS = {
  pending: '#A8A29E',
  running: '#1B2A4A',
  done:    '#16A34A',
  error:   '#DC2626',
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

function StepRow({ step, index, total }) {
  const color = STEP_COLORS[step.status] ?? '#A8A29E'
  const isPending = step.status === 'pending'
  const isDone    = step.status === 'done'
  const isRunning = step.status === 'running'
  const isError   = step.status === 'error'

  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <span style={{
          color, fontSize: 14, width: 18, textAlign: 'center',
          flexShrink: 0, lineHeight: 1,
        }}>
          {isRunning ? <SpinIcon />
            : isDone  ? '✓'
            : isError ? '✕'
            : '○'}
        </span>
        <span style={{
          fontSize: 13,
          color: isPending ? '#A8A29E' : '#1C1917',
          fontWeight: isRunning ? 600 : 400,
          flex: 1,
        }}>
          {step.label}
        </span>
        <span style={{ fontSize: 10, color: '#A8A29E', fontWeight: 600 }}>
          {index + 1}/{total}
        </span>
      </div>
      <div style={{
        height: 3, background: '#E7E4DF', borderRadius: 99,
        overflow: 'hidden', marginLeft: 28,
      }}>
        <div style={{
          width: isDone ? '100%' : isRunning ? '55%' : '0%',
          height: '100%', background: color, borderRadius: 99,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
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
    } catch {
      setPhase('error')
    }
  }

  // ── Logo compartilhado ───────────────────────────────────────────
  const Logo = () => (
    <div className="setup-logo">IT</div>
  )

  // ── Idle ─────────────────────────────────────────────────────────
  if (phase === 'idle') {
    return (
      <div className="setup-screen">
        <div className="setup-card">
          <Logo />
          <h2 className="setup-title">Bem-vindo à plataforma</h2>
          <p className="setup-desc">
            Para iniciar, precisamos carregar os dados do município de Pouso Alegre — MG.
            O processo é automático e leva cerca de 2 a 5 minutos.
          </p>

          <div className="setup-what">
            <div className="setup-what-title">O que será carregado</div>
            <ul>
              <li>Grade hexagonal H3 sobre o município</li>
              <li>Pontos de interesse (OpenStreetMap)</li>
              <li>Estabelecimentos de saúde (CNES / DataSUS)</li>
              <li>Estimativa de população por área (IBGE Censo 2022)</li>
              <li>Scores de oportunidade e risco por região</li>
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
          <Logo />
          <h2 className="setup-title">
            {mode === 'refresh' ? 'Atualizando dados…' : 'Carregando dados…'}
          </h2>
          <div style={{ fontSize: 12, color: '#78716C', marginBottom: 16 }}>
            {done} de {total} etapas concluídas ({pct}%)
          </div>
          <div className="setup-progress-bar" style={{ marginBottom: 24 }}>
            <div style={{ width: `${pct}%` }} />
          </div>
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
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: '#DCFCE7', border: '2px solid #86EFAC',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, margin: '0 auto 20px',
          }}>✓</div>
          <h2 className="setup-title" style={{ color: '#15803D' }}>Dados carregados!</h2>
          <p className="setup-desc">Abrindo o mapa da cidade…</p>
        </div>
      </div>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────
  return (
    <div className="setup-screen">
      <div className="setup-card">
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: '#FEE2E2', border: '2px solid #FCA5A5',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24, margin: '0 auto 20px',
        }}>✕</div>
        <h2 className="setup-title" style={{ color: '#DC2626' }}>Erro na inicialização</h2>
        <p className="setup-desc">
          Uma etapa falhou. Verifique se o banco de dados está acessível e tente novamente.
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
            style={{ background: '#78716C' }}
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
