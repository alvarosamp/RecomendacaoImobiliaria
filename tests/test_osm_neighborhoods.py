from recomendacao_imobiliaria.osm_neighborhoods import build_feature_collection


def _way(*coords):
    return {"type": "way", "role": "outer", "geometry": [{"lon": x, "lat": y} for x, y in coords]}


def _relation(name, level, *ways):
    return {
        "type": "relation",
        "id": hash(name) & 0xFFFF,
        "tags": {"name": name, "admin_level": level, "boundary": "administrative"},
        "members": list(ways),
    }


def test_joins_split_outer_ways_into_closed_polygon():
    # Quadrado partido em duas vias, a segunda cadastrada no sentido inverso.
    relation = _relation("Centro", "10", _way((0, 0), (1, 0), (1, 1)), _way((0, 0), (0, 1), (1, 1)))

    collection = build_feature_collection({"elements": [relation]}, "Teste")

    feature = collection["features"][0]
    ring = feature["geometry"]["coordinates"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert ring[0] == ring[-1]
    assert len(ring) == 5
    assert feature["properties"]["kind"] == "bairro"
    assert (feature["properties"]["label_lon"], feature["properties"]["label_lat"]) == (0.5, 0.5)


def test_classifies_quadrants_and_fixes_lowercase_names():
    elements = [
        _relation("Quadrante Sul", "9", _way((0, 0), (2, 0), (2, 2), (0, 2), (0, 0))),
        _relation("são geraldo", "10", _way((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))),
    ]

    names = {f["properties"]["name"]: f["properties"]["kind"] for f in build_feature_collection({"elements": elements}, "Teste")["features"]}

    assert names == {"Quadrante Sul": "quadrante", "São Geraldo": "bairro"}


def test_drops_points_that_duplicate_a_polygon_name():
    elements = [
        _relation("Centro", "10", _way((0, 0), (1, 0), (1, 1), (0, 1), (0, 0))),
        {"type": "node", "id": 1, "lon": 0.5, "lat": 0.5, "tags": {"name": "Centro", "place": "neighbourhood"}},
        {"type": "node", "id": 2, "lon": 3, "lat": 3, "tags": {"name": "Jardim Yara", "place": "neighbourhood"}},
    ]

    features = build_feature_collection({"elements": elements}, "Teste")["features"]

    assert [(f["properties"]["name"], f["properties"]["kind"]) for f in features] == [
        ("Centro", "bairro"),
        ("Jardim Yara", "bairro_ponto"),
    ]
