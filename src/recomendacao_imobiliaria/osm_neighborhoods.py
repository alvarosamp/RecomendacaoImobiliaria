"""Camada de referência de bairros a partir do OpenStreetMap (ODbL).

O IBGE (Censo 2022) não publica bairros para Pouso Alegre e a Prefeitura só
disponibiliza o mapa urbano em PDF. O OSM tem limites de bairro
(``boundary=administrative`` + ``admin_level=10``), quadrantes (``admin_level=9``)
e pontos ``place=neighbourhood|suburb`` nomeados. Esta camada serve para
rotular o mapa e nomear células H3; não substitui um limite oficial.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "RecomendacaoImobiliaria/1.0 (inteligencia territorial)"
DEFAULT_OUTPUT = Path("data/official/bairros/osm_bairros_pouso_alegre.geojson")
CEP_OUTPUT = Path("data/official/bairros/cep_bairros_pouso_alegre.geojson")


def _query(municipality: str) -> str:
    return f"""
[out:json][timeout:120];
area["boundary"="administrative"]["name"="{municipality}"]["admin_level"="8"]->.city;
(
  relation["boundary"="administrative"]["admin_level"~"^(9|10)$"](area.city);
  node["place"~"^(suburb|neighbourhood|quarter)$"]["name"](area.city);
  way["place"~"^(suburb|neighbourhood|quarter)$"]["name"](area.city);
);
out geom;
"""


def _close(ring: list[list[float]]) -> list[list[float]]:
    if ring and ring[0] != ring[-1]:
        ring = [*ring, ring[0]]
    return ring


def _join_ways(ways: list[list[list[float]]]) -> list[list[list[float]]]:
    """Encadeia membros 'outer' de uma relação em anéis fechados."""
    pending = [list(way) for way in ways if len(way) >= 2]
    rings: list[list[list[float]]] = []
    while pending:
        ring = pending.pop(0)
        changed = True
        while ring[0] != ring[-1] and changed:
            changed = False
            for index, way in enumerate(pending):
                if way[0] == ring[-1]:
                    ring.extend(way[1:])
                elif way[-1] == ring[-1]:
                    ring.extend(reversed(way[:-1]))
                elif way[-1] == ring[0]:
                    ring[:0] = way[:-1]
                elif way[0] == ring[0]:
                    ring[:0] = list(reversed(way[1:]))
                else:
                    continue
                pending.pop(index)
                changed = True
                break
        if len(ring) >= 4:
            rings.append(_close(ring))
    return rings


def _relation_geometry(element: dict) -> dict | None:
    outers = [
        [[point["lon"], point["lat"]] for point in member.get("geometry", [])]
        for member in element.get("members", [])
        if member.get("type") == "way" and member.get("role") in ("outer", "")
    ]
    rings = _join_ways(outers)
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": rings}
    return {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}


_LOWER_WORDS = {"da", "das", "de", "do", "dos", "e"}


def _display_name(name: str) -> str:
    """Corrige nomes cadastrados todo em minúsculas (ex.: 'são geraldo')."""
    if name != name.lower():
        return name
    words = name.split()
    return " ".join(w if i and w in _LOWER_WORDS else w.capitalize() for i, w in enumerate(words))


def _ring_centroid(ring: list[list[float]]) -> list[float]:
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area) < 1e-12:
        xs, ys = zip(*ring)
        return [sum(xs) / len(xs), sum(ys) / len(ys)]
    return [cx / (3 * area), cy / (3 * area)]


def build_feature_collection(payload: dict, municipality: str) -> dict:
    features = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = _display_name(str(tags.get("name", "")).strip())
        if not name:
            continue
        osm_id = f"{element['type']}/{element['id']}"
        if element["type"] == "relation":
            geometry = _relation_geometry(element)
            if geometry is None:
                continue
            level = tags.get("admin_level")
            kind = "quadrante" if level == "9" else "bairro"
            outer = geometry["coordinates"][0] if geometry["type"] == "Polygon" else max(
                (poly[0] for poly in geometry["coordinates"]), key=len
            )
            label = _ring_centroid(outer)
        elif element["type"] == "node":
            geometry = {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
            kind = "bairro_ponto"
            label = geometry["coordinates"]
        else:
            coords = [[point["lon"], point["lat"]] for point in element.get("geometry", [])]
            if len(coords) < 4:
                continue
            ring = _close(coords)
            geometry = {"type": "Polygon", "coordinates": [ring]}
            kind = "bairro"
            label = _ring_centroid(ring)
        features.append({
            "type": "Feature",
            "properties": {
                "name": name,
                "kind": kind,
                "place": tags.get("place"),
                "admin_level": tags.get("admin_level"),
                "osm_id": osm_id,
                "label_lon": round(label[0], 6),
                "label_lat": round(label[1], 6),
            },
            "geometry": geometry,
        })
    # Pontos que repetem o nome de um polígono só duplicariam o rótulo.
    polygon_names = {
        f["properties"]["name"].casefold() for f in features if f["properties"]["kind"] == "bairro"
    }
    features = [
        f for f in features
        if not (f["properties"]["kind"] == "bairro_ponto" and f["properties"]["name"].casefold() in polygon_names)
    ]
    features.sort(key=lambda f: (f["properties"]["kind"], f["properties"]["name"]))
    return {
        "type": "FeatureCollection",
        "source": "OpenStreetMap contributors (ODbL)",
        "municipality": municipality,
        "retrieved_at": date.today().isoformat(),
        "features": features,
    }


def fetch_osm_neighborhoods(municipality: str = "Pouso Alegre", output: str | Path = DEFAULT_OUTPUT) -> dict:
    response = requests.post(
        OVERPASS_URL,
        data={"data": _query(municipality)},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=180,
    )
    response.raise_for_status()
    collection = build_feature_collection(response.json(), municipality)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    kinds: dict[str, int] = {}
    for feature in collection["features"]:
        kind = feature["properties"]["kind"]
        kinds[kind] = kinds.get(kind, 0) + 1
    return {"output": str(path), "features": len(collection["features"]), "by_kind": kinds}


def _read(path: Path) -> dict:
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _name_key(name: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return " ".join(text.replace("y", "i").split())


def load_neighborhoods(path: str | Path = DEFAULT_OUTPUT, cep_path: str | Path = CEP_OUTPUT) -> dict:
    """Camada de bairros do mapa.

    Base: bairros estimados pelos Correios (``cep_neighborhoods``), que cobrem a malha
    urbana com os nomes usados em endereços e anúncios. Limites de bairro desenhados
    no OSM valem por cima da estimativa (são recortados das áreas vizinhas). Do OSM
    também ficam os quadrantes e as localidades fora da cobertura (bairros rurais).
    """
    path, cep_path = Path(path), Path(cep_path)
    stamp = tuple(p.stat().st_mtime if p.exists() else 0 for p in (path, cep_path))
    return _merged_neighborhoods(str(path), str(cep_path), stamp)


@lru_cache(maxsize=2)
def _merged_neighborhoods(path: str, cep_path: str, _stamp: tuple) -> dict:
    osm = _read(Path(path))
    cep = _read(Path(cep_path))
    if not cep["features"]:
        return osm

    from shapely.geometry import Point, mapping, shape
    from shapely.ops import unary_union

    osm_polygons = [f for f in osm["features"] if f["properties"]["kind"] == "bairro"]
    surveyed = unary_union([shape(f["geometry"]) for f in osm_polygons]) if osm_polygons else None
    surveyed_keys = {_name_key(f["properties"]["name"]) for f in osm_polygons}

    features = []
    for feature in cep["features"]:
        if _name_key(feature["properties"]["name"]) in surveyed_keys:
            continue
        geom = shape(feature["geometry"])
        if surveyed is not None and geom.intersects(surveyed):
            geom = geom.difference(surveyed)
            if geom.is_empty or geom.area < 1e-7:
                continue
            props = dict(feature["properties"])
            if not geom.contains(Point(props["label_lon"], props["label_lat"])):
                anchor = geom.representative_point()
                props["label_lon"], props["label_lat"] = round(anchor.x, 6), round(anchor.y, 6)
            feature = {"type": "Feature", "properties": props, "geometry": mapping(geom)}
        features.append(feature)
    features += [{**f, "properties": {**f["properties"], "source": "OpenStreetMap"}} for f in osm_polygons]

    covered = unary_union([shape(f["geometry"]) for f in features]).buffer(0.002)
    names = {_name_key(f["properties"]["name"]) for f in features}
    features += [
        f for f in osm["features"]
        if f["properties"]["kind"] == "quadrante"
        or (f["properties"]["kind"] == "bairro_ponto"
            and _name_key(f["properties"]["name"]) not in names
            and not covered.contains(Point(f["properties"]["label_lon"], f["properties"]["label_lat"])))
    ]
    return {
        "type": "FeatureCollection",
        "source": f"{cep.get('source')}; {osm.get('source')}",
        "retrieved_at": cep.get("retrieved_at"),
        "features": features,
    }


POINT_MAX_DISTANCE_M = 1200
RURAL_NAME = "Zona rural"


def resolve_neighborhoods(lons, lats, collection: dict | None = None) -> list[tuple[str, str]]:
    """Nome e origem do bairro de cada coordenada (mesma regra do mapa no frontend).

    Ordem: área de bairro ('cep' estimada pelos Correios ou 'limite' desenhado no OSM),
    localidade a até 1,2 km ('proximidade'), quadrante ('quadrante'), senão 'rural'.
    """
    import math

    from shapely import STRtree
    from shapely.geometry import Point, shape

    features = (collection or load_neighborhoods())["features"]
    areas = [f for f in features if f["properties"]["kind"] != "quadrante" and f["geometry"]["type"] != "Point"]
    quadrants = [f for f in features if f["properties"]["kind"] == "quadrante"]
    places = [f for f in features if f["geometry"]["type"] == "Point"]
    area_tree = STRtree([shape(f["geometry"]) for f in areas]) if areas else None
    quad_shapes = [shape(f["geometry"]) for f in quadrants]

    results = []
    for lon, lat in zip(lons, lats):
        point = Point(lon, lat)
        if area_tree is not None:
            hits = area_tree.query(point, predicate="within")
            if len(hits):
                props = areas[int(hits[0])]["properties"]
                results.append((props["name"], "cep" if props.get("approximate") else "limite"))
                continue
        kx = 111320 * math.cos(math.radians(lat))
        nearest = min(
            ((math.hypot((f["geometry"]["coordinates"][0] - lon) * kx, (f["geometry"]["coordinates"][1] - lat) * 110540), f)
             for f in places),
            default=None, key=lambda item: item[0],
        )
        if nearest and nearest[0] <= POINT_MAX_DISTANCE_M:
            results.append((nearest[1]["properties"]["name"], "proximidade"))
            continue
        quadrant = next((f for f, g in zip(quadrants, quad_shapes) if g.contains(point)), None)
        results.append((quadrant["properties"]["name"], "quadrante") if quadrant else (RURAL_NAME, "rural"))
    return results
