import { useState } from 'react'

export default function ValuationPage() {
  const [address, setAddress] = useState('')
  const [area, setArea] = useState('')
  const [rooms, setRooms] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleSimulate = (e) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => {
      setResult({
        price: 850000,
        pricePerSqm: 11500,
        confidence: 88,
        factors: [
          { name: 'Proximidade ao Metrô', impact: '+12%' },
          { name: 'Área verde no raio de 500m', impact: '+5%' },
          { name: 'Idade média do entorno', impact: '-3%' }
        ]
      })
      setLoading(false)
    }, 1500)
  }

  return (
    <div className="page">
      <div className="page-hero">
        <div className="page-hero-eyebrow">Modelo de Precificação</div>
        <h2>Avaliação de Imóvel</h2>
        <p>Estime o valor de mercado de um imóvel baseado em dados de transações reais enriquecidos com variáveis territoriais.</p>
      </div>

      <div className="card-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <div className="opp-card">
          <div className="opp-card-header">
            <h3>Dados do Imóvel</h3>
          </div>
          <form onSubmit={handleSimulate} style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
            <div className="form-group">
              <label>Endereço completo</label>
              <input type="text" placeholder="Rua, Número - Bairro" value={address} onChange={e => setAddress(e.target.value)} required />
            </div>
            <div style={{ display: 'flex', gap: '16px' }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Área útil (m²)</label>
                <input type="number" placeholder="Ex: 75" value={area} onChange={e => setArea(e.target.value)} required />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Quartos</label>
                <input type="number" placeholder="Ex: 2" value={rooms} onChange={e => setRooms(e.target.value)} required />
              </div>
            </div>
            <button type="submit" className="landing-btn-primary" disabled={loading} style={{ alignSelf: 'flex-start' }}>
              {loading ? 'Calculando...' : 'Estimar Valor'}
            </button>
          </form>
        </div>

        {result && (
          <div className="opp-card priority-investigar">
            <div className="opp-card-header">
              <h3>Resultado da Avaliação</h3>
              <div className="opp-badges">
                <span className="badge" style={{ background: '#EDE9FE', color: '#5B21B6' }}>
                  Confiança: {result.confidence}%
                </span>
              </div>
            </div>

            <div style={{ marginTop: '24px', textAlign: 'center' }}>
              <div style={{ fontSize: '14px', color: 'var(--muted)' }}>Valor de Venda Sugerido</div>
              <div style={{ fontSize: '36px', fontWeight: 'bold', color: 'var(--primary)', margin: '8px 0' }}>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(result.price)}
              </div>
              <div style={{ fontSize: '14px', color: 'var(--muted)' }}>
                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(result.pricePerSqm)} / m²
              </div>
            </div>

            <div className="opp-uses" style={{ marginTop: '32px' }}>
              <div style={{ fontWeight: 600, marginBottom: '12px', fontSize: '14px' }}>Fatores de Influência (Geoespaciais)</div>
              {result.factors.map(f => (
                <div className="use-row" key={f.name}>
                  <span className="use-label">{f.name}</span>
                  <span style={{ color: f.impact.startsWith('+') ? '#15803D' : '#B91C1C', fontWeight: 600, fontSize: 13 }}>
                    {f.impact}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
