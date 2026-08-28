import { useMemo, useState } from 'react'

const METRICS = [
  ['Score residencial', 'score_residencial', 'high'], ['Score comercial', 'score_comercial', 'high'],
  ['Confiança', 'confidence', 'high'], ['NDVI 90 dias', 'ndvi_mean_90', 'high'],
  ['NDBI 90 dias', 'ndbi_mean_90', 'high'], ['Mercado (R$/m²)', 'market_price_m2', 'high'],
  ['Risco', 'risk_level', 'text'], ['Zoneamento', 'zona', 'text'],
]
const fmt = value => typeof value === 'number' ? value.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) : (value ?? '—')
const name = row => row?.neighborhood || row?.zona || row?.h3_id

export default function CompareAreasPage({ scores }) {
  const ordered = useMemo(() => [...scores].sort((a, b) => (b.score_residencial || 0) - (a.score_residencial || 0)), [scores])
  const [ids, setIds] = useState(() => ordered.slice(0, 3).map(row => row.h3_id))
  const areas = ids.map(id => ordered.find(row => row.h3_id === id)).filter(Boolean)
  const setId = (index, value) => setIds(current => current.map((id, i) => i === index ? value : id))

  return <div className="page comparison-page">
    <div className="page-header"><div className="page-eyebrow">Decisão comparativa</div><h2>Comparar áreas</h2><p>Coloque até três células lado a lado para qualificar uma escolha territorial.</p></div>
    <div className="comparison-selectors">
      {[0, 1, 2].map(index => <label key={index}>Área {index + 1}<select value={ids[index] || ''} onChange={event => setId(index, event.target.value)}>{ordered.map(row => <option key={row.h3_id} value={row.h3_id}>{name(row)} · {row.h3_id}</option>)}</select></label>)}
    </div>
    <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Indicador</th>{areas.map(row => <th key={row.h3_id}><strong>{name(row)}</strong><small>{row.h3_id}</small></th>)}</tr></thead><tbody>{METRICS.map(([label, key, direction]) => {
      const values = areas.map(row => Number(row[key])); const best = direction === 'high' && values.some(Number.isFinite) ? Math.max(...values.filter(Number.isFinite)) : null
      return <tr key={key}><td>{label}</td>{areas.map(row => { const value = row[key]; return <td key={row.h3_id} className={Number(value) === best ? 'comparison-best' : ''}>{key === 'confidence' && Number.isFinite(Number(value)) ? `${(Number(value) <= 1 ? Number(value) * 100 : Number(value)).toFixed(0)}%` : fmt(value)}</td> })}</tr>
    })}</tbody></table></div>
  </div>
}
