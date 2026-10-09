from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine
from .decision import enrich_opportunities


MARKET_RADIUS_M = 1000


def _add_reference_neighborhoods(frame: pd.DataFrame) -> pd.DataFrame:
    """Nomeia o bairro das células sem bairro oficial importado em ``geo.neighborhoods``.

    Usa a camada de referência do mapa (Correios/ViaCEP + OpenStreetMap). Antes o
    nome vinha do anúncio mais próximo do CSV local, que é sintético.
    """
    if frame.empty or not {"latitude", "longitude"}.issubset(frame.columns):
        return frame
    from .osm_neighborhoods import resolve_neighborhoods

    enriched = frame.copy()
    existing = enriched.get("neighborhood", pd.Series(index=enriched.index, dtype=object))
    missing = (existing.isna() | (existing.astype(str).str.strip() == "")).to_numpy()
    if missing.any():
        rows = enriched.loc[missing]
        resolved = resolve_neighborhoods(rows["longitude"].astype(float), rows["latitude"].astype(float))
        enriched.loc[missing, "neighborhood"] = [name for name, _ in resolved]
        enriched.loc[missing, "neighborhood_source"] = [source for _, source in resolved]
    return enriched


def _add_market_reference(frame: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Mediana de R$/m² de anúncios reais (``market.listings``) a até 1 km da célula.

    Sem anúncios reais importados, os campos ficam vazios: não há referência de mercado.
    """
    enriched = frame.copy()
    enriched["market_price_m2"] = np.nan
    enriched["market_comparables"] = 0
    if frame.empty or not {"latitude", "longitude"}.issubset(frame.columns):
        return enriched
    query = """
        SELECT ST_Y(geom) AS lat, ST_X(geom) AS lon, price_per_m2
          FROM market.listings
         WHERE geom IS NOT NULL AND price_per_m2 > 0
    """
    try:
        with db_engine(settings) as engine:
            listings = pd.read_sql(text(query), engine)
    except Exception:
        return enriched
    if listings.empty:
        return enriched
    lat0 = np.radians(float(frame["latitude"].mean()))
    cells = np.column_stack([frame["longitude"].to_numpy(float) * 111320 * np.cos(lat0), frame["latitude"].to_numpy(float) * 110540])
    points = np.column_stack([listings["lon"].to_numpy(float) * 111320 * np.cos(lat0), listings["lat"].to_numpy(float) * 110540])
    prices = listings["price_per_m2"].to_numpy(float)
    distances = np.sqrt(((cells[:, None, :] - points[None, :, :]) ** 2).sum(axis=2))
    for index, row in enumerate(distances):
        near = prices[row <= MARKET_RADIUS_M]
        if near.size:
            enriched.iat[index, enriched.columns.get_loc("market_price_m2")] = float(np.median(near))
            enriched.iat[index, enriched.columns.get_loc("market_comparables")] = int(near.size)
    return enriched


def load_score_table(settings: Settings | None = None) -> pd.DataFrame:
    settings = settings or load_settings()
    query = """
        SELECT
            s.h3_id,
            s.score_residencial,
            s.score_comercial,
            s.explain_json,
            s.updated_at AS score_updated_at,
            f.ndvi_mean_90,
            f.ndvi_slope_180,
            f.ndbi_mean_90,
            f.ndbi_slope_180,
            f.poi_supermarket_cnt,
            f.poi_pharmacy_cnt,
            f.poi_school_cnt,
            f.poi_hospital_cnt,
            f.poi_leisure_cnt,
            f.pop_estimated,
            lc.class_name AS land_cover_class,
            lc.reference_year AS land_cover_year,
            old_lc.class_name AS land_cover_class_2019,
            CASE WHEN old_lc.class_name IS NOT NULL THEN old_lc.class_name || ' → ' || lc.class_name END AS land_cover_transition,
            CASE WHEN old_lc.class_name IN ('pastagem', 'agricultura', 'outras lavouras', 'mosaico de usos')
                       AND lc.class_name IN ('area urbanizada', 'mosaico de usos')
                 THEN true ELSE false END AS observed_urban_expansion,
            f.dist_min_supermarket_m,
            f.dist_min_pharmacy_m,
            f.dist_min_school_m,
            f.dist_min_hospital_m,
            f.dist_min_park_m,
            f.neighborhood,
            f.neighborhood_source,
            r.susceptibility_score AS satellite_risk_score,
            r.alert_level AS satellite_risk_alert,
            r.confidence AS satellite_risk_confidence,
            r.components AS satellite_risk_components,
            (SELECT string_agg(DISTINCT o.process_type || ': ' || o.susceptibility_class, ' · ')
             FROM geo.official_susceptibility o
             WHERE ST_Intersects(o.geom, ST_Centroid(g.geom))) AS official_susceptibility,
            CASE
              WHEN EXISTS (SELECT 1 FROM geo.official_susceptibility o WHERE ST_Intersects(o.geom, ST_Centroid(g.geom)) AND lower(o.susceptibility_class) IN ('alta', 'alto')) THEN 'alto'
              WHEN EXISTS (SELECT 1 FROM geo.official_susceptibility o WHERE ST_Intersects(o.geom, ST_Centroid(g.geom)) AND lower(o.susceptibility_class) IN ('média', 'medio', 'médio')) THEN 'medio'
              WHEN EXISTS (SELECT 1 FROM geo.official_susceptibility o WHERE ST_Intersects(o.geom, ST_Centroid(g.geom))) THEN 'baixo'
              ELSE NULL
            END AS official_risk_level,
            ST_Y(ST_Centroid(g.geom)) AS latitude,
            ST_X(ST_Centroid(g.geom)) AS longitude,
            zs.source_name AS zoning_source_name,
            zs.source_uri AS zoning_source_uri,
            zs.reference_date AS zoning_reference_date,
            zs.collected_at AS zoning_collected_at,
            zs.reference_label AS zoning_reference_label
        FROM geo.scores s
        LEFT JOIN geo.features f ON f.h3_id = s.h3_id
        LEFT JOIN geo.risk_signals r ON r.h3_id = s.h3_id
        LEFT JOIN geo.land_cover_h3 lc ON lc.h3_id = s.h3_id
        LEFT JOIN geo.land_cover_h3_history old_lc ON old_lc.h3_id = s.h3_id AND old_lc.reference_year = 2019
        LEFT JOIN geo.grid_h3 g ON g.h3_id = s.h3_id
        LEFT JOIN LATERAL (
            SELECT source_name, source_uri, reference_date, collected_at,
                   details ->> 'reference_label' AS reference_label
              FROM ops.data_sources
             WHERE dataset = 'zoning' AND status = 'ok'
             ORDER BY collected_at DESC
             LIMIT 1
        ) zs ON true
        ORDER BY GREATEST(
            COALESCE(s.score_residencial, 0),
            COALESCE(s.score_comercial, 0)
        ) DESC
    """
    with db_engine(settings) as engine:
        frame = pd.read_sql(text(query), engine)
    return _add_market_reference(_add_reference_neighborhoods(enrich_opportunities(frame)), settings)


def explain_to_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return value
    else:
        payload = value

    recommendations = payload.get("main_recommendations", []) if isinstance(payload, dict) else []
    zoning = payload.get("zoning", {}) if isinstance(payload, dict) else {}
    legal = zoning.get("legal_notes")
    if not recommendations:
        base = "Sem recomendacao comercial prioritaria."
    else:
        base = " | ".join(f"{item.get('use')}: {item.get('why')}" for item in recommendations)
    if legal:
        return f"{base} Plano Diretor: {legal}"
    return base
