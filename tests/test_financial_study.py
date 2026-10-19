import pytest
from pydantic import ValidationError
from recomendacao_imobiliaria.financial_study import FinancialInput, evaluate_financial


def assumptions(**changes):
    return dict(land_cost=100000, construction_cost_m2=1000, other_costs=10000, contingency_pct=10,
                saleable_area_m2=100, sale_price_m2=3000, sales_expenses_pct=10, months=2,
                annual_discount_pct=0, cost_variation_pct=20, price_variation_pct=10,
                reference_date='2026-10-14', source_note='Premissas de teste, não são cotações', **changes)


def test_cost_revenue_profit_and_cashflow_reconcile():
    result = evaluate_financial(assumptions(), 100)
    base = result['scenarios'][0]
    assert base['total_cost'] == 220000
    assert base['net_revenue'] == 270000
    assert base['profit'] == base['npv'] == 50000
    assert base['margin_pct'] == 16.67
    assert base['roi_pct'] == 22.73
    assert base['break_even_price_m2'] == 2444.44
    assert base['peak_monthly_deficit'] == 165000
    assert sum(row['net'] for row in base['cash_flow']) == base['profit']
    assert base['cash_flow'][-1]['cumulative'] == base['profit']
    assert result['scenarios'][1]['profit'] < base['profit'] < result['scenarios'][2]['profit']


def test_discount_uses_equivalent_monthly_rate_and_sale_in_final_period():
    data = assumptions(); data.update(annual_discount_pct=12, months=12)
    base = evaluate_financial(data, 100)['scenarios'][0]
    rate = 1.12 ** (1/12) - 1
    expected = sum(item['net'] / ((1+rate)**item['month']) for item in base['cash_flow'])
    assert base['npv'] == round(expected,2)
    assert all(item['revenue'] == 0 for item in base['cash_flow'][:-1])


def test_missing_values_stay_pending_but_zero_rates_are_valid():
    result = evaluate_financial({'land_cost': 0}, 100)
    assert result['status'] == 'pending'
    assert 'land_cost' not in result['missing']
    assert 'sale_price_m2' in result['missing']
    assert 'scenarios' not in result
    assert evaluate_financial(None, 100)['status'] == 'not_requested'
    data = assumptions(); data.update(land_cost=0, other_costs=0, annual_discount_pct=0, contingency_pct=0, cost_variation_pct=0, price_variation_pct=0, sales_expenses_pct=0)
    assert evaluate_financial(data,100)['status'] == 'complete'


def test_extreme_sensitivity_and_total_sales_expenses_have_no_division_by_zero():
    data = assumptions(); data.update(land_cost=0, other_costs=0, cost_variation_pct=100, price_variation_pct=100, sales_expenses_pct=100)
    result = evaluate_financial(data,100)
    assert result['scenarios'][1]['margin_pct'] is None
    assert result['scenarios'][2]['roi_pct'] is None
    assert all(item['break_even_price_m2'] is None for item in result['scenarios'])


@pytest.mark.parametrize('field,value', [('construction_cost_m2', 0), ('months', 0), ('months', 601), ('months',1.5), ('land_cost',-1), ('annual_discount_pct',-1), ('sale_price_m2',float('inf')), ('other_costs',float('nan'))])
def test_invalid_assumptions_are_rejected(field,value):
    with pytest.raises(ValidationError): FinancialInput(**{field:value})


def test_monthly_rounding_reconciles_to_cents_with_uneven_installments():
    data = assumptions(); data.update(months=7, construction_cost_m2=1000.123, other_costs=123.456)
    base = evaluate_financial(data,100)['scenarios'][0]
    assert round(sum(item['cost'] for item in base['cash_flow']),2) == base['total_cost']
    assert round(sum(item['net'] for item in base['cash_flow']),2) == base['profit']
    assert base['cash_flow'][-1]['cumulative'] == base['profit']
