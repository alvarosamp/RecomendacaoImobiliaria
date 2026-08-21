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
            f.dist_min_supermarket_m,
            f.dist_min_pharmacy_m,
            f.dist_min_school_m,
            f.dist_min_hospital_m,
            f.dist_min_park_m,
            f.neighborhood,
            f.neighborhood_source,
            ST_Y(ST_Centroid(g.geom)) AS latitude,
            ST_X(ST_Centroid(g.geom)) AS longitude
        FROM geo.scores s
        LEFT JOIN geo.features f ON f.h3_id = s.h3_id
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
