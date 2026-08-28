import { useEffect, useMemo, useState } from 'react'
import { assessLegalCompatibility } from '../api'

const USES = [
  ['residencial', 'Residencial'], ['comercial', 'Comercial'], ['misto', 'Uso misto'],
  ['industrial', 'Industrial'], ['institucional', 'Institucional'],
]
const STATUS = {
  allowed: { label: 'Permitido', tone: 'good' },
  conditioned: { label: 'Condicionado', tone: 'watch' },
  blocked: { label: 'Bloqueado', tone: 'danger' },
  analisar: { label: 'Requer análise', tone: 'neutral' },
}
const areaLabel = row => row.neighborhood || row.zona || row.h3_id

export default function LegalAuditPage({ scores }) {
  const rows = useMemo(() => [...scores].sort((a, b) => (b.score_residencial || 0) - (a.score_residencial || 0)), [scores])
  const [h3Id, setH3Id] = useState('')
  const [intendedUse, setIntendedUse] = useState('residencial')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const selected = rows.find(row => row.h3_id === h3Id) || rows[0]

  useEffect(() => { if (!h3Id && rows[0]) setH3Id(rows[0].h3_id) }, [h3Id, rows])

  const runAudit = async event => {
    event.preventDefault()
    if (!selected) return
    setLoading(true); setError(null)
    try { setResult(await assessLegalCompatibility({ h3Id: selected.h3_id, intendedUse })) }
    catch (err) { setResult(null); setError(`Não foi possível consultar a auditoria legal. ${err.message}`) }
    finally { setLoading(false) }
  }

  const status = STATUS[result?.status] || STATUS.analisar
  return <div className="page legal-page">
    <div className="page-header"><div className="page-eyebrow">Conformidade urbanística</div><h2>Auditoria legal da área</h2><p>Consulte as regras estruturadas para uma célula H3 e o uso pretendido. Esta triagem não substitui aprovação, projeto ou parecer técnico.</p></div>
    <form className="legal-form" onSubmit={runAudit}>
      <label>Área H3<select value={selected?.h3_id || ''} onChange={event => setH3Id(event.target.value)}>{rows.map(row => <option key={row.h3_id} value={row.h3_id}>{areaLabel(row)} · {row.h3_id}</option>)}</select></label>
      <label>Uso pretendido<select value={intendedUse} onChange={event => setIntendedUse(event.target.value)}>{USES.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <button className="legal-submit" disabled={loading || !selected}>{loading ? 'Verificando…' : 'Verificar compatibilidade'}</button>
    </form>
    {error && <div className="auth-error">{error}</div>}
    {!result && !error && <div className="legal-empty"><span>⚖</span><h3>Selecione uma área e consulte a compatibilidade.</h3><p>A análise vai listar o zoneamento identificado, condicionantes e fontes disponíveis.</p></div>}
    {result && <div className="legal-result"><section className="legal-summary"><div><span>Resultado da triagem</span><h3>{areaLabel(selected)}</h3><p>Zona identificada: <strong>{result.zone || selected?.zona || 'não identificada'}</strong></p></div><div className={`legal-status ${status.tone}`}><strong>{status.label}</strong><span>{result.spatial_overlays_verified ? 'camadas espaciais verificadas' : 'camadas espaciais pendentes'}</span></div></section>
      {result.notes && <p className="legal-summary-copy">{result.notes}</p>}
      <div className="legal-details-grid"><section><h4>Parâmetros e condições</h4>{Object.keys(result.parameters || {}).length ? <dl>{Object.entries(result.parameters).map(([key, value]) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{Array.isArray(value) ? value.join(', ') : String(value)}</dd></div>)}</dl> : <p>Não há parâmetros estruturados para esta combinação.</p>}</section><section><h4>Artigos e fontes</h4><ul className="legal-source-list">{(result.articles || []).map(item => <li key={item}>{item}</li>)}{(result.sources || []).map(source => <li key={source.url || source.title}>{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.url}</a> : source.title}</li>)}</ul>{!(result.articles?.length || result.sources?.length) && <p>Não foram encontradas referências estruturadas.</p>}</section></div>
      {result.overlays?.length > 0 && <section className="legal-restrictions"><h4>Camadas espaciais incidentes</h4><ul>{result.overlays.map((item, index) => <li key={`${item.tipo}-${index}`}>{item.tipo}{item.status ? ` · ${item.status}` : ''}</li>)}</ul></section>}
      <p className="legal-disclaimer">{result.disclaimer}</p>
    </div>}
  </div>
}
