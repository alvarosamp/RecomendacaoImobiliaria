from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine
from .decision import enrich_opportunities


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
            f.dist_min_supermarket_m,
            f.dist_min_pharmacy_m,
            f.dist_min_school_m,
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
    return enrich_opportunities(frame)


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
