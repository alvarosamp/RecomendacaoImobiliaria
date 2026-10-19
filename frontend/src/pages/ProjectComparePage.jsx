import { useEffect, useState } from 'react'
import { fetchProjects } from '../api'
const money = value => value == null ? 'Não disponível' : Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})
const technical = {evidence_pending:'Evidências pendentes',constraints_reported:'Indisponibilidades declaradas',ready_for_review:'Informações preenchidas para revisão',not_requested:'Não solicitado'}
const legal = {allowed:'Permitido na triagem',conditioned:'Condicionado',blocked:'Bloqueado',analisar:'Requer análise'}
const business = {criteria_pending:'Critérios incompletos',territorial_data_pending:'Dados territoriais pendentes',ready_for_market_research:'Triagem para pesquisa de mercado',not_requested:'Não solicitado'}
const metrics = [
 ['Setor comercial',project=>project.analysis?.business?.sector_label || 'Não solicitado'],
 ['Triagem comercial',project=>business[project.analysis?.business?.status] || 'Análise pendente'],
 ['População estimada na célula',project=>project.analysis?.business?.population_estimate ?? 'Não disponível'],
 ['Estabelecimentos do setor mapeados',project=>project.analysis?.business?.mapped_establishments ?? 'Não disponível'],
 ['Menor distância ao serviço (m)',project=>project.analysis?.business?.nearest_distance_m ?? 'Não disponível'],
 ['Critério de população mínima',project=>project.analysis?.business?.assumptions?.minimum_population ?? 'Não informado'],
 ['Critério de distância mínima ao serviço (m)',project=>project.analysis?.business?.assumptions?.distance_reference_m ?? 'Não informado'],
 ['Data dos critérios comerciais',project=>project.analysis?.business?.assumptions?.reference_date || 'Não informada'],
 ['Justificativa dos critérios comerciais',project=>project.analysis?.business?.assumptions?.criteria_note || 'Não informada'],
 ['Área do terreno informada (m²)',project=>project.premises?.lotArea ?? 'Não informada'],
 ['Área construída informada (m²)',project=>project.premises?.buildArea ?? 'Não informada'],
 ['Área vendável financeira (m²)',project=>project.analysis?.financial?.assumptions?.saleable_area_m2 ?? 'Não informada'],
 ['Origem das premissas financeiras',project=>project.analysis?.financial?.assumptions?.source_note || 'Não informada'],
 ['Revisão',project=>project.revision],['Região',project=>project.h3_id || 'Não selecionada'],['Uso pretendido',project=>project.intended_use],
 ['Captura dos dados',project=>project.analysis?.captured_at ? new Date(project.analysis.captured_at).toLocaleString('pt-BR') : 'Análise pendente'],
 ['Modo da análise',project=>!project.analysis ? 'Análise pendente' : project.analysis.mode === 'premises_only' ? 'Somente premissas declaradas' : 'Contexto territorial consultado'],
 ['Triagem legal',project=>legal[project.analysis?.legal?.status] || 'Análise pendente'],
 ['Evidências técnicas',project=>technical[project.analysis?.technical?.status] || 'Não solicitado ou sem análise'],
 ['Referência financeira',project=>project.analysis?.financial?.assumptions?.reference_date || 'Não informada'],
 ['Prazo financeiro (meses)',project=>project.analysis?.financial?.assumptions?.months ?? 'Não informado'],
 ...[['Custo total','total_cost'],['Receita líquida','net_revenue'],['Lucro estimado','profit'],['VPL','npv']].map(([label,key])=>[label,project=>money(project.analysis?.financial?.scenarios?.[0]?.[key])]),
 ['Taxa anual de desconto',project=>project.analysis?.financial?.assumptions?.annual_discount_pct == null ? 'Não informada' : `${project.analysis.financial.assumptions.annual_discount_pct}%`],
]
export default function ProjectComparePage() {
 const [projects,setProjects]=useState([]),[ids,setIds]=useState(['','','']),[error,setError]=useState(''),[loading,setLoading]=useState(true)
 useEffect(()=>{let active=true;fetchProjects().then(rows=>{if(active)setProjects(rows)}).catch(err=>{if(active)setError(err.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[])
 const chosen=ids.map(id=>projects.find(project=>String(project.id)===id)).filter(Boolean)
 const exportReport=()=>{
  const lines=['# Comparação de estudos salvos — Urbia',`Gerado em: ${new Date().toISOString()}`,'Comparação descritiva de capturas salvas. Verifique datas, taxas, áreas e pendências; nenhum estudo é declarado vencedor.']
  for(const project of chosen){lines.push('',`## ${project.name}`,...metrics.map(([label,value])=>`- ${label}: ${value(project)}`))}
  const url=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/markdown;charset=utf-8'}));Object.assign(document.createElement('a'),{href:url,download:'urbia-comparacao-estudos.md'}).click();setTimeout(()=>URL.revokeObjectURL(url),1000)
 }
 return <section className="page"><div className="page-header"><div className="page-eyebrow">Decisão comparativa</div><h2>Comparar estudos salvos</h2><p>Compare até três projetos pessoais ou de equipes. Os resultados correspondem à última análise salva, sem recálculo automático. Datas, áreas e taxas diferentes limitam a comparação.</p></div>
  {loading && <p role="status">Carregando estudos…</p>}{error && <p className="error-msg" role="alert">{error}</p>}
  <div className="study-fields">{ids.map((id,index)=><label key={index}>Estudo {index+1}<select aria-label={`Estudo ${index+1}`} value={id} onChange={event=>setIds(current=>current.map((value,i)=>i===index?event.target.value:value))}><option value="">Selecione um estudo</option>{projects.map(project=><option key={project.id} value={project.id} disabled={ids.some((value,i)=>i!==index&&value===String(project.id))}>{project.name} · revisão {project.revision}</option>)}</select></label>)}</div>
  {!loading && !projects.length && !error && <p>Salve um projeto pessoal ou obtenha acesso a estudos de uma equipe para comparar.</p>}
  {chosen.length>0 && <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Indicador</th>{chosen.map(project=><th key={project.id}>{project.name}</th>)}</tr></thead><tbody>{metrics.map(([label,value])=><tr key={label}><td>{label}</td>{chosen.map(project=><td key={project.id}>{value(project)}</td>)}</tr>)}</tbody></table></div>}
  <button className="report-download" disabled={chosen.length<2} onClick={exportReport}>Baixar comparação (.md)</button>
 </section>
}
