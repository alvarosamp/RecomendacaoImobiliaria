import { useMemo } from 'react'
import ConceptStudioPage from './ConceptStudioPage'

function bestOpportunity(scores) {
  return [...scores].sort((a, b) => {
    const aScore = Math.max(a.score_residencial || 0, a.score_comercial || 0)
    const bScore = Math.max(b.score_residencial || 0, b.score_comercial || 0)
    return bScore - aScore
  })[0]
}

export default function CaseStudyPage({ scores }) {
  const selected = useMemo(() => bestOpportunity(scores), [scores])
  if (!selected) {
    return (
      <div className="page">
        <div className="page-header">
          <h2>Estudo de Caso</h2>
          <p>Nenhuma oportunidade disponivel para montar o fluxo de apresentacao.</p>
        </div>
      </div>
    )
  }

  const score = Math.max(selected.score_residencial || 0, selected.score_comercial || 0)
  return (
    <div className="case-study-page">
      <section className="case-hero">
        <div>
          <span>Estudo de Caso TCC</span>
          <h2>{selected.zona || 'Area recomendada'}</h2>
          <p>Fluxo completo: recomendacao territorial, justificativa tecnica, cenario construtivo, conceito visual e relatorio.</p>
        </div>
        <div className="case-score">
          <strong>{score.toFixed(0)}</strong>
          <span>score territorial</span>
        </div>
      </section>

      <section className="case-flow">
        {['Mapa', 'Justificativa', 'Cenario', 'Imagem IA', 'Custo', 'Relatorio'].map((item, index) => (
          <div key={item}>
            <strong>{index + 1}</strong>
            <span>{item}</span>
          </div>
        ))}
      </section>

      <section className="case-explain">
        {(selected.explainability || []).map(item => (
          <div key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>

      <ConceptStudioPage seed={selected} />
    </div>
  )
}
