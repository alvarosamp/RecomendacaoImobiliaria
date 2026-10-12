import json
from unittest.mock import MagicMock

import pytest
import pandas as pd

from recomendacao_imobiliaria import api_collector, cnes_collector, ibge_collector
from recomendacao_imobiliaria.municipality import MUNICIPALITY, MunicipalityMismatch, load_municipality
from recomendacao_imobiliaria.territorial_audit import assess_population_provenance


def response(payload):
    obj = MagicMock(status_code=200)
    obj.json.return_value = payload
    return obj


def test_providers_share_identity_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_municipality().ibge_code == "3152501"
    assert ibge_collector.IBGE_CITY_CODE == int(MUNICIPALITY.ibge_code)
    assert api_collector._PA_IBGE_CODE == MUNICIPALITY.ibge_code
    assert cnes_collector.POUSO_ALEGRE_MUN_CODE == "315250"


def test_sector_from_another_city_is_rejected_without_fallback(monkeypatch):
    monkeypatch.setattr(ibge_collector.requests, "get", lambda *a, **k: response([
        {"D1C": "header"}, {"D1C": "315180005000001", "V": "456"}]))
    with pytest.raises(MunicipalityMismatch):
        ibge_collector._fetch_setor_population()


def test_municipality_polygon_is_not_misinterpreted_as_sector(monkeypatch):
    monkeypatch.setattr(ibge_collector.requests, "get", lambda *a, **k: response({"features": [
        {"properties": {"codarea": "3152501"}, "geometry": {"type": "Polygon", "coordinates": []}}]}))
    with pytest.raises(ValueError, match="setor censitario"):
        ibge_collector._fetch_setor_boundaries()


def test_population_response_rejects_wrong_locality(monkeypatch):
    monkeypatch.setattr(ibge_collector.requests, "get", lambda *a, **k: response([
        {"series": [{"localidade": {"id": "3151800"}, "serie": {"2022": "100000"}}]}]))
    with pytest.raises(MunicipalityMismatch):
        ibge_collector._get_population_estimate()


def test_population_reference_discloses_source_and_year(monkeypatch):
    monkeypatch.setattr(ibge_collector.requests, "get", MagicMock(side_effect=TimeoutError))
    estimate = ibge_collector._get_population_estimate()
    assert estimate.reference_year == 2022
    assert estimate.quality == "static_reference"
    assert estimate.value == 152_217
    assert estimate.source_uri.startswith("https://ftp.ibge.gov.br/")


def test_cnes_rejects_wrong_municipality_in_response(monkeypatch):
    get = MagicMock(return_value=response([{"coMunicipio": "315180", "latitude": -22, "longitude": -46}]))
    monkeypatch.setattr(cnes_collector.requests, "get", get)
    with pytest.raises(MunicipalityMismatch):
        cnes_collector._try_cnes_api()
    assert get.call_args.kwargs["params"]["municipio"] == "315250"


def test_housing_metadata_rejects_wrong_city_before_export(tmp_path, monkeypatch):
    monkeypatch.setattr(api_collector.requests, "get", lambda *a, **k: response({"id": 3151800}))
    output = tmp_path / "housing.csv"
    with pytest.raises(MunicipalityMismatch):
        api_collector.fetch_ibge_housing_indicators(output_csv=str(output))
    assert not output.exists()


@pytest.mark.parametrize("records", [[], [{"dataset": "h3_population", "status": "ok", "details": {"municipality_code": "3151800"}}]])
def test_legacy_population_requires_reprocessing(records):
    result = assess_population_provenance(records, 10)
    assert result["status"] == "unverified" and result["requires_reprocessing"]


def test_registered_population_is_still_an_estimate():
    record = {"dataset": "h3_population", "status": "ok", "row_count": 10, "source_name": "IBGE API",
              "details": json.dumps({"municipality_code": "3152501", "method": "ndbi_proxy",
                                     "quality": "estimated", "reference_year": 2022})}
    result = assess_population_provenance([record], 10)
    assert result["status"] == "estimated" and not result["requires_reprocessing"]
    assert result["method"] == "ndbi_proxy"
    assert assess_population_provenance([record], 11)["requires_reprocessing"]


@pytest.mark.parametrize("weights,total", [([1, 1, 1], 10), ([0, 0, 0], 2), ([3, 1, 0], 10)])
def test_proxy_population_conserves_total(weights, total):
    counts = ibge_collector._allocate_population(pd.Series(weights), total)
    assert counts.sum() == total
    assert (counts >= 0).all()
