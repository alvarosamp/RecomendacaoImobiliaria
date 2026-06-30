import { useState } from 'react'
import { predictPrice } from '../api'

const INITIAL = {
  area_m2: 100, bedrooms: 3, bathrooms: 2, parking_spaces: 1,
  property_type: 'apartamento',
  latitude: -22.230278, longitude: -45.948889,
}

const TYPE_ICONS = {
  apartamento: '🏢',
  casa:        '🏠',
  comercial:   '🏪',
  terreno:     '🌿',
}

export default function ValuationPage() {
  const [form, setForm]     = useState(INITIAL)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async e => {
    e.preventDefault()
    setLoading(true); setError(null); setResult(null)
    try {
      const res = await predictPrice(form)
      if (res.error) throw new Error(res.error)
      setResult(res.predicted_price)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fmt = val => val.toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
  })

  const fmtPerM2 = val => {
    const pm2 = val / form.area_m2
    return pm2.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Avaliação de Imóvel</h2>
        <p>Estimativa de preço com modelo LightGBM treinado em dados de Pouso Alegre — MG.</p>
      </div>

      <div className="valuation-wrapper">
        {/* Form */}
        <div className="valuation-card">
          <h3>Características do Imóvel</h3>
          <form onSubmit={submit}>
            <div className="field-group">

              {/* Property type buttons */}
              <div className="field">
                <label>Tipo de imóvel</label>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {['apartamento', 'casa', 'comercial', 'terreno'].map(t => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => set('property_type', t)}
                      style={{
                        flex: 1, minWidth: 70,
                        padding: '8px 6px',
                        border: `1.5px solid ${form.property_type === t ? 'var(--navy)' : 'var(--border)'}`,
                        borderRadius: 'var(--radius-sm)',
                        background: form.property_type === t ? 'var(--navy)' : 'var(--bg-warm)',
                        color: form.property_type === t ? '#fff' : 'var(--text-2)',
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        transition: 'all 0.15s',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: 18, marginBottom: 3 }}>{TYPE_ICONS[t]}</div>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Area */}
              <div className="field">
                <label>Área (m²)</label>
                <input
                  type="number"
                  value={form.area_m2}
                  min={10} max={2000}
                  onChange={e => set('area_m2', +e.target.value)}
                />
              </div>

              {/* Quartos e Banheiros */}
              <div className="field-row">
                <div className="field">
                  <label>Quartos</label>
                  <input type="number" value={form.bedrooms} min={0} max={20}
                    onChange={e => set('bedrooms', +e.target.value)} />
                </div>
                <div className="field">
                  <label>Banheiros</label>
                  <input type="number" value={form.bathrooms} min={0} max={20}
                    onChange={e => set('bathrooms', +e.target.value)} />
                </div>
              </div>

              {/* Vagas */}
              <div className="field">
                <label>Vagas de garagem</label>
                <input type="number" value={form.parking_spaces} min={0} max={10}
                  onChange={e => set('parking_spaces', +e.target.value)} />
              </div>

              {/* Localização */}
              <div className="field-section-title">Localização</div>
              <div className="field-row">
                <div className="field">
                  <label>Latitude</label>
                  <input type="number" step="0.0001" value={form.latitude}
                    onChange={e => set('latitude', +e.target.value)} />
                </div>
                <div className="field">
                  <label>Longitude</label>
                  <input type="number" step="0.0001" value={form.longitude}
                    onChange={e => set('longitude', +e.target.value)} />
                </div>
              </div>

            </div>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? '⟳ Calculando…' : 'Estimar preço'}
            </button>
            {error && <p className="error">{error}</p>}
          </form>
        </div>

        {/* Result */}
        <div className="valuation-card">
          <h3>Resultado da Avaliação</h3>
          <div className="result-card">
            {result == null && !error && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 40, marginBottom: 16 }}>🏡</div>
                <p className="result-empty">
                  Preencha as características ao lado e clique em <strong>Estimar preço</strong> para obter a avaliação.
                </p>
              </div>
            )}
            {result != null && (
              <>
                <div className="result-eyebrow">Preço estimado</div>
                <div className="result-price">{fmt(result)}</div>
                <div className="result-gold-line" />
                <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 500 }}>
                  {fmtPerM2(result)} / m²
                </div>
                <div className="result-range">
                  Intervalo indicativo: {fmt(result * 0.85)} – {fmt(result * 1.15)}
                </div>
                <div className="result-note">
                  <strong style={{ display: 'block', color: 'var(--navy)', marginBottom: 4, fontSize: 12 }}>
                    Sobre esta estimativa
                  </strong>
                  Modelo LightGBM com otimização Optuna (MAE ≈ R$ 104 mil, R² 0,69).
                  Enriquecimento geoespacial aplicado automaticamente quando disponível.
                  Use como referência — não substitui avaliação profissional.
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
