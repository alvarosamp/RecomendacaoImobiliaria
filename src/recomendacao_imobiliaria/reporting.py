from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine
from .decision import enrich_opportunities


@lru_cache(maxsize=1)
def _neighborhood_references() -> pd.DataFrame:
    """Centros de bairros obtidos da base local de anúncios.

    Enquanto a camada oficial de bairros não estiver no PostGIS, este é um
    enriquecimento explícito de referência — não uma delimitação oficial.
    """
    path = Path(__file__).resolve().parents[2] / "data" / "pouso_alegre_listings.csv"
    frame = pd.read_csv(path, usecols=["neighborhood", "lat", "lon"])
    frame = frame.dropna(subset=["neighborhood", "lat", "lon"])
    return frame.reset_index(drop=True)


def _add_reference_neighborhoods(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or not {"latitude", "longitude"}.issubset(frame.columns):
        return frame
    references = _neighborhood_references()
    if references.empty:
        return frame

    targets = frame[["latitude", "longitude"]].to_numpy(dtype=float)
    points = references[["lat", "lon"]].to_numpy(dtype=float)
    # Latitude/longitude estão na mesma cidade: a menor distância quadrática
    # é suficiente para escolher o bairro de referência mais próximo.
    distances = ((targets[:, None, :] - points[None, :, :]) ** 2).sum(axis=2)
    closest = distances.argmin(axis=1)
    enriched = frame.copy()
    existing = enriched.get("neighborhood", pd.Series(index=enriched.index, dtype=object))
    missing = existing.isna() | (existing.astype(str).str.strip() == "")
    enriched.loc[missing, "neighborhood"] = references.iloc[closest[missing.to_numpy()]]["neighborhood"].to_numpy()
    enriched["neighborhood_source"] = enriched.get("neighborhood_source", pd.Series(index=enriched.index, dtype=object)).fillna("referência por anúncios próximos")
    listings = pd.read_csv(Path(__file__).resolve().parents[2] / "data" / "pouso_alegre_listings.csv", usecols=["price", "area_m2", "neighborhood"])
    listings["price_per_m2"] = listings["price"] / listings["area_m2"].replace(0, np.nan)
    medians = listings.groupby("neighborhood")["price_per_m2"].median()
    enriched["market_price_m2"] = enriched["neighborhood"].map(medians)
    enriched["market_comparables"] = enriched["neighborhood"].map(listings.groupby("neighborhood").size()).fillna(0).astype(int)
    return enriched


def load_score_table(settings: Settings | None = None) -> pd.DataFrame:
    settings = settings or load_settings()
    query = """
        SELECT
            s.h3_id,
            s.score_residencial,
            s.score_comercial,
            s.explain_json,
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
            ST_X(ST_Centroid(g.geom)) AS longitude
        FROM geo.scores s
        LEFT JOIN geo.features f ON f.h3_id = s.h3_id
        LEFT JOIN geo.risk_signals r ON r.h3_id = s.h3_id
        LEFT JOIN geo.land_cover_h3 lc ON lc.h3_id = s.h3_id
        LEFT JOIN geo.land_cover_h3_history old_lc ON old_lc.h3_id = s.h3_id AND old_lc.reference_year = 2019
        LEFT JOIN geo.grid_h3 g ON g.h3_id = s.h3_id
        ORDER BY GREATEST(
            COALESCE(s.score_residencial, 0),
            COALESCE(s.score_comercial, 0)
        ) DESC
    """
    with db_engine(settings) as engine:
        frame = pd.read_sql(text(query), engine)
    return _add_reference_neighborhoods(enrich_opportunities(frame))


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
