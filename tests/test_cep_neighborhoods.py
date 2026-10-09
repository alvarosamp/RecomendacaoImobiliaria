from shapely.geometry import Point, shape

from recomendacao_imobiliaria.cep_neighborhoods import build_neighborhoods, normalize, street_neighborhoods

CITY = "Pouso Alegre"


def _cep(logradouro, bairro, localidade=CITY):
    return {"logradouro": logradouro, "bairro": bairro, "localidade": localidade}


def test_normalize_expands_abbreviations_and_accents():
    assert normalize("Av. Dr. João Beraldo") == "avenida doutor joao beraldo"
    assert normalize("Rua Cel. Otávio Meyer") == normalize("Rua Coronel Otavio Meyer")


def test_street_neighborhoods_ignores_fuzzy_viacep_matches():
    results = [
        _cep("Rua A", "Recanto das Rosas"),
        _cep("Rua Acre", "Cascalho"),
        _cep("Rua A", "Outra Cidade", localidade="Cambuí"),
    ]
    assert street_neighborhoods("Rua A", results, CITY) == {"Recanto das Rosas"}


def test_street_neighborhoods_accepts_same_name_with_other_street_type():
    results = [_cep("Avenida Vereador Antônio da Costa Rios", "Centro")]
    assert street_neighborhoods("Rua Ver. Antônio da Costa Rios", results, CITY) == {"Centro"}


def test_build_partitions_area_and_splits_multi_neighborhood_street():
    # Ruas a oeste pertencem a "Oeste", a leste a "Leste"; a rua horizontal cruza os dois.
    lon0, lat0 = -45.95, -22.23
    streets = []
    viacep = {}
    for i in range(6):
        for side, offset in (("Oeste", -0.012), ("Leste", 0.004)):
            name = f"Rua {side} {i}"
            x = lon0 + offset + i * 0.0015
            streets.append({"name": name, "coords": [(x, lat0 - 0.006), (x, lat0 + 0.006)]})
            viacep[name] = [_cep(name, side)]
    streets.append({"name": "Avenida Central", "coords": [(lon0 - 0.012, lat0), (lon0 + 0.0115, lat0)]})
    viacep["Avenida Central"] = [_cep("Avenida Central", "Oeste"), _cep("Avenida Central", "Leste")]

    collection, stats = build_neighborhoods(streets, None, viacep, CITY)

    shapes = {f["properties"]["name"]: shape(f["geometry"]) for f in collection["features"]}
    assert set(shapes) == {"Oeste", "Leste"}
    assert shapes["Oeste"].intersection(shapes["Leste"]).area < 1e-9
    assert shapes["Oeste"].contains(Point(lon0 - 0.008, lat0))
    assert shapes["Leste"].contains(Point(lon0 + 0.008, lat0))
    assert stats["street_names_matched"] == 13
    assert all(f["properties"]["approximate"] for f in collection["features"])


def test_locates_subdivisions_that_only_have_generic_street_names():
    # Dois loteamentos distantes, ambos com "Rua A" e "Rua B"; um deles também tem uma rua exclusiva.
    lon0, lat0 = -45.95, -22.23
    streets, viacep = [], {}
    for name, dx in (("Rua A", 0.0), ("Rua B", 0.0015)):
        for offset in (0.0, 0.03):
            x = lon0 + offset + dx
            streets.append({"name": name, "coords": [(x, lat0), (x, lat0 + 0.004)]})
        viacep[name] = [_cep(name, "Recanto das Rosas"), _cep(name, "Solar dos Quitas")]
    streets.append({"name": "Rua das Hortênsias", "coords": [(lon0 + 0.0305, lat0), (lon0 + 0.0305, lat0 + 0.004)]})
    viacep["Rua das Hortênsias"] = [_cep("Rua das Hortênsias", "Solar dos Quitas")]

    collection, _ = build_neighborhoods(streets, None, viacep, CITY)

    shapes = {f["properties"]["name"]: shape(f["geometry"]) for f in collection["features"]}
    assert shapes["Solar dos Quitas"].contains(Point(lon0 + 0.031, lat0 + 0.002))
    assert shapes["Recanto das Rosas"].contains(Point(lon0 + 0.0008, lat0 + 0.002))
