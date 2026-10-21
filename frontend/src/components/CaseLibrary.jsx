import {useEffect,useState} from 'react'
import {DECISION_JOURNEYS,journeyForKind} from '../config/decisionJourneys'
import {ProductIcon} from './ProductVisuals'

const QUESTIONS = {
 incorpora:['O que construir neste terreno?','Compare duas propostas e seus custos.'],
 obras:['O que verificar antes de construir?','Organize vistorias e pendências do terreno.'],
 invest:['Qual imóvel cabe no meu orçamento?','Compare compra, reforma e revenda.'],
 mercado:['Como apresentar e discutir o preço?','Prepare a apresentação de um imóvel.'],
 negocios:['Qual ponto escolher para meu negócio?','Compare endereços, aluguel e visitas.'],
 governo:['Onde investigar atendimento escolar?','Organize regiões e próximas visitas.'],
}
export default function CaseLibrary({profile,items,demonstration,onFilter,onNew,onDemo,onOpen,loading,busy,error}) {
 const [choosing,setChoosing]=useState(false)
 const recommended=DECISION_JOURNEYS[profile]
 const savedItems=items.filter(item=>Boolean(item.demonstration)===demonstration)
 useEffect(()=>{document.querySelector('.main')?.scrollTo({top:0});document.querySelector('.decision-library h1')?.focus({preventScroll:true})},[choosing])
 if(choosing)return <section className="page decision-library simple-library">
  <button className="library-back" onClick={()=>setChoosing(false)}>← Voltar às minhas análises</button>
  <header className="page-header"><h1 tabIndex={-1}>O que você quer descobrir?</h1><p>Escolha uma opção. Vamos mostrar o que preencher.</p></header>
  <section className="case-type-picker simple-picker" aria-label="Escolha o tipo de decisão"><div>{Object.values(DECISION_JOURNEYS).map(choice=><button disabled={busy} aria-label={'Começar em '+choice.name} key={choice.kind} onClick={()=>onNew(choice.kind)}><span className="picker-icon"><ProductIcon name={choice.icon} size={27}/></span><strong>{QUESTIONS[choice.kind][0]}</strong><span>{QUESTIONS[choice.kind][1]}</span><small>{choice.name}<ProductIcon name="arrow" size={18}/></small></button>)}</div></section>
 </section>
 return <section className="page decision-library simple-library">
  <header className="library-heading"><div><h1 tabIndex={-1}>Minhas análises</h1><p>Comece uma análise ou continue de onde parou.</p></div><button disabled={busy} className="product-button ink" onClick={()=>setChoosing(true)}><span aria-hidden="true">+</span> Nova análise</button></header>
  <aside className="library-example-short"><span className="example-short-icon"><ProductIcon name="document" size={23}/></span><div><strong>Quer entender antes de começar?</strong><p>Veja um exemplo de {recommended.name.replace('Urbia ','')}, já preenchido com dados fictícios.</p></div><button disabled={busy} onClick={onDemo}>Ver exemplo preenchido <ProductIcon name="arrow" size={18}/></button></aside>
  {error&&<p role="alert" className="error-msg">{error}</p>}
  <section className="case-library-saved" aria-label="Suas análises salvas"><header><div className="case-library-filters" role="group" aria-label="Tipo de trabalho salvo"><button disabled={busy} aria-pressed={!demonstration} onClick={()=>onFilter(false)}>Meus trabalhos</button><button disabled={busy} aria-pressed={demonstration} onClick={()=>onFilter(true)}>Exemplos salvos</button></div><span className="library-count">{loading?'Buscando…':`${savedItems.length} ${savedItems.length===1?'análise':'análises'}`}</span></header>
   {loading?<p role="status">Buscando suas análises…</p>:!savedItems.length?<div className="case-library-empty"><ProductIcon name="document" size={32}/><h3>{demonstration?'Nenhum exemplo salvo.':'Nenhuma análise salva ainda.'}</h3><p>{demonstration?'Clique em “Ver exemplo preenchido” para conhecer uma análise pronta.':'Clique em “Nova análise” para começar. Não precisa preencher tudo de uma vez.'}</p></div>:<div className="case-saved-grid">{savedItems.map(item=>{const journey=journeyForKind(item.kind),state=item.stale?'stale':item.result?'ready':'draft';return <article key={item.id} className="case-saved-card" data-state={state}><span className="saved-analysis-icon"><ProductIcon name={journey?.icon} size={25}/></span><div className="saved-analysis-description"><h3>{item.title}</h3><p>{journey?.name||'Análise salva'}{item.demonstration?' · Dados fictícios':''}{item.can_edit===false?' · Somente leitura':''}</p></div><span className="saved-analysis-status"><i/>{item.stale?'Revisar dados':item.result?'Resultado pronto':'Falta preencher'}</span><button disabled={busy} aria-label={'Abrir análise: '+item.title} onClick={()=>onOpen(item.id)}>{item.result&&!item.stale?'Ver resultado':'Continuar'}<ProductIcon name="arrow" size={18}/></button></article>})}</div>}
  </section>
 </section>
}
