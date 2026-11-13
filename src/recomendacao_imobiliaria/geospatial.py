from __future__ import annotations

import dataclasses
import json

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .config import Settings, load_settings
from .db import db_engine
from .plan_director import evaluate_plan_compatibility
from .scoring import AreaFeatures, score_area
from .scoring_config import load_scoring_config


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
        # O limite municipal tem milhares de vertices e estoura o tamanho de
        # requisicao do Overpass (HTTP 413). A consulta usa o retangulo
        # envolvente (left, bottom, right, top); o recorte exato e feito abaixo.
        import os

        # Permite apontar para um espelho quando o servidor publico esta sem capacidade.
        if os.getenv("OVERPASS_URL"):
            ox.settings.overpass_url = os.environ["OVERPASS_URL"]
        pois = ox.features_from_bbox(geom.bounds, tags=POI_TAGS)
        if pois.empty:
            return 0

        from shapely.prepared import prep

        inside = prep(geom)
        pois = pois.reset_index()
        rows = []
        for _, row in pois.iterrows():
            point = row.geometry
            if point is None or point.is_empty:
                continue
            if point.geom_type != "Point":
                point = point.representative_point()
            if not inside.covers(point):
                continue

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
                            WHERE ST_DWithin(g.geom::geography, p.geom::geography, :count_radius_m) AND p.subcategory = 'supermarket'
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE ST_DWithin(g.geom::geography, p.geom::geography, :count_radius_m) AND p.subcategory = 'pharmacy'
                        )::INT,
                        COUNT(*) FILTER (
                            WHERE ST_DWithin(g.geom::geography, p.geom::geography, :count_radius_m) AND p.subcategory IN ('school', 'kindergarten')
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
                ),
                # Mercado, farmacia e escola (usados no score) sao contados no entorno
                # caminhavel. Demais contagens e as distancias minimas seguem em 5 km.
                {"count_radius_m": load_scoring_config().poi_count_radius_m},
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


def run_mvp_pipeline(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or load_settings()
    fetch_city_boundary(settings)
    grid_count = build_h3_grid(settings)
    poi_count = fetch_osm_pois(settings)
    feature_count = build_features(settings)
    # O zoneamento depende de grid/features e deve existir antes do score.
    from .zoning_import import default_zoning_file, import_zoning_file

    zoning = import_zoning_file(default_zoning_file(), settings=settings)
    score_count = score_database(settings)
    return {
        "grid_h3": grid_count,
        "pois": poi_count,
        "features": feature_count,
        "zoning": dataclasses.asdict(zoning),
        "scores": score_count,
    }


def _load_area_features(engine: Engine) -> list[AreaFeatures]:
    with engine.begin() as conn:
        # Camada opcional (mapbox_access.compute_travel_access); colunas podem
        # nao existir ainda em bancos que nunca rodaram essa coleta.
        for column in ("travel_min_supermarket", "travel_min_pharmacy", "travel_min_school"):
            conn.execute(text(f"ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS {column} INT"))
    query = """
        SELECT
            f.h3_id,
            f.zona,
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
            f.travel_min_supermarket,
            f.travel_min_pharmacy,
            f.travel_min_school,
            COALESCE(NOT ('residencial' = ANY(z.usos_vetados)), true) AS residential_allowed,
            COALESCE(NOT ('comercial' = ANY(z.usos_vetados)), true) AS commercial_allowed
        FROM geo.features f
        LEFT JOIN geo.zoning z ON z.zona = f.zona
    """
    frame = pd.read_sql(query, engine)
    frame = frame.merge(_latest_change(engine), on="h3_id", how="left")
    catchment, service_rates = _population_demand(engine, load_scoring_config().poi_count_radius_m)
    frame = frame.merge(catchment, on="h3_id", how="left")
    # Com zoneamento carregado, a tendencia de satelite so e interpretada dentro do
    # perimetro zoneado, e a linha de base sazonal vem dessas mesmas celulas.
    zoned = frame[frame["zona"].notna()]
    has_zoning = not zoned.empty
    baselines = slope_baselines(zoned if has_zoning else frame)
    zoning_official = _zoning_layer_is_official(engine)
    areas = []
    for row in frame.to_dict(orient="records"):
        clean = _clean_feature_row(row)
        clean.update(baselines)
        clean["service_rates"] = service_rates if service_rates and clean.get("population_catchment") is not None else None
        clean["growth_trend_reliable"] = bool(clean.get("zona")) or not has_zoning
        clean["zoning_official"] = zoning_official and bool(clean.get("zona"))
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


def _population_demand(engine: Engine, radius_m: float) -> tuple[pd.DataFrame, dict[str, float] | None]:
    """Populacao (Censo 2022) no raio de cada celula e estabelecimentos por habitante da cidade.

    Retorna (tabela vazia, None) quando o Censo ainda nao foi carregado; o score cai
    entao nas metas fixas por celula.
    """
    empty = pd.DataFrame(columns=["h3_id", "population_catchment"])
    with engine.connect() as conn:
        if conn.execute(text("SELECT to_regclass('geo.census_h3')")).scalar() is None:
            return empty, None
        total = float(conn.execute(text("SELECT COALESCE(SUM(population_2022), 0) FROM geo.census_h3")).scalar() or 0)
        if total <= 0:
            return empty, None
        catchment = pd.read_sql(text("""
            SELECT g1.h3_id, COALESCE(SUM(c.population_2022), 0) AS population_catchment
              FROM geo.grid_h3 g1
              LEFT JOIN geo.grid_h3 g2
                ON ST_DWithin(ST_Centroid(g1.geom)::geography, ST_Centroid(g2.geom)::geography, :radius)
              LEFT JOIN geo.census_h3 c ON c.h3_id = g2.h3_id
             GROUP BY g1.h3_id
        """), conn, params={"radius": float(radius_m)})
        counts = dict(conn.execute(text("""
            SELECT CASE WHEN subcategory IN ('school', 'kindergarten') THEN 'school' ELSE subcategory END, COUNT(*)
              FROM geo.osm_pois WHERE subcategory IN ('supermarket', 'pharmacy', 'school', 'kindergarten')
             GROUP BY 1
        """)).all())
    rates = {key: float(counts.get(key, 0)) / total for key in ("supermarket", "pharmacy", "school")}
    if not any(rates.values()):
        return empty, None
    return catchment, rates


def _latest_change(engine: Engine) -> pd.DataFrame:
    """Deteccao anual mais recente por celula; vazia se ainda nao foi rodada.

    Usa o nivel "provavel" (classificador) quando existe e, senao, o de alta
    confianca (regra).
    """
    empty = pd.DataFrame(columns=["h3_id", "change_fraction", "change_valid_fraction"])
    with engine.connect() as conn:
        if conn.execute(text("SELECT to_regclass('geo.urban_change_h3')")).scalar() is None:
            return empty
    with engine.begin() as conn:  # migracao idempotente de tabelas criadas antes do classificador
        conn.execute(text("ALTER TABLE geo.urban_change_h3 ADD COLUMN IF NOT EXISTS probable_area_ha DOUBLE PRECISION"))
        conn.execute(text("ALTER TABLE geo.urban_change_h3 ADD COLUMN IF NOT EXISTS probable_fraction DOUBLE PRECISION"))
    with engine.connect() as conn:
        return pd.read_sql(text("""
            SELECT h3_id, COALESCE(probable_fraction, changed_fraction) AS change_fraction,
                   valid_fraction AS change_valid_fraction
              FROM geo.urban_change_h3
             WHERE (year_after, year_before) = (
                   SELECT year_after, year_before FROM geo.urban_change_h3
                    ORDER BY year_after DESC, year_before DESC LIMIT 1)
        """), conn)


def slope_baselines(frame: pd.DataFrame) -> dict[str, float]:
    """Tendencia tipica da cidade (mediana) para descontar sazonalidade dos slopes."""
    result = {}
    for column, key in (("ndvi_slope_180", "ndvi_slope_baseline"), ("ndbi_slope_180", "ndbi_slope_baseline")):
        values = pd.to_numeric(frame[column], errors="coerce").dropna() if column in frame.columns else pd.Series(dtype=float)
        result[key] = float(values.median()) if len(values) else 0.0
    return result


def _zoning_layer_is_official(engine: Engine) -> bool:
    """Consulta a ultima carga de zoneamento registrada em ops.data_sources."""
    try:
        with engine.connect() as conn:
            value = conn.execute(text("""
                SELECT details ->> 'official' FROM ops.data_sources
                 WHERE dataset = 'zoning' AND status = 'ok'
                 ORDER BY collected_at DESC, id DESC LIMIT 1
            """)).scalar()
        return str(value).lower() == "true"
    except Exception:
        # Sem registro de proveniencia nao ha como afirmar que a camada e oficial.
        return False


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
