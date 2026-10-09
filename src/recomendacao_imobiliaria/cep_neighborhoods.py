"""Bairros aproximados a partir dos Correios (ViaCEP) + ruas do OpenStreetMap.

Não há camada oficial de limites de bairro para Pouso Alegre. Os Correios, porém,
atribuem um bairro a cada logradouro/faixa de CEP. Este módulo:

1. baixa as ruas nomeadas do município no OSM (traçado);
2. pergunta ao ViaCEP o(s) bairro(s) de cada rua (nome exatamente igual);
3. rotula pontos ao longo das ruas — ruas com um só bairro primeiro; ruas que
   cruzam vários bairros têm cada trecho atribuído ao candidato mais próximo;
4. remove pontos isolados e particiona a área urbana em polígonos de Voronoi,
   dissolvidos por bairro e recortados pelo entorno das ruas e pelo município.

O resultado é uma estimativa (``approximate: true``), não um limite legal.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote

import requests

from .osm_neighborhoods import CEP_OUTPUT, OVERPASS_URL, USER_AGENT, _relation_geometry

DEFAULT_OUTPUT = CEP_OUTPUT
# Cache bruto das respostas do ViaCEP; aponte VIACEP_CACHE para um disco externo se faltar espaço.
DEFAULT_CACHE = Path(os.environ.get("VIACEP_CACHE", "data/official/bairros/viacep_cache.json"))
VIACEP_URL = "https://viacep.com.br/ws/{uf}/{city}/{street}/json/"
METRIC_CRS = "EPSG:31983"  # SIRGAS 2000 / UTM 23S
SAMPLE_STEP_M = 35
URBAN_BUFFER_M = 160

ABBREVIATIONS = {
    "av": "avenida", "r": "rua", "al": "alameda", "tv": "travessa", "trav": "travessa", "pc": "praca",
    "pca": "praca", "rod": "rodovia", "est": "estrada", "dr": "doutor", "dra": "doutora", "prof": "professor",
    "profa": "professora", "cel": "coronel", "cap": "capitao", "ten": "tenente", "sgt": "sargento",
    "mal": "marechal", "gen": "general", "gal": "general", "pe": "padre", "sto": "santo", "sta": "santa",
    "eng": "engenheiro", "gov": "governador", "pres": "presidente", "ver": "vereador", "dep": "deputado",
    "sen": "senador", "cmte": "comandante", "com": "comendador", "d": "dom", "n": "nossa", "sra": "senhora",
}
STREET_TYPES = {"rua", "avenida", "alameda", "travessa", "praca", "rodovia", "estrada", "viela", "largo", "beco", "via", "acesso", "anel", "contorno"}


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    words = re.sub(r"[^a-z0-9 ]", " ", text).split()
    return " ".join(ABBREVIATIONS.get(word, word) for word in words)


def core_name(name: str) -> str:
    words = normalize(name).split()
    return " ".join(words[1:]) if len(words) > 1 and words[0] in STREET_TYPES else " ".join(words)


def _overpass(query: str) -> dict:
    response = requests.post(OVERPASS_URL, data={"data": query},
                             headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=240)
    response.raise_for_status()
    return response.json()


def fetch_streets(municipality: str) -> tuple[list[dict], dict | None]:
    payload = _overpass(f"""
[out:json][timeout:200];
relation["boundary"="administrative"]["name"="{municipality}"]["admin_level"="8"]->.rel;
.rel map_to_area->.city;
(way["highway"]["name"](area.city); .rel;);
out geom;
""")
    streets, boundary = [], None
    for element in payload.get("elements", []):
        if element["type"] == "relation":
            boundary = _relation_geometry(element)
        elif element["type"] == "way" and len(element.get("geometry", [])) >= 2:
            streets.append({
                "name": element["tags"]["name"],
                "coords": [(point["lon"], point["lat"]) for point in element["geometry"]],
            })
    return streets, boundary


def _query_viacep(session: requests.Session, name: str, uf: str, city: str) -> list | None:
    query = name if len(name) >= 3 else f"Rua {name}"
    url = VIACEP_URL.format(uf=uf, city=quote(city), street=quote(query))
    for attempt in range(4):
        try:
            response = session.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
            if response.status_code == 400:
                return []
        except (requests.RequestException, ValueError):
            pass
        time.sleep(2 * (attempt + 1))
    return None  # falhou: fica fora do cache e é tentado de novo na próxima execução


def lookup_viacep(names: list[str], uf: str, city: str, cache_path: Path, workers: int = 3) -> dict[str, list]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cache: dict[str, list] = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    pending = [name for name in names if name not in cache]

    def save() -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cache_path)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_query_viacep, session, name, uf, city): name for name in pending}
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            if result is not None:
                cache[futures[future]] = result
            if index % 50 == 0:
                save()
    save()
    return cache


def street_neighborhoods(name: str, results: list[dict], city: str) -> set[str]:
    """Bairros dos registros do ViaCEP cujo logradouro é a mesma rua do OSM."""
    target_full, target_core = normalize(name), core_name(name)
    city_key = normalize(city)
    exact = {r["bairro"].strip() for r in results
             if normalize(r.get("localidade", "")) == city_key and r.get("bairro") and normalize(r.get("logradouro", "")) == target_full}
    if exact:
        return exact
    return {r["bairro"].strip() for r in results
            if normalize(r.get("localidade", "")) == city_key and r.get("bairro") and core_name(r.get("logradouro", "")) == target_core
            and len(target_core) >= 4}


def _sample_line(coords, step: float):
    from shapely.geometry import LineString

    line = LineString(coords)
    if line.length == 0:
        return []
    count = max(2, int(line.length // step) + 1)
    return [line.interpolate(i / (count - 1), normalized=True).coords[0] for i in range(count)]


KNOWN_NEAR_M = 350      # trecho homônimo perto de um bairro já localizado pertence a ele
GROUP_RADIUS_M = 600    # ruas de um mesmo loteamento ficam a poucas centenas de metros


def _street_components(streets: list[dict], to_metric) -> list[dict]:
    """Separa cada nome de rua em trechos fisicamente distintos (ex.: as várias 'Rua A')."""
    from shapely.geometry import LineString

    by_name: dict[str, list] = defaultdict(list)
    for street in streets:
        by_name[street["name"]].append(LineString([to_metric(*c) for c in street["coords"]]))
    components = []
    for name, lines in by_name.items():
        parent = list(range(len(lines)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                if lines[i].distance(lines[j]) < 60:
                    parent[find(i)] = find(j)
        groups: dict[int, list] = defaultdict(list)
        for i, line in enumerate(lines):
            groups[find(i)].append(line)
        for group in groups.values():
            points = [pt for line in group for pt in _sample_line(list(line.coords), SAMPLE_STEP_M)]
            xs, ys = zip(*points)
            components.append({"name": name, "points": points, "center": (sum(xs) / len(xs), sum(ys) / len(ys))})
    return components


def _label_street_points(streets: list[dict], candidates: dict[str, set], to_metric) -> tuple[list, int]:
    """Rotula pontos das ruas com o bairro dos Correios.

    1. trechos cujo nome tem um único bairro;
    2. trechos homônimos/compartilhados perto de um bairro já localizado;
    3. bairros ainda sem posição são fixados onde várias ruas candidatas a eles
       aparecem juntas (Rua A + Rua B + Rua C de um mesmo loteamento);
    repetindo 2–3 enquanto houver progresso.
    """
    import numpy as np
    from scipy.spatial import cKDTree

    components = [c for c in _street_components(streets, to_metric) if candidates.get(c["name"])]
    for comp in components:
        comp["options"] = set(candidates[comp["name"]])

    known: dict[str, list] = defaultdict(list)
    labeled: list[tuple[float, float, str]] = []

    def assign(comp: dict, bairro: str) -> None:
        comp["done"] = True
        known[bairro].extend(comp["points"])
        labeled.extend((x, y, bairro) for x, y in comp["points"])

    for comp in components:
        if len(comp["options"]) == 1:
            assign(comp, next(iter(comp["options"])))

    progress = True
    while progress:
        progress = False
        trees = {b: cKDTree(np.array(pts)) for b, pts in known.items()}
        for comp in components:
            if comp.get("done"):
                continue
            near = [b for b in comp["options"] if b in trees and trees[b].query(comp["center"])[0] <= KNOWN_NEAR_M]
            if not near:
                continue
            comp["done"] = True
            progress = True
            for x, y in comp["points"]:
                best = min(near, key=lambda b: trees[b].query((x, y))[0])
                known[best].append((x, y))
                labeled.append((x, y, best))

        pending = [c for c in components if not c.get("done")]
        unknown = defaultdict(list)
        for comp in pending:
            for b in comp["options"]:
                if b not in known:
                    unknown[b].append(comp)
        for bairro, comps in sorted(unknown.items(), key=lambda item: -len(item[1])):
            comps = [c for c in comps if not c.get("done")]
            if not comps:
                continue
            centers = np.array([c["center"] for c in comps])
            tree = cKDTree(centers)
            groups = [tree.query_ball_point(center, GROUP_RADIUS_M) for center in centers]
            best = max(groups, key=lambda g: len({comps[i]["name"] for i in g}))
            distinct_names = len({comps[i]["name"] for i in best})
            if distinct_names >= 2 or len(comps) == 1:
                for i in best:
                    assign(comps[i], bairro)
                progress = True
                break  # recalcula vizinhanças com o novo bairro localizado

    unresolved = 0
    trees = {b: cKDTree(np.array(pts)) for b, pts in known.items()}
    for comp in components:
        if comp.get("done"):
            continue
        options = [b for b in comp["options"] if b in trees]
        if not options:
            unresolved += 1
            continue
        for x, y in comp["points"]:
            labeled.append((x, y, min(options, key=lambda b: trees[b].query((x, y))[0])))
    return labeled, unresolved


def build_neighborhoods(streets: list[dict], boundary: dict | None, viacep: dict[str, list], city: str) -> tuple[dict, dict]:
    import numpy as np
    import shapely
    from pyproj import Transformer
    from shapely.geometry import MultiPoint, Point, shape
    from shapely.ops import polylabel, transform, unary_union
    from sklearn.cluster import DBSCAN

    to_metric = Transformer.from_crs("EPSG:4326", METRIC_CRS, always_xy=True).transform
    to_wgs = Transformer.from_crs(METRIC_CRS, "EPSG:4326", always_xy=True).transform

    candidates = {name: street_neighborhoods(name, viacep.get(name, []), city) for name in {s["name"] for s in streets}}

    labeled, unresolved = _label_street_points(streets, candidates, to_metric)

    # Remove pontos isolados de cada bairro (CEP genérico, homônimos, erro de cadastro).
    kept: list[tuple[float, float, str]] = []
    for label in {p[2] for p in labeled}:
        pts = np.array([(x, y) for x, y, l in labeled if l == label])
        if len(pts) < 12:  # loteamento pequeno: poucos pontos, nada a filtrar
            kept.extend((x, y, label) for x, y in pts)
            continue
        clusters = DBSCAN(eps=260, min_samples=3).fit_predict(pts)
        sizes = defaultdict(int)
        for c in clusters:
            if c >= 0:
                sizes[c] += 1
        if not sizes:
            continue
        biggest = max(sizes.values())
        keep = {c for c, n in sizes.items() if n >= max(3, biggest * 0.25)}
        kept.extend((x, y, label) for (x, y), c in zip(pts, clusters) if c in keep)

    # Um ponto por coordenada (o Voronoi não aceita duplicatas).
    unique: dict[tuple[int, int], tuple[float, float, str]] = {}
    for x, y, label in kept:
        unique.setdefault((round(x), round(y)), (x, y, label))
    points = list(unique.values())

    urban = unary_union([Point(x, y).buffer(URBAN_BUFFER_M, quad_segs=4) for x, y, _ in points])
    urban = urban.buffer(120).buffer(-120)  # fecha vãos pequenos entre quarteirões
    if boundary:
        urban = urban.intersection(transform(to_metric, shape(boundary)))

    cells = shapely.voronoi_polygons(MultiPoint([(x, y) for x, y, _ in points]), extend_to=urban, ordered=True)
    grouped: dict[str, list] = defaultdict(list)
    for (_, _, label), cell in zip(points, cells.geoms):
        grouped[label].append(cell)

    features = []
    for label, parts in grouped.items():
        geom = shapely.make_valid(unary_union(parts).intersection(urban)).buffer(0).simplify(6)
        polys = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon" and g.area >= 800]
        if not polys:
            continue
        geom = unary_union(polys)
        main = max(polys, key=lambda g: g.area)
        anchor = polylabel(main, tolerance=10)
        wgs = transform(to_wgs, geom)
        lon, lat = to_wgs(anchor.x, anchor.y)
        features.append({
            "type": "Feature",
            "properties": {
                "name": label,
                "kind": "bairro",
                "approximate": True,
                "source": "Correios (ViaCEP) + OpenStreetMap",
                "street_points": sum(1 for p in points if p[2] == label),
                "area_km2": round(geom.area / 1e6, 3),
                "label_lon": round(lon, 6),
                "label_lat": round(lat, 6),
            },
            "geometry": json.loads(shapely.to_geojson(shapely.set_precision(wgs, 1e-6))),
        })
    features.sort(key=lambda f: f["properties"]["name"])

    all_names = {b for bairros in candidates.values() for b in bairros}
    stats = {
        "street_names": len(candidates),
        "street_names_matched": sum(1 for b in candidates.values() if b),
        "street_segments_unresolved": unresolved,
        "bairros_in_viacep": len(all_names),
        "bairros_mapped": len(features),
        "bairros_without_area": sorted(all_names - {f["properties"]["name"] for f in features}),
    }
    return {
        "type": "FeatureCollection",
        "source": "Correios via ViaCEP (nomes) + OpenStreetMap contributors, ODbL (traçado das ruas)",
        "method": "Voronoi de pontos amostrados nas ruas, rotulados pelo bairro dos Correios",
        "retrieved_at": date.today().isoformat(),
        "features": features,
    }, stats


def build_cep_neighborhoods(municipality: str = "Pouso Alegre", uf: str = "MG",
                            output: str | Path = DEFAULT_OUTPUT, cache: str | Path = DEFAULT_CACHE) -> dict:
    streets, boundary = fetch_streets(municipality)
    viacep = lookup_viacep(sorted({s["name"] for s in streets}), uf, municipality, Path(cache))
    collection, stats = build_neighborhoods(streets, boundary, viacep, municipality)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    return {"output": str(path), "streets": len(streets), **stats}
