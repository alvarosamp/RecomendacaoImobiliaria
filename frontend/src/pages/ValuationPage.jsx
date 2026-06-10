import { useState } from 'react'
import { predictPrice } from '../api'

const INITIAL = {
  area_m2: 100, bedrooms: 3, bathrooms: 2, parking_spaces: 1,
  property_type: 'apartamento',
  latitude: -22.230278, longitude: -45.948889,
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

  return (
    <div className="page">
      <div className="page-header">
        <h2>Avaliar imóvel</h2>
        <p>Estimativa de preço com modelo LightGBM treinado em dados de Pouso Alegre.</p>
      </div>

      <div className="valuation-wrapper">
        <div className="valuation-card">
          <h3>Características do imóvel</h3>
          <form onSubmit={submit}>
            <div className="field-group">
              <div className="field-row">
                <div className="field">
                  <label>Área (m²)</label>
                  <input type="number" value={form.area_m2} min={10} max={2000}
                    onChange={e => set('area_m2', +e.target.value)} />
                </div>
                <div className="field">
                  <label>Tipo</label>
                  <select value={form.property_type} onChange={e => set('property_type', e.target.value)}>
                    <option value="apartamento">Apartamento</option>
                    <option value="casa">Casa</option>
                    <option value="comercial">Comercial</option>
                    <option value="terreno">Terreno</option>
                  </select>
                </div>
              </div>

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

              <div className="field">
                <label>Vagas de garagem</label>
                <input type="number" value={form.parking_spaces} min={0} max={10}
                  onChange={e => set('parking_spaces', +e.target.value)} />
              </div>

              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 10 }}>
                  Localização (latitude / longitude)
                </div>
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
            </div>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading ? 'Calculando…' : 'Estimar preço'}
            </button>
            {error && <p className="error">{error}</p>}
          </form>
        </div>

        <div className="valuation-card">
          <h3>Resultado</h3>
          <div className="result-card">
            {result == null && !error && (
              <p className="result-empty">Preencha as características ao lado e clique em "Estimar preço".</p>
            )}
            {result != null && (
              <>
                <div className="result-label">Preço estimado</div>
                <div className="result-price">{fmt(result)}</div>
                <div className="result-range">
                  Intervalo indicativo: {fmt(result * 0.85)} – {fmt(result * 1.15)}
                </div>
                <div className="result-note">
                  Modelo LightGBM com Optuna (CV MAE ≈ R$ 104 mil, R² 0.69).
                  O enriquecimento geoespacial (NDVI, scores H3, zoneamento) é
                  aplicado automaticamente quando o banco está disponível.
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
