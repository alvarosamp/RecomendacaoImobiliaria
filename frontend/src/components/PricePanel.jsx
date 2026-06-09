import { useState } from 'react'
import { predictPrice } from '../api'

const CITY = { lat: -22.230278, lon: -45.948889 }

export default function PricePanel() {
  const [form, setForm] = useState({
    area_m2: 100,
    bedrooms: 3,
    bathrooms: 2,
    parking_spaces: 1,
    property_type: 'apartamento',
    latitude: CITY.lat,
    longitude: CITY.lon,
  })
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)
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

  const Field = ({ label, name, type = 'number', step, children }) => (
    <div className="form-row">
      <label>{label}</label>
      {children ?? (
        <input
          type={type}
          step={step}
          value={form[name]}
          onChange={e => set(name, type === 'number' ? +e.target.value : e.target.value)}
        />
      )}
    </div>
  )

  return (
    <div className="panel">
      <h2>Estimativa de Preço</h2>
      <form onSubmit={handleSubmit} className="price-form">
        <Field label="Área (m²)" name="area_m2" />
        <Field label="Quartos"   name="bedrooms" />
        <Field label="Banheiros" name="bathrooms" />
        <Field label="Vagas"     name="parking_spaces" />
        <Field label="Tipo" name="property_type">
          <select value={form.property_type} onChange={e => set('property_type', e.target.value)}>
            <option value="apartamento">Apartamento</option>
            <option value="casa">Casa</option>
            <option value="comercial">Comercial</option>
            <option value="terreno">Terreno</option>
          </select>
        </Field>
        <Field label="Latitude"  name="latitude"  step="0.0001" />
        <Field label="Longitude" name="longitude" step="0.0001" />
        <button type="submit" disabled={loading}>
          {loading ? 'Calculando…' : 'Estimar Preço'}
        </button>
      </form>

      {result !== null && (
        <div className="price-result">
          <span>Preço estimado (LightGBM)</span>
          <strong>
            {result.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })}
          </strong>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  )
}
