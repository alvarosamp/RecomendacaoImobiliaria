from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .config import Settings, load_settings
from .db import db_engine
from .plan_director import evaluate_plan_compatibility
from .scoring import AreaFeatures, score_area


POI_TAGS = {
    "amenity": [
        "school",
        "kindergarten",
        "pharmacy",
        "hospital",
        "clinic",
        "restaurant",
        "cafe",
        "bank",
        "atm",
        "fuel",
        "bus_station",
        "community_centre",
    ],
    "shop": [
        "supermarket",
        "convenience",
        "bakery",
        "mall",
        "pharmacy",
        "butcher",
        "greengrocer",
    ],
    "leisure": [
        "park",
        "garden",
        "sports_centre",
        "fitness_centre",
        "pitch",
        "playground",
    ],
    "public_transport": [
        "stop_position",
        "platform",
    ],
    "highway": [
        "bus_stop",
    ],
    "healthcare": [
        "pharmacy",
        "hospital",
        "clinic",
        "doctor",
        "dentist",
    ],
}


def fetch_city_boundary(settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    import osmnx as ox

    boundary = ox.geocode_to_gdf(settings.city_name)
    if boundary.empty:
        raise RuntimeError(f"Nenhum limite encontrado para {settings.city_name}.")

    geom = boundary.geometry.iloc[0]
    with db_engine(settings) as engine:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE geo.city_boundary RESTART IDENTITY CASCADE"))
            conn.execute(
                text(
                    """
                    INSERT INTO geo.city_boundary (name, geom)
                    VALUES (:name, ST_Multi(ST_SetSRID(ST_GeomFromText(:wkt), 4326)))
                    """
                ),
                {"name": settings.city_name, "wkt": geom.wkt},
            )


def build_h3_grid(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    import h3
    from shapely.geometry import Polygon

    with db_engine(settings) as engine:
        boundary = pd.read_sql(
            "SELECT ST_AsText(ST_Union(geom)) AS wkt FROM geo.city_boundary",
            engine,
        )
        if boundary.empty or not boundary.loc[0, "wkt"]:
            raise RuntimeError("Tabela geo.city_boundary esta vazia. Rode fetch-boundary primeiro.")

        from shapely import wkt

        geom = wkt.loads(boundary.loc[0, "wkt"])
        cells = sorted(_polygon_to_h3_cells(geom, settings.h3_res, h3))

        with engine.begin() as conn:
            conn.execute(text("TRUNCATE geo.grid_h3 CASCADE"))
            for cell in cells:
                polygon = Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])
                conn.execute(
                    text(
                        """
                        INSERT INTO geo.grid_h3 (h3_id, res, geom)
                        VALUES (:h3_id, :res, ST_SetSRID(ST_GeomFromText(:wkt), 4326))
                        ON CONFLICT (h3_id) DO UPDATE
                        SET res = EXCLUDED.res, geom = EXCLUDED.geom
                        """
                    ),
                    {"h3_id": cell, "res": settings.h3_res, "wkt": polygon.wkt},
                )

    return len(cells)


def fetch_osm_pois(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    import osmnx as ox

    with db_engine(settings) as engine:
        boundary = pd.read_sql(
            "SELECT ST_AsText(ST_Union(geom)) AS wkt FROM geo.city_boundary",
            engine,
        )
        if boundary.empty or not boundary.loc[0, "wkt"]:
            raise RuntimeError("Tabela geo.city_boundary esta vazia. Rode fetch-boundary primeiro.")

        from shapely import wkt

        geom = wkt.loads(boundary.loc[0, "wkt"])
        pois = ox.features_from_polygon(geom, tags=POI_TAGS)
        if pois.empty:
            return 0

        pois = pois.reset_index()
        rows = []
        for _, row in pois.iterrows():
            point = row.geometry
            if point is None or point.is_empty:
                continue
            if point.geom_type != "Point":
                point = point.representative_point()

            category, subcategory = _normalize_poi(row)
            if subcategory is None:
                continue

            rows.append(
                {
                    "name": _safe_text(row.get("name")),
                    "category": category,
                    "subcategory": subcategory,
                    "wkt": point.wkt,
                }
            )

        with engine.begin() as conn:
            conn.execute(text("TRUNCATE geo.osm_pois RESTART IDENTITY"))
            for row in rows:
                conn.execute(
                    text(
                        """
                        INSERT INTO geo.osm_pois (name, category, subcategory, geom)
                        VALUES (
                            :name,
                            :category,
                            :subcategory,
                            ST_SetSRID(ST_GeomFromText(:wkt), 4326)
                        )
                        """
                    ),
                    row,
                )

    return len(rows)


def build_features(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    with db_engine(settings) as engine:
        with engine.begin() as conn:
            # Auto-migrate: add extended columns for existing databases
            for col_def in [
                "poi_hospital_cnt INT",
                "poi_restaurant_cnt INT",
                "poi_bank_cnt INT",
                "poi_leisure_cnt INT",
                "dist_min_hospital_m DOUBLE PRECISION",
                "dist_min_park_m DOUBLE PRECISION",
                "dist_min_bus_stop_m DOUBLE PRECISION",
            ]:
                conn.execute(text(
                    f"ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS {col_def}"
                ))

            conn.execute(
                text(
                    """
                    INSERT INTO geo.features (
                        h3_id,
                        poi_supermarket_cnt,
                        poi_pharmacy_cnt,
                        poi_school_cnt,
                        poi_hospital_cnt,
                        poi_restaurant_cnt,
                        poi_bank_cnt,
                        poi_leisure_cnt,
                        dist_min_supermarket_m,
                        dist_min_pharmacy_m,
                        dist_min_school_m,
                        dist_min_hospital_m,
                        dist_min_park_m,
                        dist_min_bus_stop_m,
                        updated_at
                    )
                    SELECT
                        g.h3_id,
                        COUNT(*) FILTER (
                            WHERE p.subcategory = 'supermarket'
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.subcategory = 'pharmacy'
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.subcategory IN ('school', 'kindergarten')
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.subcategory = 'hospital'
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.subcategory IN ('restaurant', 'cafe')
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.subcategory IN ('bank', 'atm')
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE p.category = 'leisure'
                        )::INT,
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.subcategory = 'supermarket'),
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.subcategory = 'pharmacy'),
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.subcategory IN ('school', 'kindergarten')),
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.subcategory = 'hospital'),
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.category = 'leisure'
                              AND p.subcategory IN ('park', 'garden', 'pitch', 'playground')),
                        MIN(ST_Distance(g.geom::geography, p.geom::geography))
                            FILTER (WHERE p.subcategory = 'bus_stop'),
                        now()
                    FROM geo.grid_h3 g
                    LEFT JOIN geo.osm_pois p
                      ON ST_DWithin(g.geom::geography, p.geom::geography, 5000)
                    GROUP BY g.h3_id
                    ON CONFLICT (h3_id) DO UPDATE SET
                        poi_supermarket_cnt   = EXCLUDED.poi_supermarket_cnt,
                        poi_pharmacy_cnt      = EXCLUDED.poi_pharmacy_cnt,
                        poi_school_cnt        = EXCLUDED.poi_school_cnt,
                        poi_hospital_cnt      = EXCLUDED.poi_hospital_cnt,
                        poi_restaurant_cnt    = EXCLUDED.poi_restaurant_cnt,
                        poi_bank_cnt          = EXCLUDED.poi_bank_cnt,
                        poi_leisure_cnt       = EXCLUDED.poi_leisure_cnt,
                        dist_min_supermarket_m = EXCLUDED.dist_min_supermarket_m,
                        dist_min_pharmacy_m   = EXCLUDED.dist_min_pharmacy_m,
                        dist_min_school_m     = EXCLUDED.dist_min_school_m,
                        dist_min_hospital_m   = EXCLUDED.dist_min_hospital_m,
                        dist_min_park_m       = EXCLUDED.dist_min_park_m,
                        dist_min_bus_stop_m   = EXCLUDED.dist_min_bus_stop_m,
                        updated_at = now()
                    """
                )
            )

            result = conn.execute(text("SELECT COUNT(*) FROM geo.features"))
            return int(result.scalar_one())


def score_database(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    with db_engine(settings) as engine:
        features = _load_area_features(engine)
        with engine.begin() as conn:
            for item in features:
                result = score_area(item)
                conn.execute(
                    text(
                        """
                        INSERT INTO geo.scores (
                            h3_id,
                            score_residencial,
                            score_comercial,
                            explain_json,
                            updated_at
                        )
                        VALUES (
                            :h3_id,
                            :score_residencial,
                            :score_comercial,
                            CAST(:explain_json AS jsonb),
                            now()
                        )
                        ON CONFLICT (h3_id) DO UPDATE SET
                            score_residencial = EXCLUDED.score_residencial,
                            score_comercial = EXCLUDED.score_comercial,
                            explain_json = EXCLUDED.explain_json,
                            updated_at = now()
                        """
                    ),
                    {
                        "h3_id": result.h3_id,
                        "score_residencial": result.score_residencial,
                        "score_comercial": result.score_comercial,
                        "explain_json": json.dumps(result.explain),
                    },
                )

    return len(features)


def run_mvp_pipeline(settings: Settings | None = None) -> dict[str, int]:
    settings = settings or load_settings()
    fetch_city_boundary(settings)
    grid_count = build_h3_grid(settings)
    poi_count = fetch_osm_pois(settings)
    feature_count = build_features(settings)
    score_count = score_database(settings)
    return {
        "grid_h3": grid_count,
        "pois": poi_count,
        "features": feature_count,
        "scores": score_count,
    }


def _load_area_features(engine: Engine) -> list[AreaFeatures]:
    query = """
        SELECT
            f.h3_id,
            z.zona,
            f.ndvi_mean_90,
            f.ndvi_slope_180,
            f.ndbi_mean_90,
            f.ndbi_slope_180,
            f.poi_supermarket_cnt,
            f.poi_pharmacy_cnt,
            f.poi_school_cnt,
            f.dist_min_supermarket_m,
            f.dist_min_pharmacy_m,
            f.dist_min_school_m,
            COALESCE(NOT ('residencial' = ANY(z.usos_vetados)), true) AS residential_allowed,
            COALESCE(NOT ('comercial' = ANY(z.usos_vetados)), true) AS commercial_allowed
        FROM geo.features f
        LEFT JOIN geo.v_h3_zona z ON z.h3_id = f.h3_id
    """
    frame = pd.read_sql(query, engine)
    areas = []
    for row in frame.to_dict(orient="records"):
        clean = _clean_feature_row(row)
        residential = evaluate_plan_compatibility(clean.get("zona"), "residencial")
        commercial = evaluate_plan_compatibility(clean.get("zona"), "comercial")
        clean["residential_allowed"] = bool(clean["residential_allowed"]) and residential.allowed
        clean["commercial_allowed"] = bool(clean["commercial_allowed"]) and commercial.allowed
        clean["residential_plan_status"] = residential.status
        clean["commercial_plan_status"] = commercial.status
        clean["residential_plan_multiplier"] = residential.multiplier
        clean["commercial_plan_multiplier"] = commercial.multiplier
        clean["legal_notes"] = commercial.notes if commercial.status != "allowed" else residential.notes
        decisions = (residential, commercial)
        clean["legal_articles"] = tuple(dict.fromkeys(article for decision in decisions for article in decision.articles))
        clean["legal_parameters"] = {
            "residencial": residential.parameters,
            "comercial": commercial.parameters,
        }
        clean["legal_sources"] = tuple(commercial.sources or residential.sources)
        areas.append(AreaFeatures(**clean))
    return areas


def _clean_feature_row(row: dict[str, object]) -> dict[str, object]:
    values = {}
    for key, value in row.items():
        if pd.isna(value):
            values[key] = None
        else:
            values[key] = value
    return values


def _polygon_to_h3_cells(geom, resolution: int, h3_module) -> set[str]:
    if geom.geom_type == "Polygon":
        return set(_single_polygon_to_h3_cells(geom, resolution, h3_module))
    if geom.geom_type == "MultiPolygon":
        cells: set[str] = set()
        for polygon in geom.geoms:
            cells.update(_single_polygon_to_h3_cells(polygon, resolution, h3_module))
        return cells
    raise ValueError(f"Geometria nao suportada para H3: {geom.geom_type}")


def _single_polygon_to_h3_cells(polygon, resolution: int, h3_module) -> set[str]:
    outer = [(lat, lng) for lng, lat in list(polygon.exterior.coords)[:-1]]
    holes = [[(lat, lng) for lng, lat in list(ring.coords)[:-1]] for ring in polygon.interiors]
    h3_polygon = h3_module.LatLngPoly(outer, *holes)
    return set(h3_module.polygon_to_cells(h3_polygon, resolution))


def _normalize_poi(row) -> tuple[str | None, str | None]:
    amenity = _safe_text(row.get("amenity"))
    shop = _safe_text(row.get("shop"))
    leisure = _safe_text(row.get("leisure"))
    highway = _safe_text(row.get("highway"))
    public_transport = _safe_text(row.get("public_transport"))
    healthcare = _safe_text(row.get("healthcare"))

    if shop in {"supermarket", "convenience", "bakery", "mall", "butcher", "greengrocer"}:
        return "shop", shop
    if shop == "pharmacy":
        return "amenity", "pharmacy"
    if amenity in {
        "school", "kindergarten", "pharmacy", "hospital", "clinic",
        "restaurant", "cafe", "bank", "atm", "fuel", "bus_station",
        "community_centre",
    }:
        return "amenity", amenity
    if leisure in {"park", "garden", "sports_centre", "fitness_centre", "pitch", "playground"}:
        return "leisure", leisure
    if highway == "bus_stop":
        return "transport", "bus_stop"
    if public_transport in {"stop_position", "platform"}:
        return "transport", "bus_stop"
    if healthcare in {"pharmacy", "hospital", "clinic", "doctor", "dentist"}:
        hc_sub = healthcare if healthcare in {"pharmacy", "hospital"} else "clinic"
        return "amenity", hc_sub
    return None, None


def _safe_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)
