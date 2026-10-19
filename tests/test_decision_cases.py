from copy import deepcopy
import pytest
from pydantic import ValidationError
from recomendacao_imobiliaria.case_demos import demo_context, demo_inputs
from recomendacao_imobiliaria.decision_cases import KINDS, MODELS, evaluate_case

@pytest.mark.parametrize('kind', KINDS)
def test_each_journey_has_distinct_results(kind):
    c=demo_context(kind)
    r=evaluate_case(kind,demo_inputs(kind),project=c['project'],territory=c['territory'],diagnosis=c['diagnosis'],demonstration=True)
    assert r['methodology']=='decision_'+kind+'_v1'
    assert r['summary']['conclusion'] and len(r['summary']['reasons'])<=3
    assert r['summary']['next_action']['evidence_required']
    assert evaluate_case(kind,{})['summary']['gaps']

def test_investment_zero_is_valid_and_cashflow_reconciles():
    data=demo_inputs('invest');data['budget']=0
    data['properties'][0].update(acquisition=0,improvements=0,other_costs=0)
    row=evaluate_case('invest',data)['details']['properties'][0]
    assert row['within_budget'] and row['capital']==0
    assert row['scenarios'][0]['roi_pct'] is None
    assert sum(x['net'] for x in row['cash_flow'])==row['scenarios'][0]['profit']

def test_market_filters_do_not_expand_sample():
    data=demo_inputs('mercado');first=data['comparables'][0];first['provenance']='user'
    data['comparables']=[first]+[{**deepcopy(first),**change} for change in [
        {'city_ibge':'3550308'},{'property_type':'apartamento'},{'transaction':'aluguel'},
        {'area_m2':500},{'reference_date':'2020-01-01'},{'reference_date':'2027-01-01'},{'provenance':'simulation'}]]
    r=evaluate_case('mercado',data)
    assert r['details']['sample_size']==1 and len(r['details']['excluded'])==7
    data['comparables']=[]
    assert 'reference_price_m2' not in evaluate_case('mercado',data)['details']

def test_restriction_precedes_economic_conclusion():
    p=demo_context('incorpora')['project'];p['analysis']['legal']['status']='blocked'
    r=evaluate_case('incorpora',demo_inputs('incorpora'),project=p)
    assert 'restrição' in r['summary']['conclusion']
    assert r['summary']['gaps'][0].startswith('Há restrição')

@pytest.mark.parametrize('kind,data',[('invest',{'budget':float('nan')}),('invest',{'properties':[{'acquisition':-1}]}),
    ('incorpora',{'proposals':[{'build_area_m2':10,'financial':{'saleable_area_m2':20}}]}),
    ('governo',{'target_distance_m':float('inf')}),('negocios',{'points':[{'rent':-1}]}),('obras',{'unexpected':'ignored?'})])
def test_invalid_inputs_rejected(kind,data):
    with pytest.raises(ValidationError):MODELS[kind].model_validate(data)

def test_subcent_price_per_m2_does_not_round_denominator_to_zero():
    import math
    data=demo_inputs('mercado');data.update(area_m2=1e8,asking_price=.01)
    data['comparables']=[{**data['comparables'][0],'area_m2':1e8,'price':.01,'provenance':'user'}]
    result=evaluate_case('mercado',data)
    assert result['details']['deviation_pct']==0
    assert math.isfinite(result['details']['reference_price_m2'])

@pytest.mark.parametrize('data',[{'area_m2':1e-300},{'asking_price':1e-300}])
def test_market_rejects_values_below_supported_precision(data):
    with pytest.raises(ValidationError):MODELS['mercado'].model_validate(data)
