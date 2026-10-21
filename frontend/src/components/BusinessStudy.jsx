const RESULTS={criteria_pending:'Critérios incompletos',territorial_data_pending:'Dados territoriais pendentes',ready_for_market_research:'Triagem disponível para pesquisa de mercado'}
const CHECKS={unknown:'Não verificado',criterion_met:'Atende ao critério escolhido',criterion_not_met:'Não atende ao critério escolhido'}
const MISSING={minimum_population:'população mínima',distance_reference_m:'distância de referência',criteria_note:'justificativa dos critérios',reference_date:'data de referência'}
const fmt=value=>value==null?'Não disponível':Number(value).toLocaleString('pt-BR',{maximumFractionDigits:1})
export function BusinessPremises({value,onChange,disabled}){
 const set=(key,next)=>onChange({...value,[key]:next})
 return <fieldset className="study-fields" disabled={disabled}><legend>Localização comercial</legend><label className="financial-toggle"><input type="checkbox" checked={value!=null} onChange={event=>onChange(event.target.checked?{}:null)} />Incluir critérios de localização comercial</label>
 {value!=null&&<><label>Setor comercial<select aria-label="Setor comercial" value={value.sector||'pharmacy'} onChange={event=>set('sector',event.target.value)}><option value="pharmacy">Farmácia</option><option value="market">Mercado</option></select></label>
 <label>População mínima estimada na célula<input type="number" min="0" max="1000000000" step="any" value={value.minimum_population??''} onChange={event=>set('minimum_population',event.target.value===''?null:Number(event.target.value))} /></label>
 <label>Referência de distância ao serviço (m)<input type="number" min="100" max="50000" step="any" value={value.distance_reference_m??''} onChange={event=>set('distance_reference_m',event.target.value===''?null:Number(event.target.value))} /></label>
 <label>Data dos critérios comerciais<input type="date" value={value.reference_date||''} onChange={event=>set('reference_date',event.target.value||null)} /></label>
 <label className="study-notes">Justificativa dos critérios comerciais<textarea rows={3} maxLength={4000} value={value.criteria_note||''} onChange={event=>set('criteria_note',event.target.value)} /></label>
 <p className="study-notes">Os limites orientam investigação. Não representam demanda medida ou previsão de vendas. A população da célula não é uma área de influência comercial.</p></>}
 </fieldset>
}
export function BusinessResults({result}){
 if(!result||result.status==='not_requested')return null
 return <section className="financial-results"><h3>Triagem de localização comercial</h3><p><strong>{RESULTS[result.status]}</strong> · {result.sector_label}. Não constitui recomendação de abertura ou previsão de faturamento.</p>
 {!!result.missing_criteria.length&&<p>Critérios pendentes: {result.missing_criteria.map(key=>MISSING[key]||key).join(', ')}.</p>}{!!result.missing_data.length&&<p>Dados a obter: {result.missing_data.join(', ')}.</p>}
 <div className="workspace-grid"><article className="workspace-card"><h4>Indicadores do recorte</h4><p>População estimada: {fmt(result.population_estimate)}</p><p>Estabelecimentos mapeados: {fmt(result.mapped_establishments)}</p><p>Menor distância ao serviço: {fmt(result.nearest_distance_m)} m</p></article><article className="workspace-card"><h4>Critérios escolhidos</h4><ul>{result.checks.map(item=><li key={item.label}>{item.label}: {CHECKS[item.status]}</li>)}</ul></article></div>
 {!!result.alerts.length&&<ul>{result.alerts.map(item=><li key={item}>{item}</li>)}</ul>}
 <details><summary>Critérios e limites da triagem comercial</summary><p>Referência: {result.assumptions.reference_date||'Não informada'} · {result.assumptions.criteria_note||'Justificativa pendente'}</p><p>Processamento dos indicadores: {result.processing_timestamp||'Não disponível'}. Essa data não equivale à coleta dos estabelecimentos.</p><ul>{result.limitations.map(item=><li key={item}>{item}</li>)}</ul></details>
 </section>
}
