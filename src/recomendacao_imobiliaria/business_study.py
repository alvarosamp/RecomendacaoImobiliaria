"""Commercial-location criteria against a territorial snapshot; no sales forecast."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .public_services import number


class BusinessInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    sector: Literal['pharmacy','market'] = 'pharmacy'
    minimum_population: float | None = Field(None, ge=0, le=1e9)
    distance_reference_m: float | None = Field(None, ge=100, le=50000)
    criteria_note: str = Field('', max_length=4000)
    reference_date: date | None = None


SECTORS = {'pharmacy':('Farmácia','poi_pharmacy_cnt','dist_min_pharmacy_m'), 'market':('Mercado','poi_supermarket_cnt','dist_min_supermarket_m')}
LIMITATIONS = [
    'Os limites são critérios exploratórios definidos pelo usuário, não padrões de demanda ou garantia de faturamento.',
    'População estimada por célula H3 não representa população de uma área de influência ou público consumidor medido.',
    'Contagens e distâncias de estabelecimentos mapeados não comprovam funcionamento, concorrência efetiva ou ausência de oferta.',
    'As datas e a cobertura dos POIs devem ser confirmadas; processamento do score não equivale à coleta de cada estabelecimento.',
    'O diagnóstico exige pesquisa de mercado, fluxo de pessoas, renda, concorrência, custos operacionais e validação do uso urbanístico.',
]


def evaluate_business(raw, area, legal):
    if raw is None: return {'status':'not_requested','methodology':'commercial_criteria_v1','limitations':LIMITATIONS}
    data=BusinessInput.model_validate(raw)
    label,count_key,distance_key=SECTORS[data.sector]
    population,count,distance=number(area.get('pop_estimated')),number(area.get(count_key)),number(area.get(distance_key))
    missing_criteria=[]
    for key,value in data.model_dump().items():
        if value is None or (key=='criteria_note' and not value.strip()):missing_criteria.append(key)
    missing_data=[label for label,value in [('população estimada',population),('estabelecimentos mapeados',count),('distância ao serviço',distance)] if value is None]
    checks=[
        {'label':'População no recorte atinge o mínimo escolhido','status':'unknown' if population is None or data.minimum_population is None else 'criterion_met' if population>=data.minimum_population else 'criterion_not_met'},
        {'label':'Distância ao serviço atinge a referência escolhida','status':'unknown' if distance is None or data.distance_reference_m is None else 'criterion_met' if distance>=data.distance_reference_m else 'criterion_not_met'},
    ]
    return {'status':'criteria_pending' if missing_criteria else 'territorial_data_pending' if missing_data else 'ready_for_market_research',
            'methodology':'commercial_criteria_v1','sector_label':label,'assumptions':data.model_dump(mode='json'),
            'population_estimate':population,'mapped_establishments':count,'nearest_distance_m':distance,
            'processing_timestamp':area.get('score_updated_at'),'missing_criteria':missing_criteria,'missing_data':missing_data,
            'checks':checks,'legal_status':legal.get('status','analisar'),
            'alerts':['A triagem legal indica bloqueio. O atendimento aos critérios comerciais não afasta a restrição.'] if legal.get('status')=='blocked' else [],
            'limitations':LIMITATIONS}
