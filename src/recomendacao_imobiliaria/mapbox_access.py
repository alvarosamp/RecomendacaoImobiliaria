"""Tempo real de deslocamento (Mapbox Isochrone) como camada adicional de acesso.

Esta camada NAO substitui `dist_min_*_m` (distancia geodesica reta, calculada em
`geospatial.build_features`) nem entra na formula calibrada de `scoring.score_area`.
O score oficial e sua calibracao (`config/scoring_weights.json`) permanecem
baseados em linha reta ate uma decisao explicita de recalibrar com tempo real.

O resultado aqui e exposto apenas como um campo informativo adicional no
`explain` de cada celula: a que faixa de minutos a pe (5/10/15) pertence o
estabelecimento mais proximo de cada categoria, segundo a malha viaria real do
Mapbox — em vez da reta usada no score.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import requests
from shapely.geometry import Point, shape
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine

ISOCHRONE_URL = "https://api.mapbox.com/isochrone/v1/mapbox/{profile}/{lon},{lat}"
PROFILE = "walking"
# Faixas em minutos, da mais estreita para a mais ampla; o Mapbox retorna um
# poligono por contorno, cada um ja contendo os anteriores.
MINUTES_BANDS = (5, 10, 15)
TRAVEL_CATEGORIES = {
    "supermarket": "travel_min_supermarket",
    "pharmacy": "travel_min_pharmacy",
    "school": "travel_min_school",
}


class MapboxConfigError(RuntimeError):
    """Token do Mapbox ausente; a coleta nao pode ser executada."""


@dataclass(frozen=True)
class IsochroneBand:
    minutes: int
    geometry: dict  # GeoJSON Polygon/MultiPolygon


def fetch_isochrone_bands(
    lon: float,
    lat: float,
    settings: Settings | None = None,
    profile: str = PROFILE,
    minutes: tuple[int, ...] = MINUTES_BANDS,
) -> list[IsochroneBand]:
    """Busca os contornos de tempo real de deslocamento a partir de um ponto.

    Faz uma chamada por celula a Isochrone API do Mapbox. Exige `MAPBOX_TOKEN`
    configurado; nao ha modo offline nem cache aqui (ver `compute_travel_access`
    para a camada que grava o resultado no banco).
    """
    settings = settings or load_settings()
    if not settings.mapbox_token:
        raise MapboxConfigError("MAPBOX_TOKEN nao configurado; defina no .env antes de coletar.")

    response = requests.get(
        ISOCHRONE_URL.format(profile=profile, lon=lon, lat=lat),
        params={
            "contours_minutes": ",".join(str(m) for m in minutes),
            "polygons": "true",
            "access_token": settings.mapbox_token,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    bands = [
        IsochroneBand(minutes=int(feature["properties"]["contour"]), geometry=feature["geometry"])
        for feature in payload.get("features", [])
    ]
    return sorted(bands, key=lambda band: band.minutes)


def classify_band(point_lon: float, point_lat: float, bands: list[IsochroneBand]) -> int | None:
    """Menor faixa (minutos) cujo poligono contem o ponto; `None` se nenhuma contem.

    Pura e testavel sem rede: recebe os poligonos ja buscados (reais ou de teste).
    """
    point = Point(point_lon, point_lat)
    for band in sorted(bands, key=lambda b: b.minutes):
        if shape(band.geometry).contains(point):
            return band.minutes
    return None


def _nearest_poi_rows(conn, subcategories: tuple[str, ...]) -> dict[str, tuple[float, float] | None]:
    """Para cada h3_id, coordenada do POI mais proximo (reta) dentre as subcategorias dadas."""
    result = conn.execute(
        text(
            """
            SELECT DISTINCT ON (g.h3_id)
                g.h3_id,
                ST_X(p.geom) AS poi_lon,
                ST_Y(p.geom) AS poi_lat
            FROM geo.grid_h3 g
            JOIN geo.osm_pois p
              ON p.subcategory = ANY(:subcategories)
            ORDER BY g.h3_id, g.geom <-> p.geom
            """
        ),
        {"subcategories": list(subcategories)},
    )
    return {row.h3_id: (row.poi_lon, row.poi_lat) for row in result}


def compute_travel_access(settings: Settings | None = None) -> int:
    """Grava `travel_min_*` em `geo.features`: faixa de minutos a pe ate o POI mais proximo (reta).

    Uma chamada de isocrona por celula (nao por categoria): as tres faixas de
    cada celula sao buscadas uma vez e reusadas para classificar as tres
    categorias. Celulas sem POI da categoria, ou fora de todas as faixas,
    ficam com o campo nulo (sem o estabelecimento alcancavel a pe em 15 min,
    nao "zero minutos").
    """
    settings = settings or load_settings()
    category_pois: dict[str, dict[str, tuple[float, float] | None]] = {}
    cell_points: dict[str, tuple[float, float]] = {}

    with db_engine(settings) as engine:
        with engine.begin() as conn:
            for col_def in (f"{column} INT" for column in TRAVEL_CATEGORIES.values()):
                conn.execute(text(f"ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS {col_def}"))

            category_pois["supermarket"] = _nearest_poi_rows(conn, ("supermarket",))
            category_pois["pharmacy"] = _nearest_poi_rows(conn, ("pharmacy",))
            category_pois["school"] = _nearest_poi_rows(conn, ("school", "kindergarten"))

            cells = conn.execute(text("SELECT h3_id, ST_X(ST_Centroid(geom)) AS lon, ST_Y(ST_Centroid(geom)) AS lat FROM geo.grid_h3"))
            cell_points = {row.h3_id: (row.lon, row.lat) for row in cells}

    updated = 0
    with db_engine(settings) as engine:
        with engine.begin() as conn:
            for h3_id, (lon, lat) in cell_points.items():
                bands = fetch_isochrone_bands(lon, lat, settings)
                values = {}
                for category, column in TRAVEL_CATEGORIES.items():
                    poi = category_pois[category].get(h3_id)
                    values[column] = classify_band(*poi, bands) if poi else None
                conn.execute(
                    text(
                        f"""
                        UPDATE geo.features
                        SET {", ".join(f"{column} = :{column}" for column in TRAVEL_CATEGORIES.values())}
                        WHERE h3_id = :h3_id
                        """
                    ),
                    {**values, "h3_id": h3_id},
                )
                updated += 1
    return updated
