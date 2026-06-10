import { useState, useEffect } from 'react'
import { fetchCommerceGaps } from '../api'

function DistDisplay({ dist_m }) {
  if (!dist_m) return <span className="gap-dist">–</span>
  return (
    <div className="gap-dist">
      {(dist_m / 1000).toFixed(1)} <span>km até o mais próximo</span>
    </div>
  )
}

function GapCard({ loc, rank }) {
  return (
    <div className="gap-card">
      <div>
        <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>#{rank} · {loc.typology}</div>
        <div className="gap-card-title">{loc.h3_id}</div>
        <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>Zona: {loc.zona}</div>
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

  return (
    <div className="commerce-section">
      <div className="commerce-section-header">
        <h3>{data.label}</h3>
        <span className="affected-badge">{data.cells_affected} células afetadas</span>
      </div>
      <p className="commerce-desc">{data.description}</p>

      <div className="gap-cards">
        {shown.map((loc, i) => <GapCard key={loc.h3_id} loc={loc} rank={i + 1} />)}
      </div>

      {data.top_locations.length > 3 && (
        <button
          onClick={() => setExpanded(e => !e)}
          style={{
            marginTop: 12, background: 'none', border: '1px solid #e2e8f0',
            borderRadius: 8, padding: '6px 16px', cursor: 'pointer',
            fontSize: 12, color: '#64748b',
          }}
        >
          {expanded ? 'Ver menos' : `Ver mais ${data.top_locations.length - 3} locais`}
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

  if (loading) return <div className="loading">Analisando demanda de comércios…</div>
  if (error)   return (
    <div className="page">
      <div className="page-header">
        <h2>Comércios faltantes</h2>
      </div>
      <p className="error">Banco sem dados suficientes ainda. Rode o pipeline para popular as features.</p>
    </div>
  )

  return (
    <div className="page">
      <div className="page-header">
        <h2>Onde há demanda não atendida?</h2>
        <p>
          Análise de gaps por tipo de comércio — mostra <strong>por que</strong> cada local precisa
          de um serviço, não apenas onde ele está ausente.
        </p>
      </div>

      <div className="ml-insight">
        <strong>Como identificamos a demanda</strong>
        Cada célula H3 recebe uma tipologia por clustering (K-Means) nas features geoespaciais:
        densidade de construção (NDBI), cobertura vegetal (NDVI), tendência de crescimento e distâncias
        aos serviços existentes. Isso cria perfis de bairro — "Urbano denso", "Residencial consolidado",
        "Em expansão", "Rural/periférico" — que explicam <em>por que</em> um serviço é necessário
        naquele ponto específico, e não apenas que ele está ausente.
      </div>

      {gaps.length === 0
        ? <p style={{ color: '#64748b', marginTop: 20 }}>
            Nenhuma análise disponível. Certifique-se de que o pipeline foi executado.
          </p>
        : gaps.map(g => <CommerceSection key={g.type} data={g} />)
      }
    </div>
  )
}
