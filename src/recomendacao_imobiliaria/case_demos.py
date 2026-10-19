"""Isolated, explicitly synthetic examples. Never imported into public datasets."""
from .decision_cases import PA
from .technical_study import evaluate_technical
from .public_services import build_diagnosis

DAY = '2026-10-15'
CELL = '88a88c994bfffff'
SOURCE = 'Valores fictícios para demonstrar o fluxo; não são cotações ou observações reais.'


def financial(area, price):
    return dict(land_cost=180000, construction_cost_m2=2200, other_costs=25000, contingency_pct=10,
                saleable_area_m2=area, sale_price_m2=price, sales_expenses_pct=8, months=18,
                annual_discount_pct=10, cost_variation_pct=10, price_variation_pct=10,
                source_note=SOURCE, reference_date=DAY)


def demo_inputs(kind):
    if kind == 'incorpora':
        return dict(proposals=[dict(name='Proposta A', product='Duas unidades residenciais — hipótese', build_area_m2=200, financial=financial(170, 5000)),
                               dict(name='Proposta B', product='Três unidades compactas — hipótese', build_area_m2=240, financial=financial(200, 4800))])
    if kind == 'obras': return dict(investigation_note='Exemplo: organizar a verificação de infraestrutura e documentos antes da contratação.')
    if kind == 'invest':
        return dict(budget=400000, variation_pct=10, properties=[dict(name=name, acquisition=cost, improvements=35000, other_costs=20000,
            sale_price=sale, sales_expenses_pct=8, months=12, source_note=SOURCE, reference_date=DAY)
            for name, cost, sale in [('Casa A — exemplo', 280000, 430000), ('Casa B — exemplo', 360000, 510000)]])
    if kind == 'mercado':
        return dict(address='Imóvel ilustrativo em Pouso Alegre; sem endereço real', property_type='casa', transaction='venda', area_m2=120,
                    asking_price=520000, source_note=SOURCE, reference_date=DAY, positives='Área útil informada e acesso a verificar.',
                    objections='Conservação e documentação ainda precisam de confirmação.', owner_questions='Há reforma recente? Quais documentos estão disponíveis?',
                    comparables=[dict(name=f'Casa ilustrativa {index+1}', area_m2=area, price=price, source_note=SOURCE, reference_date=DAY,
                        city_ibge=PA, property_type='casa', transaction='venda', provenance='simulation', differences='Condição fictícia para explicar comparação.')
                        for index, (area, price) in enumerate([(110, 440000), (125, 540000), (130, 560000)])])
    if kind == 'negocios':
        return dict(criteria=dict(sector='pharmacy', minimum_population=1000, distance_reference_m=500, criteria_note='Critérios fictícios para investigar, sem previsão de demanda.', reference_date=DAY),
                    points=[dict(name=f'Ponto {letter} — exemplo', address='Endereço ilustrativo; visita não realizada', h3_id=CELL if letter == 'A' else None,
                        rent=rent, other_monthly_costs=500, area_m2=80, visibility='favoravel', access='unknown', observed_competitors=0,
                        source_note=SOURCE, reference_date=DAY, visit_note='Ficha simulada; confirmar acesso, contrato e uso.') for letter, rent in [('A', 3500), ('B', 2800)]])
    return dict(target_distance_m=2000, regions=[dict(h3_id=CELL, name='Recorte escolar ilustrativo', justification='Investigar a oferta e a acessibilidade; exemplo sem vistoria real.')])


def demo_context(kind):
    technical = evaluate_technical(dict(slope_pct=0, road_access='reported_available', water='reported_unavailable',
        source_note=SOURCE, reference_date=DAY, registry_reference='Referência fictícia'), {}, {})
    project = dict(revision=1, analysis=dict(mode='premises_only', captured_at=DAY+'T12:00:00+00:00', technical=technical,
        legal=dict(status='analisar', notes='Contexto inteiramente demonstrativo. Restrições e parâmetros legais não foram consultados.', sources=[], spatial_overlays_verified=False)))
    territory = [dict(h3_id=CELL, neighborhood='Recorte ilustrativo', pop_estimated=1200, poi_pharmacy_cnt=0, dist_min_pharmacy_m=700)]
    diagnosis = build_diagnosis([dict(h3_id=CELL, neighborhood='Recorte escolar ilustrativo', pop_estimated=1200, poi_school_cnt=0, dist_min_school_m=2500)], 'schools', 2000, [])
    return dict(project=project if kind in ('incorpora', 'obras') else None, territory=territory, diagnosis=diagnosis)
