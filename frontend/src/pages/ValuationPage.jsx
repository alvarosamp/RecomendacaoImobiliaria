import { useState } from 'react'
import { predictPrice } from '../api'

const PROPERTY_TYPES = [['apartamento', 'Apartamento'], ['casa', 'Casa'], ['comercial', 'Comercial'], ['terreno', 'Terreno']]
const money = value => Number(value || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

export default function ValuationPage() {
  const [form, setForm] = useState({ reference: '', area_m2: '', bedrooms: 2, bathrooms: 1, parking_spaces: 1, property_type: 'apartamento', latitude: '', longitude: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const set = (field, value) => setForm(current => ({ ...current, [field]: value }))
  const handleSubmit = async event => {
    event.preventDefault(); setLoading(true); setError(null); setResult(null)
    try {
      setResult(await predictPrice({ ...form, area_m2: Number(form.area_m2), bedrooms: Number(form.bedrooms), bathrooms: Number(form.bathrooms), parking_spaces: Number(form.parking_spaces), latitude: Number(form.latitude || 0), longitude: Number(form.longitude || 0) }))
    } catch (err) { setError(`Não foi possível calcular a avaliação. ${err.message}`) } finally { setLoading(false) }
  }
  return <div className="page">
    <div className="page-hero"><div className="page-hero-eyebrow">Modelo de Precificação</div><h2>Avaliação de Imóvel</h2><p>Estimativa baseada nas características informadas e, quando disponíveis, na localização do imóvel. O resultado mostra a faixa de preço e o método usado.</p></div>
    <div className="card-grid valuation-grid">
      <section className="opp-card"><div className="opp-card-header"><h3>Dados para a estimativa</h3></div>
        <form onSubmit={handleSubmit} className="valuation-form">
          <div className="form-group"><label>Referência do imóvel</label><input value={form.reference} onChange={e => set('reference', e.target.value)} placeholder="Ex.: Centro, Pouso Alegre" /><small>Usada para identificação. Informe coordenadas para considerar a localização.</small></div>
          <div className="valuation-fields">
            <div className="form-group"><label>Área útil (m²)</label><input type="number" min="1" value={form.area_m2} onChange={e => set('area_m2', e.target.value)} required /></div>
            <div className="form-group"><label>Tipo</label><select value={form.property_type} onChange={e => set('property_type', e.target.value)}>{PROPERTY_TYPES.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></div>
            <div className="form-group"><label>Quartos</label><input type="number" min="0" value={form.bedrooms} onChange={e => set('bedrooms', e.target.value)} /></div>
            <div className="form-group"><label>Banheiros</label><input type="number" min="0" value={form.bathrooms} onChange={e => set('bathrooms', e.target.value)} /></div>
            <div className="form-group"><label>Vagas</label><input type="number" min="0" value={form.parking_spaces} onChange={e => set('parking_spaces', e.target.value)} /></div>
            <div className="form-group"><label>Latitude <small>(opcional)</small></label><input type="number" step="any" value={form.latitude} onChange={e => set('latitude', e.target.value)} /></div>
            <div className="form-group"><label>Longitude <small>(opcional)</small></label><input type="number" step="any" value={form.longitude} onChange={e => set('longitude', e.target.value)} /></div>
          </div>
          <button type="submit" className="landing-btn-primary" disabled={loading}>{loading ? 'Calculando…' : 'Calcular estimativa'}</button>
        </form>{error && <div className="auth-error">{error}</div>}
      </section>
      <section className="opp-card priority-investigar valuation-result" aria-live="polite">
        {!result ? <div className="empty-state"><h3>Informe os dados do imóvel</h3><p>A faixa de valor aparecerá aqui após o cálculo.</p></div> : <>
          <div className="opp-card-header"><h3>Resultado da avaliação</h3><span className="badge" style={{ background: '#EDE9FE', color: '#5B21B6' }}>{result.model_status === 'lightgbm' ? 'Modelo treinado' : 'Estimativa inicial'}</span></div>
          <div className="valuation-price"><span>Valor central estimado</span><strong>{money(result.predicted_price)}</strong><small>{money(result.price_per_m2)} / m²</small></div>
          <div className="valuation-range"><span>Faixa de referência</span><strong>{money(result.price_low)} — {money(result.price_high)}</strong></div>
          {result.warning && <div className="valuation-warning">{result.warning}</div>}
          {result.explain?.length > 0 && <div className="opp-uses"><h4>Como a estimativa foi calculada</h4>{result.explain.map(item => <div className="use-row" key={item}><span className="use-label">{item}</span></div>)}</div>}
        </>}
      </section>
    </div>
  </div>
}
