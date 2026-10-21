import { lazy, Suspense, useState } from 'react'
import { fetchPublicDiagnosis } from '../api'
const MapPage = lazy(() => import('./MapPage'))
const priorities = { alta: 'Alta', media: 'Média', baixa: 'Baixa', dados_pendentes: 'Dados pendentes', sem_populacao: 'Sem população informada' }
const fmt = value => value == null ? 'Não disponível' : Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 1 })

export default function PublicDiagnosisPage({ scores, ...mapProps }) {
  const [service, setService] = useState('schools')
  const [distance, setDistance] = useState(2000)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState('')
  const stale = result && (result.service !== service || result.target_distance_m !== Number(distance))
  const current = stale ? null : result
  const rows = (current?.rows || []).filter(row => !filter || row.priority === filter)
  const run = async event => {
    event.preventDefault(); setLoading(true); setError(''); setResult(null); setSelected('')
    try { setResult(await fetchPublicDiagnosis(service, distance)) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([current.report_markdown], { type: 'text/markdown;charset=utf-8' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: `urbia-diagnostico-${current.service}.md` })
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <section className="page public-diagnosis">
    <div className="page-header"><div className="page-eyebrow">Urbia Governo</div><h2>Diagnóstico de acesso a equipamentos</h2><p>Identifique regiões para investigação a partir de população, estabelecimentos mapeados e distância. Este ranking não mede déficit de vagas nem comprova oferta pública.</p></div>
    <form className="study-fields" onSubmit={run}><label>Necessidade<select disabled={loading} value={service} onChange={event => setService(event.target.value)}><option value="schools">Escolas e creches</option><option value="hospitals">Atendimento hospitalar</option></select></label><label>Referência exploratória de distância (m)<input disabled={loading} type="number" min="100" max="50000" required value={distance} onChange={event => setDistance(event.target.value)} /></label><button className="report-download" disabled={loading}>{loading ? 'Calculando…' : 'Gerar diagnóstico'}</button></form>
    <p>A distância de referência é uma escolha para explorar o território, não uma norma de atendimento.</p>
    {error && <div className="error-msg" role="alert">{error}</div>}
    {stale && <p role="status">Parâmetros alterados. Gere novamente o diagnóstico antes de exportar.</p>}
    {current && <>
      <div className="workspace-grid public-summary"><article className="workspace-card"><h3>{current.summary.ranked} regiões ranqueadas</h3><p>{current.summary.high_priority} com prioridade alta de investigação.</p></article><article className="workspace-card"><h3>{current.summary.pending} com dados pendentes</h3><p>Valores ausentes permanecem indisponíveis e não geram indicação de prioridade.</p></article></div>
      <details className="workspace-card"><summary>Critérios, fontes e limitações</summary><p>{current.formula}</p><p>Metodologia: {current.methodology}. Captura: {new Date(current.captured_at).toLocaleString('pt-BR')}.</p><ul>{current.limitations.map(item => <li key={item}>{item}</li>)}</ul><h3>Fontes registradas</h3>{current.sources.length ? current.sources.map((source, index) => <p key={index}>{source.source_name} · referência: {source.reference_date || 'não informada'} · coleta: {source.collected_at || 'não informada'}{source.source_uri && <> · <a href={source.source_uri} target="_blank" rel="noreferrer">Consultar fonte</a></>}</p>) : <p>Proveniência dos equipamentos não registrada. Confirmar cobertura e atualização antes de interpretar ausência como falta de oferta.</p>}</details>
      <div className="study-toolbar"><label>Filtrar prioridade<select value={filter} onChange={event => setFilter(event.target.value)}><option value="">Todas</option>{Object.entries(priorities).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><button onClick={download}>Baixar diagnóstico (.md)</button></div>
      <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Região</th><th>População</th><th>Oferta mapeada</th><th>Distância</th><th>Prioridade</th><th>Explicação</th></tr></thead><tbody>{rows.map(row => <tr key={row.h3_id}><td><strong>{row.neighborhood || row.h3_id}</strong><small>{row.h3_id}</small><button onClick={() => setSelected(row.h3_id)}>Ver região no mapa</button></td><td>{fmt(row.population)}<small>{row.population_basis === 'census_h3' ? 'Censo agregado por H3' : row.population_basis === 'estimate' ? 'Estimativa territorial' : 'Fonte pendente'}</small></td><td>{fmt(row.count)}</td><td>{fmt(row.distance_m)} m</td><td>{priorities[row.priority]}<small>Score: {fmt(row.investigation_score)}</small></td><td>{row.reason}</td></tr>)}</tbody></table></div>
      {!rows.length && <p>Nenhuma região para os filtros selecionados.</p>}
      {selected && <section><h3>Região selecionada: {selected}</h3>{scores.some(row => row.h3_id === selected) ? <Suspense fallback={<p>Carregando mapa…</p>}><MapPage {...mapProps} scores={scores} profile="governo" selectedAreaId={selected} onSelectArea={row => setSelected(row.h3_id)} /></Suspense> : <p>Esta região não está disponível no mapa de scores atual. O diagnóstico continua registrado acima.</p>}</section>}
    </>}
  </section>
}
