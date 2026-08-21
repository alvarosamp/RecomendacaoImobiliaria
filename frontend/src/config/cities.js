export const CITY_CONFIGS = [
  {
    id: 'pouso_alegre',
    name: 'Pouso Alegre',
    state: 'MG',
    ibgeCode: '3152501',
    status: 'operational',
    center: { longitude: -45.9489, latitude: -22.2303, zoom: 12 },
    searchViewbox: '-46.05,-22.13,-45.83,-22.38',
    sources: ['Plano Diretor', 'OSM', 'Sentinel-2', 'anuncios imobiliarios'],
    notes: 'Cidade piloto com scores, zoneamento, POIs e series NDVI/NDBI.',
  },
  {
    id: 'segunda_cidade',
    name: 'Nova cidade',
    state: 'BR',
    ibgeCode: '',
    status: 'planned',
    center: { longitude: -45.9489, latitude: -22.2303, zoom: 12 },
    searchViewbox: '-46.05,-22.13,-45.83,-22.38',
    sources: [],
    notes: 'Modelo preparado para receber limite, zoneamento, POIs e regras locais.',
  },
]

export const ANALYSIS_OBJECTIVES = [
  {
    id: 'real_estate',
    label: 'Investimento',
    shortLabel: 'Imobiliario',
    primaryMetric: 'score_residencial',
    secondaryMetric: 'score_comercial',
    decisionTitle: 'Potencial imobiliario',
    goodSignal: 'prioridade alta com risco controlado',
    emptySignal: 'sem oportunidade imobiliaria forte nos filtros atuais',
  },
  {
    id: 'commerce',
    label: 'Ponto comercial',
    shortLabel: 'Comercio',
    primaryMetric: 'score_comercial',
    secondaryMetric: 'score_residencial',
    decisionTitle: 'Carencia comercial',
    goodSignal: 'lacuna de servicos com zoneamento compativel',
    emptySignal: 'sem lacuna comercial forte nos filtros atuais',
  },
  {
    id: 'government',
    label: 'Gestao publica',
    shortLabel: 'Governo',
    primaryMetric: 'score_comercial',
    secondaryMetric: 'score_residencial',
    decisionTitle: 'Diagnostico urbano',
    goodSignal: 'area relevante para planejamento e servicos publicos',
    emptySignal: 'sem alerta urbano forte nos filtros atuais',
  },
]

export const DEFAULT_CITY_ID = 'pouso_alegre'
export const DEFAULT_OBJECTIVE_ID = 'real_estate'
