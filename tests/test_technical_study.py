import pytest
from pydantic import ValidationError
from recomendacao_imobiliaria.technical_study import TechnicalInput, evaluate_technical


def complete(**changes):
    return {**dict(slope_pct=0,road_access='reported_available',water='reported_available',sewer='reported_available',power='reported_available',drainage='reported_available',registry_reference='Matrícula de teste',topography_reference='Levantamento de teste',geotechnical_reference='Sondagem de teste',source_note='Informado para teste',reference_date='2026-10-14'),**changes}


def test_missing_evidence_is_not_converted_to_availability():
    result=evaluate_technical({}, {}, {})
    assert result['status']=='evidence_pending'
    assert 'Declividade medida' in result['pending']
    assert result['assumptions']['water']=='unknown'
    assert evaluate_technical(None,{}, {})['status']=='not_requested'


def test_zero_slope_valid_and_all_evidence_only_means_ready_for_review():
    result=evaluate_technical(complete(),{}, {'status':'blocked','spatial_overlays_verified':False})
    assert result['status']=='ready_for_review'
    assert result['pending']==[]
    assert result['assumptions']['slope_pct']==0
    assert any('bloqueio' in text for text in result['alerts'])
    assert any('não viabilidade' in text for text in result['limitations'])


def test_unavailable_infrastructure_remains_visible_with_pending_documents():
    result=evaluate_technical(complete(water='reported_unavailable',topography_reference=' '),{'official_risk_level':'alto'}, {})
    assert result['unavailable']==['Água']
    assert 'Levantamento topográfico' in result['pending']
    assert any('suscetibilidade oficial' in text for text in result['alerts'])


@pytest.mark.parametrize('data',[{'slope_pct':-1},{'slope_pct':float('nan')},{'slope_pct':float('inf')},{'water':'verified'}])
def test_invalid_technical_values_rejected(data):
    with pytest.raises(ValidationError): TechnicalInput(**data)


@pytest.mark.parametrize('value',[float('inf'),float('nan')])
def test_shared_concept_model_rejects_nonfinite_inputs(value):
    from api.routes.concept import ConceptInput
    with pytest.raises(ValidationError): ConceptInput(predictedMarketPrice=value)
