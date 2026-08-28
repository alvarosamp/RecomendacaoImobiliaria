import { useMemo, useState } from 'react'

const label = row => row.neighborhood || row.zona || row.h3_id
const score = row => Math.max(Number(row.score_residencial) || 0, Number(row.score_comercial) || 0)

export default function ReportsPage({ scores }) {
  const rows = useMemo(() => [...scores].sort((a, b) => score(b) - score(a)), [scores])
  const [selected, setSelected] = useState(() => rows[0]?.h3_id || '')
  const area = rows.find(row => row.h3_id === selected) || rows[0]
  const download = () => {
    if (!area) return
    const report = [`# Relatório territorial`, '', `Área: ${label(area)}`, `Célula H3: ${area.h3_id}`, `Gerado em: ${new Date().toLocaleDateString('pt-BR')}`, '', '## Indicadores', `- Score residencial: ${score(area).toFixed(0)}`, `- Score comercial: ${Number(area.score_comercial || 0).toFixed(0)}`, `- Prioridade: ${area.priority || '—'}`, `- Risco: ${area.risk_level || '—'}`, `- Zoneamento: ${area.zona || 'não identificado'}`, '', '## Evidências', ...(area.explainability || []).map(item => `- ${item.label}: ${item.value}`), '', '## Aviso', 'Este relatório é uma análise de apoio e requer validação técnica e urbanística.'].join('\n')
    const url = URL.createObjectURL(new Blob([report], { type: 'text/markdown;charset=utf-8' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: `urbia-${area.h3_id}.md` })
    link.click(); URL.revokeObjectURL(url)
  }
  return <div className="page reports-page"><div className="page-header"><div className="page-eyebrow">Comunicação técnica</div><h2>Relatórios territoriais</h2><p>Gere uma síntese rastreável da área selecionada, com indicadores e evidências do processamento atual.</p></div><div className="reports-grid"><section className="report-card"><span>Laudo territorial</span><h3>Análise de uma célula H3</h3><p>Score, risco, zoneamento e fatores que sustentam a recomendação.</p><label>Área incluída<select value={area?.h3_id || ''} onChange={event => setSelected(event.target.value)}>{rows.map(row => <option key={row.h3_id} value={row.h3_id}>{label(row)} · score {score(row).toFixed(0)}</option>)}</select></label><button className="report-download" onClick={download} disabled={!area}>Baixar relatório (.md)</button></section><aside className="report-preview"><span>Prévia</span><h3>{area ? label(area) : 'Sem áreas carregadas'}</h3>{area && <><div><strong>{score(area).toFixed(0)}</strong><small>score territorial</small></div><p>{area.explainability?.[0]?.value || 'Sem evidências disponíveis.'}</p></>}</aside></div></div>
}
