"""Hidrografia OSM e distancia de drenagem por celula H3."""
from __future__ import annotations

import json
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine


def fetch_osm_hydrology(settings: Settings | None = None) -> int:
    import osmnx as ox
    settings = settings or load_settings()
    with db_engine(settings) as engine, engine.connect() as conn:
        boundary = conn.execute(text("SELECT ST_AsGeoJSON(geom) FROM geo.city_boundary LIMIT 1")).scalar()
    if not boundary:
        raise RuntimeError("Limite municipal ausente.")
    from shapely.geometry import shape
    frame = ox.features_from_polygon(shape(json.loads(boundary)), {"waterway": True})
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty]
    with db_engine(settings) as engine, engine.begin() as conn:
        conn.execute(text("TRUNCATE geo.hydrology RESTART IDENTITY"))
        for _, row in frame.iterrows():
            conn.execute(text("INSERT INTO geo.hydrology(name, waterway_type, geom) VALUES (:name, :kind, ST_SetSRID(ST_GeomFromGeoJSON(:geom),4326))"), {
                "name": str(row.get("name") or ""), "kind": str(row.get("waterway") or "waterway"),
                "geom": json.dumps(row.geometry.__geo_interface__),
            })
    return len(frame)


def update_drainage_distances(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    with db_engine(settings) as engine, engine.begin() as conn:
        result = conn.execute(text("""
          INSERT INTO geo.risk_inputs(h3_id, drainage_distance_m, source_name, updated_at)
          SELECT g.h3_id,
            (SELECT MIN(ST_Distance(ST_Centroid(g.geom)::geography, h.geom::geography)) FROM geo.hydrology h),
            'openstreetmap_hydrology', now()
          FROM geo.grid_h3 g
          ON CONFLICT (h3_id) DO UPDATE SET drainage_distance_m=EXCLUDED.drainage_distance_m,
            source_name=EXCLUDED.source_name, updated_at=now()
        """))
    return result.rowcount or 0
