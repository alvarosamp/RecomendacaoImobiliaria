"""Controlled analytical captures for browser tests; run from the repository root.

PYTHONPATH=src python frontend/tests/generate_fixtures.py --output-dir /private/tmp
"""
import argparse
import json
from pathlib import Path

from recomendacao_imobiliaria.business_study import evaluate_business
from recomendacao_imobiliaria.financial_study import evaluate_financial
from recomendacao_imobiliaria.technical_study import evaluate_technical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    target = parser.parse_args().output_dir
    target.mkdir(parents=True, exist_ok=True)
    captures = {
        'finance': evaluate_financial(dict(land_cost=100000, construction_cost_m2=1000, other_costs=0,
            contingency_pct=0, saleable_area_m2=100, sale_price_m2=3000, sales_expenses_pct=0,
            months=12, annual_discount_pct=0, cost_variation_pct=10, price_variation_pct=10,
            reference_date='2026-10-14', source_note='Premissas controladas para teste'), 165),
        'technical': evaluate_technical(dict(slope_pct=0, water='reported_unavailable',
            registry_reference='Referência de teste', source_note='Declaração controlada para teste',
            reference_date='2026-10-14'), {}, {}),
        'business': evaluate_business(dict(sector='pharmacy', minimum_population=0,
            distance_reference_m=500, reference_date='2026-10-15', criteria_note='Hipótese a investigar'),
            dict(pop_estimated=1200, poi_pharmacy_cnt=0, dist_min_pharmacy_m=600,
                 score_updated_at='2026-10-15T12:00:00Z'), {'status': 'blocked'}),
    }
    for name, result in captures.items():
        path = target / f'urbia-{name}-fixture.json'
        path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        print(path)


if __name__ == '__main__':
    main()
