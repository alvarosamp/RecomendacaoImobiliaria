import pandas as pd

from recomendacao_imobiliaria.osm_neighborhoods import resolve_neighborhoods
from recomendacao_imobiliaria.reporting import _add_reference_neighborhoods

SQUARE = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
COLLECTION = {"features": [
    {"type": "Feature", "properties": {"name": "Centro", "kind": "bairro", "approximate": True}, "geometry": SQUARE},
    {"type": "Feature", "properties": {"name": "Quadrante Sul", "kind": "quadrante"},
     "geometry": {"type": "Polygon", "coordinates": [[[0, -2], [1, -2], [1, -1], [0, -1], [0, -2]]]}},
    {"type": "Feature", "properties": {"name": "Algodão", "kind": "bairro_ponto"},
     "geometry": {"type": "Point", "coordinates": [5, 5]}},
]}


def test_resolve_follows_area_place_quadrant_rural_order():
    result = resolve_neighborhoods([0.5, 5.005, 0.5, 9.0], [0.5, 5.0, -1.5, 9.0], COLLECTION)
    assert result == [
        ("Centro", "cep"),
        ("Algodão", "proximidade"),
        ("Quadrante Sul", "quadrante"),
        ("Zona rural", "rural"),
    ]


def test_official_neighborhood_is_kept(monkeypatch):
    monkeypatch.setattr(
        "recomendacao_imobiliaria.osm_neighborhoods.load_neighborhoods", lambda *a, **k: COLLECTION
    )
    frame = pd.DataFrame({
        "latitude": [0.5, 0.5],
        "longitude": [0.5, 0.5],
        "neighborhood": ["Bairro Oficial", None],
        "neighborhood_source": ["oficial", None],
    })
    enriched = _add_reference_neighborhoods(frame)
    assert enriched["neighborhood"].tolist() == ["Bairro Oficial", "Centro"]
    assert enriched["neighborhood_source"].tolist() == ["oficial", "cep"]
