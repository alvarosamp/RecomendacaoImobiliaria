import { Link } from 'react-router-dom'
import { ProductIcon, TerritoryVisual } from '../components/ProductVisuals'

const ENVIRONMENTS = [
  { name: 'Incorpora', audience: 'Para incorporadoras', icon: 'building', desc: 'Do terreno à proposta que merece avançar.', delivery: 'Comparação de empreendimentos', color: 'sage' },
  { name: 'Obras', audience: 'Para construtoras', icon: 'tools', desc: 'Saiba o que verificar antes de construir.', delivery: 'Plano de investigação do terreno', color: 'sand' },
  { name: 'Invest', audience: 'Para investidores', icon: 'chart', desc: 'Coloque capital, prazo e cenários lado a lado.', delivery: 'Comparação de investimentos', color: 'blue' },
  { name: 'Mercado', audience: 'Para corretores', icon: 'home', desc: 'Transforme informações em uma boa conversa.', delivery: 'Apresentação comercial do imóvel', color: 'rose' },
  { name: 'Negócios', audience: 'Para empreendedores', icon: 'shop', desc: 'Compare pontos antes de escolher o endereço.', delivery: 'Comparação de pontos comerciais', color: 'lavender' },
  { name: 'Governo', audience: 'Para o setor público', icon: 'civic', desc: 'Organize onde investigar o atendimento escolar.', delivery: 'Agenda de investigação territorial', color: 'mint' },
]

export default function LandingPage() {
  return <div className="showcase">
    <nav className="showcase-nav" aria-label="Navegação principal">
      <Link to="/" className="product-brand"><span className="product-symbol"><ProductIcon name="building" /></span>urbia<span className="brand-period">.</span></Link>
      <div className="showcase-links"><a href="#ambientes">Os ambientes</a><a href="#como-funciona">Como funciona</a></div>
      <Link to="/login" className="product-button ink">Acessar plataforma <ProductIcon name="arrow" size={17} /></Link>
    </nav>
    <main>
      <section className="showcase-hero">
        <div className="showcase-hero-copy"><span className="product-eyebrow"><span className="live-dot" /> Inteligência para decisões sobre lugares</span>
          <h1>Um lugar.<br />Muitas possibilidades.<br /><em>Um próximo passo.</em></h1>
          <p>A Urbia organiza os dados de uma localização, explica o que importa para o seu objetivo e ajuda você a decidir o que fazer a seguir.</p>
          <div className="showcase-actions"><Link to="/login" className="product-button lime">Explorar a plataforma <ProductIcon name="arrow" size={19} /></Link><a href="#ambientes" className="showcase-text-link">Encontre seu ambiente <span>↗</span></a></div>
          <div className="showcase-territory"><ProductIcon name="pin" size={17} /><span>Começando por <strong>Pouso Alegre, MG</strong></span></div>
        </div>
        <div className="showcase-scene"><div className="scene-heading"><span>Um território, novas perspectivas</span><span className="scene-badge">Prévia ilustrativa</span></div><TerritoryVisual />
          <div className="scene-decision"><span className="scene-icon"><ProductIcon name="document" /></span><div><small>Mais clareza para avançar</small><strong>Da informação ao plano de ação.</strong><p>Compare alternativas. Entenda pendências.</p></div><span className="scene-check"><ProductIcon name="check" size={18} /></span></div>
        </div>
      </section>
      <section className="showcase-principles" aria-label="O que você leva da análise"><div><span>01</span><strong>Uma decisão por vez</strong><p>Perguntas próprias para o seu objetivo.</p></div><div><span>02</span><strong>Informação que faz sentido</strong><p>Motivos, fontes e lacunas à vista.</p></div><div><span>03</span><strong>Uma entrega para usar</strong><p>Síntese, relatório e próximas ações.</p></div></section>
      <section className="showcase-environments" id="ambientes"><div className="showcase-section-heading"><div><span className="product-eyebrow">Escolha sua perspectiva</span><h2>Seis ambientes.<br />Seis formas de avançar.</h2></div><p>Cada atividade tem suas perguntas.<br />E merece uma entrega própria.</p></div>
        <div className="environment-grid">{ENVIRONMENTS.map((env, index) => <Link to="/register" className={`environment-card tone-${env.color}`} key={env.name}><div className="environment-card-top"><span className="environment-icon"><ProductIcon name={env.icon} size={26} /></span><span className="environment-number">0{index+1}</span></div><small>{env.audience}</small><h3>Urbia {env.name}</h3><p>{env.desc}</p><div className="environment-delivery"><span>{env.delivery}</span><ProductIcon name="arrow" size={19} /></div></Link>)}</div>
      </section>
      <section className="showcase-process" id="como-funciona"><div><span className="product-eyebrow">Da pergunta à próxima ação</span><h2>Menos esforço para entender.<br />Mais clareza para decidir.</h2><p>Um caminho guiado, com o essencial primeiro. Fontes e memória de cálculo ficam disponíveis quando você quiser se aprofundar.</p><Link to="/register" className="product-button ink">Criar meu acesso <ProductIcon name="arrow" size={18}/></Link></div><ol>{[['Seu objetivo','Escolha o que você precisa decidir.'],['Informações essenciais','Preencha o que sabe, sem esconder o que falta.'],['Confira os dados','Revise a origem, as premissas e as pendências.'],['Sua análise','Entenda o resultado e organize a próxima ação.']].map(([title,desc],i)=><li key={title}><span>0{i+1}</span><div><h3>{title}</h3><p>{desc}</p></div></li>)}</ol></section>
      <section className="showcase-closing"><span className="product-eyebrow">Sua próxima decisão começa aqui</span><h2>Conheça a Urbia<br />com um caso demonstrativo.</h2><Link to="/login" className="product-button lime">Entrar na plataforma <ProductIcon name="arrow" size={19}/></Link><p>Exemplos identificados como simulação. Estudos reais dependem das fontes disponíveis.</p></section>
    </main>
    <footer className="showcase-footer"><span className="product-brand">urbia<span className="brand-period">.</span></span><p>Inteligência territorial. Decisões com contexto.</p><span>Pouso Alegre · MG</span></footer>
  </div>
}
