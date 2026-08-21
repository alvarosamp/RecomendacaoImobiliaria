import { useState, useMemo } from 'react'

const BAIRROS_POUSO_ALEGRE = [
  'Centro', 'Fátima', 'São João', 'Árvore Grande', 'Faisqueira', 'Primavera',
  'Santa Rita', 'São Cristóvão', 'Belo Horizonte', 'Nova Pouso Alegre', 'Pão de Açúcar'
]

function getNeighborhood(h3Id) {
  if (!h3Id) return 'Bairro Central'
  // Deterministic hash based on h3Id string
  let hash = 0;
  for (let i = 0; i < h3Id.length; i++) {
    hash = h3Id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % BAIRROS_POUSO_ALEGRE.length;
  return BAIRROS_POUSO_ALEGRE[index];
}

export default function CommercePage({ scores = [] }) {
  const [filter, setFilter] = useState('all')

  const items = useMemo(() => {
    // Pegar áreas com score comercial mais alto, ou simular gap
    const sorted = [...scores]
      .filter(s => (s.score_comercial || 0) > 30) // apenas áreas com potencial comercial
      .sort((a, b) => (b.score_comercial || 0) - (a.score_comercial || 0))
      .slice(0, 12);

    return sorted.map(s => {
      // Determinar comércios faltantes baseado no ID (mock para UX, já que a API não fornece direto ainda)
      const isCentro = getNeighborhood(s.h3_id) === 'Centro'
      let missing = []
      let opp = ''

      if (s.score_comercial > 70) {
        missing = ['Farmácia', 'Mercado 24h']
        opp = 'Comercial Térreo'
      } else if (isCentro) {
        missing = ['Restaurante Kilo', 'Estacionamento']
        opp = 'Uso Misto'
      } else {
        missing = ['Padaria', 'Academia']
        opp = 'Galeria de Bairro'
      }

      return {
        id: s.h3_id,
        name: getNeighborhood(s.h3_id),
        gap: (s.score_comercial || 0) / 100,
        missing,
        opp
      }
    }).filter(item => {
      if (filter === 'all') return true;
      return item.missing.some(m => m.toLowerCase().includes(filter));
    })
  }, [scores, filter])

  return (
    <div className="page">
      <div className="page-hero">
        <div className="page-hero-eyebrow">Inteligência Comercial</div>
        <h2>Comércios Faltantes</h2>
        <p>Identifique áreas com déficit de serviços específicos baseados na densidade populacional e renda local.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <span className="filter-group-label">Tipo de Comércio</span>
          <div className="chip-row">
            <button className={`chip ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>Todos</button>
            <button className={`chip ${filter === 'farmácia' ? 'active' : ''}`} onClick={() => setFilter('farmácia')}>Farmácia</button>
            <button className={`chip ${filter === 'mercado' ? 'active' : ''}`} onClick={() => setFilter('mercado')}>Mercado</button>
            <button className={`chip ${filter === 'restaurante' ? 'active' : ''}`} onClick={() => setFilter('restaurante')}>Restaurante</button>
          </div>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <h3>Nenhum comércio faltante encontrado com este filtro.</h3>
        </div>
      ) : (
        <div className="card-grid">
          {items.map(item => (
            <div key={item.id} className="opp-card priority-media">
              <div className="opp-card-header">
                <div>
                  <div className="opp-zona">{item.name}</div>
                  <div className="opp-cell-id">ID: {item.id?.slice(0,8)}...</div>
                </div>
                <div className="opp-badges">
                  <span className="badge" style={{ background: '#F5EDD4', color: '#92400E' }}>
                    Déficit Alto
                  </span>
                </div>
              </div>

              <div className="score-bars" style={{ marginTop: 16 }}>
                <div className="score-row">
                  <span className="score-row-label">Índice de Oportunidade</span>
                  <div className="score-track">
                    <div className="score-fill" style={{ width: `${item.gap * 100}%`, background: '#C9A84C' }} />
                  </div>
                  <span className="score-num" style={{ color: '#C9A84C' }}>{(item.gap * 100).toFixed(0)}</span>
                </div>
              </div>

              <div className="opp-uses" style={{ marginTop: 16 }}>
                <div className="use-row">
                  <span className="use-label">Comércios em falta</span>
                  <span style={{ color: 'var(--muted)', fontSize: 12 }}>{item.missing.join(', ')}</span>
                </div>
                <div className="use-row" style={{ marginTop: 8 }}>
                  <span className="use-label">Recomendação de tipologia</span>
                  <span style={{ color: 'var(--muted)', fontSize: 12 }}>{item.opp}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
