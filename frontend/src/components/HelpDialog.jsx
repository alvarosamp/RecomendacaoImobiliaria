import {useEffect,useRef,useState} from 'react'
import {DECISION_JOURNEYS} from '../config/decisionJourneys'
import {USAGE_GUIDES} from '../config/usageGuides'
import {ProductIcon} from './ProductVisuals'

export default function HelpDialog({profile,onClose,onNavigate}) {
 const dialogRef=useRef(null),headingRef=useRef(null)
 const [selectedProfile,setSelectedProfile]=useState(profile)
 const journey=DECISION_JOURNEYS[selectedProfile],guide=USAGE_GUIDES[selectedProfile]
 useEffect(()=>{
  const previous=document.activeElement,dialog=dialogRef.current
  dialog.showModal()
  dialog.querySelector('h1')?.focus({preventScroll:true})
  return ()=>{if(dialog.open)dialog.close();if(previous?.isConnected)previous.focus({preventScroll:true})}
 },[])
 useEffect(()=>{headingRef.current?.focus({preventScroll:true})},[selectedProfile])
 return <dialog ref={dialogRef} className="help-dialog help-by-activity" aria-labelledby="help-title" onClose={onClose}>
  <header className="help-dialog-heading"><div><span className="product-eyebrow">Uma explicação para cada atividade</span><h1 id="help-title" tabIndex={-1}>Como usar a Urbia</h1><p>Escolha sua atividade para ver o passo a passo.</p></div><button className="help-close" aria-label="Fechar como usar" onClick={()=>dialogRef.current.close()}>×</button></header>
  <div className="help-dialog-body">
   <div className="help-activity-options" role="group" aria-label="Como usar por atividade">{Object.entries(USAGE_GUIDES).map(([role,item])=><button key={role} aria-pressed={selectedProfile===role} onClick={()=>setSelectedProfile(role)}><ProductIcon name={DECISION_JOURNEYS[role].icon} size={19}/>{item.label}</button>)}</div>
   <section className="help-activity-content" aria-labelledby="help-activity-title" data-profile={selectedProfile}>
    <div className="help-activity-intro"><span className="product-eyebrow">{journey.name}</span><h2 ref={headingRef} id="help-activity-title" tabIndex={-1}>Como usar: {guide.label}</h2><p>{guide.purpose}</p><button className="product-button ink" onClick={()=>onNavigate('example',selectedProfile)}>Ver exemplo preenchido <ProductIcon name="arrow" size={18}/></button><small>Exemplo fictício de {journey.name}, separado dos trabalhos reais.</small></div>
    <section className="help-prepare"><h3>O que ter em mãos</h3><ul>{guide.prepare.map(item=><li key={item}>{item}</li>)}</ul></section>
    <ol className="help-steps">{guide.steps.map(([title,paragraphs],index)=><li key={title}><span className="help-step-number">{index+1}</span><div><h3>{title}</h3>{paragraphs.map(text=><p key={text}>{text}</p>)}</div></li>)}</ol>
    <section className="help-role-result"><h3>O que olhar no resultado</h3><ul>{guide.read.map(item=><li key={item}>{item}</li>)}</ul><p className="help-role-limit">{guide.limit}</p></section>
    <details className="help-worked-example"><summary>Exemplo explicado: {guide.example.title}</summary><p className="help-simulation-label">SIMULAÇÃO · valores e situações fictícios do demonstrativo.</p>{guide.example.lines.map(line=><p key={line}>{line}</p>)}</details>
    <details className="help-field-glossary"><summary>O que significam os campos deste ambiente?</summary><dl>{guide.glossary.map(([term,meaning])=><div key={term}><dt>{term}</dt><dd>{meaning}</dd></div>)}</dl></details>
    <details className="help-extra-functions"><summary>Outras funções de {guide.label}</summary><p>Em “Modo de trabalho”, selecione este ambiente para encontrar suas ferramentas complementares.</p><dl>{guide.tools.map(([name,how])=><div key={name}><dt>{name}</dt><dd>{how}</dd></div>)}</dl></details>
    <div className="help-role-start"><p>Pronto para preencher com suas informações?</p><button className="product-button ink" onClick={()=>onNavigate('new',selectedProfile)}>Começar em {journey.name} <ProductIcon name="arrow" size={18}/></button></div>
   </section>
   <section className="help-questions" aria-label="Salvar e retomar"><h2>Salvar, retomar e levar o relatório</h2><p>Use <strong>Salvar análise</strong> para guardar o preenchimento. Em <strong>Minhas análises → Meus trabalhos</strong>, escolha <strong>Continuar</strong> ou <strong>Ver resultado</strong>.</p><p>Para PDF, use <strong>Abrir relatório para PDF</strong>. No relatório, abra <strong>Imprimir</strong> no navegador e escolha <strong>Salvar como PDF</strong>.</p><button className="help-action" onClick={()=>onNavigate('library',selectedProfile)}>Abrir minhas análises <ProductIcon name="arrow" size={17}/></button><details><summary>Preciso preencher tudo de uma vez?</summary><p>Não. Dê um nome à análise e escolha a cidade para salvar o que já sabe. Campos em branco permanecem pendentes. Use zero apenas quando o valor for realmente zero.</p></details><details><summary>E se uma ferramenta estiver sem dados?</summary><p>Algumas funções dependem de fontes territoriais carregadas. Use os exemplos para conhecer o fluxo e confira quais fontes precisam ser disponibilizadas para sua análise real.</p></details></section>
   <p className="help-return-note">Consultar outro guia não muda seu modo de trabalho nem altera a análise aberta. Fechar a ajuda mantém seu rascunho; abrir outro trabalho pede confirmação se houver alterações não salvas.</p>
  </div>
 </dialog>
}
