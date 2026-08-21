import { Link } from 'react-router-dom'

const FEATURES = [
  {
    icon: '🗺',
    title: 'Mapa de oportunidades',
    desc: 'Visualize cada área da cidade com scores residenciais e comerciais, zoneamento e indicadores de crescimento urbano.',
  },
  {
    icon: '📊',
    title: 'Score territorial explicado',
    desc: 'Cada recomendação vem acompanhada de fatores positivos, negativos, restrições legais e dados utilizados. Nada de caixa-preta.',
  },
  {
    icon: '⚖️',
    title: 'Plano Diretor integrado',
    desc: 'Regras urbanísticas verificadas automaticamente. Áreas bloqueadas ou condicionadas são sinalizadas antes de qualquer recomendação.',
  },
  {
    icon: '💰',
    title: 'Avaliação de imóvel',
    desc: 'Estimativa de preço por modelo treinado em dados reais de mercado, enriquecido com features geoespaciais da cidade.',
  },
  {
    icon: '🏪',
    title: 'Comércios faltantes',
    desc: 'Identifique quais serviços estão ausentes em cada região e por que aquele local é uma oportunidade comercial.',
  },
  {
    icon: '👥',
    title: 'Lead Scoring',
    desc: 'Priorize clientes com maior probabilidade de conversão, baseado em orçamento, perfil e comportamento de busca.',
  },
]

const PROFILES = [
  { icon: '🏗', title: 'Incorporadoras', desc: 'Encontre terrenos e zonas com alto potencial construtivo e permissividade legal.' },
  { icon: '📐', title: 'Investidores', desc: 'Análise de risco, crescimento e valorização para decisões de alocação de capital.' },
  { icon: '🏡', title: 'Corretores', desc: 'Apresente dados concretos aos clientes e identifique leads mais qualificados.' },
  { icon: '🏛', title: 'Poder Público', desc: 'Mapeie carências de serviços, expansão urbana e impacto de zoneamento.' },
]

function StatBar() {
  return (
    <div className="landing-stats">
      <div className="landing-stat">
        <span className="landing-stat-value">H3</span>
        <span className="landing-stat-label">Grade hexagonal de análise</span>
      </div>
      <div className="landing-stat">
        <span className="landing-stat-value">22+</span>
        <span className="landing-stat-label">Zonas urbanas reconhecidas</span>
      </div>
      <div className="landing-stat">
        <span className="landing-stat-value">10+</span>
        <span className="landing-stat-label">Camadas de dados integradas</span>
      </div>
      <div className="landing-stat">
        <span className="landing-stat-value">100%</span>
        <span className="landing-stat-label">Explicável e auditável</span>
      </div>
    </div>
  )
}

export default function LandingPage() {
  return (
    <div className="landing">
      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <div className="landing-nav-logo">Ur</div>
          <span className="landing-nav-name">Urbia</span>
        </div>
        <div className="landing-nav-actions">
          <a href="#funcionalidades" className="landing-nav-link">Funcionalidades</a>
          <a href="#para-quem" className="landing-nav-link">Para quem</a>
          <Link to="/login" className="landing-btn-outline">Entrar</Link>
          <Link to="/register" className="landing-btn-primary">
            Começar agora
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 7h10M8 3l4 4-4 4"/>
            </svg>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section>
        <div className="landing-hero">
          <div className="landing-hero-bg" />
          <div className="landing-hex-bg" />

          <div className="landing-hero-eyebrow">Inteligência territorial</div>

          <h1>
            Decida com dados<br />
            onde <em>realmente</em><br />
            vale investir.
          </h1>

          <p className="landing-hero-desc">
            Urbia combina mapas urbanos, Plano Diretor, sensoriamento remoto e
            dados de mercado para mostrar o potencial real de cada área de qualquer cidade.
          </p>

          <div className="landing-hero-actions">
            <Link to="/register" className="landing-hero-btn-primary">
              Acessar a plataforma
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 8h10M9 4l4 4-4 4"/>
              </svg>
            </Link>
            <Link to="/login" className="landing-hero-btn-secondary">
              Já tenho conta
            </Link>
          </div>

          <StatBar />
        </div>
      </section>

      {/* Features */}
      <section id="funcionalidades" className="landing-features">
        <div className="landing-features-inner">
          <div className="landing-section-label">Funcionalidades</div>
          <h2>Tudo que você precisa para<br />analisar uma cidade.</h2>

          <div className="landing-features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="landing-feature-card">
                <div className="landing-feature-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Profiles */}
      <section id="para-quem" className="landing-profiles">
        <div className="landing-section-label">Para quem</div>
        <h2>Uma ferramenta,<br />múltiplos perfis.</h2>
        <p>O mesmo dado, visto do ângulo certo para cada decisão.</p>
        <div className="landing-profiles-grid">
          {PROFILES.map(p => (
            <div key={p.title} className="landing-profile-card">
              <div className="landing-profile-card-icon">{p.icon}</div>
              <h4>{p.title}</h4>
              <p>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="landing-cta">
        <div className="landing-cta-inner">
          <h2>Pronto para analisar sua cidade?</h2>
          <p>Acesse a plataforma, selecione sua cidade e explore as oportunidades do território com dados reais.</p>
          <div className="landing-cta-actions">
            <Link to="/register" className="landing-hero-btn-primary">
              Criar conta gratuita
            </Link>
            <Link to="/login" className="landing-hero-btn-secondary">
              Já tenho acesso
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-brand">
          <div className="landing-nav-logo" style={{ width: 24, height: 24, fontSize: 10, borderRadius: 5 }}>Ur</div>
          Urbia
        </div>
        <span className="landing-footer-copy">Plataforma de inteligência territorial · Dados geoespaciais + Plano Diretor + Mercado imobiliário</span>
      </footer>
    </div>
  )
}
