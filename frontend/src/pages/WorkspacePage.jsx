import { WORKSPACES } from '../config/workspaces'
import { ProductIcon, TerritoryVisual } from '../components/ProductVisuals'

const PRIMARY={
 incorporadora:['Comparar propostas','Compare duas propostas de empreendimento e descubra quais premissas precisam de confirmação.'],
 construtora:['Preparar investigação','Transforme pendências técnicas do terreno em tarefas com responsável, prazo e evidência.'],
 investidor:['Comparar investimentos','Compare capital inicial, cenários de compra e revenda e compatibilidade com seu orçamento.'],
 corretor:['Apresentar imóvel','Prepare argumentos para captação ou negociação com referências de preço e perguntas ao proprietário.'],
 empreendedor:['Comparar pontos','Compare custos e observações de visita antes de aprofundar a escolha de um ponto comercial.'],
 governo:['Priorizar visitas','Organize regiões, justificativas e tarefas para investigar atendimento escolar.'],
}
const PRESENTATION = {
 incorporadora: { icon:'building', tone:'sage', title:'Dê forma à próxima oportunidade.', output:'Comparação de propostas', items:['Duas alternativas lado a lado','Premissas financeiras à vista','Restrições e próximos passos'] },
 construtora: { icon:'tools', tone:'sand', title:'Avance com as perguntas certas.', output:'Plano de investigação', items:['Verificações técnicas prioritárias','Responsáveis, prazos e evidências','Pendências que viram ações'] },
 investidor: { icon:'chart', tone:'blue', title:'Enxergue o investimento por inteiro.', output:'Quadro de investimento', items:['Até três alternativas de compra','Capital necessário e cenários','Compatibilidade com seu orçamento'] },
 corretor: { icon:'home', tone:'rose', title:'Uma boa apresentação começa nos dados.', output:'Apresentação comercial', items:['Comparáveis e diferenças relevantes','Argumentos e pontos de atenção','Perguntas para o proprietário'] },
 empreendedor: { icon:'shop', tone:'lavender', title:'Seu negócio começa pela localização.', output:'Comparação de pontos', items:['Até três endereços para comparar','Custos e condições observadas','Roteiro para a próxima visita'] },
 governo: { icon:'civic', tone:'mint', title:'Um olhar mais atento para a cidade.', output:'Agenda de investigação', items:['Regiões escolhidas com justificativa','Evidências e limitações dos dados','Visitas com responsáveis definidos'] },
}
export default function WorkspacePage({ profile, onStart, onPrimary, disabled = false }) {
  const workspace = WORKSPACES[profile], presentation = PRESENTATION[profile]
  return (
    <section className={`workspace-page workspace-refresh tone-${presentation.tone}`}>
      <div className="workspace-topline"><span>Seu espaço de decisão</span><span><ProductIcon name="pin" size={15} /> Pouso Alegre · MG <small>Cobertura parcial</small></span></div>
      <header className="workspace-intro"><span className="workspace-product"><ProductIcon name={presentation.icon} size={19} />{workspace.name}</span><h1>{presentation.title}</h1><p>{PRIMARY[profile][1]}</p></header>
      <div className="workspace-main-grid">
        <section className="workspace-launch"><span className="product-eyebrow">Sua próxima análise</span><h2>{PRIMARY[profile][0]}</h2><p>Um caminho guiado para transformar as informações que você tem em uma decisão mais clara.</p><ol className="workspace-mini-steps">{['Objetivo','Informações','Conferência','Sua análise'].map((step,i)=><li key={step}><span>{i+1}</span>{step}</li>)}</ol><button className="product-button ink" disabled={disabled} onClick={onPrimary}>{PRIMARY[profile][0]}<ProductIcon name="arrow" size={19}/></button><small>Você pode começar com um exemplo demonstrativo.</small></section>
        <aside className="workspace-delivery"><div className="delivery-visual"><TerritoryVisual compact/><span><ProductIcon name="document" size={23}/></span></div><div className="delivery-copy"><span className="product-eyebrow">O que você vai levar</span><h2>{presentation.output}</h2><ul>{presentation.items.map(item=><li key={item}><ProductIcon name="check" size={17}/>{item}</li>)}</ul><div className="delivery-format"><ProductIcon name="document" size={16}/> Síntese na tela + relatório para PDF</div></div></aside>
      </div>
      <details className="workspace-secondary"><summary>Ferramentas e pesquisas complementares <span aria-hidden="true">+</span></summary>
      <p className="workspace-secondary-intro">Aprofunde uma questão específica com as ferramentas do seu ambiente.</p>
      <div className="workspace-grid">
        {workspace.journeys.map(journey => (
          <article className="workspace-card" key={journey.id}>
            <h3>{journey.title}</h3><p>{journey.description}</p>
            <ol>{journey.steps.map(([page, label]) => <li key={`${page}-${label}`}>{label}</li>)}</ol>
            <p className="workspace-result"><strong>Resultado esperado</strong><br />{journey.result}</p>
            <button disabled={disabled} onClick={() => onStart(journey)}>Iniciar análise <span aria-hidden="true">→</span></button>
          </article>
        ))}
      </div>
      </details>
      <aside className="workspace-note"><ProductIcon name="document" size={18}/><p><strong>Clareza também é saber o que falta.</strong> As análises são preliminares. Confira fontes, pendências e restrições antes de tomar uma decisão.</p></aside>
    </section>
  )
}

export function JourneyNavigation({ journey, page, onNavigate, onClose }) {
  return (
    <nav className="journey-nav" aria-label={`Etapas: ${journey.title}`}>
      <div className="journey-heading"><strong>{journey.title}</strong><button onClick={onClose}>Voltar ao início</button></div>
      <ol>{journey.steps.map(([id, label], index) => (
        <li key={`${id}-${label}`}><button aria-current={page === id ? 'step' : undefined} onClick={() => onNavigate(id)}>{index + 1}. {label}</button></li>
      ))}</ol>
      <p>{journey.result}</p>
    </nav>
  )
}
