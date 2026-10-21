import math
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.routes import government
from recomendacao_imobiliaria.public_services import build_diagnosis


def row(cell='a', **changes):
    return {'h3_id': cell, 'population_2022': 100, 'poi_school_cnt': 0, 'dist_min_school_m': 3000, **changes}


def test_rank_is_independent_of_real_estate_score_and_population_breaks_ties():
    result = build_diagnosis([row('a', population_2022=50, score_residencial=100), row('b', population_2022=200, score_residencial=0)], 'schools', 2000)
    assert [item['h3_id'] for item in result['rows']] == ['b', 'a']
    assert result['rows'][0]['investigation_score'] == 100
    assert result['rows'][0]['contributions'] == {'absence': 40, 'access': 60}


@pytest.mark.parametrize('changes', [
    {'population_2022': None}, {'poi_school_cnt': None}, {'dist_min_school_m': None},
    {'dist_min_school_m': float('nan')}, {'population_2022': -5},
])
def test_missing_invalid_data_never_becomes_zero_or_rank(changes):
    result = build_diagnosis([row(**changes)], 'schools', 2000)
    assert result['rows'][0]['rank'] is None
    assert result['rows'][0]['investigation_score'] is None
    assert result['summary']['pending'] == 1


def test_actual_zero_values_remain_zero_and_census_precedes_estimate():
    result = build_diagnosis([row(population_2022=0, pop_estimated=2000, dist_min_school_m=0)], 'schools', 2000)
    assert result['rows'][0]['population'] == 0
    assert result['rows'][0]['priority'] == 'sem_populacao'
    assert result['rows'][0]['contributions']['access'] == 0
    assert result['summary']['ranked'] == 0


def test_estimated_population_is_explicit_and_reference_changes_ranking():
    records = [row(population_2022=None, pop_estimated=80, dist_min_school_m=1000, poi_school_cnt=1)]
    first = build_diagnosis(records, 'schools', 2000)
    second = build_diagnosis(records, 'schools', 1000)
    assert first['rows'][0]['population_basis'] == 'estimate'
    assert first['rows'][0]['investigation_score'] == 30
    assert second['rows'][0]['investigation_score'] == 60


def test_hospital_diagnosis_does_not_use_school_fields():
    result = build_diagnosis([row(poi_hospital_cnt=2, dist_min_hospital_m=500)], 'hospitals', 1000)
    assert result['rows'][0]['investigation_score'] == 30


def test_report_matches_snapshot_and_discloses_capacity_and_provenance_gaps():
    result = build_diagnosis([row()], 'schools', 2000)
    assert result['captured_at'] in result['report_markdown']
    assert 'não mede déficit de vagas' in result['report_markdown']
    assert 'Proveniência de equipamentos não registrada' in result['report_markdown']
    assert 'triagem_acesso_v1' in result['report_markdown']


def test_route_validates_parameters_and_does_not_fallback_to_demo(monkeypatch):
    app = FastAPI()
    app.include_router(government.router)
    client = TestClient(app)
    monkeypatch.setattr(government, 'load_public_service_data', lambda: ([row()], []))
    assert client.get('/government/diagnosis').status_code == 200
    assert client.get('/government/diagnosis?service=pharmacy').status_code == 422
    assert client.get('/government/diagnosis?target_distance_m=0').status_code == 422
    def unavailable(): raise RuntimeError('no db')
    monkeypatch.setattr(government, 'load_public_service_data', unavailable)
    assert client.get('/government/diagnosis').status_code == 503
