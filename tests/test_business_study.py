import pytest
from pydantic import ValidationError
from recomendacao_imobiliaria.business_study import BusinessInput, evaluate_business


def criteria(**changes):
    return dict(sector='pharmacy', minimum_population=1000, distance_reference_m=500,
                criteria_note='Hipótese a investigar', reference_date='2026-10-15', **changes)


def test_missing_data_stays_unknown_and_zero_is_valid():
    result = evaluate_business(criteria(), {}, {})
    assert result['status'] == 'territorial_data_pending'
    assert result['mapped_establishments'] is None
    assert all(item['status'] == 'unknown' for item in result['checks'])
    result = evaluate_business(criteria(), {'pop_estimated': 0, 'poi_pharmacy_cnt': 0, 'dist_min_pharmacy_m': 0}, {})
    assert result['status'] == 'ready_for_market_research'
    assert result['mapped_establishments'] == 0
    assert all(item['status'] == 'criterion_not_met' for item in result['checks'])


def test_sector_specific_indicators_and_legal_block_are_preserved():
    area = {'pop_estimated': 1000, 'poi_pharmacy_cnt': 0, 'dist_min_pharmacy_m': 600,
            'poi_supermarket_cnt': 4, 'dist_min_supermarket_m': 100, 'score_updated_at': '2026-10-15T12:00:00Z'}
    pharmacy = evaluate_business(criteria(), area, {'status': 'blocked'})
    assert all(item['status'] == 'criterion_met' for item in pharmacy['checks'])
    assert pharmacy['legal_status'] == 'blocked'
    assert pharmacy['alerts']
    assert pharmacy['processing_timestamp'] == area['score_updated_at']
    market = evaluate_business({**criteria(), 'sector': 'market'}, area, {})
    assert market['mapped_establishments'] == 4
    assert market['checks'][1]['status'] == 'criterion_not_met'


def test_missing_criteria_and_invalid_source_values_do_not_imply_success():
    result = evaluate_business({}, {'pop_estimated': float('nan'), 'poi_pharmacy_cnt': -1, 'dist_min_pharmacy_m': float('inf')}, {})
    assert result['status'] == 'criteria_pending'
    assert set(result['missing_criteria']) == {'minimum_population', 'distance_reference_m', 'criteria_note', 'reference_date'}
    assert len(result['missing_data']) == 3
    assert evaluate_business(None, {}, {})['status'] == 'not_requested'


@pytest.mark.parametrize('values', [{'sector': 'hospital'}, {'minimum_population': -1}, {'minimum_population': float('nan')}, {'distance_reference_m': 99}, {'distance_reference_m': 50001}])
def test_invalid_criteria_rejected(values):
    with pytest.raises(ValidationError):
        BusinessInput(**values)
