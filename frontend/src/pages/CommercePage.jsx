import { useState, useEffect } from 'react'
import { fetchCommerceGaps } from '../api'

// Ícones de categoria de comércio
const COMMERCE_ICONS = {
  farmacia:      '💊',
  supermercado:  '🛒',
  padaria:       '🍞',
  escola:        '📚',
  academia:      '🏋️',
  restaurante:   '🍽️',
  banco:         '🏦',
  clinica:       '🏥',
  default:       '🏪',
}

function getIcon(label) {
  const l = (label || '').toLowerCase()
  for (const [key, icon] of Object.entries(COMMERCE_ICONS)) {
    if (l.includes(key)) return icon
  }
  return COMMERCE_ICONS.default
}

function DistDisplay({ dist_m }) {
  if (!dist_m) return <span className="gap-dist">–</span>
  const km = (dist_m / 1000).toFixed(1)
  return (
    <div className="gap-dist">
      {km}
      <span>km até o mais próximo</span>
    </div>
  )
}

function GapCard({ loc, rank }) {
  return (
    <div className="gap-card">
      <div>
        <div className="gap-card-rank">#{rank} · {loc.typology}</div>
        <div className="gap-card-title">{loc.h3_id}</div>
        <div className="gap-card-zona">Zona: {loc.zona}</div>
      </div>
      <DistDisplay dist_m={loc.dist_m} />
      <div className="gap-reasons">
        {loc.reasons.map((r, i) => (
          <div className="gap-reason" key={i}>{r}</div>
        ))}
      </div>
    </div>
  )
}

function CommerceSection({ data }) {
  const [expanded, setExpanded] = useState(false)
  const shown = expanded ? data.top_locations : data.top_locations.slice(0, 3)
  const icon  = getIcon(data.label)

  return (
    <div className="commerce-section">
      <div className="commerce-section-header">
        <h3>
          <span style={{ marginRight: 10 }}>{icon}</span>
          {data.label}
        </h3>
        <span className="affected-badge">{data.cells_affected} áreas afetadas</span>
      </div>
      <p className="commerce-desc">{data.description}</p>

      <div className="gap-cards">
        {shown.map((loc, i) => <GapCard key={loc.h3_id} loc={loc} rank={i + 1} />)}
      </div>

      {data.top_locations.length > 3 && (
        <button
          className="show-more-btn"
          onClick={() => setExpanded(e => !e)}
        >
          {expanded ? 'Ver menos ↑' : `Ver mais ${data.top_locations.length - 3} locais ↓`}
        </button>
      )}
    </div>
  )
}

export default function CommercePage() {
  const [gaps, setGaps]       = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    fetchCommerceGaps()
      .then(data => {
        if (data?.error) throw new Error(data.error)
        setGaps(Array.isArray(data) ? data : [])
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="loading">
      <div className="loading-spinner" />
      Analisando demanda de comércios…
    </div>
  )

  if (error) return (
    <div className="page">
      <div className="page-header">
        <h2>Comércios Faltantes</h2>
      </div>
      <p className="error">Banco sem dados suficientes ainda. Rode o pipeline para popular as features.</p>
    </div>
  )

  return (
    <div className="page">
      <div className="page-header">
        <h2>Onde Há Demanda Não Atendida?</h2>
        <p>
          Análise de gaps por tipo de comércio — mostra <strong>por que</strong> cada local precisa
          de um serviço, não apenas onde ele está ausente.
        </p>
      </div>

      {/* Insight box */}
      <div className="ml-insight">
        <strong>Como identificamos a demanda</strong>
        Cada área recebe uma tipologia por clustering nas features geoespaciais:
        densidade de construção (NDBI), cobertura vegetal (NDVI), tendência de crescimento e distâncias
        aos serviços existentes. Isso cria perfis de bairro — "Urbano denso", "Residencial consolidado",
        "Em expansão", "Rural/periférico" — que explicam <em>por que</em> um serviço é necessário
        naquele ponto específico.
      </div>

      {gaps.length === 0
        ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#78716C' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📊</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Nenhuma análise disponível</div>
            <div style={{ fontSize: 13, marginTop: 6 }}>
              Certifique-se de que o pipeline foi executado.
            </div>
          </div>
        )
        : gaps.map(g => <CommerceSection key={g.type} data={g} />)
      }
    </div>
  )
}
