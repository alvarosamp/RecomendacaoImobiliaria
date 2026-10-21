// Workspaces describe decisions, not authorization. Access remains enforced by the API.
export const WORKSPACES = {
  investidor: {
    name: 'Urbia Invest', title: 'Onde investir com mais informação?',
    description: 'Compare regiões, investigue riscos e reúna evidências antes de investir.',
    journeys: [
      { id: 'investimento', title: 'Comparar regiões para investir', description: 'Da seleção de oportunidades ao relatório de apoio à decisão.', result: 'Comparação territorial com justificativas e riscos.', steps: [['opportunities', 'Selecionar oportunidades'], ['map', 'Investigar localização'], ['compare', 'Comparar áreas'], ['legal', 'Consultar restrições'], ['reports', 'Preparar relatório']] },
      { id: 'preco', title: 'Estimar o preço de um imóvel', description: 'Explore uma estimativa e confira o contexto territorial.', result: 'Estimativa de preço e contexto da localização.', steps: [['valuation', 'Estimar preço'], ['map', 'Examinar entorno'], ['score', 'Entender os indicadores']] },
    ],
  },
  corretor: {
    name: 'Urbia Mercado', title: 'Qual decisão comercial você precisa apoiar?',
    description: 'Conecte avaliações, conhecimento da região e qualificação de clientes.',
    journeys: [
      { id: 'captacao', title: 'Preparar uma avaliação comercial', description: 'Estime preço, compare o entorno e prepare os argumentos para o cliente.', result: 'Avaliação exploratória com evidências territoriais.', steps: [['valuation', 'Estimar preço'], ['map', 'Conhecer a localização'], ['compare', 'Comparar regiões'], ['reports', 'Preparar apresentação']] },
      { id: 'clientes', title: 'Qualificar clientes e oportunidades', description: 'Organize leads e investigue oportunidades relevantes.', result: 'Leads qualificados e oportunidades para investigação.', steps: [['leads', 'Qualificar leads'], ['opportunities', 'Explorar oportunidades'], ['legal', 'Consultar restrições']] },
    ],
  },
  incorporadora: {
    name: 'Urbia Incorpora', title: 'Onde e o que desenvolver?',
    description: 'Investigue terrenos, restrições urbanísticas e cenários preliminares de empreendimento.',
    journeys: [
      { id: 'terreno', title: 'Estudar a viabilidade de um terreno', description: 'Investigue a região, consulte restrições e compare cenários de implantação.', result: 'Estudo preliminar de implantação; requer validação técnica e urbanística.', steps: [['study', 'Selecionar terreno e região'], ['study', 'Registrar premissas'], ['study', 'Consultar restrições e comparar cenários'], ['study', 'Gerar relatório integrado']] },
      { id: 'prospeccao', title: 'Prospectar regiões para empreender', description: 'Compare oportunidades e indicadores antes de selecionar um terreno.', result: 'Seleção inicial de regiões para aprofundar o estudo.', steps: [['opportunities', 'Encontrar regiões'], ['score', 'Examinar fatores'], ['compare', 'Comparar alternativas']] },
    ],
  },
  construtora: {
    name: 'Urbia Obras', title: 'O que falta verificar antes de construir?',
    description: 'Reúna evidências de terreno, infraestrutura e levantamentos para apoiar a revisão técnica.',
    journeys: [
      { id:'tecnico', title:'Organizar a investigação de um terreno', description:'Registre evidências de acesso, infraestrutura, topografia e solo, com origem e pendências.', result:'Dossiê preliminar para revisão por responsável técnico.', steps:[['study','Selecionar região e registrar evidências'],['study','Investigar pendências técnicas'],['study','Consultar restrições e cenários'],['study','Exportar o estudo']] },
      { id:'alternativas', title:'Comparar estudos de terrenos', description:'Confronte capturas salvas com suas restrições, pendências e premissas financeiras.', result:'Comparação descritiva de até três estudos, sem aprovação automática.', steps:[['project-compare','Escolher estudos salvos'],['project-compare','Conferir datas, premissas e pendências'],['project-compare','Exportar comparação']] },
    ],
  },
  empreendedor: {
    name:'Urbia Negócios', title:'Onde investigar uma nova localização comercial?',
    description:'Explore oferta de serviços e contexto territorial antes de aprofundar um estudo de mercado.',
    journeys:[
      { id:'localizacao', title:'Investigar regiões para um negócio', description:'Examine a cobertura de serviços, a localização e os usos estruturados.', result:'Triagem exploratória; demanda, concorrência e faturamento exigem pesquisa própria.', steps:[['study','Escolher região e setor'],['study','Definir critérios comerciais'],['study','Conferir dados e restrições'],['study','Exportar triagem e pendências']] },
      { id:'comparar', title:'Comparar estudos imobiliários salvos', description:'Compare projetos relacionados à escolha de localização ou aquisição de imóvel.', result:'Comparação de estudos de terrenos; não é projeção operacional de um negócio.', steps:[['project-compare','Selecionar estudos'],['project-compare','Conferir premissas'],['project-compare','Exportar comparação']] },
    ],
  },
  governo: {
    name: 'Urbia Governo', title: 'Que necessidade da cidade você quer investigar?',
    description: 'Explore a oferta de serviços e o território para apoiar o planejamento público.',
    journeys: [
      { id: 'equipamentos', title: 'Investigar carências de equipamentos públicos', description: 'Examine escolas e saúde no mapa e compare regiões para investigação.', result: 'Diagnóstico exploratório de oferta e acesso. População e capacidade precisam ser validadas.', steps: [['government', 'Definir necessidade e distância de referência'], ['government', 'Priorizar investigação com dados disponíveis'], ['government', 'Examinar explicações e fontes'], ['government', 'Exportar diagnóstico']] },
      { id: 'expansao', title: 'Acompanhar a expansão urbana', description: 'Explore o histórico territorial e confronte o crescimento com as regras de uso.', result: 'Análise territorial para apoiar estudos de planejamento.', steps: [['map', 'Explorar território e histórico'], ['legal', 'Consultar regras urbanísticas'], ['compare', 'Comparar áreas'], ['reports', 'Preparar relatório']] },
    ],
  },
}
