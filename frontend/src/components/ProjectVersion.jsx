import { BusinessResults } from './BusinessStudy'
import { TechnicalResults } from './TechnicalStudy'
import { FinancialResults } from './FinancialStudy'
const LABELS = {
 name:'Nome',h3_id:'Região de referência',intended_use:'Uso pretendido',notes:'Observações',
 premises:'Terreno',financial:'Financeiro',technical:'Evidências técnicas',business:'Critérios comerciais',
 lotArea:'Área do terreno (m²)',frontage:'Testada (m)',buildArea:'Área construída (m²)',floors:'Pavimentos',
 typology:'Tipologia',finish:'Acabamento',style:'Estilo',zone:'Zona',neighborhood:'Bairro',latitude:'Latitude',longitude:'Longitude',
 residentialScore:'Indicador residencial informado',commercialScore:'Indicador comercial informado',riskLevel:'Risco informado',
 riskConfidence:'Confiança informada',riskAlert:'Alerta informado',growthSignal:'Sinal de crescimento informado',predictedMarketPrice:'Preço informado',
 land_cost:'Aquisição do terreno (R$)',construction_cost_m2:'Construção por m² (R$)',other_costs:'Outros custos (R$)',
 contingency_pct:'Contingência (%)',saleable_area_m2:'Área vendável (m²)',sale_price_m2:'Venda por m² (R$)',
 sales_expenses_pct:'Despesas de venda (%)',months:'Prazo (meses)',annual_discount_pct:'Taxa anual de desconto (%)',
 cost_variation_pct:'Variação do custo (%)',price_variation_pct:'Variação do preço (%)',source_note:'Origem declarada',reference_date:'Data de referência',
 slope_pct:'Declividade (%)',road_access:'Acesso viário',water:'Água',sewer:'Esgoto',power:'Energia',drainage:'Drenagem',
 registry_reference:'Referência cadastral',topography_reference:'Referência topográfica',geotechnical_reference:'Referência geotécnica',
 sector:'Setor',minimum_population:'População mínima',distance_reference_m:'Distância mínima ao serviço (m)',criteria_note:'Justificativa',
}
const VALUES={unknown:'Desconhecido',reported_available:'Disponível segundo declaração',reported_unavailable:'Indisponível segundo declaração',pharmacy:'Farmácia',market:'Mercado'}
const label=field=>field.split('.').map(key=>LABELS[key]||key).join(' · ')
const value=data=>data==null?'Não informado':typeof data==='object'?Object.entries(data).map(([key,next])=>`${LABELS[key]||key}: ${value(next)}`).join('\n'):data===''?'Não preenchido':VALUES[data]||String(data)
export default function ProjectVersion({version,canRestore,onRestore,onClose}){
 return <section className="project-version" aria-label={`Conteúdo da revisão ${version.revision}`}>
  <div className="study-toolbar"><h4>Conteúdo da revisão {version.revision}</h4><button onClick={onClose}>Fechar revisão</button></div>
  <p><strong>{version.name}</strong> · conteúdo preservado em {new Date(version.saved_at).toLocaleString('pt-BR')}.</p>
  <p>Comparação com a revisão {version.current_revision} salva. Edições ainda não salvas não entram nesta comparação.</p>
  {version.differences.length ? <div className="comparison-table-wrap"><table className="comparison-table version-differences"><caption>Diferenças de premissas</caption><thead><tr><th>Campo</th><th>Revisão {version.revision}</th><th>Atual salva ({version.current_revision})</th></tr></thead><tbody>{version.differences.map(item=><tr key={item.field}><td>{label(item.field)}</td><td><pre>{value(item.historical)}</pre></td><td><pre>{value(item.current)}</pre></td></tr>)}</tbody></table></div> : <p>As premissas desta revisão são iguais às atuais salvas.</p>}
  <details><summary>Ver todas as premissas preservadas</summary><dl>{Object.entries(version.inputs).map(([key,data])=><div key={key}><dt>{LABELS[key]||key}</dt><dd>{data&&typeof data==='object'?<dl>{Object.entries(data).map(([field,next])=><div key={field}><dt>{LABELS[field]||field}</dt><dd>{value(next)}</dd></div>)}</dl>:value(data)}</dd></div>)}</dl></details>
  {version.analysis ? <p className="study-caution">Esta revisão contém uma análise histórica de {new Date(version.analysis.captured_at).toLocaleString('pt-BR')}. Recuperar premissas não recupera nem atualiza essa análise.</p> : <p>Esta revisão não possui análise salva.</p>}
  {version.analysis&&<details><summary>Consultar resultados históricos (sem recálculo)</summary><p>Triagem legal histórica: {({allowed:'Permitido na triagem',conditioned:'Condicionado',blocked:'Bloqueado',analisar:'Requer análise'})[version.analysis.legal?.status]||'Não informada'}. {version.analysis.legal?.notes}</p><ul>{(version.analysis.legal?.sources||[]).map((source,index)=><li key={index}>{source.title}{source.url&&<> · <a href={source.url} target="_blank" rel="noreferrer">Consultar fonte</a></>}</li>)}</ul><BusinessResults result={version.analysis.business}/><TechnicalResults result={version.analysis.technical}/><FinancialResults result={version.analysis.financial}/></details>}
  {version.revision!==version.current_revision&&<><p>A recuperação cria uma nova revisão, mantém o compartilhamento atual e deixa a análise pendente de novo cálculo.</p><button disabled={!canRestore} onClick={()=>{if(window.confirm(`Recuperar as premissas da revisão ${version.revision}? Isso criará uma nova revisão, manterá a equipe atual e deixará a análise pendente.`))onRestore(version.revision)}}>Recuperar premissas desta revisão</button></>}
 </section>
}
