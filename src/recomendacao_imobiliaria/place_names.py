"""Bairro e principais ruas de cada celula H3, para dizer ONDE fica uma area.

* Ruas: vias nomeadas do OpenStreetMap (Overpass). Em cada celula, cada rua e
  ranqueada pela extensao dentro da celula multiplicada por um peso da classe da
  via (avenida e via arterial pesam mais que rua residencial). Ficam as 3 primeiras.
* Bairro: o poligono (Correios/OSM) com maior area dentro da celula, desde que cubra
  pelo menos ``MIN_OVERLAP`` dela; senao, a mesma regra de ``resolve_neighborhoods``
  (ponto central, proximidade, quadrante, zona rural).

Limite: os poligonos dos Correios sao estimados (``approximate``), e o OSM pode nao
ter todas as ruas nem os nomes atuais. O nome mostrado e uma referencia de
localizacao, nao um endereco oficial.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "RecomendacaoImobiliaria/1.0 (inteligencia territorial)"
DEFAULT_CACHE_DIR = Path("data/cache/places")
STREET_WEIGHT = {
    "motorway": 3.0, "trunk": 3.0, "primary": 3.0, "secondary": 2.5, "tertiary": 2.0,
    "unclassified": 1.2, "residential": 1.0, "living_street": 0.9, "pedestrian": 0.8, "road": 0.8,
}
MIN_OVERLAP = 0.15          # fracao da celula que o bairro precisa cobrir
MIN_STREET_METERS = 40      # ruas com menos que isto dentro da celula nao entram
TOP_STREETS = 3


# ---------------------------------------------------------------------------
# Ruas do OpenStreetMap
# ---------------------------------------------------------------------------

def _query(municipality: str) -> str:
    classes = "|".join(STREET_WEIGHT)
    name = municipality.replace('"', "")
    return (
        '[out:json][timeout:240];\n'
        f'relation["boundary"="administrative"]["name"="{name}"]["admin_level"="8"]->.rel;\n'
        '.rel map_to_area->.city;\n'
        f'way["highway"~"^({classes})$"]["name"](area.city);\n'
        'out geom;'
    )


def fetch_named_streets(municipality: str, cache_path: Path | None = None, *, refresh: bool = False,
                        progress=print) -> list[dict]:
    """Vias nomeadas do municipio: [{name, highway, coords:[(lon, lat), ...]}]."""
    import requests

    if cache_path and cache_path.exists() and not refresh:
        progress(f"  ruas: lidas do cache ({cache_path.name})")
        return json.loads(cache_path.read_text(encoding="utf-8"))
    payload, last_error = None, None
    for round_ in range(3):
        for url in OVERPASS_MIRRORS:
            try:
                response = requests.post(url, data={"data": _query(municipality)},
                                         headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=300)
                if response.status_code == 200 and response.text.lstrip().startswith("{"):
                    payload = response.json()
                    break
                last_error = f"{url} respondeu {response.status_code}"
            except requests.RequestException as exc:
                last_error = f"{url}: {exc}"
        if payload is not None:
            break
        progress(f"  Overpass indisponivel ({last_error}); tentando de novo...")
        time.sleep(20 * (round_ + 1))
    if payload is None:
        raise RuntimeError(f"Nao foi possivel baixar as ruas do OpenStreetMap: {last_error}")
    streets = [
        {"name": element["tags"]["name"].strip(), "highway": element["tags"]["highway"],
         "coords": [(point["lon"], point["lat"]) for point in element["geometry"]]}
        for element in payload.get("elements", [])
        if element.get("type") == "way" and len(element.get("geometry", [])) >= 2 and element["tags"].get("name", "").strip()
    ]
    if not streets:
        raise RuntimeError(f"Nenhuma rua nomeada encontrada para {municipality!r} no OpenStreetMap.")
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(streets, ensure_ascii=False), encoding="utf-8")
    return streets


def rank_streets_in_cells(streets: list[dict], cells, *, top: int = TOP_STREETS) -> dict[str, list[dict]]:
    """Principais ruas de cada celula. ``cells``: GeoDataFrame com ``h3_id``, em CRS metrico."""
    import geopandas as gpd
    from shapely.geometry import LineString

    lines = gpd.GeoDataFrame(
        {"name": [s["name"] for s in streets], "highway": [s["highway"] for s in streets]},
        geometry=[LineString(s["coords"]) for s in streets], crs=4326,
    ).to_crs(cells.crs)
    pieces = gpd.overlay(lines, cells[["h3_id", "geometry"]], how="intersection", keep_geom_type=True)
    pieces["meters"] = pieces.geometry.length
    pieces = pieces[pieces["meters"] >= 1]
    pieces["weight"] = pieces["highway"].map(STREET_WEIGHT).fillna(0.8)
    best_class = pieces.sort_values("weight", ascending=False).drop_duplicates(["h3_id", "name"])[["h3_id", "name", "highway"]]
    per_street = pieces.groupby(["h3_id", "name"], as_index=False).agg(meters=("meters", "sum"))
    per_street = per_street.merge(best_class, on=["h3_id", "name"])
    per_street = per_street[per_street["meters"] >= MIN_STREET_METERS]
    per_street["rank"] = per_street["meters"] * per_street["highway"].map(STREET_WEIGHT).fillna(0.8)
    result: dict[str, list[dict]] = {}
    for h3_id, group in per_street.sort_values("rank", ascending=False).groupby("h3_id"):
        result[h3_id] = [
            {"name": row.name, "highway": row.highway, "meters": int(round(row.meters))}
            for row in group.head(top).itertuples()
        ]
    return result


# ---------------------------------------------------------------------------
# Bairros
# ---------------------------------------------------------------------------

def assign_neighborhoods(cells_metric, cells_ll, collection: dict, *, min_overlap: float = MIN_OVERLAP) -> pd.DataFrame:
    """Bairro por maior area de sobreposicao; senao, a regra por ponto central."""
    import geopandas as gpd
    from shapely.geometry import shape

    from .osm_neighborhoods import resolve_neighborhoods

    features = [f for f in collection["features"]
                if f["properties"].get("kind") != "quadrante" and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
    rows: dict[str, tuple[str, str]] = {}
    if features:
        areas = gpd.GeoDataFrame(
            {"name": [f["properties"]["name"] for f in features],
             "source": ["cep" if f["properties"].get("approximate") else "limite" for f in features]},
            geometry=[shape(f["geometry"]) for f in features], crs=4326,
        ).to_crs(cells_metric.crs)
        areas["geometry"] = areas.geometry.make_valid()
        pieces = gpd.overlay(cells_metric[["h3_id", "geometry"]], areas, how="intersection", keep_geom_type=True)
        pieces["area"] = pieces.geometry.area
        cell_area = cells_metric.set_index("h3_id").geometry.area
        pieces["share"] = pieces["area"] / pieces["h3_id"].map(cell_area)
        # Poligonos "limite" (OSM) vencem os estimados dos Correios quando ha empate de cobertura.
        pieces["bonus"] = (pieces["source"] == "limite").astype(int)
        best = pieces[pieces["share"] >= min_overlap].sort_values(["share", "bonus"], ascending=False).drop_duplicates("h3_id")
        rows = {r.h3_id: (r.name, r.source) for r in best.itertuples()}
    missing = cells_ll[~cells_ll["h3_id"].isin(rows)]
    if len(missing):
        centers = missing.geometry.representative_point()
        resolved = resolve_neighborhoods(centers.x.tolist(), centers.y.tolist(), collection)
        for h3_id, (name, source) in zip(missing["h3_id"], resolved):
            rows[h3_id] = (name, source)
    return pd.DataFrame(
        [{"h3_id": h3_id, "neighborhood": name, "neighborhood_source": source} for h3_id, (name, source) in rows.items()]
    )


def street_label(streets: list[dict] | None) -> str | None:
    return " · ".join(item["name"] for item in streets) if streets else None


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def ensure_places_schema(conn) -> None:
    from sqlalchemy import text

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS geo.cell_places (
            h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
            streets JSONB NOT NULL DEFAULT '[]'::jsonb,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """))
    conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood TEXT"))
    conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood_source TEXT"))


def collect_place_names(settings=None, *, cache_dir: Path | str | None = None, refresh: bool = False,
                        progress=print) -> dict[str, object]:
    """Baixa as ruas, descobre bairro e ruas de cada celula e grava no banco."""
    import geopandas as gpd
    from sqlalchemy import text

    from .census_population import metric_crs
    from .config import load_settings
    from .data_registry import ensure_data_schema, record_data_source
    from .db import db_engine
    from .osm_neighborhoods import load_neighborhoods

    settings = settings or load_settings()
    municipality = settings.city_name.split(",")[0].strip()
    cache = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    streets = fetch_named_streets(municipality, cache / f"osm_streets_{settings.city_ibge_code}.json",
                                  refresh=refresh, progress=progress)

    cells_ll = _load_cells(settings)
    cells_metric = cells_ll.to_crs(metric_crs(cells_ll))
    progress(f"  {len(streets)} vias nomeadas; calculando ruas e bairro de {len(cells_ll)} celulas...")
    ranked = rank_streets_in_cells(streets, cells_metric)
    neighborhoods = assign_neighborhoods(cells_metric, cells_ll, load_neighborhoods())

    ensure_data_schema(settings)
    with db_engine(settings) as engine, engine.begin() as conn:
        ensure_places_schema(conn)
        for h3_id in cells_ll["h3_id"]:
            conn.execute(text("""
                INSERT INTO geo.cell_places (h3_id, streets, updated_at) VALUES (:h3, CAST(:streets AS jsonb), now())
                ON CONFLICT (h3_id) DO UPDATE SET streets = EXCLUDED.streets, updated_at = now()
            """), {"h3": h3_id, "streets": json.dumps(ranked.get(h3_id, []), ensure_ascii=False)})
        for row in neighborhoods.itertuples():
            conn.execute(text("""
                INSERT INTO geo.features (h3_id, neighborhood, neighborhood_source) VALUES (:h3, :name, :source)
                ON CONFLICT (h3_id) DO UPDATE SET neighborhood = EXCLUDED.neighborhood,
                    neighborhood_source = EXCLUDED.neighborhood_source
            """), {"h3": row.h3_id, "name": row.neighborhood, "source": row.neighborhood_source})

    report = {
        "municipality": municipality,
        "streets_downloaded": len(streets),
        "cells": int(len(cells_ll)),
        "cells_with_streets": len(ranked),
        "cells_without_streets": int(len(cells_ll) - len(ranked)),
        "distinct_street_names": len({item["name"] for items in ranked.values() for item in items}),
        "neighborhoods": int(neighborhoods["neighborhood"].nunique()),
        "neighborhood_sources": neighborhoods["neighborhood_source"].value_counts().to_dict(),
    }
    record_data_source(
        "place_names", "OpenStreetMap (vias nomeadas) + bairros Correios/OSM", source_uri=OVERPASS_MIRRORS[0],
        row_count=len(cells_ll), details=report, license_name="ODbL (OpenStreetMap contributors)",
        schema_version="place-names-v1", settings=settings,
    )
    return report


def _load_cells(settings):
    import geopandas as gpd
    from shapely import wkt

    from .db import db_engine

    with db_engine(settings) as engine:
        grid = pd.read_sql("SELECT h3_id, ST_AsText(geom) AS wkt FROM geo.grid_h3", engine)
    if grid.empty:
        raise RuntimeError("Grade H3 vazia. Rode fetch-boundary e build-grid antes.")
    return gpd.GeoDataFrame({"h3_id": grid["h3_id"]}, geometry=[wkt.loads(item) for item in grid["wkt"]], crs=4326)
