import {useEffect,useRef} from 'react'
import {DECISION_JOURNEYS} from '../config/decisionJourneys'
import {ProductIcon} from './ProductVisuals'

export default function HelpDialog({profile,onClose,onNavigate}) {
 const dialogRef=useRef(null),journey=DECISION_JOURNEYS[profile]
 useEffect(()=>{
  const previous=document.activeElement,dialog=dialogRef.current
  dialog.showModal()
  dialog.querySelector('h1')?.focus({preventScroll:true})
  return ()=>{if(dialog.open)dialog.close();if(previous?.isConnected)previous.focus({preventScroll:true})}
 },[])
 return <dialog ref={dialogRef} className="help-dialog" aria-labelledby="help-title" onClose={onClose}>
  <header className="help-dialog-heading"><div><span className="product-eyebrow">Um passo de cada vez</span><h1 id="help-title" tabIndex={-1}>Como usar a Urbia</h1><p>Veja um exemplo primeiro. Depois, use suas informações.</p></div><button className="help-close" aria-label="Fechar como usar" onClick={()=>dialogRef.current.close()}>×</button></header>
  <div className="help-dialog-body">
   <aside className="help-current-workspace"><ProductIcon name={journey.icon} size={25}/><div><strong>Seu ambiente: {journey.name}</strong><p>{journey.delivery}.</p></div></aside>
   <ol className="help-steps">
    <li><span className="help-step-number">1</span><div><h2>Conheça um exemplo pronto</h2><p>Abra uma análise já preenchida. Os valores são fictícios e ficam separados dos seus trabalhos reais.</p><button className="product-button ink" onClick={()=>onNavigate('example')}>Ver exemplo preenchido <ProductIcon name="arrow" size={18}/></button></div></li>
    <li><span className="help-step-number">2</span><div><h2>Comece uma análise sua</h2><p>Em <strong>Minhas análises</strong>, clique em <strong>Nova análise</strong> e escolha a pergunta que quer responder. Dê um nome ao trabalho e avance pelas etapas.</p><p className="help-preparation"><strong>Para {journey.name}:</strong> {journey.prepare}</p><button className="help-action" onClick={()=>onNavigate('new')}>Começar em {journey.name} <ProductIcon name="arrow" size={17}/></button></div></li>
    <li><span className="help-step-number">3</span><div><h2>Leia o resultado nesta ordem</h2><ul className="help-reading"><li><strong>O que encontramos</strong><span>A conclusão e os motivos.</span></li><li><strong>Pendências decisivas</strong><span>O que ainda precisa ser confirmado.</span></li><li><strong>Próxima ação</strong><span>O que fazer depois da análise.</span></li></ul><p>Na etapa <strong>Confira os dados</strong>, use o botão de análise para gerar o resultado. Informações ausentes aparecem como pendências.</p></div></li>
    <li><span className="help-step-number">4</span><div><h2>Salve e continue depois</h2><p>Clique em <strong>Salvar análise</strong>. Para retomar, abra <strong>Minhas análises → Meus trabalhos</strong> e escolha <strong>Continuar</strong> ou <strong>Ver resultado</strong>.</p><p>Quer levar a entrega para uma reunião? Use <strong>Abrir relatório para PDF</strong> e, no relatório, abra a opção <strong>Imprimir</strong> do navegador. Escolha <strong>Salvar como PDF</strong>.</p><button className="help-action" onClick={()=>onNavigate('library')}>Abrir minhas análises <ProductIcon name="arrow" size={17}/></button></div></li>
   </ol>
   <section className="help-questions" aria-label="Dúvidas comuns"><h2>Se surgir uma dúvida</h2><details><summary>Preciso preencher tudo de uma vez?</summary><p>Não. Dê um nome à análise e escolha a cidade para salvar o que já sabe. Campos em branco permanecem pendentes. Use zero apenas quando o valor for realmente zero.</p></details><details><summary>Como escolho outro tipo de análise?</summary><p>Em <strong>Minhas análises → Nova análise</strong>, escolha a pergunta mais próxima da sua necessidade. Há seis opções: Incorpora, Obras, Invest, Mercado, Negócios e Governo.</p></details><details><summary>Por que uma ferramenta do mapa está sem dados?</summary><p>Algumas ferramentas dependem de fontes territoriais carregadas. Quando elas não estiverem disponíveis, volte para <strong>Minhas análises</strong> e use os exemplos ou suas informações. Outras ferramentas ficam em <strong>Mais ferramentas</strong>, no menu.</p></details></section>
   <p className="help-return-note">Fechar este guia mantém você na tela em que estava. Se houver alterações não salvas, a Urbia pede confirmação antes de abrir outro trabalho.</p>
  </div>
 </dialog>
}
